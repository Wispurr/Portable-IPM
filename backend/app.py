# app.py: A FastAPI application for a simple user management system

from typing import Union
<<<<<<< HEAD
from fastapi import FastAPI, UploadFile, File, WebSocket
=======
from fastapi import FastAPI, Request
>>>>>>> abe2e4da0e996b229e96e267be989d7d909bd1c8
from pydantic import BaseModel
# for server configuration and running the FastAPI app
from uvicorn import Config, Server
import os
<<<<<<< HEAD
import base64
import asyncio
import cv2
=======
# for handling file uploads and responses
from fastapi.responses import JSONResponse, HTMLResponse
# Templates and static files for serving HTML and static content
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# HTML Exception
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils import CONFIG, build_result_json, build_error_json, HTTPExceptionLoading  # Importing utility functions for API formatting
from api import analyze_image_router  # Importing the image analysis router
>>>>>>> abe2e4da0e996b229e96e267be989d7d909bd1c8

# initialize FastAPI application
app = FastAPI()
templates = Jinja2Templates(directory="./templates")
app.mount("/static", StaticFiles(directory="./static"), name="static")
app.mount("/uploads", StaticFiles(directory="./uploads"), name="uploads")
app.include_router(analyze_image_router)

# Define a User model
class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None
    
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/upload-image/") #upload image function
async def upload_image(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_FOLDER}/image.png"
    with open(file_location , "wb") as buffer:
        content = await file.read()  # Read file content asynchronously
        buffer.write(content)  
    return{"message": "Upload successful", "filename": file.filename}

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    cap = cv2.VideoCapture(0)  # Open the default camera
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            await websocket.send_text(img_b64)
            await asyncio.sleep(0.03)
    except Exception as e:
        print("Error: ", e)
    finally:
        cap.release()
        await websocket.close()
@app.get("/")
async def root():
    return {"Hello": "World"}

# Run the FastAPI application using Uvicorn server
def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()