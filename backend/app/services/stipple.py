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


def stipple_image(
    source_path: str,
    params: dict,
    output_size: tuple,
    seed: int,
) -> np.ndarray:
    _validate_params(params)

    rng = np.random.default_rng(seed)

    gray = validate_and_load(source_path)
    gray = cv2.resize(gray, output_size, interpolation=cv2.INTER_AREA)
    img_norm = gray.astype(np.float32) / 255.0

    dot_size = params["dot_size"]
    density = params["density"]
    black_point = params["black_point"]
    highlights = params["highlights"]
    shadow_depth = params["shadow_depth"]

    bp = black_point / 100.0
    img_mapped = np.clip((img_norm - bp) / (1.0 - bp + 1e-6), 0.0, 1.0)
    img_mapped = np.power(img_mapped, 1.0 + shadow_depth)
    img_mapped = img_mapped + highlights * (1.0 - img_mapped) ** 2
    img_mapped = np.clip(img_mapped, 0.0, 1.0)

    step = max(1, int(dot_size * 2 / density))
    h, w = output_size[1], output_size[0]

    ys = np.arange(0, h, step)
    xs = np.arange(0, w, step)
    grid_x, grid_y = np.meshgrid(xs, ys)

    gy = np.clip(grid_y, 0, h - 1).astype(int)
    gx = np.clip(grid_x, 0, w - 1).astype(int)
    luminance = img_mapped[gy, gx]

    rand_matrix = rng.random(luminance.shape)
    place_dot = rand_matrix > luminance

    base_radius = max(1, int(dot_size))
    radius_map = np.where(
        place_dot,
        np.clip(
            (base_radius * (1.0 - luminance * 0.5)).astype(int),
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
