from utils import CONFIG
import cv2
import base64
from fastapi import HTTPException

# for Debug(when IPM process and object detection are not available)
if CONFIG.debug:
    def ipm_process(image_path: str) -> str:
        return image_path

    def object_detection(ipm_path: str) -> tuple:
        # Read image using OpenCV
        img = cv2.imread(ipm_path)
        if img is None:
            raise HTTPException(status_code=400, detail=f"Failed to load image from {ipm_path}")

        success, buffer = cv2.imencode(".png", img)
        if not success:
            raise RuntimeError("Failed to encode image")

        #  Encode to base64 string
        encoded = base64.b64encode(buffer).decode("utf-8")
        encoded_str = f"data:image/png;base64,{encoded}"

        offset = {"x": 12, "y": -2}
        obstacles = [
            {"type": "cone", "x": 120, "y": 220},
            {"type": "pedestrian", "x": 300, "y": 180}
        ]
        warnings = ["obstacle-nearby", "left-deviation"]
        return offset, obstacles, warnings, encoded_str
