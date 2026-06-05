import cv2
import numpy as np
import torch
from skimage.transform import PiecewiseAffineTransform, warp

class PixelDriftFixNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "edited_image": ("IMAGE",),
                "method": (["flat_4_points", "mesh"], {"default": "flat_4_points", "tooltip": "flat_4_points gives better results and is faster. Mesh is experimental."}),
                "max_mesh_points": ("INT", {
                    "default": 400, 
                    "min": 100, 
                    "max": 10000, 
                    "step": 100,
                    "display": "number",
                    "tooltip": "Only used when method is set to 'mesh'. Higher values increase alignment accuracy but take longer. 400 = good/fast (~4s), 10000 = best quality (~90s)."
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("fixed_image",)
    FUNCTION = "fix_pixel_drift"
    CATEGORY = "image/processing"

    def fix_pixel_drift(self, source_image, edited_image, method, max_mesh_points):
        # ComfyUI image tensors are shapes: [B, H, W, C] and range 0.0 to 1.0
        b1, h1, w1, c1 = source_image.shape
        b2, h2, w2, c2 = edited_image.shape
        
        batch_size = min(b1, b2)
        output_tensors = []

        for i in range(batch_size):
            # 1. Convert PyTorch tensor to uint8 BGR for OpenCV processing
            img_orig_rgb = (source_image[i].cpu().numpy() * 255).astype(np.uint8)
            img_mod_rgb = (edited_image[i].cpu().numpy() * 255).astype(np.uint8)
            
            img_orig = cv2.cvtColor(img_orig_rgb, cv2.COLOR_RGB2BGR)
            img_mod = cv2.cvtColor(img_mod_rgb, cv2.COLOR_RGB2BGR)
            
            height, width = img_orig.shape[:2]
            
            # Grayscale conversion
            gray_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGR2GRAY)
            gray_mod = cv2.cvtColor(img_mod, cv2.COLOR_BGR2GRAY)
            
            # Ultra-Sensitive SIFT
            sift = cv2.SIFT_create(
                nfeatures=0,
                nOctaveLayers=3,
                contrastThreshold=0.01,
                edgeThreshold=20,
                sigma=1.6
            )
            
            kp_orig, des_orig = sift.detectAndCompute(gray_orig, None)
            kp_mod, des_mod = sift.detectAndCompute(gray_mod, None)
            
            # Fallback check if features are completely missing
            if des_orig is None or des_mod is None or len(kp_orig) < 10 or len(kp_mod) < 10:
                print(f"[PixelDriftFix] Warning: Not enough features found in batch {i}. Passing edited image through.")
                output_tensors.append(edited_image[i])
                continue

            # Match features
            bf = cv2.BFMatcher()
            matches = bf.knnMatch(des_mod, des_orig, k=2)
            
            # Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.80 * n.distance:
                        good_matches.append(m)
            
            if len(good_matches) < 10:
                print(f"[PixelDriftFix] Warning: Too few good matches ({len(good_matches)}) in batch {i}. Passing edited image through.")
                output_tensors.append(edited_image[i])
                continue

            # Extract coordinates
            pts_mod = np.float32([kp_mod[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
            pts_orig = np.float32([kp_orig[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)
            
            # RANSAC filter to get Homography matrix
            M, mask = cv2.findHomography(pts_mod, pts_orig, cv2.RANSAC, 5.0)
            
            if M is None or mask is None:
                print(f"[PixelDriftFix] Warning: Homography matrix computation failed in batch {i}.")
                output_tensors.append(edited_image[i])
                continue

            inliers_mod = pts_mod[mask.ravel() == 1]
            inliers_orig = pts_orig[mask.ravel() == 1]

            if len(inliers_mod) < 10:
                print(f"[PixelDriftFix] Warning: Too few static features ({len(inliers_mod)}) found after RANSAC filtering. Images should be similar.")
                output_tensors.append(edited_image[i])
                continue

            # Calculate Global Layer (always needed either as final output or as mesh fallback boundary)
            global_warped = cv2.warpPerspective(
                img_mod, M, (width, height), borderMode=cv2.BORDER_REPLICATE
            )

            # Route calculation based on selected UI dropdown method
            if method == "mesh":
                try:
                    # Construct rigid outer boundary anchors
                    edge_points = []
                    step_size = 30  
                    for x in range(0, width, step_size):
                        edge_points.append([x, 0])
                        edge_points.append([x, height - 1])
                    for y in range(0, height, step_size):
                        edge_points.append([0, y])
                        edge_points.append([width - 1, y])
                        
                    edge_points.extend([[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]])
                    corners = np.array(edge_points, dtype=np.float32).reshape(-1, 2)
                    corners = np.unique(corners, axis=0)  

                    corners_proj = cv2.perspectiveTransform(corners.reshape(-1, 1, 2), M).reshape(-1, 2)
                    corners_proj[:, 0] = np.clip(corners_proj[:, 0], 0, width - 1)
                    corners_proj[:, 1] = np.clip(corners_proj[:, 1], 0, height - 1)

                    final_mod = np.vstack([inliers_mod, corners])
                    final_orig = np.vstack([inliers_orig, corners_proj])

                    # Cap points based on user's slider choice
                    if len(final_mod) > max_mesh_points:
                        idx = np.linspace(0, len(final_mod) - 1, max_mesh_points, dtype=int)
                        final_mod = final_mod[idx]
                        final_orig = final_orig[idx]
                    print(f"PixelDriftFix: using mesh with {len(final_mod)} points")

                    # Adaptive API initialization for scikit-image cross-version compatibility
                    if hasattr(PiecewiseAffineTransform, 'from_estimate'):
                        tform = PiecewiseAffineTransform.from_estimate(final_orig, final_mod)
                    else:
                        tform = PiecewiseAffineTransform()
                        tform.estimate(final_orig, final_mod)
                    
                    local_warped_raw = warp(img_mod, tform, output_shape=(height, width), order=1, mode='edge')
                    local_warped = (local_warped_raw * 255).astype(np.uint8)
                    
                    coverage_input = np.ones((height, width), dtype=np.float32)
                    coverage_warped = warp(coverage_input, tform, output_shape=(height, width), order=0, cval=0)
                    valid_mesh_mask = coverage_warped > 0.5
                    
                    final_img = np.where(valid_mesh_mask[:, :, None], local_warped, global_warped)
                except Exception as warp_error:
                    print(f"[PixelDriftFix] Error during dense warping: {warp_error}. Falling back to linear matrix transform.")
                    final_img = global_warped
            else:
                # Default "flat_4_points" path: clean global warp matrix execution
                print("PixelDriftFix: using flat_4_points")
                final_img = global_warped

            # 2. Convert final BGR image back to RGB and then normalize PyTorch Tensor [H, W, C]
            final_rgb = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
            out_tensor = torch.from_numpy(final_rgb).float() / 255.0
            output_tensors.append(out_tensor)

        # Stack separate batch images back into uniform [B, H, W, C] format
        fixed_image_batch = torch.stack(output_tensors, dim=0)
        return (fixed_image_batch,)