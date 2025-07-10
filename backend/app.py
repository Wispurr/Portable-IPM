# app.py: A FastAPI application for a simple user management system

from typing import Union
from fastapi import FastAPI, Request
from pydantic import BaseModel
# for server configuration and running the FastAPI app
from uvicorn import Config, Server
import os
# for handling file uploads and responses
from fastapi.responses import JSONResponse, HTMLResponse
# Templates and static files for serving HTML and static content
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# HTML Exception
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils import CONFIG, build_result_json, build_error_json, HTTPExceptionLoading  # Importing utility functions for API formatting
from api import analyze_image_router  # Importing the image analysis router

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

# index route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    files = os.listdir(CONFIG.UPLOAD_FOLDER)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "uploads": files
    })
    return {"message": "Welcome to the IPM Model API!"}

# Exception handler for HTTP exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    loader = HTTPExceptionLoading()
    if exc.status_code == 403:
        return await loader.error_403()
    elif exc.status_code == 404:
        return await loader.error_404()
    elif exc.status_code == 405:
        return await loader.error_405()
    elif exc.status_code == 500:
        return await loader.error_500()
    else:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    loader = HTTPExceptionLoading()
    return await loader.error_500()

# Run the FastAPI application using Uvicorn server
def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()