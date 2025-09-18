# stream.py: WebSocket for real-time image streaming
from fastapi import APIRouter, WebSocket
from fastapi.responses import HTMLResponse
import cv2
import base64
import asyncio
from aiofiles import open as aopen

router = APIRouter(
    prefix="/stream",
    tags=["stream"],
)

TEMPLATE_PATH = "./templates/ws_doc.html"

@router.websocket("/ws/image")
async def stream(websocket: WebSocket):
    await websocket.accept()
    cap = cv2.VideoCapture(0)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode("utf-8")
            await websocket.send_text(img_base64)
            await asyncio.sleep(0.05)
    except Exception as e:
        print(f"WebSocket closed: {e}")
        await websocket.close()
    finally:
        cap.release()
        await websocket.close()


@router.get("/ws-doc", response_class=HTMLResponse)
async def ws_doc():
    html = ""
    async with aopen(TEMPLATE_PATH, "r") as f:
        html = await f.read()
    return HTMLResponse(html)
