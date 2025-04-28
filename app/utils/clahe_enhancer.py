import cv2
import numpy as np

class CLAHEEnhancer:
    """光線補償增強工具，用於處理低光環境下的圖像，提高唇部檢測的準確性"""
    
    def __init__(self, clip_limit=3.0, tile_grid_size=(8, 8)):
        """初始化CLAHE增強器
        
        Args:
            clip_limit: 對比度限制 (大於1的浮點數)
            tile_grid_size: 網格大小
        """
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    
    def enhance(self, image):
        """增強圖像
        
        Args:
            image: 輸入的BGR圖像
            
        Returns:
            enhanced: 增強後的圖像
        """
        # 轉換到LAB色彩空間以保留顏色信息
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 只對亮度通道進行CLAHE處理
        l_enhanced = self.clahe.apply(l)
        
        # 合併通道
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        
        # 轉回BGR色彩空間
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def is_low_light(self, image):
        """檢測圖像是否為低光環境
        
        Args:
            image: 輸入的BGR圖像
            
        Returns:
            is_low: 是否為低光環境
        """
        # 轉換為灰度圖
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 計算平均亮度
        avg_brightness = np.mean(gray)
        
        # 如果平均亮度低於閾值，判定為低光環境
        is_low = avg_brightness < 100
        
        return is_low
    
    def process_image(self, image):
        """根據圖像光照條件進行處理
        
        Args:
            image: 輸入的BGR圖像
            
        Returns:
            processed: 處理後的圖像
        """
        if self.is_low_light(image):
            return self.enhance(image)
        else:
            return image 