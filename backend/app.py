# app.py: A FastAPI application for a simple user management system

from typing import Union
from fastapi import FastAPI, Request
from pydantic import BaseModel
# for server configuration and running the FastAPI app
from uvicorn import Config, Server
import os
from aiofiles import open as aopen

# for handling file uploads and responses
from fastapi.responses import JSONResponse, HTMLResponse
# Templates and static files for serving HTML and static content
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# HTML Exception
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils import CONFIG, build_result_json, build_error_json, HTTPExceptionLoading  # Importing utility functions for API formatting
from api import analyze_image_router, stream_router  # Importing the image analysis router

# initialize FastAPI application
app = FastAPI()
templates = Jinja2Templates(directory="./templates")
app.mount("/static", StaticFiles(directory="./static"), name="static")
app.mount("/uploads", StaticFiles(directory="./uploads"), name="uploads")
app.include_router(analyze_image_router)
app.include_router(stream_router)
# print(f"API routers included successfully\n{app.routes}")

# Define a User model
class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None
    
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
async def root():
    html = ""
    async with aopen(TEMPLATE_PATH, "r") as f:
        html = await f.read()
    return HTMLResponse(html)

# Run the FastAPI application using Uvicorn server
def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()