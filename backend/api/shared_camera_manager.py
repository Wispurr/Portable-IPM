# shared_camera_manager.py
import cv2
import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import numpy as np
from collections import deque
import time

class SharedCameraManager:
    """共享攝像頭管理器，支援多個消費者"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.cap = None
            self.current_frame = None
            self.frame_lock = threading.Lock()
            self.is_running = False
            self.capture_thread = None
            self.subscribers = set()
            self.frame_counter = 0
            self.fps = 30
            self.last_frame_time = time.time()
            self.initialized = True
            
    def start_capture(self, video_source=0):
        """啟動攝像頭捕獲"""
        if self.is_running:
            print("Camera capture already running")
            return True
            
        try:
            self.cap = cv2.VideoCapture(video_source)
            if not self.cap.isOpened():
                raise RuntimeError("Cannot open camera")
                
            # 設置攝像頭參數
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 減少延遲
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            print(f"📷 Camera capture started (source: {video_source})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start camera: {e}")
            return False
    
    def _capture_loop(self):
        """持續捕獲攝像頭畫面的循環"""
        while self.is_running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                        self.frame_counter += 1
                        current_time = time.time()
                        self.fps = 1.0 / (current_time - self.last_frame_time)
                        self.last_frame_time = current_time
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """獲取當前幀"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def add_subscriber(self, subscriber_id: str):
        """添加訂閱者"""
        self.subscribers.add(subscriber_id)
        print(f"➕ Subscriber added: {subscriber_id} (Total: {len(self.subscribers)})")
        
        # 如果是第一個訂閱者，啟動攝像頭
        if len(self.subscribers) == 1:
            self.start_capture()
    
    def remove_subscriber(self, subscriber_id: str):
        """移除訂閱者"""
        self.subscribers.discard(subscriber_id)
        print(f"➖ Subscriber removed: {subscriber_id} (Remaining: {len(self.subscribers)})")
        
        # 如果沒有訂閱者了，停止攝像頭
        if len(self.subscribers) == 0:
            self.stop_capture()
    
    def stop_capture(self):
        """停止攝像頭捕獲"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
        print("🛑 Camera capture stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取狀態信息"""
        return {
            'is_running': self.is_running,
            'frame_counter': self.frame_counter,
            'fps': round(self.fps, 1),
            'subscribers_count': len(self.subscribers),
            'has_frame': self.current_frame is not None
        }
