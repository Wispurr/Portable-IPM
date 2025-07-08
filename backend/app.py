from config import CONFIG
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import Config, Server

app = FastAPI()

class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None
    
@app.get("/")
async def root():
    return {"Hello": "World"}

def run():
    config = Config(app, host=CONFIG.host, port=CONFIG.port)
    server = Server(config=config)
    server.run()
    
if __name__ == "__main__":
    run()