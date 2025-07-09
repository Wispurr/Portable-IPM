# app.py: A FastAPI application for a simple user management system

from typing import Union
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel
# for server configuration and running the FastAPI app
from uvicorn import Config, Server
import os
# for handling file uploads and responses
from fastapi.responses import JSONResponse, HTMLResponse
# for base64 encoding and decoding
import base64
# for generating unique filenames
import uuid
# Templates and static files for serving HTML and static content
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Importing configuration settings
from utils.config import CONFIG
# Importing utility functions for JSON formatting
from utils.api_formatter import build_result_json, build_error_json  # Importing utility functions for API formatting

# initialize FastAPI application
app = FastAPI()
templates = Jinja2Templates(directory="./templates")
app.mount("/static", StaticFiles(directory="./static"), name="static")
app.mount("/uploads", StaticFiles(directory="./uploads"), name="uploads")

# Define a User model
class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None

# Constants for file upload
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# for Debug(when IPM process and object detection are not available)
if CONFIG.debug:
    def ipm_process(image_path: str) -> str:
        return image_path

    def object_detection(image_path: str) -> tuple:
        offset = {"x": 12, "y": -2}
        obstacles = [
            {"type": "cone", "x": 120, "y": 220},
            {"type": "pedestrian", "x": 300, "y": 180}
        ]
        warnings = ["obstacle-nearby", "left-deviation"]
        return offset, obstacles, warnings

@app.post("/upload-image/", tags=["analyze-image"]) #upload image function
async def upload_image(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_FOLDER}/image.png"
    with open(file_location , "wb") as buffer:
        content = await file.read()  # Read file content asynchronously
        buffer.write(content)  
    return{"message": "Upload successful", "filename": file.filename}

@app.post("/analyze-image-ui", tags=["analyze-image"])
async def analyze_image(
    request: Request,
    file: UploadFile = File(None),               # 修改為可選
    base64_image: str = Form(None)               # 兩者皆為 Optional
):
    try:
        if not file and not base64_image:
            raise HTTPException(status_code=400, detail="No image provided")

        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # 解析圖片來源
        if file:
            content = await file.read()
        else:
            try:
                header_removed = base64_image.split(",")[-1]
                content = base64.b64decode(header_removed)
            except Exception as decode_error:
                raise HTTPException(status_code=400, detail="Invalid base64 image") from decode_error

        # 儲存圖片
        with open(file_path, "wb") as f:
            f.write(content)

        # 呼叫影像處理模組
        ipm_path = ipm_process(file_path)
        offset, obstacles, warnings = object_detection(ipm_path)

        # 封裝結果
        result = build_result_json(offset, obstacles, warnings)
        return JSONResponse(content=result)

    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content=build_error_json(he.detail))

    except Exception as e:
        return JSONResponse(status_code=500, content=build_error_json(str(e)))

# index route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    files = os.listdir(UPLOAD_FOLDER)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "uploads": files
    })
    return {"message": "Welcome to the IPM Model API!"}


# Run the FastAPI application using Uvicorn server
def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()