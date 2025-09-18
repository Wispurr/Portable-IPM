import cv2
import os
import numpy as np
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from collections import deque
import argparse

class RealTimeIPMProcessor:
    """即時IPM (Inverse Perspective Mapping) 視頻處理器"""
    
    def __init__(self, config=None):
        """初始化即時IPM處理器"""
        self.config = self._load_default_config()
        if config:
            self.config.update(config)
        
        # 色彩範圍配置
        self.color_ranges = {
            "Red":    {"lower": [0, 213, 146],   "upper": [8, 255, 255]},   
            "Blue":   {"lower": [38, 246, 174], "upper": [123, 255, 255]},  
            "Yellow": {"lower": [18, 96, 181],  "upper": [24, 187, 207]}   
        }
        
        # 透視變換相關
        self.perspective_points = []
        self.perspective_matrix = None
        self.inverse_matrix = None
        
        # 即時處理相關
        self.is_running = False
        self.frame_queue = deque(maxlen=5)  # 框架緩衝區
        self.result_queue = deque(maxlen=3) # 結果緩衝區
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0
        
        # 性能優化
        self.skip_frames = 0  # 跳幀計數
        self.process_every_n_frames = 1  # 每N幀處理一次
        
        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'processed_frames': 0,
            'detection_results': [],
            'processing_times': deque(maxlen=100)
        }
    
    def _load_default_config(self):
        """載入預設配置"""
        return {
            # 輸入輸出配置
            'video_source': 0,  # 0為攝像頭，或視頻檔路徑
            'output_video': None,  # 輸出視頻路徑
            'save_frames': False,
            'frame_output_dir': 'frame_outputs',
            'json_output_dir': 'realtime_results',
            
            # 顯示配置
            'display_realtime': True,
            'display_size': (1280, 720),
            'show_fps': True,
            'show_stats': True,
            
            # 性能配置
            'target_fps': 30,
            'process_every_n_frames': 1,  # 處理頻率
            'max_queue_size': 5,
            'enable_multithreading': True,
            
            # 處理配置
            'enable_perspective_transform': True,
            'enable_color_detection': True,
            'enable_lane_detection': True,
            'perspective_dst_size': (640, 480),
            
            # ROI和檢測參數
            'roi_top_ratio': 0.35,
            'roi_left_crop': 0.05,
            'roi_right_crop': 0.05,
            'canny_low': 50,
            'canny_high': 150,
            'hough_threshold': 30,
            'hough_min_line_length': 50,
            'hough_max_line_gap': 10,
            'min_contour_area': 300,
            
            # 穩定性配置
            'lane_smoothing_frames': 5,  # 車道檢測平滑幀數
            'confidence_threshold': 0.6,
        }
    
    def setup_video_source(self):
        """設置視頻源"""
        source = self.config['video_source']
        
        if isinstance(source, int) or source.isdigit():
            # 攝像頭
            self.cap = cv2.VideoCapture(int(source))
            print(f"📷 使用攝像頭: {source}")
        else:
            # 視頻檔
            if not Path(source).exists():
                raise FileNotFoundError(f"視頻檔不存在: {source}")
            self.cap = cv2.VideoCapture(source)
            print(f"🎥 使用視頻檔: {source}")
        
        if not self.cap.isOpened():
            raise RuntimeError("無法打開視頻源")
        
        # 獲取視頻屬性
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"視頻屬性: {self.video_width}x{self.video_height} @ {self.video_fps:.1f}fps")
        
        # 設置緩衝區大小（減少延遲）
        if isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    def setup_video_writer(self):
        """設置視頻寫入器"""
        if not self.config['output_video']:
            return None
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_fps = min(self.config['target_fps'], self.video_fps)
        
        writer = cv2.VideoWriter(
            self.config['output_video'],
            fourcc,
            output_fps,
            (self.video_width, self.video_height)
        )
        
        print(f"🎬 輸出視頻: {self.config['output_video']}")
        return writer
    
    def load_default_perspective_points(self, frame_shape):
        """載入預設透視變換點（用於無顯示模式）"""
        h, w = frame_shape[:2]
        
        # 根據圖像尺寸設置預設的透視變換點
        # 這些點構成一個梯形，模擬道路的透視效果
        default_points = [
            (int(w * 0.45), int(h * 0.6)),   # 左上
            (int(w * 0.55), int(h * 0.6)),   # 右上
            (int(w * 0.85), int(h * 0.95)),  # 右下
            (int(w * 0.15), int(h * 0.95))   # 左下
        ]
        
        self.perspective_points = default_points
        self._calculate_perspective_matrix()
        print(f"✅ 使用默認透視變換點: {default_points}")
        return True

    def select_perspective_points_from_frame(self, frame, interactive=True):
        """從視頻幀中選擇透視變換點"""
        if not interactive:
            # 無顯示模式，使用預設點
            return self.load_default_perspective_points(frame.shape)
            
        print("\n🎯 從當前幀選擇透視變換點")
        print("請按順序選擇4個點：左上 -> 右上 -> 右下 -> 左下")
        
        try:
            clone = frame.copy()
            points = []
            
            def mouse_callback(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
                    points.append((x, y))
                    print(f"點 {len(points)}: ({x}, {y})")
            
            cv2.namedWindow("選擇透視變換點 (按q確認)", cv2.WINDOW_NORMAL)
            cv2.setMouseCallback("選擇透視變換點 (按q確認)", mouse_callback)
            
            while True:
                temp_img = clone.copy()
                
                # 繪製已選擇的點
                for i, pt in enumerate(points):
                    cv2.circle(temp_img, pt, 8, (0, 0, 255), -1)
                    cv2.putText(temp_img, str(i+1), (pt[0]+15, pt[1]-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # 繪製連接線
                if len(points) >= 2:
                    for i in range(len(points)-1):
                        cv2.line(temp_img, points[i], points[i+1], (255, 0, 0), 2)
                    if len(points) == 4:
                        cv2.line(temp_img, points[3], points[0], (255, 0, 0), 2)
                
                cv2.imshow("選擇透視變換點 (按q確認)", temp_img)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('r'):
                    points.clear()
                    print("已重置所有點")
                elif key == ord('q') or len(points) == 4:
                    break
            
            cv2.destroyWindow("選擇透視變換點 (按q確認)")
            
            if len(points) == 4:
                self.perspective_points = points
                self._calculate_perspective_matrix()
                print(f"✅ 透視變換點設置完成: {points}")
                return True
            else:
                print("❌ 需要選擇4個點")
                return False
                
        except cv2.error as e:
            print(f"⚠️ OpenCV GUI不可用: {e}")
            print("🔄 使用默認透視變換點...")
            return self.load_default_perspective_points(frame.shape)
    
    def _calculate_perspective_matrix(self):
        """計算透視變換矩陣"""
        if len(self.perspective_points) != 4:
            return
        
        src_pts = np.float32(self.perspective_points)
        dst_size = self.config['perspective_dst_size']
        dst_pts = np.float32([
            [0, 0],
            [dst_size[0], 0], 
            [dst_size[0], dst_size[1]],
            [0, dst_size[1]]
        ])
        
        self.perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        self.inverse_matrix = cv2.getPerspectiveTransform(dst_pts, src_pts)
    
    def apply_perspective_transform_fast(self, image):
        """快速透視變換"""
        if self.perspective_matrix is None:
            return image
        
        dst_size = self.config['perspective_dst_size']
        return cv2.warpPerspective(image, self.perspective_matrix, dst_size)
    
    def detect_colors_optimized(self, image):
        """優化的顏色檢測"""
        # 縮小圖像以提高處理速度
        scale = 0.5
        small_img = cv2.resize(image, None, fx=scale, fy=scale)
        hsv = cv2.cvtColor(small_img, cv2.COLOR_BGR2HSV)
        
        result_img = image.copy()
        detection_results = {'objects': [], 'color_counts': {}}
        
        for color_name, ranges in self.color_ranges.items():
            lower = np.array(ranges["lower"])
            upper = np.array(ranges["upper"])
            mask = cv2.inRange(hsv, lower, upper)
            
            # 形態學操作去噪
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            object_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.config['min_contour_area'] * (scale ** 2):
                    continue
                
                # 恢復到原圖尺寸
                contour = (contour / scale).astype(np.int32)
                x, y, w, h = cv2.boundingRect(contour)
                
                # 繪製檢測框
                cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(result_img, color_name, (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                detection_results['objects'].append({
                    'color': color_name,
                    'bbox': [x, y, w, h],
                    'area': float(area / (scale ** 2)),
                    'center': [x + w//2, y + h//2]
                })
                
                object_count += 1
            
            detection_results['color_counts'][color_name] = object_count
        
        return result_img, detection_results
    
    def detect_lanes_fast(self, image):
        """快速車道檢測"""
        h, w = image.shape[:2]
        
        # ROI設定
        y_top = int(h * self.config['roi_top_ratio'])
        y_bot = h
        x_left = int(w * self.config['roi_left_crop'])
        x_right = int(w * (1.0 - self.config['roi_right_crop']))
        
        # 提取並縮小ROI以提高速度
        roi = image[y_top:y_bot, x_left:x_right]
        roi_small = cv2.resize(roi, None, fx=0.5, fy=0.5)
        roi_gray = cv2.cvtColor(roi_small, cv2.COLOR_BGR2GRAY) if len(roi_small.shape) == 3 else roi_small
        
        # 增強對比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4))
        enhanced = clahe.apply(roi_gray)
        
        # 邊緣檢測
        edges = cv2.Canny(enhanced, self.config['canny_low'], self.config['canny_high'])
        
        # 霍夫變換（調整參數以提高速度）
        lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                               threshold=self.config['hough_threshold']//2,
                               minLineLength=self.config['hough_min_line_length']//2,
                               maxLineGap=self.config['hough_max_line_gap'])
        
        # 線條分類和繪製
        result_img = image.copy()
        left_lines = []
        right_lines = []
        
        if lines is not None:
            roi_center_x = roi_small.shape[1] // 2
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # 恢復到原圖座標
                x1, x2 = x1 * 2, x2 * 2
                y1, y2 = y1 * 2, y2 * 2
                
                if abs(x2 - x1) < 10:
                    continue
                
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) < 0.3:
                    continue
                
                line_center_x = (x1 + x2) / 2
                
                # 轉換到全圖座標進行繪製
                global_x1, global_y1 = x_left + x1, y_top + y1
                global_x2, global_y2 = x_left + x2, y_top + y2
                
                if line_center_x < roi_center_x * 2 * 0.8:
                    left_lines.append(line[0])
                    cv2.line(result_img, (global_x1, global_y1), (global_x2, global_y2), (255, 0, 0), 2)
                elif line_center_x > roi_center_x * 2 * 1.2:
                    right_lines.append(line[0])
                    cv2.line(result_img, (global_x1, global_y1), (global_x2, global_y2), (0, 0, 255), 2)
        
        # 繪製ROI框
        cv2.rectangle(result_img, (x_left, y_top), (x_right, y_bot), (255, 255, 0), 2)
        
        # 計算車道中心和偏移
        lane_center_x = None
        offset_px = 0.0
        
        if left_lines and right_lines:
            left_x = np.mean([((line[0] + line[2]) / 2) for line in left_lines])
            right_x = np.mean([((line[0] + line[2]) / 2) for line in right_lines])
            lane_center_x = x_left + (left_x + right_x) / 2
            offset_px = (w / 2.0) - lane_center_x
            
            # 繪製車道中心線
            cv2.line(result_img, (int(lane_center_x), y_bot), (int(lane_center_x), y_top), (0, 255, 255), 2)
        
        # 車輛中心線
        cv2.line(result_img, (w//2, y_bot), (w//2, y_top), (0, 255, 0), 2)
        
        return result_img, {
            'left_lines_count': len(left_lines),
            'right_lines_count': len(right_lines),
            'lane_center_x': float(lane_center_x) if lane_center_x is not None else None,
            'offset_px': float(offset_px),
            'confidence': min(len(left_lines) + len(right_lines), 10) / 10.0
        }
    
    def process_frame(self, frame):
        """處理單幀圖像"""
        start_time = time.time()
        
        result_frame = frame.copy()
        frame_results = {
            'timestamp': time.time(),
            'processing_results': {}
        }
        
        try:
            # 1. 透視變換
            if self.config['enable_perspective_transform'] and self.perspective_matrix is not None:
                perspective_frame = self.apply_perspective_transform_fast(result_frame)
                result_frame = perspective_frame
                frame_results['processing_results']['perspective_transform'] = True
            
            # 2. 顏色檢測
            if self.config['enable_color_detection']:
                result_frame, color_results = self.detect_colors_optimized(result_frame)
                frame_results['processing_results']['color_detection'] = color_results
            
            # 3. 車道檢測
            if self.config['enable_lane_detection']:
                result_frame, lane_results = self.detect_lanes_fast(result_frame)
                frame_results['processing_results']['lane_detection'] = lane_results
            
            # 計算處理時間
            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)
            frame_results['processing_time'] = processing_time
            
        except Exception as e:
            print(f"幀處理錯誤: {e}")
            frame_results['error'] = str(e)
        
        return result_frame, frame_results
    
    def add_overlay_info(self, frame, frame_results):
        """添加覆蓋資訊顯示"""
        if not self.config['show_stats']:
            return frame
        
        overlay = frame.copy()
        
        # FPS顯示
        if self.config['show_fps']:
            cv2.putText(overlay, f"FPS: {self.current_fps:.1f}", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # 處理時間
        if 'processing_time' in frame_results:
            processing_ms = frame_results['processing_time'] * 1000
            cv2.putText(overlay, f"Process: {processing_ms:.1f}ms", (20, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # 檢測統計
        y_pos = 110
        if 'lane_detection' in frame_results.get('processing_results', {}):
            lane_data = frame_results['processing_results']['lane_detection']
            offset = lane_data.get('offset_px', 0)
            confidence = lane_data.get('confidence', 0)
            
            cv2.putText(overlay, f"Lane Offset: {offset:.1f}px", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            y_pos += 35
            
            cv2.putText(overlay, f"Confidence: {confidence:.2f}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            y_pos += 35
        
        if 'color_detection' in frame_results.get('processing_results', {}):
            color_data = frame_results['processing_results']['color_detection']
            total_objects = len(color_data.get('objects', []))
            cv2.putText(overlay, f"Objects: {total_objects}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 狀態指示器
        status_color = (0, 255, 0) if len(frame_results.get('processing_results', {})) > 0 else (0, 0, 255)
        cv2.circle(overlay, (frame.shape[1] - 30, 30), 10, status_color, -1)
        
        return overlay
    
    def update_fps_counter(self):
        """更新FPS計數器"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_timer)
            self.fps_counter = 0
            self.fps_timer = current_time
    
    def run_realtime_processing(self):
        """運行即時處理"""
        print("🚀 啟動即時IPM處理...")
        
        # 設置視頻源和輸出
        self.setup_video_source()
        video_writer = self.setup_video_writer()
        
        # 創建輸出目錄
        if self.config['save_frames']:
            Path(self.config['frame_output_dir']).mkdir(parents=True, exist_ok=True)
        if self.config['json_output_dir']:
            Path(self.config['json_output_dir']).mkdir(parents=True, exist_ok=True)
        
        # 透視變換點設置
        if self.config['enable_perspective_transform'] and not self.perspective_points:
            print("📷 獲取第一幀用於設置透視變換...")
            ret, first_frame = self.cap.read()
            if ret:
                # 根據是否有顯示介面決定對話模式
                interactive_mode = self.config['display_realtime']
                self.select_perspective_points_from_frame(first_frame, interactive_mode)
        
        self.is_running = True
        frame_count = 0
        
        print("▶️ 開始即時處理... (按 'q' 退出, 'p' 暫停, 's' 保存當前幀)")
        
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("📹 視頻結束或無法讀取幀")
                    break
                
                frame_count += 1
                self.stats['total_frames'] += 1
                
                # 跳幀處理以提高性能
                if frame_count % self.config['process_every_n_frames'] != 0:
                    continue
                
                # 調整幀大小以提高性能
                if self.config['display_size']:
                    display_frame = cv2.resize(frame, self.config['display_size'])
                else:
                    display_frame = frame
                
                # 處理幀
                processed_frame, frame_results = self.process_frame(display_frame)
                self.stats['processed_frames'] += 1
                
                # 添加資訊覆蓋層
                final_frame = self.add_overlay_info(processed_frame, frame_results)
                
                # 顯示結果
                if self.config['display_realtime']:
                    cv2.imshow('Real-time IPM Processing', final_frame)
                
                # 保存視頻幀
                if video_writer is not None:
                    # 確保尺寸匹配
                    if final_frame.shape[:2] != (self.video_height, self.video_width):
                        save_frame = cv2.resize(final_frame, (self.video_width, self.video_height))
                    else:
                        save_frame = final_frame
                    video_writer.write(save_frame)
                
                # 保存單獨的幀
                if self.config['save_frames'] and frame_count % (self.config['process_every_n_frames'] * 10) == 0:
                    frame_path = Path(self.config['frame_output_dir']) / f"frame_{frame_count:06d}.jpg"
                    cv2.imwrite(str(frame_path), final_frame)
                
                # 保存JSON結果
                if self.config['json_output_dir'] and frame_count % (self.config['process_every_n_frames'] * 30) == 0:
                    json_path = Path(self.config['json_output_dir']) / f"results_{frame_count:06d}.json"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(frame_results, f, indent=2, ensure_ascii=False)
                
                # 更新FPS
                self.update_fps_counter()
                
                # 鍵盤控制
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    print("⏸️ 暫停... (按任意鍵繼續)")
                    cv2.waitKey(0)
                elif key == ord('s'):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"manual_save_{timestamp}.jpg"
                    cv2.imwrite(save_path, final_frame)
                    print(f"💾 手動保存幀: {save_path}")
                elif key == ord('r') and self.config['display_realtime']:
                    # 重新設置透視變換點（僅在顯示模式下）
                    if self.select_perspective_points_from_frame(display_frame, True):
                        print("✅ 透視變換點已更新")
                
        except KeyboardInterrupt:
            print("\n⏹️ 用戶中斷處理")
        
        except Exception as e:
            print(f"❌ 處理錯誤: {e}")
        
        finally:
            # 清理資源
            self.cleanup(video_writer)
    
    def cleanup(self, video_writer=None):
        """清理資源"""
        print("\n🧹 清理資源...")
        
        self.is_running = False
        
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        
        if video_writer:
            video_writer.release()
        
        cv2.destroyAllWindows()
        
        # 列印統計資訊
        print(f"\n📊 處理統計:")
        print(f"總幀數: {self.stats['total_frames']}")
        print(f"處理幀數: {self.stats['processed_frames']}")
        print(f"平均FPS: {self.current_fps:.1f}")
        
        if self.stats['processing_times']:
            avg_time = np.mean(self.stats['processing_times'])
            print(f"平均處理時間: {avg_time*1000:.1f}ms")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='即時IPM視頻處理常式')
    parser.add_argument('--source', '-s', default=0, 
                       help='視頻源 (0為攝像頭，或視頻檔路徑)')
    parser.add_argument('--output', '-o', help='輸出視頻檔路徑')
    parser.add_argument('--config', '-c', help='設定檔路徑(JSON)')
    parser.add_argument('--fps', type=int, default=30, help='目標FPS')
    parser.add_argument('--process-every', type=int, default=1, help='每N幀處理一次')
    parser.add_argument('--no-display', action='store_true', help='不顯示即時畫面')
    parser.add_argument('--save-frames', action='store_true', help='保存處理後的幀')
    parser.add_argument('--no-perspective', action='store_true', help='禁用透視變換')
    parser.add_argument('--no-colors', action='store_true', help='禁用顏色檢測')
    parser.add_argument('--perspective-points', help='透視變換點JSON檔或預設名稱')
    parser.add_argument('--save-perspective', help='保存選擇的透視變換點到檔')
    
    parser.add_argument('--no-lanes', action='store_true', help='禁用車道檢測')
    
    args = parser.parse_args()
    
    # 載入配置
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 應用命令列參數
    config.update({
        'video_source': args.source,
        'output_video': args.output,
        'target_fps': args.fps,
        'process_every_n_frames': args.process_every,
        'display_realtime': not args.no_display,
        'save_frames': args.save_frames,
        'enable_perspective_transform': not args.no_perspective,
        'enable_color_detection': not args.no_colors,
        'enable_lane_detection': not args.no_lanes
    })
    
    # 初始化處理器
    processor = RealTimeIPMProcessor(config)
    
    # 預載入透視變換點
    if args.perspective_points:
        if args.perspective_points.endswith('.json') and Path(args.perspective_points).exists():
            with open(args.perspective_points, 'r') as f:
                points_data = json.load(f)
                processor.perspective_points = points_data.get('points', [])
                if len(processor.perspective_points) == 4:
                    processor._calculate_perspective_matrix()
                    print(f"✅ 從檔載入透視變換點: {args.perspective_points}")
        elif args.perspective_points == 'road':
            # 道路預設（梯形）
            processor.perspective_points = [(576, 324), (704, 324), (1020, 684), (300, 684)]
            processor._calculate_perspective_matrix()
            print("✅ 使用道路預設透視變換點")
        elif args.perspective_points == 'parking':
            # 停車場預設（矩形）
            processor.perspective_points = [(480, 270), (800, 270), (800, 810), (480, 810)]
            processor._calculate_perspective_matrix()
            print("✅ 使用停車場預設透視變換點")
    
    print("🚀 即時IPM視頻處理常式")
    print(f"視頻源: {config['video_source']}")
    print(f"目標FPS: {config['target_fps']}")
    print(f"處理頻率: 每{config['process_every_n_frames']}幀")
    print(f"透視變換: {'✓' if config['enable_perspective_transform'] else '✗'}")
    print(f"顏色檢測: {'✓' if config['enable_color_detection'] else '✗'}")
    print(f"車道檢測: {'✓' if config['enable_lane_detection'] else '✗'}")
    
    # 開始處理
    try:
        processor.run_realtime_processing()
        
        # 保存透視變換點（如果指定）
        if args.save_perspective and processor.perspective_points:
            save_data = {
                'points': processor.perspective_points,
                'timestamp': datetime.now().isoformat(),
                'video_source': args.source
            }
            with open(args.save_perspective, 'w') as f:
                json.dump(save_data, f, indent=2)
            print(f"💾 透視變換點已保存到: {args.save_perspective}")
            
    except Exception as e:
        print(f"❌ 程式執行錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
