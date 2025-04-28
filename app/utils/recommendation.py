import numpy as np

class LipstickRecommender:
    """口紅色彩推薦系統，基於膚色HSV值推薦適合的口紅色號"""
    
    def __init__(self):
        """初始化推薦系統和預設色庫"""
        # 預設色庫 - 格式: {色號ID: [R, G, B, 質地類型, 暖/冷色調]}
        self.color_library = {
            # 暖色調 - 橘紅、橘粉、珊瑚色
            101: [255, 69, 0, "matte", "warm"],    # 熱情橘紅
            102: [255, 99, 71, "matte", "warm"],   # 珊瑚橘
            103: [255, 127, 80, "velvet", "warm"], # 珊瑚粉
            104: [240, 128, 128, "gloss", "warm"], # 淺珊瑚紅
            105: [205, 92, 92, "matte", "warm"],   # 印第安紅
            
            # 冷色調 - 莓紅、玫紅、紫紅
            201: [199, 21, 133, "matte", "cool"],   # 中紫紅
            202: [219, 112, 147, "gloss", "cool"],  # 苺紅
            203: [176, 48, 96, "velvet", "cool"],   # 覆盆子紅
            204: [220, 20, 60, "matte", "cool"],    # 猩紅
            205: [139, 0, 139, "velvet", "cool"],   # 深洋紅
            
            # 中性色調 - 玫瑰、裸色
            301: [188, 143, 143, "velvet", "neutral"], # 玫瑰褐
            302: [222, 184, 135, "matte", "neutral"],  # 暖裸色
            303: [210, 180, 140, "gloss", "neutral"],  # 棕褐色
            304: [245, 222, 179, "velvet", "neutral"], # 小麥色
            305: [160, 82, 45, "matte", "neutral"],    # 棕赭色
        }
    
    def get_recommendations(self, hsv_values):
        """根據膚色HSV值獲取推薦的口紅色號
        
        Args:
            hsv_values: 膚色HSV值 [H, S, V]
            
        Returns:
            recommendations: 包含不同色調推薦的字典
        """
        if hsv_values is None:
            # 如果沒有膚色信息，返回預設推薦
            return {
                "warm_tones": [101, 102, 103],
                "cool_tones": [201, 202, 203],
                "neutral_tones": [301, 302, 303]
            }
        
        # 提取HSV分量
        h, s, v = hsv_values
        
        # 判斷膚色調性
        # H值: 0-30, 330-360為暖色調(紅、橙、黃)
        # H值: 30-330為冷色調(綠、藍、紫)
        is_warm = (h < 30) or (h > 330)
        
        # 根據膚色明度(V)和飽和度(S)進行推薦
        recommendations = {
            "warm_tones": [],
            "cool_tones": [],
            "neutral_tones": []
        }
        
        # 為每種色調選擇最適合的3種口紅
        warm_candidates = [id for id, info in self.color_library.items() if info[4] == "warm"]
        cool_candidates = [id for id, info in self.color_library.items() if info[4] == "cool"]
        neutral_candidates = [id for id, info in self.color_library.items() if info[4] == "neutral"]
        
        # 根據膚色明度調整推薦
        if v < 100:  # 較深膚色
            # 深膚色適合鮮豔色彩，提高對比度
            warm_preference = [101, 102, 105]  # 較鮮豔的暖色調
            cool_preference = [201, 204, 205]  # 較鮮豔的冷色調
            neutral_preference = [301, 302, 305]  # 較深的中性色調
        elif v < 170:  # 中等膚色
            warm_preference = [102, 103, 104]  # 中等亮度暖色調
            cool_preference = [201, 202, 203]  # 中等亮度冷色調
            neutral_preference = [301, 302, 303]  # 中等亮度中性色調
        else:  # 較淺膚色
            warm_preference = [103, 104, 105]  # 較深暖色調，增加對比
            cool_preference = [202, 203, 204]  # 較深冷色調，增加對比
            neutral_preference = [302, 303, 305]  # 較深中性色調
        
        # 根據膚色調性進一步優化推薦
        if is_warm:
            # 暖色調膚色優先推薦暖色唇色和中性色
            recommendations["warm_tones"] = warm_preference
            recommendations["neutral_tones"] = neutral_preference
            recommendations["cool_tones"] = cool_preference
        else:
            # 冷色調膚色優先推薦冷色唇色和中性色
            recommendations["cool_tones"] = cool_preference
            recommendations["neutral_tones"] = neutral_preference
            recommendations["warm_tones"] = warm_preference
        
        return recommendations
    
    def get_lipstick_details(self, lipstick_id):
        """獲取特定口紅色號的詳細信息
        
        Args:
            lipstick_id: 口紅色號ID
            
        Returns:
            details: 口紅詳細信息
        """
        if lipstick_id not in self.color_library:
            return None
        
        lipstick_info = self.color_library[lipstick_id]
        return {
            "id": lipstick_id,
            "color_rgb": lipstick_info[:3],
            "texture": lipstick_info[3],
            "tone": lipstick_info[4]
        } 