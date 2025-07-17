from utils import CONFIG

# for Debug(when IPM process and object detection are not available)
if CONFIG.debug:
    def ipm_process(image_path: str) -> str:
        return image_path

    def object_detection() -> tuple:
        offset = {"x": 12, "y": -2}
        obstacles = [
            {"type": "cone", "x": 120, "y": 220},
            {"type": "pedestrian", "x": 300, "y": 180}
        ]
        warnings = ["obstacle-nearby", "left-deviation"]
        return offset, obstacles, warnings
