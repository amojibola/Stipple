Decision: Stipple algorithm visual quality improvement
Date: April 25 2026
Status: Deferred - will revisit after Layer 7

What we tried
Three rounds of algorithm improvements were made between
Layer 5 and Layer 6:

Round 1: Added CLAHE preprocessing, reduced shadow gamma,
expanded radius range from 2x to 4x.

Round 2: Added Sobel edge detection blended into dot
placement probability at 30 percent weight. Added position
jitter at 40 percent of step size. Updated defaults to
dot_size 3.5, density 0.9, black_point 28, highlights 0.2,
shadow_depth 0.85.

Round 3: Reduced CLAHE aggressiveness, rebalanced shadow
gamma, adjusted dot placement probability weights, added
luminance diagnostic for very dark source images. Updated
defaults to dot_size 2.5, density 0.7, black_point 15,
highlights 0.25, shadow_depth 0.6.

Current state
The algorithm produces dots and edge awareness is working
but portrait facial structure is still not clearly preserved.
The output does not yet match the desired artistic stipple
illustration style.

Files modified during this work
backend/app/services/stipple.py
frontend/src/app/editor/page.tsx

Why deferred
Further improvement requires more sophisticated approaches
such as Voronoi relaxation, face-aware regional processing,
or integration with a reference stipple style library. These
approaches require more development time than is appropriate
before completing Layer 6 and Layer 7.

When to revisit
After the app is deployed to Hostinger and the core product
is live. Algorithm quality improvement becomes a product
iteration task rather than a pre-launch blocker.