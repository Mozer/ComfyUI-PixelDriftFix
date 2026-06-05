# ComfyUI-PixelDriftFix

A ComfyUI custom node designed to eliminate pixel drifting, stretching, and minor cropping inconsistencies between a source image and an edited/upscaled version. It automatically realigns pixels to ensure structural consistency.

## Features
* **Perfect Alignment:** Fixes framing changes introduced by complex image-to-image or upscaling workflows.
* **Dual Alignment Modes:**
  * `linear_4_points`: (recommended) A lightning-fast global perspective transform using homography matrices with 4 points (Best for most use cases, ~4s processing).
  * `mesh`: (experimental, worse and slow) A dense, non-linear piecewise affine warping mesh for complex local deformations, uses 100-10000 points.

## Notes
- resizes output image to the exact size of source image
- source and output image should be similar, should have at least 10 similar points.
- can add tiny strip of dupilicate pixels on the edges

## Installation

Install via git URL in comfy manager. Restart.

## Workflow
Workflows are in workflows folder.

This node can be used for old image restoration. Workflow for klein-9b + pixel_drift_fix + blend_with_original is in Workflows folder.
