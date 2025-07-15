# app.py: A FastAPI application for a simple user management system

from config import CONFIG
from typing import Union
from fastapi import FastAPI, UploadFile, File, WebSocket
from pydantic import BaseModel
from uvicorn import Config, Server
import os
import base64
import asyncio
import cv2

# initialize FastAPI application
app = FastAPI()

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