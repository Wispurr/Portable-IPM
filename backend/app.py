from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    uid: str
    name: str
    isRoot: Union[bool, None] = None
    
@app.get("/")
async def root():
    return {"Hello": "World"}

@app.post("/user/{uid}")
async def create_user(uid: str, user: Union[dict, None] = None):
    if user is None:
        return {"message": "No user data provided"}
    return {"user_id": uid, "user_data": user}