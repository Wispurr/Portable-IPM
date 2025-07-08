from config import CONFIG
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import Config, Server
import os

app = FastAPI()

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
        shutil.copyfileobj(file, buffer)
    return{"message": "Upload successful", "filename": file.filename}


@app.get("/")
async def root():
    return {"Hello": "World"}

def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()