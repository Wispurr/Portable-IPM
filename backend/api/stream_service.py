# stream_service.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import base64
import asyncio
import json
import uuid
from datetime import datetime
# from shared_camera_manager import SharedCameraManager
from utils.vision_processing.vision_processing import RealTimeIPMProcessor
from .shared_camera_manager import SharedCameraManager

router = APIRouter(
    prefix="/stream",
    tags=["stream"],
)

# 全局攝像頭管理器
camera_manager = SharedCameraManager()

# 全局處理器實例（共享配置）
global_processor = RealTimeIPMProcessor({
    'display_realtime': False,
    'enable_perspective_transform': True,
    'enable_color_detection': True,
    'enable_lane_detection': True,
    'process_every_n_frames': 2,  # 降低處理頻率以提高性能
})

@router.websocket("/ws/image")
async def stream_image(websocket: WebSocket):
    """WebSocket端點：串流處理後的影像"""
    await websocket.accept()
    subscriber_id = f"image_{uuid.uuid4().hex[:8]}"
    
    try:
        # 註冊訂閱者
        camera_manager.add_subscriber(subscriber_id)
        print(f"📹 Image stream client connected: {subscriber_id}")
        
        frame_skip = 0
        
        while True:
            # 獲取當前幀
            frame = camera_manager.get_frame()
            
            if frame is not None:
                # 每3幀發送一次以控制頻寬
                frame_skip += 1
                if frame_skip % 3 == 0:
                    
                    processed_frame = frame
                    # 縮小影像以減少傳輸量
                    height, width = processed_frame.shape[:2]
                    if width > 640:
                        scale = 640 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        processed_frame = cv2.resize(processed_frame, (new_width, new_height))
                    
                    # 編碼為JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]  # 降低品質以提高速度
                    _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                    
                    # 轉換為base64
                    img_base64 = base64.b64encode(buffer).decode("utf-8")
                    
                    # 發送影像數據
                    await websocket.send_text(img_base64)
            
            # 控制發送頻率
            await asyncio.sleep(0.1)  # 10 FPS
            
    except WebSocketDisconnect:
        print(f"📹 Image stream client disconnected: {subscriber_id}")
    except Exception as e:
        print(f"❌ Image stream error: {e}")
    finally:
        camera_manager.remove_subscriber(subscriber_id)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/data")
async def stream_data(websocket: WebSocket):
    """WebSocket端點：串流分析數據（不含影像）"""
    await websocket.accept()
    subscriber_id = f"data_{uuid.uuid4().hex[:8]}"
    
    try:
        # 註冊訂閱者
        camera_manager.add_subscriber(subscriber_id)
        print(f"📊 Data stream client connected: {subscriber_id}")
        
        while True:
            # 獲取當前幀
            frame = camera_manager.get_frame()
            
            if frame is not None:
                # 處理影像但不傳送影像數據
                _, frame_results = global_processor.process_frame(frame)
                
                # 提取分析結果
                offset = 0.0
                obstacles = []
                warnings = []
                confidence = 0.0
                
                # 提取車道檢測結果
                if 'lane_detection' in frame_results.get('processing_results', {}):
                    lane_data = frame_results['processing_results']['lane_detection']
                    offset = lane_data.get('offset_px', 0.0)
                    confidence = lane_data.get('confidence', 0.0)
                    
                    if confidence < 0.5:
                        warnings.append("Low lane detection confidence")
                    if abs(offset) > 50:
                        warnings.append(f"Large lane offset: {offset:.1f}px")
                
                # 提取顏色檢測結果（障礙物）
                if 'color_detection' in frame_results.get('processing_results', {}):
                    color_data = frame_results['processing_results']['color_detection']
                    objects = color_data.get('objects', [])
                    
                    for obj in objects:
                        obstacle = {
                            'type': obj['color'],
                            'position': obj['center'],
                            'bbox': obj['bbox'],
                            'area': obj['area']
                        }
                        obstacles.append(obstacle)
                
                # 構建回傳數據
                data = {
                    "type": "analysis_data",
                    "data": {
                        "offset": round(offset, 2),
                        "obstacles": obstacles,
                        "warnings": warnings,
                        "confidence": round(confidence, 2),
                        "lane_center_x": frame_results.get('processing_results', {})
                                        .get('lane_detection', {})
                                        .get('lane_center_x'),
                        "left_lines_count": frame_results.get('processing_results', {})
                                           .get('lane_detection', {})
                                           .get('left_lines_count', 0),
                        "right_lines_count": frame_results.get('processing_results', {})
                                            .get('lane_detection', {})
                                            .get('right_lines_count', 0),
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "frame_counter": camera_manager.frame_counter,
                    "fps": round(camera_manager.fps, 1),
                    "status": "success"
                }
                
                # 發送JSON數據
                await websocket.send_text(json.dumps(data))
            
            # 控制發送頻率 (數據可以更頻繁)
            await asyncio.sleep(0.05)  # 20 Hz
            
    except WebSocketDisconnect:
        print(f"📊 Data stream client disconnected: {subscriber_id}")
    except Exception as e:
        print(f"❌ Data stream error: {e}")
    finally:
        camera_manager.remove_subscriber(subscriber_id)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/combined")
async def stream_combined(websocket: WebSocket):
    """WebSocket端點：同時串流影像和數據"""
    await websocket.accept()
    subscriber_id = f"combined_{uuid.uuid4().hex[:8]}"
    
    try:
        # 註冊訂閱者
        camera_manager.add_subscriber(subscriber_id)
        print(f"🎯 Combined stream client connected: {subscriber_id}")
        
        frame_skip = 0
        
        while True:
            # 獲取當前幀
            frame = camera_manager.get_frame()
            
            if frame is not None:
                # 處理影像
                processed_frame, frame_results = global_processor.process_frame(frame)
                
                # 準備數據
                data_packet = {
                    "type": "combined",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                
                # 每3幀發送一次影像
                frame_skip += 1
                send_image = (frame_skip % 3 == 0)
                
                if send_image:
                    # 縮小並編碼影像
                    height, width = processed_frame.shape[:2]
                    if width > 640:
                        scale = 640 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        processed_frame = cv2.resize(processed_frame, (new_width, new_height))
                    
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                    _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                    img_base64 = base64.b64encode(buffer).decode("utf-8")
                    data_packet["image"] = img_base64
                
                # 總是發送分析數據
                offset = 0.0
                obstacles = []
                warnings = []
                
                if 'lane_detection' in frame_results.get('processing_results', {}):
                    lane_data = frame_results['processing_results']['lane_detection']
                    offset = lane_data.get('offset_px', 0.0)
                    confidence = lane_data.get('confidence', 0.0)
                    
                    if confidence < 0.5:
                        warnings.append("Low confidence")
                    if abs(offset) > 50:
                        warnings.append(f"Offset: {offset:.1f}px")
                
                if 'color_detection' in frame_results.get('processing_results', {}):
                    color_data = frame_results['processing_results']['color_detection']
                    objects = color_data.get('objects', [])
                    
                    for obj in objects[:5]:  # 限制數量
                        obstacles.append({
                            'type': obj['color'],
                            'position': obj['center'],
                            'area': int(obj['area'])
                        })
                
                data_packet["analysis"] = {
                    "offset": round(offset, 2),
                    "obstacles": obstacles,
                    "warnings": warnings,
                    "fps": round(camera_manager.fps, 1)
                }
                
                # 發送組合數據
                await websocket.send_text(json.dumps(data_packet))
            
            # 控制發送頻率
            await asyncio.sleep(0.1)  # 10 Hz
            
    except WebSocketDisconnect:
        print(f"🎯 Combined stream client disconnected: {subscriber_id}")
    except Exception as e:
        print(f"❌ Combined stream error: {e}")
    finally:
        camera_manager.remove_subscriber(subscriber_id)
        try:
            await websocket.close()
        except:
            pass


@router.get("/status")
async def get_camera_status():
    """獲取攝像頭狀態"""
    return camera_manager.get_status()