# ComfyUI-PixelDriftFix

A ComfyUI custom node designed to eliminate pixel drifting, stretching, and minor cropping inconsistencies between a source image and an edited/upscaled version. It automatically realigns pixels to ensure structural consistency.

## Features
* **Perfect Alignment:** Fixes framing changes introduced by complex image-to-image or upscaling workflows.
* **Dual Alignment Modes:**
  * `flat_4_points`: (recommended) A lightning-fast global perspective transform using homography matrices with 4 points (Best for most use cases, ~4s processing).
  * `mesh`: (experimental, worse and slow) A dense, non-linear piecewise affine warping mesh for complex local deformations, uses 100-10000 points.

## Notes
- resizes output image to the exact size of source image
- source and output image should be similar, should have at least 10 similar points.
- can add tiny strip of dupilicate pixels on the edges

## Installation

Install via git URL in comfy manager. Restart.

## Workflow
<img width="1207" height="881" alt="_Unsaved Workflow - ComfyUI - Google Chrome 05 06 2026 16_59_38" src="https://github.com/user-attachments/assets/69c727f0-43a5-4fdf-9e28-3a634ad1f659" />

Workflows are in workflows folder.

This node can also be used for old image restoration. Workflow for klein-9b + pixel_drift_fix + blend_with_original is in Workflows folder.

## Demo video

https://github.com/user-attachments/assets/7341c4f8-5f28-4823-8682-1745060fdada


