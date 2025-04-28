import cv2
import numpy as np
from typing import Tuple, Optional, Union

class LipstickRenderer:
    """口紅渲染器，負責將口紅效果應用到唇部"""
    
    def __init__(self):
        """初始化口紅渲染器"""
        pass
    
    def apply_lipstick(
        self, 
        image: np.ndarray, 
        mask: np.ndarray, 
        color_rgb: Tuple[int, int, int], 
        texture_type: str = "matte",
        opacity: float = 0.7
    ) -> np.ndarray:
        """
        將口紅效果應用到圖片上的唇部區域
        
        Args:
            image: 原始圖片
            mask: 唇部遮罩
            color_rgb: 口紅顏色的RGB值
            texture_type: 口紅質地，可選 "matte"（霧面）, "gloss"（珠光）, "velvet"（絲絨）
            opacity: 口紅不透明度/強度
        
        Returns:
            應用了口紅效果的圖片
        """
        try:
            # 確保輸入圖像和遮罩的數據類型正確
            if image is None or mask is None:
                return image
                
            image = image.astype(np.uint8)
            
            # 確保遮罩是合適的數據類型且不為空
            if mask.size == 0:
                return image
            
            mask = mask.astype(np.uint8)
            
            # 創建圖像的副本以避免修改原始圖像
            result = image.copy()
            
            # 優化色彩：調整色相和飽和度以增強口紅效果
            color_hsv = cv2.cvtColor(np.uint8([[color_rgb]]), cv2.COLOR_RGB2HSV)[0][0]
            
            # 根據色相調整飽和度，紅色系增強更多
            h, s, v = color_hsv
            if 0 <= h <= 20 or 160 <= h <= 180:  # 紅色系
                s = min(255, int(s * 1.3))  # 增強紅色系飽和度
            else:
                s = min(255, int(s * 1.2))  # 其他顏色稍微增強飽和度
                
            # 提高明度，使顏色更鮮明
            v = min(255, int(v * 1.1))
                
            # 更新HSV值
            color_hsv = np.array([h, s, v], dtype=np.uint8)
            
            # 轉回RGB
            enhanced_color = cv2.cvtColor(np.uint8([[color_hsv]]), cv2.COLOR_HSV2RGB)[0][0]
            
            # 轉換為BGR以匹配OpenCV的格式
            color_bgr = (enhanced_color[2], enhanced_color[1], enhanced_color[0])
            
            # 進行唇部邊緣細化處理
            refined_mask = self._refine_mask(mask)
            
            # 將遮罩擴展為3通道
            mask_3channel = cv2.cvtColor(refined_mask, cv2.COLOR_GRAY2BGR)
            mask_3channel = mask_3channel.astype(np.float32) / 255.0
            
            # 計算加強後的不透明度，確保效果更加明顯
            enhanced_opacity = min(1.0, opacity * 1.2)  # 增強不透明度但不超過1.0
            
            # 創建與輸入圖像相同大小的顏色層
            color_layer = np.zeros_like(result, dtype=np.float32)
            color_layer[:] = color_bgr
            
            # 根據質地類型應用不同的效果
            if texture_type == "matte":
                result_float = self.apply_matte_effect(
                    result.astype(np.float32),
                    color_layer,
                    mask_3channel,
                    enhanced_opacity
                )
            elif texture_type == "gloss":
                result_float = self.apply_gloss_effect(
                    result.astype(np.float32),
                    color_layer,
                    mask_3channel,
                    enhanced_opacity
                )
            elif texture_type == "velvet":
                result_float = self.apply_velvet_effect(
                    result.astype(np.float32),
                    color_layer,
                    mask_3channel,
                    enhanced_opacity
                )
            else:
                # 默認為霧面效果
                result_float = self.apply_matte_effect(
                    result.astype(np.float32),
                    color_layer,
                    mask_3channel,
                    enhanced_opacity
                )
            
            # 確保結果在有效範圍內並轉換回uint8
            result = np.clip(result_float, 0, 255).astype(np.uint8)
            
            # 進行最終的唇部混合優化
            result = self._blend_lips_with_skin(image, result, refined_mask)
            
            return result
        except Exception as e:
            print(f"渲染口紅時發生錯誤: {str(e)}")
            # 發生錯誤時返回原始圖像
            return image
    
    def _refine_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        細化唇部遮罩，創建更自然的邊緣過渡
        
        Args:
            mask: 原始唇部遮罩
            
        Returns:
            refined_mask: 細化後的遮罩
        """
        # 獲取遮罩尺寸
        h, w = mask.shape[:2]
        
        # 先進行高斯模糊使邊緣變柔和
        blurred = cv2.GaussianBlur(mask, (7, 7), 0)
        
        # 應用平均濾波器進一步平滑
        kernel_size = max(3, min(h, w) // 50)  # 根據圖像大小調整核大小
        kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1  # 確保是奇數
        smoothed = cv2.blur(blurred, (kernel_size, kernel_size))
        
        # 確保遮罩中心保持實心
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        # 創建漸變邊緣
        edge_mask = cv2.bitwise_xor(
            binary_mask,
            cv2.erode(binary_mask, None, iterations=2)
        )
        
        # 將漸變邊緣與原始遮罩結合
        inner_mask = cv2.erode(binary_mask, None, iterations=2)
        gradient_edge = cv2.addWeighted(
            cv2.bitwise_and(edge_mask, smoothed),
            0.7,
            cv2.bitwise_and(edge_mask, blurred),
            0.3,
            0
        )
        
        # 組合內部和邊緣
        refined_mask = cv2.bitwise_or(inner_mask, gradient_edge)
        
        return refined_mask
    
    def _blend_lips_with_skin(
        self, 
        original: np.ndarray, 
        lipstick: np.ndarray, 
        mask: np.ndarray
    ) -> np.ndarray:
        """
        將口紅效果與皮膚自然融合
        
        Args:
            original: 原始圖像
            lipstick: 應用了口紅的圖像
            mask: 唇部遮罩
            
        Returns:
            blended: 融合後的圖像
        """
        # 創建模糊的遮罩邊緣
        mask_blur = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 使用Alpha混合實現柔和過渡
        mask_norm = mask_blur.astype(np.float32) / 255.0
        mask_3ch = cv2.merge([mask_norm, mask_norm, mask_norm])
        
        # 應用混合
        blended = original.astype(np.float32) * (1.0 - mask_3ch) + lipstick.astype(np.float32) * mask_3ch
        
        return blended.astype(np.uint8)
    
    def apply_matte_effect(
        self, 
        image: np.ndarray, 
        color_layer: np.ndarray, 
        mask: np.ndarray,
        opacity: float
    ) -> np.ndarray:
        """應用霧面效果的口紅"""
        # 直接混合顏色，不加特殊效果
        # 確保所有輸入都是float32類型
        image = image.astype(np.float32)
        color_layer = color_layer.astype(np.float32)
        mask = mask.astype(np.float32)
        
        # 應用顏色混合
        # 使用遮罩的Alpha通道與不透明度參數混合
        blended = image * (1 - mask * opacity) + color_layer * (mask * opacity)
        
        # 應用輕微的紋理以增強霧面感
        noise = np.random.normal(0, 2.0, image.shape).astype(np.float32)
        noise_mask = noise * mask * 0.05  # 輕微噪點
        
        # 將噪點應用到混合結果
        matte_result = blended + noise_mask
        matte_result = np.clip(matte_result, 0, 255)
        
        return matte_result
    
    def apply_gloss_effect(
        self, 
        image: np.ndarray, 
        color_layer: np.ndarray, 
        mask: np.ndarray,
        opacity: float
    ) -> np.ndarray:
        """應用珠光/光澤效果的口紅"""
        # 確保所有輸入都是float32類型
        image = image.astype(np.float32)
        color_layer = color_layer.astype(np.float32)
        mask = mask.astype(np.float32)
        
        # 首先應用基本的顏色
        blended = image * (1 - mask * opacity) + color_layer * (mask * opacity)
        
        # 創建高光效果
        # 先定義高光區域（唇部中央偏上區域）
        highlight_mask = np.zeros_like(mask)
        h, w, _ = mask.shape
        
        # 創建徑向漸變作為高光（從中心向外漸變）
        y, x = np.ogrid[:h, :w]
        center_y, center_x = int(h * 0.4), int(w * 0.5)  # 稍微上移中心點
        
        # 計算到中心的距離
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        
        # 創建徑向漸變
        max_dist = np.sqrt(h**2 + w**2) * 0.3  # 控制高光大小
        highlight_gradient = np.clip(1 - dist_from_center / max_dist, 0, 1)
        
        # 應用到遮罩
        for c in range(3):
            highlight_mask[:, :, c] = highlight_gradient
        
        # 只在唇部區域內應用高光
        highlight_mask = highlight_mask * mask
        
        # 創建動態高光強度 - 較亮的顏色使用較低的高光強度
        color_brightness = np.mean(color_layer)
        highlight_strength = 0.35 - (color_brightness / 255.0) * 0.15  # 0.2 到 0.35 範圍
        
        # 創建高光層（白色）
        highlight_layer = np.ones_like(image) * 255
        
        # 將高光混合到已著色的唇部
        final = blended * (1 - highlight_mask * highlight_strength) + highlight_layer * (highlight_mask * highlight_strength)
        
        # 減少可能的雜訊
        # 對唇部應用輕微的高斯模糊（只在唇部區域）
        lips_only = np.zeros_like(image)
        lips_only = np.where(mask > 0.1, final, lips_only)
        
        # 對唇部進行輕微模糊
        blurred_lips = cv2.GaussianBlur(lips_only, (3, 3), 0)
        
        # 使用原始遮罩將模糊唇部與原始圖像合成
        mask_for_blur = np.where(mask > 0.1, 1.0, 0.0).astype(np.float32)
        result = image * (1 - mask_for_blur) + blurred_lips * mask_for_blur
        
        return result
    
    def apply_velvet_effect(
        self, 
        image: np.ndarray, 
        color_layer: np.ndarray, 
        mask: np.ndarray,
        opacity: float
    ) -> np.ndarray:
        """應用絲絨效果的口紅（介於霧面和珠光之間，但更偏向啞光）"""
        # 確保所有輸入都是float32類型
        image = image.astype(np.float32)
        color_layer = color_layer.astype(np.float32)
        mask = mask.astype(np.float32)
        
        # 混合顏色 - 絲絨效果需要更深的顏色基礎
        # 稍微加深顏色以增強絲絨質感
        deepened_color = color_layer * 0.85  # 降低亮度，呈現絲絨啞光感
        
        # 應用較高的不透明度來增強顏色表現
        velvet_opacity = min(1.0, opacity * 1.2)
        blended = image * (1 - mask * velvet_opacity) + deepened_color * (mask * velvet_opacity)
        
        # 添加細緻的絲絨質感 - 使用更微妙的紋理
        h, w, _ = mask.shape
        
        # 創建較為均勻細緻的紋理效果 - 絲絨的細微顆粒感
        texture = np.zeros((h, w), dtype=np.float32)
        
        # 使用更小的噪聲比例以創建更細緻的質感
        for scale in [2, 5, 10]:  # 更細緻的紋理比例
            noise = np.random.normal(0, 1, (h//scale+1, w//scale+1)).astype(np.float32)
            noise = cv2.resize(noise, (w, h))
            texture += noise * (scale / 30.0)  # 更低的噪聲強度
        
        # 使紋理更加均勻和細緻
        texture = cv2.GaussianBlur(texture, (3, 3), 0)
        texture = (texture - texture.min()) / (texture.max() - texture.min() + 1e-8)
        texture = texture * 0.09  # 微妙但可察覺的紋理效果
        
        # 將紋理轉換為3通道
        texture_3channel = np.zeros_like(blended)
        for c in range(3):
            texture_3channel[:, :, c] = texture
        
        # 只在唇部區域應用紋理
        texture_mask = texture_3channel * mask * 0.15
        
        # 絲絨效果特點: 啞光但有細膩質感，不平也不亮
        # 絲絨的微妙變化 - 小區域的明暗變化
        final = blended * (1.0 - texture_mask) + blended * (1.06 + texture_mask)
        
        # 輕微模糊唇部以創造柔和效果 - 絲絨的柔和感
        lips_only = np.zeros_like(final)
        lips_only = np.where(mask > 0.1, final, lips_only)
        
        # 非常輕微的模糊，僅足以消除紋理的尖銳邊緣
        blurred_lips = cv2.GaussianBlur(lips_only, (3, 3), 0)
        
        # 使模糊效果更加細微，保持一些質感 - 絲絨質感既柔和又有質感
        result = lips_only * 0.6 + blurred_lips * 0.4
        
        # 最終混合回原圖
        mask_for_result = np.where(mask > 0.1, 1.0, 0.0).astype(np.float32)
        result = image * (1 - mask_for_result) + result * mask_for_result
        
        # 裁剪到有效範圍
        result = np.clip(result, 0, 255)
        
        return result 