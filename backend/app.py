# app.py: A FastAPI application for a simple user management system

from config import CONFIG
from typing import Union
from fastapi import FastAPI
from fastapi import UploadFile, File
from pydantic import BaseModel
from uvicorn import Config, Server
import os

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

# index route

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