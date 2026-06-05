from .pixel_drift_fix_node import PixelDriftFixNode

NODE_CLASS_MAPPINGS = {
    "PixelDriftFix": PixelDriftFixNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PixelDriftFix": "Pixel Drift Fix"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']