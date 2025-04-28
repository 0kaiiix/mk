import cv2
import mediapipe as mp
import numpy as np

class FaceDetector:
    """面部特徵檢測工具，負責唇部特徵提取"""
    
    def __init__(self, max_num_faces=1):
        """初始化MediaPipe面部檢測模型
        
        Args:
            max_num_faces: 最大檢測人臉數量
        """
        self.max_num_faces = max_num_faces
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,  # 使用靜態圖像模式提高精度
            max_num_faces=max_num_faces,  # 支援多個人臉檢測
            refine_landmarks=True,  # 啟用唇部精細定位
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # 定義唇部特徵點索引 - 擴充更多點以提高精確度
        # 嘴唇外圍點 - 順時鐘方向從上唇中心開始
        self.outer_lip_points = [
            0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37
        ]
        
        # 嘴唇內部點 - 順時鐘方向
        self.inner_lip_points = [
            78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95
        ]
        
        # 所有唇部點
        self.all_lip_points = self.outer_lip_points + self.inner_lip_points
    
    def reinitialize(self, max_num_faces=1):
        """重新初始化檢測器以更新設定
        
        Args:
            max_num_faces: 最大檢測人臉數量
        """
        # 釋放當前資源
        self.mp_face_mesh.close()
        
        # 更新設定並重新初始化
        self.max_num_faces = max_num_faces
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=max_num_faces,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
    
    def detect_face(self, image):
        """檢測面部特徵點 (兼容舊的單人臉檢測接口)
        
        Args:
            image: 輸入的RGB圖像
            
        Returns:
            landmarks: 面部特徵點
            processed_image: 處理後的圖像
        """
        # 處理圖像並獲取所有人臉
        landmarks_list = self.detect_multiple_faces(image)
        
        # 如果有檢測到人臉，返回第一個（通常是最大或最中心的）
        if landmarks_list:
            return landmarks_list[0], image
        
        return None, image
    
    def detect_multiple_faces(self, image):
        """檢測多個面部特徵點
        
        Args:
            image: 輸入的RGB圖像
            
        Returns:
            landmarks_list: 面部特徵點列表
        """
        # 確保圖像為RGB格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 and image.shape[2] == 3 else image
        
        # 調整圖像大小以提高處理速度和穩定性 - 最大尺寸1280像素
        h, w = image_rgb.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            image_rgb = cv2.resize(image_rgb, (int(w*scale), int(h*scale)))
            # 記錄縮放比例用於後續還原座標
            self.scale_factor = 1/scale
        else:
            self.scale_factor = 1.0
            
        # 增強圖像對比度以改善弱光環境下的檢測
        lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        enhanced_image = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        
        # 處理圖像
        results = self.mp_face_mesh.process(enhanced_image)
        
        # 如果檢測到面部，返回所有人臉的特徵點
        landmarks_list = []
        if results.multi_face_landmarks:
            # 對於多人臉處理，我們按面積大小排序
            face_info = []
            
            for i, face_landmarks in enumerate(results.multi_face_landmarks):
                h, w = image.shape[:2]
                x_min = w
                y_min = h
                x_max = 0
                y_max = 0
                
                for landmark in face_landmarks.landmark:
                    x, y = int(landmark.x * w), int(landmark.y * h)
                    x_min = min(x_min, x)
                    y_min = min(y_min, y)
                    x_max = max(x_max, x)
                    y_max = max(y_max, y)
                
                area = (x_max - x_min) * (y_max - y_min)
                center = ((x_min + x_max) // 2, (y_min + y_max) // 2)
                
                # 計算到圖像中心的距離，用於評分
                img_center = (image.shape[1] // 2, image.shape[0] // 2)
                distance_to_center = ((center[0] - img_center[0]) ** 2 + (center[1] - img_center[1]) ** 2) ** 0.5
                
                # 我們將人臉按面積大小排序，但也考慮中心位置
                # 面積越大，距離中心越近，得分越高
                score = area - (distance_to_center * 0.5)  # 調整權重
                
                face_info.append((face_landmarks, score, i))
            
            # 按得分降序排序
            face_info.sort(key=lambda x: x[1], reverse=True)
            
            # 限制返回的人臉數量不超過設定的最大值
            for landmarks, _, _ in face_info[:self.max_num_faces]:
                landmarks_list.append(landmarks)
            
        return landmarks_list
    
    def get_lip_mask(self, image, landmarks):
        """獲取唇部遮罩
        
        Args:
            image: 輸入圖像
            landmarks: 面部特徵點
            
        Returns:
            mask: 唇部區域的二值遮罩
        """
        if landmarks is None:
            return None
        
        height, width = image.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # 1. 提取唇部外輪廓點
        outer_points = []
        for idx in self.outer_lip_points:
            try:
                landmark = landmarks.landmark[idx]
                x, y = int(landmark.x * width), int(landmark.y * height)
                # 應用縮放係數還原座標
                x, y = int(x * self.scale_factor), int(y * self.scale_factor)
                outer_points.append((x, y))
            except IndexError:
                continue
        
        # 2. 提取唇部內輪廓點
        inner_points = []
        for idx in self.inner_lip_points:
            try:
                landmark = landmarks.landmark[idx]
                x, y = int(landmark.x * width), int(landmark.y * height)
                # 應用縮放係數還原座標
                x, y = int(x * self.scale_factor), int(y * self.scale_factor)
                inner_points.append((x, y))
            except IndexError:
                continue
        
        # 確保有足夠的點來創建遮罩
        if len(outer_points) <= 3 or len(inner_points) <= 3:
            return None
        
        # 唇部檢測改進：對點進行處理以創建更平滑的唇形
        
        # 3. 檢查唇部是否閉合，如果唇部非常靠近，則視為閉合
        is_mouth_closed = self._is_mouth_closed(landmarks, width, height)
        
        # 4. 繪製外輪廓
        outer_lip_np = np.array(outer_points, dtype=np.int32)
        cv2.fillPoly(mask, [outer_lip_np], 255)
        
        # 5. 如果嘴巴未閉合，則挖空內部區域
        if not is_mouth_closed:
            inner_lip_np = np.array(inner_points, dtype=np.int32)
            cv2.fillPoly(mask, [inner_lip_np], 0)
        
        # 6. 應用形態學平滑處理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 7. 獲取唇部角度，如果唇部傾斜，則調整形狀
        angle = self._get_lip_angle(outer_points)
        if abs(angle) > 10:  # 如果唇部傾斜超過10度
            try:
                # 創建旋轉矩陣
                # 修復中心點計算方式，確保返回整數元組
                center_x = int(np.mean([p[0] for p in outer_points]))
                center_y = int(np.mean([p[1] for p in outer_points]))
                center = (center_x, center_y)
                
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                
                # 旋轉遮罩
                rotated_mask = cv2.warpAffine(mask, M, (width, height))
                
                # 應用更多圓潤處理
                rotated_mask = cv2.GaussianBlur(rotated_mask, (9, 9), 0)
                _, rotated_mask = cv2.threshold(rotated_mask, 50, 255, cv2.THRESH_BINARY)
                
                # 旋轉回原始角度
                M_back = cv2.getRotationMatrix2D(center, -angle, 1.0)
                mask = cv2.warpAffine(rotated_mask, M_back, (width, height))
            except Exception as e:
                print(f"Warning: 旋轉唇形時出錯: {e}")
                # 出錯時使用原始遮罩
                pass
        
        # 8. 最終處理：邊緣平滑
        mask = cv2.GaussianBlur(mask, (7, 7), 0)
        _, mask = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)
        
        # 9. 提高邊緣質量
        mask = cv2.dilate(mask, None, iterations=1)
        mask = cv2.erode(mask, None, iterations=1)
        
        return mask
    
    def _is_mouth_closed(self, landmarks, width, height):
        """檢查嘴巴是否閉合
        
        Args:
            landmarks: 面部特徵點
            width: 圖像寬度
            height: 圖像高度
            
        Returns:
            is_closed: 是否閉合
        """
        # 上唇中心點和下唇中心點
        top_lip = landmarks.landmark[13]
        bottom_lip = landmarks.landmark[14]
        
        # 計算垂直距離
        top_y = top_lip.y * height
        bottom_y = bottom_lip.y * height
        
        # 計算臉部高度作為參考
        nose_top = landmarks.landmark[168].y * height
        chin = landmarks.landmark[152].y * height
        face_height = chin - nose_top
        
        # 如果唇間距離小於臉部高度的4%，視為閉合
        return (bottom_y - top_y) < (face_height * 0.04)
    
    def _get_lip_angle(self, lip_points):
        """計算唇部角度
        
        Args:
            lip_points: 唇部點的列表
            
        Returns:
            angle: 唇部傾斜角度（度）
        """
        if len(lip_points) < 2:
            return 0
            
        # 獲取左右兩個點
        points = np.array(lip_points)
        leftmost_idx = np.argmin(points[:, 0])
        rightmost_idx = np.argmax(points[:, 0])
        
        # 如果點太靠近，返回0
        if rightmost_idx == leftmost_idx:
            return 0
            
        # 計算角度
        left_point = points[leftmost_idx]
        right_point = points[rightmost_idx]
        
        delta_x = right_point[0] - left_point[0]
        delta_y = right_point[1] - left_point[1]
        
        # 防止除零錯誤
        if delta_x == 0:
            return 90
            
        # 計算角度（度）
        angle = np.degrees(np.arctan2(delta_y, delta_x))
        return angle
    
    def get_skin_tone(self, image, landmarks):
        """獲取膚色調
        
        Args:
            image: 輸入圖像
            landmarks: 面部特徵點
            
        Returns:
            hsv_values: HSV色值
        """
        if landmarks is None:
            return None
        
        height, width = image.shape[:2]
        
        # 使用臉頰和額頭區域採樣膚色 - 更可靠
        forehead_point = landmarks.landmark[10]  # 額頭特徵點
        left_cheek = landmarks.landmark[123]  # 左臉頰
        right_cheek = landmarks.landmark[352]  # 右臉頰
        
        sample_points = [
            (int(forehead_point.x * width), int(forehead_point.y * height)),
            (int(left_cheek.x * width), int(left_cheek.y * height)),
            (int(right_cheek.x * width), int(right_cheek.y * height))
        ]
        
        # 從多個區域採樣並計算平均值
        samples = []
        roi_size = 15
        
        for x, y in sample_points:
            roi = image[max(0, y-roi_size):min(height, y+roi_size), 
                         max(0, x-roi_size):min(width, x+roi_size)]
            if roi.size > 0:
                # 轉換為HSV色彩空間
                roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                # 計算該區域的平均HSV值
                samples.append(np.mean(roi_hsv, axis=(0, 1)))
        
        if not samples:
            return None
            
        # 返回平均膚色
        return np.mean(samples, axis=0) 