import datetime
import base64
import cv2
import numpy as np
from pathlib import Path

class CONFIG:
    """配置類"""
    UPLOAD_FOLDER = "./uploads"
    
    def __init__(self):
        # 確保上傳目錄存在
        Path(self.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# 實例化配置
CONFIG = CONFIG()

def build_result_json(offset, obstacles, warnings, image_base64=None):
    """構建成功結果的JSON響應"""
    result = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "success",
        "data": {
            "offset": offset,
            "obstacles": obstacles,
            "warnings": warnings
        }
    }
    if image_base64:
        result["data"]["image_base64"] = image_base64
    return result

def build_error_json(message: str, code: int = 400, details: str = None):
    """構建錯誤響應的JSON"""
    error_response = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        error_response["error"]["details"] = details
    return error_response

def ipm_processing():
    """
    IPM處理函數 - 使用攝像頭作為輸入源
    返回處理結果：offset, obstacles, warnings, encoded_frame
    """
    try:
        # 使用更簡化的方法直接調用攝像頭處理
        from ipm_processing import process_camera_frame
        
        # 直接處理攝像頭的單幀
        offset, obstacles, warnings, encoded_frame = process_camera_frame()
        
        return offset, obstacles, warnings, encoded_frame
        
    except ImportError:
        # 如果無法導入，使用備用方案
        try:
            from vision_processing import RealTimeIPMProcessor
            import cv2
            
            # 創建處理器實例，設置攝像頭作為輸入源
            config = {
                'video_source': 0,  # 使用攝像頭
                'enable_perspective_transform': True,
                'enable_color_detection': True,
                'enable_lane_detection': True,
                'display_realtime': False,  # API模式不顯示界面
                'process_every_n_frames': 1,  # 處理每一幀
                'target_fps': 30
            }
            
            processor = RealTimeIPMProcessor(config)
            
            # 設置攝像頭
            processor.setup_video_source()
            
            # 讀取一幀進行處理
            ret, frame = processor.cap.read()
            if not ret:
                raise RuntimeError("無法從攝像頭讀取圖像")
            
            # 如果需要透視變換但還沒有設置點，使用默認點
            if processor.config['enable_perspective_transform'] and not processor.perspective_points:
                processor.load_default_perspective_points(frame.shape)
            
            # 處理這一幀
            processed_frame, frame_results = processor.process_frame(frame)
            
            # 提取處理結果
            offset = 0.0
            obstacles = []
            warnings = []
            
            # 從處理結果中提取車道偏移信息
            if 'lane_detection' in frame_results.get('processing_results', {}):
                lane_data = frame_results['processing_results']['lane_detection']
                offset = lane_data.get('offset_px', 0.0)
                confidence = lane_data.get('confidence', 0.0)
                
                if confidence < 0.5:
                    warnings.append("車道檢測置信度低")
                
                if abs(offset) > 50:  # 偏移超過50像素
                    warnings.append(f"車道偏移過大: {offset:.1f}px")
            
            # 從顏色檢測結果中提取障礙物信息
            if 'color_detection' in frame_results.get('processing_results', {}):
                color_data = frame_results['processing_results']['color_detection']
                objects = color_data.get('objects', [])
                
                for obj in objects:
                    obstacle = {
                        'type': obj['color'],
                        'position': obj['center'],
                        'size': obj['area'],
                        'bbox': obj['bbox']
                    }
                    obstacles.append(obstacle)
            
            # 編碼處理後的圖像
            encoded_frame = encode_image_to_base64(processed_frame)
            
            # 清理攝像頭資源
            processor.cap.release()
            
            return offset, obstacles, warnings, encoded_frame
            
        except Exception as e:
            print(f"IPM處理錯誤: {e}")
            # 返回默認值
            return 0.0, [], [f"處理錯誤: {str(e)}"], None
        
    except Exception as e:
        print(f"IPM處理錯誤: {e}")
        # 返回默認值
        return 0.0, [], [f"處理錯誤: {str(e)}"], None

def encode_image_to_base64(image):
    """將OpenCV圖像編碼為base64字符串"""
    if image is None:
        return None
    
    try:
        # 將圖像編碼為JPEG格式
        _, buffer = cv2.imencode('.jpg', image)
        # 轉換為base64字符串
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{image_base64}"
    except Exception as e:
        print(f"圖像編碼錯誤: {e}")
        return None

def decode_base64_to_image(base64_string):
    """將base64字符串解碼為OpenCV圖像"""
    try:
        # 移除data URL前綴
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # 解碼base64
        image_data = base64.b64decode(base64_string)
        
        # 轉換為numpy數組
        nparr = np.frombuffer(image_data, np.uint8)
        
        # 解碼為OpenCV圖像
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return image
    except Exception as e:
        print(f"圖像解碼錯誤: {e}")
        return None

def validate_image_file(file_path):
    """驗證圖像文件是否有效"""
    try:
        if not Path(file_path).exists():
            return False, "文件不存在"
        
        # 嘗試讀取圖像
        image = cv2.imread(str(file_path))
        if image is None:
            return False, "無效的圖像文件"
        
        return True, "圖像文件有效"
    except Exception as e:
        return False, f"文件驗證錯誤: {str(e)}"

def cleanup_temp_files(file_path, max_age_hours=24):
    """清理臨時文件"""
    try:
        file_path = Path(file_path)
        if file_path.exists():
            # 檢查文件年齡
            file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age.total_seconds() > max_age_hours * 3600:
                file_path.unlink()
                return True, "文件已清理"
        return False, "文件不需要清理"
    except Exception as e:
        return False, f"清理錯誤: {str(e)}"