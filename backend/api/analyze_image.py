# analyze_image.py: 修正後的 WebSocket 端點
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, WebSocket, WebSocketDisconnect
import base64
import uuid
import os
import asyncio
import json
from fastapi.responses import JSONResponse, HTMLResponse
from aiofiles import open as aopen
from utils import CONFIG, ipm_process, object_detection, build_result_json, build_error_json

router = APIRouter(
    prefix="/analyze-image",
    tags=["analyze-image"],
)

TEMPLATE_PATH = "./templates/analyze_image.html"

@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}.png"
    file_location = os.path.join(CONFIG.UPLOAD_FOLDER, filename)
    content = await file.read()
    with open(file_location, "wb") as buffer:
        buffer.write(content)
    return {"message": "Upload successful", "filename": filename}

# User Interface for DEMO
@router.get("/ui", description="Analyze image from file or base64 string in User Interface")
async def analyze_image_ui(
    request: Request,
    file: UploadFile = File(None),
    base64_image: str = Form(None)
):
    html = ""
    async with aopen(TEMPLATE_PATH, "r") as f:
        html = await f.read()
    return HTMLResponse(html)

@router.post("/ui", description="Analyze image from file or base64 string in User Interface")
async def analyze_image(
    request: Request,
    file: UploadFile = File(None),
    base64_image: str = Form(None)
):
    try:
        if not file and not base64_image:
            raise HTTPException(status_code=400, detail="No image provided")
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(CONFIG.UPLOAD_FOLDER, filename)
        # Handle file or base64 image
        if file:
            content = await file.read()
        else:
            try:
                header_removed = base64_image.split(",")[-1]
                content = base64.b64decode(header_removed)
            except Exception as decode_error:
                raise HTTPException(status_code=400, detail="Invalid base64 image") from decode_error
        # Save image
        with open(file_path, "wb") as f:
            f.write(content)
        # Call image processing modules
        ipm_path = ipm_process(file_path)
        offset, obstacles, warnings, encoded = object_detection(ipm_path)
        # Build and return result
        result = build_result_json(offset, obstacles, warnings, encoded)
        return JSONResponse(content=result)
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content=build_error_json(he.detail))
    except Exception as e:
        return JSONResponse(status_code=500, content=build_error_json(str(e)))

@router.websocket("/ws")
async def dataSocket(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket connected: {websocket.client}")
    
    try:
        # 發送初始門檻值
        initial_data = {
            "angleWarnDeg": 5.0,
            "minDistM": 0.8,
            "maxDistM": 2.0,
            "data": {
                "offset": 0.0,
                "obstacles": [],
                "warnings": []
            },
            "timestamp": "2024-01-01T00:00:00.000Z",
            "status": "success"
        }
        await websocket.send_text(json.dumps(initial_data))
        
        # 持續發送模擬資料（實際應用中這裡會是真實的感測器資料）
        counter = 0
        while True:
            # 模擬動態門檻值和感測器資料
            counter += 1
            
            # 每10秒更新一次門檻值
            if counter % 20 == 0:  # 假設每0.5秒發送一次，所以20次 = 10秒
                angle_warn = 4.0 + (counter // 20) % 3  # 4, 5, 6 度循環
                min_dist = 0.7 + ((counter // 20) % 2) * 0.1  # 0.7, 0.8 循環
                max_dist = 1.8 + ((counter // 20) % 3) * 0.2  # 1.8, 2.0, 2.2 循環
            else:
                angle_warn = 5.0
                min_dist = 0.8
                max_dist = 2.0
            
            # 模擬感測器資料
            import math
            offset = math.sin(counter * 0.1) * 3  # -3 到 +3 度
            distance = 1.2 + math.sin(counter * 0.05) * 0.5  # 0.7 到 1.7 米
            
            # 生成警告
            warnings = []
            if abs(offset) > angle_warn:
                warnings.append(f"偏移過大: {offset:.1f}°")
            if distance < min_dist:
                warnings.append(f"距離過近: {distance:.2f}m")
            elif distance > max_dist:
                warnings.append(f"距離過遠: {distance:.2f}m")
            
            data = {
                "angleWarnDeg": angle_warn,
                "minDistM": min_dist,
                "maxDistM": max_dist,
                "data": {
                    "offset": round(offset, 2),
                    "obstacles": [
                        {"distance": round(distance, 2), "angle": 0},
                        {"distance": round(distance + 0.3, 2), "angle": 5}
                    ],
                    "warnings": warnings
                },
                "timestamp": f"2024-01-01T{(counter % 86400):05d}Z",
                "status": "success"
            }
            
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(0.5)  # 每0.5秒發送一次
            
    except WebSocketDisconnect:
        print("WebSocket disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1000)
        except:
            pass
    finally:
        print("WebSocket connection closed")