import cv2
import numpy as np
from PIL import Image, ImageFile
import hashlib
import json

Image.MAX_IMAGE_PIXELS = 8_000_000  # module-level — always active before any open()
ImageFile.LOAD_TRUNCATED_IMAGES = False

MAX_DIMENSION = 4000

# Allowed parameter ranges — enforced here as defense in depth
_PARAM_RANGES = {
    "dot_size":    (0.5, 10.0),
    "density":     (0.1, 1.0),
    "black_point": (0,   100),
    "highlights":  (0.0, 1.0),
    "shadow_depth":(0.0, 1.0),
}


def validate_and_load(source_path: str) -> np.ndarray:
    with Image.open(source_path) as img:
        w, h = img.size
        if w > MAX_DIMENSION or h > MAX_DIMENSION:
            raise ValueError(f"Image {w}x{h} exceeds max {MAX_DIMENSION}px per side")
        mp = (w * h) / 1_000_000
        if mp > 8.0:
            raise ValueError(f"Image is {mp:.1f}MP, max is 8MP")
        img.load()  # triggers decompression bomb check
        return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)


def load_for_preview(source_path: str, preview_width: int) -> np.ndarray:
    """Load and resize image to preview_width before numpy conversion.

    PIL thumbnail resizes in-place before any large array is created, keeping
    memory proportional to the preview size rather than the source size.
    """
    with Image.open(source_path) as img:
        w, h = img.size
        if w > MAX_DIMENSION or h > MAX_DIMENSION:
            raise ValueError(f"Image {w}x{h} exceeds max {MAX_DIMENSION}px per side")
        mp = (w * h) / 1_000_000
        if mp > 8.0:
            raise ValueError(f"Image is {mp:.1f}MP, max is 8MP")
        preview_height = max(1, int(preview_width * h / w))
        img.thumbnail((preview_width, preview_height), Image.LANCZOS)
        img.load()  # triggers decompression bomb check on the resized image
        return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)


def compute_seed(file_id: str, params: dict) -> int:
    raw = file_id + json.dumps(params, sort_keys=True)
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _validate_params(params: dict) -> None:
    for key, (lo, hi) in _PARAM_RANGES.items():
        val = params.get(key)
        if val is None:
            raise ValueError(f"Missing required parameter: {key}")
        if not (lo <= val <= hi):
            raise ValueError(f"{key}={val} is outside allowed range [{lo}, {hi}]")


def _apply_stipple_effect(gray: np.ndarray, params: dict, rng: np.random.Generator) -> np.ndarray:
    """Apply the stipple dot effect to a grayscale image already at output size."""
    dot_size     = params["dot_size"]
    density      = params["density"]
    black_point  = params["black_point"]
    highlights   = params["highlights"]
    shadow_depth = params["shadow_depth"]

    # ── 1. Gentle luminance normalization ─────────────────────────────────────
    # Global min-max stretch ensures the full [0, 255] range is used without the
    # local contrast amplification that CLAHE (clipLimit=2.0) was applying to
    # portrait skin tones. CLAHE was pushing skin midtones toward shadows,
    # collapsing the luminance distribution before dot placement.
    normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

    # Lift inherently dark images so the pipeline does not collapse to solid dots.
    # The mean is checked on the normalized array — no log of this value.
    mean_lum = float(np.mean(normalized))
    if mean_lum < 80:
        normalized = cv2.add(normalized, np.full_like(normalized, 20))

    # ── 2. Edge weight map (Sobel) ────────────────────────────────────────────
    # Gradient magnitude on the normalized image captures feature boundaries
    # (eyes, nose, lips, hair) that should carry elevated dot probability even
    # in midtone areas. Normalized to [0, 1]; zero on flat images.
    grad_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
    mag_max = magnitude.max()
    edge_weight = (magnitude / mag_max) if mag_max > 0 else magnitude

    img_norm = normalized.astype(np.float32) / 255.0

    # ── 3. Tone mapping ───────────────────────────────────────────────────────
    bp = black_point / 100.0
    img_mapped = np.clip((img_norm - bp) / (1.0 - bp + 1e-6), 0.0, 1.0)

    # Capped shadow gamma: power stays in [1.0, 1.25] — mild enough to preserve
    # facial midtones. The old 0.45 multiplier pushed this to 1.45, which was
    # collapsing the face midtone range into near-black.
    img_mapped = np.power(img_mapped, 1.0 + shadow_depth * 0.25)

    img_mapped = img_mapped + highlights * (1.0 - img_mapped) ** 2
    img_mapped = np.clip(img_mapped, 0.0, 1.0)

    # ── 4. Grid with position jitter ─────────────────────────────────────────
    h, w = gray.shape[:2]
    step = max(1, int(dot_size * 1.5 / density))

    ys = np.arange(0, h, step)
    xs = np.arange(0, w, step)
    grid_x, grid_y = np.meshgrid(xs, ys)

    # Jitter breaks the mechanical grid artifact and makes dots look hand-placed.
    # Offsets are drawn first so the rng call order is stable for determinism.
    jitter_amount = step * 0.4
    jitter_y = rng.uniform(-jitter_amount, jitter_amount, size=grid_y.shape)
    jitter_x = rng.uniform(-jitter_amount, jitter_amount, size=grid_x.shape)
    gy = np.clip(np.round(grid_y + jitter_y).astype(int), 0, h - 1)
    gx = np.clip(np.round(grid_x + jitter_x).astype(int), 0, w - 1)

    luminance  = img_mapped[gy, gx]
    edge_at_pt = edge_weight[gy, gx]

    # ── 5. Dot placement with edge-boosted probability and density scaling ────
    # Rebalanced: edges contribute 40 %, luminance inversion 60 %.
    # density_factor scales back global dot saturation — without this, high
    # placement probability combined with large dot radii fills the canvas solid.
    placement_prob = (1.0 - luminance) * 0.6 + edge_at_pt * 0.4
    density_factor = density * 0.7
    rand_matrix = rng.random(luminance.shape)
    place_dot = rand_matrix < (placement_prob * density_factor)

    # ── 6. Variable radius ────────────────────────────────────────────────────
    base_radius = max(1, int(dot_size))
    # dark_factor = 1 in absolute shadows, 0 in pure highlights.
    # Radius spans 4× (shadow 1.7× base → highlight 0.4× base).
    dark_factor = 1.0 - luminance
    radius_map = np.where(
        place_dot,
        np.clip(
            (base_radius * (0.4 + dark_factor * 1.3)).astype(int),
            1,
            base_radius * 2,
        ),
        0,
    )

    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    dot_rows, dot_cols = np.where(place_dot)
    dot_cx = gx[dot_rows, dot_cols]
    dot_cy = gy[dot_rows, dot_cols]
    dot_radii = radius_map[dot_rows, dot_cols]

    # Loop over unique RADIUS VALUES (bounded by dot_size*2, typically < 20),
    # not over individual dots (potentially hundreds of thousands).
    # cv2.dilate with an ellipse kernel does all per-pixel work at C level.
    for r in np.unique(dot_radii).tolist():
        if r == 0:
            continue
        dot_mask = np.zeros((h, w), dtype=np.uint8)
        positions = dot_radii == r
        dot_mask[dot_cy[positions], dot_cx[positions]] = 255
        kernel_size = 2 * int(r) + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(dot_mask, kernel)
        canvas[dilated > 0] = [0, 0, 0]

    return canvas


def stipple_image(
    source_path: str,
    params: dict,
    output_size: tuple,
    seed: int,
) -> np.ndarray:
    """Full-resolution stipple render. Used by the Celery worker."""
    _validate_params(params)
    rng = np.random.default_rng(seed)
    gray = validate_and_load(source_path)
    gray = cv2.resize(gray, output_size, interpolation=cv2.INTER_AREA)
    return _apply_stipple_effect(gray, params, rng)


def stipple_preview_image(
    source_path: str,
    params: dict,
    preview_width: int,
    seed: int,
) -> np.ndarray:
    """Preview stipple render. Resizes the source to preview_width before any
    numpy allocation, keeping memory proportional to the preview size."""
    _validate_params(params)
    rng = np.random.default_rng(seed)
    gray = load_for_preview(source_path, preview_width)
    return _apply_stipple_effect(gray, params, rng)
