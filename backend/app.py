# app.py: A FastAPI application for a simple user management system

from config import CONFIG
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import Config, Server

# initialize FastAPI application
app = FastAPI()

# Define a User model
class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None

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