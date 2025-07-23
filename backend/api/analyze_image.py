# analyze_image.py: router for image analysis functionality

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
import base64
import uuid
import os
from fastapi.responses import JSONResponse, HTMLResponse
from aiofiles import open as aopen

from utils import CONFIG, ipm_process, object_detection, build_result_json, build_error_json

router = APIRouter(
    prefix="/analyze-image",
    tags=["analyze-image"],
)

TEMPLATE_PATH = "./templates/analyze_image.html"

@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}.png"
    file_location = os.path.join(CONFIG.UPLOAD_FOLDER, filename)
    content = await file.read()
    with open(file_location, "wb") as buffer:
        buffer.write(content)
    return {"message": "Upload successful", "filename": filename}

# User Interface for DEMO

@router.get("/ui", description="Analyze image from file or base64 string in User Interface")
async def analyze_image_ui(
    request: Request,
    file: UploadFile = File(None),
    base64_image: str = Form(None)
):
    html = ""
    async with aopen(TEMPLATE_PATH, "r") as f:
        html = await f.read()
    return HTMLResponse(html)

@router.post("/ui", description="Analyze image from file or base64 string in User Interface")
async def analyze_image(
    request: Request,
    file: UploadFile = File(None),
    base64_image: str = Form(None)
):
    try:
        if not file and not base64_image:
            raise HTTPException(status_code=400, detail="No image provided")

        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(CONFIG.UPLOAD_FOLDER, filename)

        # Handle file or base64 image
        if file:
            content = await file.read()
        else:
            try:
                header_removed = base64_image.split(",")[-1]
                content = base64.b64decode(header_removed)
            except Exception as decode_error:
                raise HTTPException(status_code=400, detail="Invalid base64 image") from decode_error

        # Save image
        with open(file_path, "wb") as f:
            f.write(content)

        # Call image processing modules
        ipm_path = ipm_process(file_path)
        offset, obstacles, warnings, encoded = object_detection(ipm_path)

        # Build and return result
        result = build_result_json(offset, obstacles, warnings, encoded)
        return JSONResponse(content=result)

    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content=build_error_json(he.detail))

    except Exception as e:
        return JSONResponse(status_code=500, content=build_error_json(str(e)))
