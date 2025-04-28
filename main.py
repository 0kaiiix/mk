import streamlit as st
import requests
import cv2
import numpy as np
from PIL import Image
import io
import os
import time
import base64
from streamlit_lottie import st_lottie
import json
from streamlit_image_comparison import image_comparison
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration

from app.utils.face_detection import FaceDetector
from app.utils.lipstick_renderer import LipstickRenderer
from app.utils.recommendation import LipstickRecommender
from app.utils.clahe_enhancer import CLAHEEnhancer
from app.utils.lipstick_library import get_all_brands, get_colors_for_brand, get_color_rgb, get_texture

# 初始化核心組件
face_detector = FaceDetector(max_num_faces=3)
lipstick_renderer = LipstickRenderer()
recommender = LipstickRecommender()
clahe_enhancer = CLAHEEnhancer()

# 設置緩存清理計時器
LAST_CLEANUP_TIME = None
CLEANUP_INTERVAL = 600  # 10分鐘

# 根據質地類型獲取預設顯色強度
def get_default_strength_by_texture(texture):
    if texture == "matte":  # 霧面
        return 0.3
    elif texture == "gloss":  # 珠光
        return 0.6
    elif texture == "velvet":  # 絲絨
        return 0.7
    else:
        return 0.4  # 默認值

# 載入 Lottie 動畫
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# 設置頁面背景
def set_background(image_file):
    with open(image_file, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    
    page_bg = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{data}");
        background-size: cover;
    }}
    .css-1avcm0n, .css-18e3th9, .css-1d391kg {{
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(5px);
    }}
    .css-1wrcr25 {{
        background-color: rgba(240, 242, 246, 0.8);
        border-radius: 15px;
        backdrop-filter: blur(5px);
    }}
    .stSidebar {{
        background-color: #4a4a4a !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
    }}
    .stSidebar * {{
        color: #fff !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 1px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px 10px 0px 0px;
        background-color: #f0f2f6;
        color: #333333;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        border-top: 1px solid #ddd;
        padding: 10px 15px;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: white;
    }}
    .stButton>button {{
        border-radius: 20px;
        background-color: #FF4B4B;
        color: white;
        transition: all 0.3s ease;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .stButton>button:hover {{
        background-color: #EB2929;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }}
    </style>
    '''
    st.markdown(page_bg, unsafe_allow_html=True)

# 自定義CSS樣式
def local_css():
    st.markdown("""
    <style>
    /* 顏色卡片樣式 */
    .color-card {
        border: 1px solid #ddd;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        margin-bottom: 10px;
        background-color: #fff6fa !important;
        color: #333 !important;
    }
    .color-card:hover {
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transform: translateY(-5px);
    }
    .color-preview {
        height: 70px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .color-name {
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 5px;
        color: #333 !important;
    }
    .texture-badge {
        display: inline-block;
        font-size: 12px;
        padding: 3px 8px;
        border-radius: 10px;
        background-color: #f0f2f6;
        color: #555;
        margin-top: 5px;
    }
    /* 推薦卡片、收藏卡片等通用卡片底色 */
    .rec-card, .fav-card, .stMarkdown > div[style*='background-color: white'] {
        background-color: #fff6fa !important;
        color: #333 !important;
    }
    /* 標題樣式 */
    h1 {
        background: linear-gradient(to right, #FF4B4B, #FF86A5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: 800 !important;
        white-space: nowrap; /* 防止標題換行 */
    }
    h2 {
        color: #FF4B4B;
        font-weight: 700 !important;
        margin-top: 2rem;
    }
    h3 {
        color: #444;
        font-weight: 600 !important;
    }
    /* 滑桿樣式 */
    .stSlider {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stSlider > div > div {
        height: 1rem;
    }
    .stSlider > div > div > div > div {
        background-color: #FF4B4B !important;
    }
    /* 表格頁籤樣式 */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #fff6fa !important;
        color: #333 !important;
        border-radius: 0px 15px 15px 15px;
        border: 1px solid #ddd;
        padding: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

class LipstickVideoTransformer(VideoTransformerBase):
    """用於處理實時攝像頭視頻的口紅效果應用器"""
    
    def __init__(self):
        """初始化視頻轉換器"""
        # 初始化唇部檢測器
        self.face_detector = FaceDetector(max_num_faces=3)  # 實時處理時支援多達3個人臉
        self.lipstick_renderer = LipstickRenderer()
        self.current_lipstick = None
        self.current_skin_tone = None  # 儲存最近檢測到的膚色HSV值
        self.skin_tone_updated = False  # 標記是否更新了膚色
        
    def set_lipstick(self, brand, color, texture, strength):
        """設置當前使用的口紅"""
        self.current_lipstick = {
            'brand': brand,
            'color': color,
            'texture': texture,
            'strength': strength
        }
    
    def get_skin_tone(self):
        """獲取當前檢測到的膚色HSV值"""
        return self.current_skin_tone
    
    def has_skin_tone_update(self):
        """檢查是否有新的膚色更新"""
        if self.skin_tone_updated:
            self.skin_tone_updated = False  # 重置標記
            return True
        return False
        
    def transform(self, frame):
        """處理每一幀視頻"""
        if self.current_lipstick is None:
            return frame
            
        img = frame.to_ndarray(format="bgr24")
        
        try:
            # 改用detect_multiple_faces檢測多個人臉
            all_landmarks = self.face_detector.detect_multiple_faces(img)
            
            if all_landmarks and len(all_landmarks) > 0:
                # 創建結果圖像副本
                result = img.copy()
                
                # 使用第一個人臉的膚色作為參考（用於推薦）
                first_face = all_landmarks[0]
                hsv_values = self.face_detector.get_skin_tone(img, first_face)
                if hsv_values is not None:
                    self.current_skin_tone = hsv_values
                    self.skin_tone_updated = True
                
                # 處理每個人臉
                for landmarks in all_landmarks:
                    # 獲取唇部遮罩
                    lip_mask = self.face_detector.get_lip_mask(img, landmarks)
                    
                    if lip_mask is not None:
                        # 獲取口紅顏色和質地
                        color_rgb = get_color_rgb(
                            self.current_lipstick['brand'], 
                            self.current_lipstick['color']
                        )
                        
                        # 應用口紅效果到當前人臉
                        face_result = self.lipstick_renderer.apply_lipstick(
                            result.copy(),
                            lip_mask,
                            color_rgb,
                            texture_type=self.current_lipstick['texture'],
                            opacity=self.current_lipstick['strength']
                        )
                        
                        # 使用遮罩將處理後的唇部區域合併到最終結果
                        mask_3channel = cv2.merge([lip_mask, lip_mask, lip_mask])
                        mask_normalized = mask_3channel.astype(float) / 255.0
                        
                        # 在遮罩區域用處理後的臉部替換結果圖像
                        result = (result * (1.0 - mask_normalized) + 
                                face_result * mask_normalized).astype(np.uint8)
                
                return result
                
        except Exception as e:
            # 如發生錯誤，返回原始圖像
            print(f"處理攝像頭影像時出錯: {str(e)}")
                
        return img

# 主程式
def main():
    """主應用程式入口"""
    # 設置頁面
    st.set_page_config(
        page_title="虛擬口紅試妝系統",
        page_icon="💄",
        layout="wide"
    )
    
    # 加載自定義CSS和背景
    try:
        set_background("app/assets/bg_pattern.png")
    except:
        pass
    local_css()
    
    # 初始化session state
    if 'current_lipstick' not in st.session_state:
        default_texture = "matte"
        st.session_state['current_lipstick'] = {
            'brand': 'MAC',
            'color': 'Ruby Woo',
            'texture': default_texture,
            'strength': get_default_strength_by_texture(default_texture)
        }
    
    if 'compare_mode' not in st.session_state:
        st.session_state['compare_mode'] = False
    
    if 'favorites' not in st.session_state:
        st.session_state['favorites'] = []
        
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    
    if 'webcam_mode' not in st.session_state:
        st.session_state['webcam_mode'] = False
        
    # 載入動畫
    lottie_lipstick = load_lottieurl("https://lottie.host/20ed6612-d631-4fba-9f0d-21feab85e805/0yzKdXtXqR.json")
    
    # 標題區塊
    col_title1, col_title2, col_title3 = st.columns([1, 3, 1])
    with col_title2:
        st.title("💄 虛擬口紅試妝系統")
        st.markdown("<p style='text-align: center; font-size: 1.2rem; margin-top: -1rem;'>探索最適合您的專屬口紅色彩</p>", unsafe_allow_html=True)
    
    with col_title3:
        if lottie_lipstick:
            st_lottie(lottie_lipstick, height=120, key="lipstick_anim")
    
    # 側邊欄 - 上傳圖片和控制
    with st.sidebar:
        st.markdown("<h3 style='text-align: center; color: #FF4B4B;'>💋 上傳照片 & 設定</h3>", unsafe_allow_html=True)
        
        # 上傳圖片選項
        st.markdown("#### 📸 上傳圖片")
        uploaded_file = st.file_uploader("選擇含有人臉的圖片", type=["jpg", "jpeg", "png"])
        
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        
        st.markdown("#### 🎨 口紅設定")
        
        # 品牌選擇
        all_brands = get_all_brands()
        selected_brand = st.selectbox(
            "品牌", 
            all_brands,
            index=all_brands.index(st.session_state['current_lipstick']['brand']) if st.session_state['current_lipstick']['brand'] in all_brands else 0,
            key="brand_selector"
        )
        
        # 色號選擇
        colors_for_brand = get_colors_for_brand(selected_brand)
        selected_color = st.selectbox(
            "色號", 
            colors_for_brand,
            index=colors_for_brand.index(st.session_state['current_lipstick']['color']) if st.session_state['current_lipstick']['color'] in colors_for_brand else 0,
            key="color_selector"
        )
        
        # 更新session state中的品牌和色號
        if selected_brand != st.session_state['current_lipstick']['brand'] or selected_color != st.session_state['current_lipstick']['color']:
            st.session_state['current_lipstick']['brand'] = selected_brand
            st.session_state['current_lipstick']['color'] = selected_color
            # 套用新設定時清除舊的處理結果
            if 'processed_image' in st.session_state:
                del st.session_state['processed_image']
                # 觸發頁面重新運行
                st.rerun()
        
        # 獲取選擇的色號對應的RGB值
        color_rgb = get_color_rgb(selected_brand, selected_color)
        
        # 顯示顏色預覽 - 改進樣式
        preview_html = f"""
        <div style="
            background-color: rgb{color_rgb}; 
            height: 70px; 
            border-radius: 15px; 
            margin: 10px 0px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position: absolute;
                bottom: 0;
                right: 0;
                background-color: rgba(255,255,255,0.8);
                padding: 5px 10px;
                border-top-left-radius: 10px;
                font-size: 12px;
                font-weight: bold;
            ">
                {selected_brand} {selected_color}
            </div>
        </div>
        """
        st.markdown(preview_html, unsafe_allow_html=True)
        
        # 獲取預設質地
        default_texture = get_texture(selected_brand, selected_color)
        
        # 質地選擇 - 使用更加視覺化的選項
        texture_options = {
            "霧面 (Matte)": "matte",
            "珠光 (Gloss)": "gloss",
            "絲絨 (Velvet)": "velvet"
        }
        
        # 反向映射，用於找到預設質地的顯示名稱
        reverse_texture_map = {v: k for k, v in texture_options.items()}
        current_texture = st.session_state['current_lipstick']['texture']
        default_texture_index = list(texture_options.values()).index(current_texture) if current_texture in texture_options.values() else list(texture_options.values()).index(default_texture)
        
        st.markdown("#### 質地選擇")
        texture_cols = st.columns(3)
        
        texture_icons = {
            "霧面 (Matte)": "🟥",
            "珠光 (Gloss)": "✨",
            "絲絨 (Velvet)": "🧶"
        }
        
        selected_texture = None
        
        for i, (texture_name, texture_val) in enumerate(texture_options.items()):
            with texture_cols[i]:
                is_selected = current_texture == texture_val
                icon = texture_icons.get(texture_name, "")
                if st.button(
                    f"{icon} {texture_name.split(' ')[0]}", 
                    key=f"tex_{texture_val}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                ):
                    selected_texture = texture_val
        
        if selected_texture and selected_texture != st.session_state['current_lipstick']['texture']:
            st.session_state['current_lipstick']['texture'] = selected_texture
            
            # 根據質地類型設定預設顯色強度
            if selected_texture == "matte":  # 霧面
                st.session_state['current_lipstick']['strength'] = 0.3
            elif selected_texture == "gloss":  # 珠光
                st.session_state['current_lipstick']['strength'] = 0.6
            elif selected_texture == "velvet":  # 絲絨
                st.session_state['current_lipstick']['strength'] = 0.7
                
            if 'processed_image' in st.session_state:
                del st.session_state['processed_image']
            st.rerun()
        
        # 口紅強度滑桿 - 添加更多視覺效果
        st.markdown("#### 口紅強度")
        strength_cols = st.columns([1, 3])
        with strength_cols[0]:
            st.markdown(f"### {int(st.session_state['current_lipstick']['strength'] * 10)}")
        with strength_cols[1]:
            strength = st.slider(
                "調整顯色度", 
                0.0, 1.0,
                st.session_state['current_lipstick']['strength'], 
                0.1,
                label_visibility="collapsed",
                help="調整口紅的顯色強度，數值越大效果越明顯",
                key="strength_slider"
            )
        
        # 更新session state中的強度
        if strength != st.session_state['current_lipstick']['strength']:
            st.session_state['current_lipstick']['strength'] = strength
            if 'processed_image' in st.session_state:
                del st.session_state['processed_image']
                st.rerun()
        
        # 比較模式開關
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        st.markdown("#### 🔄 進階選項")
        
        # 新增一行放置兩個選項
        mode_cols = st.columns(2)
        
        with mode_cols[0]:
            compare_mode = st.toggle("開啟比較模式", value=st.session_state['compare_mode'])
            if compare_mode != st.session_state['compare_mode']:
                st.session_state['compare_mode'] = compare_mode
                if 'processed_image' in st.session_state:
                    st.rerun()
        
        with mode_cols[1]:
            webcam_mode = st.toggle("開啟攝像頭實時試妝", value=st.session_state['webcam_mode'])
            if webcam_mode != st.session_state['webcam_mode']:
                st.session_state['webcam_mode'] = webcam_mode
                st.rerun()
                
        # 添加到收藏
        if 'processed_image' in st.session_state:
            if st.button("❤️ 加入收藏", use_container_width=True, type="secondary"):
                current = st.session_state['current_lipstick'].copy()
                if current not in st.session_state['favorites']:
                    st.session_state['favorites'].append(current)
                    st.success("已加入收藏！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("此口紅已在收藏中")
                    time.sleep(1)
                    st.rerun()
                    
        # 收藏按鈕
        if st.session_state['favorites'] and st.button("💖 查看收藏", use_container_width=True):
            st.session_state['show_favorites'] = True
            st.rerun()
        
        # 驚喜按鈕
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        st.markdown("#### 🎁 驚喜功能")
        
        surprise_col1, surprise_col2 = st.columns([3, 1])
        with surprise_col1:
            st.markdown("讓AI為您挑選一款驚喜口紅！")
        
        with surprise_col2:
            if st.button("🎲", help="隨機選擇一款適合您膚色的口紅", use_container_width=True, type="primary"):
                # 顯示驚喜動畫效果
                st.markdown("""
                <style>
                @keyframes surprise {
                    0% { transform: scale(0.5); opacity: 0; }
                    50% { transform: scale(1.2); opacity: 1; }
                    100% { transform: scale(1); opacity: 1; }
                }
                .surprise-container {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 200px;
                    margin: 20px 0;
                }
                .surprise-text {
                    font-size: 28px;
                    font-weight: bold;
                    color: #FF4B4B;
                    animation: surprise 1s ease-out;
                    text-align: center;
                }
                </style>
                <div class="surprise-container">
                    <div class="surprise-text">
                        選擇驚喜口紅中...✨
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 如果在攝像頭模式下且已檢測到膚色
                if st.session_state['webcam_mode'] and 'lipstick_video_transformer' in locals() and lipstick_video_transformer.get_skin_tone() is not None:
                    hsv_values = lipstick_video_transformer.get_skin_tone()
                    recommendations = recommender.get_recommendations(hsv_values)
                    
                    # 從所有推薦中隨機選擇一個ID
                    all_recommendations = recommendations["warm_tones"] + recommendations["cool_tones"] + recommendations["neutral_tones"]
                    import random
                    lipstick_id = random.choice(all_recommendations)
                    
                    # 獲取推薦詳情
                    details = recommender.get_lipstick_details(lipstick_id)
                    if details:
                        color_rgb = details["color_rgb"]
                        
                        # 尋找最接近的品牌色號
                        closest_brand = None
                        closest_color = None
                        min_distance = float('inf')
                        
                        for brand in all_brands:
                            for color_name in get_colors_for_brand(brand):
                                brand_rgb = get_color_rgb(brand, color_name)
                                # 計算RGB距離
                                distance = sum((a - b) ** 2 for a, b in zip(color_rgb, brand_rgb)) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_brand = brand
                                    closest_color = color_name
                        
                        if closest_brand and closest_color:
                            # 更新當前使用的口紅
                            st.session_state['current_lipstick']['brand'] = closest_brand
                            st.session_state['current_lipstick']['color'] = closest_color
                            texture = get_texture(closest_brand, closest_color)
                            st.session_state['current_lipstick']['texture'] = texture
                            # 使用質地對應的默認顯色強度
                            st.session_state['current_lipstick']['strength'] = get_default_strength_by_texture(texture)
                            
                            # 顯示漂亮的結果提示
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, #FF86A5, #FF4B4B);
                                padding: 2px;
                                border-radius: 15px;
                                margin: 20px 0;
                            ">
                                <div style="
                                    background-color: #fff6fa;
                                    border-radius: 13px;
                                    padding: 20px;
                                    text-align: center;
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    justify-content: center;
                                ">
                                    <div style="
                                        width: 80px;
                                        height: 80px;
                                        background-color: rgb{color_rgb};
                                        border-radius: 50%;
                                        margin-bottom: 15px;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                                    "></div>
                                    <h3 style="margin: 0; color: #333;">驚喜口紅!</h3>
                                    <p style="margin: 10px 0; color: #333; font-size: 18px; font-weight: bold;">
                                        {closest_brand} - {closest_color}
                                    </p>
                                    <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                        質地: {get_texture(closest_brand, closest_color)} | 強度: {get_default_strength_by_texture(texture)}
                                    </p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            time.sleep(2)
                            st.rerun()
                
                # 沒有膚色數據時，完全隨機選擇
                else:
                    # 隨機選擇品牌
                    import random
                    random_brand = random.choice(all_brands)
                    # 獲取該品牌的所有色號
                    colors = get_colors_for_brand(random_brand)
                    # 隨機選擇色號
                    random_color = random.choice(colors)
                    # 獲取質地
                    texture = get_texture(random_brand, random_color)
                    
                    # 更新當前使用的口紅
                    st.session_state['current_lipstick']['brand'] = random_brand
                    st.session_state['current_lipstick']['color'] = random_color
                    st.session_state['current_lipstick']['texture'] = texture
                    # 使用質地對應的默認顯色強度
                    st.session_state['current_lipstick']['strength'] = get_default_strength_by_texture(texture)
                    
                    # 顯示漂亮的結果提示
                    color_rgb = get_color_rgb(random_brand, random_color)
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #FF86A5, #FF4B4B);
                        padding: 2px;
                        border-radius: 15px;
                        margin: 20px 0;
                    ">
                        <div style="
                            background-color: #fff6fa;
                            border-radius: 13px;
                            padding: 20px;
                            text-align: center;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                        ">
                            <div style="
                                width: 80px;
                                height: 80px;
                                background-color: rgb{color_rgb};
                                border-radius: 50%;
                                margin-bottom: 15px;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                            "></div>
                            <h3 style="margin: 0; color: #333;">驚喜口紅!</h3>
                            <p style="margin: 10px 0; color: #333; font-size: 18px; font-weight: bold;">
                                {random_brand} - {random_color}
                            </p>
                            <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                質地: {texture} | 強度: {get_default_strength_by_texture(texture)}
                            </p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    time.sleep(2)
                    if 'processed_image' in st.session_state:
                        del st.session_state['processed_image']
                    st.rerun()
        
        # 在後台設置固定的多人臉數量
        if 'max_faces' not in st.session_state:
            st.session_state['max_faces'] = 3
        
        # 確保人臉檢測器使用正確的設置
        if face_detector.max_num_faces != st.session_state['max_faces']:
            face_detector.reinitialize(max_num_faces=st.session_state['max_faces'])
    
    # 主要內容區域
    if st.session_state['webcam_mode']:
        # 攝像頭模式
        st.header("📹 實時口紅試妝")
        st.markdown("對準攝像頭，可以實時查看口紅效果。請保持良好光線，臉部正對攝像頭。")
        
        # 創建一個新的LipstickVideoTransformer實例
        lipstick_video_transformer = LipstickVideoTransformer()
        
        # 設置口紅參數
        lipstick_video_transformer.set_lipstick(
            st.session_state['current_lipstick']['brand'],
            st.session_state['current_lipstick']['color'],
            st.session_state['current_lipstick']['texture'],
            st.session_state['current_lipstick']['strength']
        )
        
        # 設置WebRTC配置
        rtc_configuration = RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        )
        
        # 創建WebRTC流媒體
        webrtc_ctx = webrtc_streamer(
            key="lipstick-effect",
            video_transformer_factory=lambda: lipstick_video_transformer,
            rtc_configuration=rtc_configuration,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        
        # 顯示當前使用的口紅信息
        current = st.session_state['current_lipstick']
        texture_display = reverse_texture_map.get(current['texture'], current['texture'])
        color_rgb = get_color_rgb(current['brand'], current['color'])
        
        st.markdown(f"""
        <div style="
            background-color: #fff6fa;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 20px 0;
            display: flex;
            align-items: center;
        ">
            <div style="
                width: 80px;
                height: 80px;
                background-color: rgb{color_rgb};
                border-radius: 50%;
                margin-right: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            "></div>
            <div>
                <h3 style="margin: 0; color: #333;">實時應用: {current['brand']} {current['color']}</h3>
                <p style="margin: 5px 0; color: #666;">質地: {texture_display} | 顯色強度: {current['strength']}</p>
                <p style="margin: 5px 0; font-size: 0.8rem; color: #888;">從側邊欄選擇不同口紅可直接更換效果</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 提示信息
        st.info("💡 提示: 確保面部保持在攝像頭視野內，光線充足，效果最佳。如遇卡頓，可能是因為電腦處理能力有限。")
        
        # 添加推薦區域
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #FF86A5, #FF4B4B);
            padding: 2px;
            border-radius: 15px;
            margin: 30px 0 20px 0;
        ">
            <div style="
                background-color: #fff6fa;
                border-radius: 13px;
                padding: 20px;
                color: #333;
            ">
                <h2 style="margin-top: 0; text-align: center; color: #333;">👸 基於您的膚色推薦</h2>
                <p style="text-align: center; margin-top: 5px;">將實時檢測您的膚色並提供適合的口紅色號推薦</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 從攝像頭獲取膚色數據
        hsv_values = lipstick_video_transformer.get_skin_tone()
        
        # 使用更美觀的標籤頁切換不同場景推薦
        occasion_tabs = st.tabs(["✨ 日常妝容", "🎉 派對妝容", "💼 職場妝容"])
        
        # 如果已檢測到膚色，使用膚色數據獲取推薦
        if hsv_values is not None:
            # 獲取膚色適配的口紅推薦
            recommendations = recommender.get_recommendations(hsv_values)
            
            # 日常妝容推薦 - 使用推薦系統的結果
            with occasion_tabs[0]:
                daily_rec_items = []
                
                # 獲取推薦的暖色調和中性色調口紅
                for lipstick_id in recommendations["warm_tones"][:2] + recommendations["neutral_tones"][:3]:
                    details = recommender.get_lipstick_details(lipstick_id)
                    if details:
                        color_rgb = details["color_rgb"]
                        html_color = f"rgb{tuple(color_rgb)}"
                        
                        # 尋找品牌和色號與推薦的RGB最接近的口紅
                        closest_brand = None
                        closest_color = None
                        min_distance = float('inf')
                        
                        for brand in all_brands:
                            for color_name in get_colors_for_brand(brand):
                                brand_rgb = get_color_rgb(brand, color_name)
                                # 計算RGB距離
                                distance = sum((a - b) ** 2 for a, b in zip(color_rgb, brand_rgb)) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_brand = brand
                                    closest_color = color_name
                        
                        if closest_brand and closest_color:
                            texture = get_texture(closest_brand, closest_color)
                            
                            daily_rec_items.append({
                                "brand": closest_brand,
                                "color": closest_color,
                                "texture": texture,
                                "rgb": get_color_rgb(closest_brand, closest_color),
                                "html_color": f"rgb{get_color_rgb(closest_brand, closest_color)}"
                            })
                
                # 顯示推薦項目
                display_recommendations(daily_rec_items)
            
            # 派對妝容推薦
            with occasion_tabs[1]:
                party_rec_items = []
                
                # 獲取推薦的冷色調和暖色調中較鮮豔的口紅
                for lipstick_id in recommendations["cool_tones"][:3] + recommendations["warm_tones"][:2]:
                    details = recommender.get_lipstick_details(lipstick_id)
                    if details:
                        color_rgb = details["color_rgb"]
                        html_color = f"rgb{tuple(color_rgb)}"
                        
                        # 尋找品牌和色號與推薦的RGB最接近的口紅
                        closest_brand = None
                        closest_color = None
                        min_distance = float('inf')
                        
                        for brand in all_brands:
                            for color_name in get_colors_for_brand(brand):
                                brand_rgb = get_color_rgb(brand, color_name)
                                # 計算RGB距離
                                distance = sum((a - b) ** 2 for a, b in zip(color_rgb, brand_rgb)) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_brand = brand
                                    closest_color = color_name
                        
                        if closest_brand and closest_color:
                            texture = get_texture(closest_brand, closest_color)
                            
                            party_rec_items.append({
                                "brand": closest_brand,
                                "color": closest_color,
                                "texture": texture,
                                "rgb": get_color_rgb(closest_brand, closest_color),
                                "html_color": f"rgb{get_color_rgb(closest_brand, closest_color)}"
                            })
                
                # 顯示推薦項目
                display_recommendations(party_rec_items)
            
            # 職場妝容推薦
            with occasion_tabs[2]:
                work_rec_items = []
                
                # 獲取推薦的中性色調和冷色調中較柔和的口紅
                for lipstick_id in recommendations["neutral_tones"][:3] + recommendations["cool_tones"][:2]:
                    details = recommender.get_lipstick_details(lipstick_id)
                    if details:
                        color_rgb = details["color_rgb"]
                        html_color = f"rgb{tuple(color_rgb)}"
                        
                        # 尋找品牌和色號與推薦的RGB最接近的口紅
                        closest_brand = None
                        closest_color = None
                        min_distance = float('inf')
                        
                        for brand in all_brands:
                            for color_name in get_colors_for_brand(brand):
                                brand_rgb = get_color_rgb(brand, color_name)
                                # 計算RGB距離
                                distance = sum((a - b) ** 2 for a, b in zip(color_rgb, brand_rgb)) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_brand = brand
                                    closest_color = color_name
                        
                        if closest_brand and closest_color:
                            texture = get_texture(closest_brand, closest_color)
                            
                            work_rec_items.append({
                                "brand": closest_brand,
                                "color": closest_color,
                                "texture": texture,
                                "rgb": get_color_rgb(closest_brand, closest_color),
                                "html_color": f"rgb{get_color_rgb(closest_brand, closest_color)}"
                            })
                
                # 顯示推薦項目
                display_recommendations(work_rec_items)
        else:
            # 如果未檢測到膚色，顯示默認推薦
            with occasion_tabs[0]:
                shown_brands = set()
                rec_items = []
                
                for brand in all_brands:
                    if len(shown_brands) >= 5:
                        break
                        
                    for color_name in get_colors_for_brand(brand):
                        rgb = get_color_rgb(brand, color_name)
                        hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                        
                        # 偏中性、不太艷麗的色調適合日常
                        if 30 < hsv_img[1] < 160 and 90 < hsv_img[2] < 220:
                            texture = get_texture(brand, color_name)
                            html_color = f"rgb{rgb}"
                            
                            rec_items.append({
                                "brand": brand,
                                "color": color_name,
                                "texture": texture,
                                "rgb": rgb,
                                "html_color": html_color
                            })
                            
                            shown_brands.add(brand)
                            break
                
                # 顯示推薦項目
                display_recommendations(rec_items)
                
                # 提示用戶
                st.info("尚未檢測到膚色，請保持面部在攝像頭範圍內並確保光線充足")
            
            # 使用預設推薦繼續填充其他標籤頁
            # 派對妝容推薦
            with occasion_tabs[1]:
                # 與當前代碼相同的默認派對推薦
                shown_brands = set()
                rec_items = []
                
                for brand in all_brands:
                    if len(shown_brands) >= 5:
                        break
                        
                    for color_name in get_colors_for_brand(brand):
                        rgb = get_color_rgb(brand, color_name)
                        hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                        
                        # 高飽和度、高亮度的色調適合派對
                        if hsv_img[1] > 150 and hsv_img[2] > 160:
                            texture = get_texture(brand, color_name)
                            html_color = f"rgb{rgb}"
                            
                            rec_items.append({
                                "brand": brand,
                                "color": color_name,
                                "texture": texture,
                                "rgb": rgb,
                                "html_color": html_color
                            })
                            
                            shown_brands.add(brand)
                            break
                
                # 顯示推薦項目
                display_recommendations(rec_items)
            
            # 職場妝容推薦
            with occasion_tabs[2]:
                # 與當前代碼相同的默認職場推薦
                shown_brands = set()
                rec_items = []
                
                for brand in all_brands:
                    if len(shown_brands) >= 5:
                        break
                        
                    for color_name in get_colors_for_brand(brand):
                        rgb = get_color_rgb(brand, color_name)
                        hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                        
                        # 低飽和度、中等亮度的色調適合職場
                        if 20 < hsv_img[1] < 120 and 50 < hsv_img[2] < 160:
                            texture = get_texture(brand, color_name)
                            html_color = f"rgb{rgb}"
                            
                            rec_items.append({
                                "brand": brand,
                                "color": color_name,
                                "texture": texture,
                                "rgb": rgb,
                                "html_color": html_color
                            })
                            
                            shown_brands.add(brand)
                            break
                
                # 顯示推薦項目
                display_recommendations(rec_items)
                
    elif 'show_favorites' in st.session_state and st.session_state['show_favorites']:
        # 顯示收藏區域
        st.markdown("## 💖 我的收藏")
        if not st.session_state['favorites']:
            st.info("您還沒有收藏任何口紅")
        else:
            # 收藏項目展示
            fav_cols = st.columns(3)
            for i, fav in enumerate(st.session_state['favorites']):
                col_idx = i % 3
                with fav_cols[col_idx]:
                    color_rgb = get_color_rgb(fav['brand'], fav['color'])
                    texture_display = reverse_texture_map.get(fav['texture'], fav['texture'])
                    
                    # 美化收藏卡片
                    st.markdown(f"""
                    <div class="color-card">
                        <div class="color-preview" style="background-color: rgb{color_rgb};"></div>
                        <div class="color-name">{fav['brand']} {fav['color']}</div>
                        <div class="texture-badge">{texture_display} | 強度: {fav['strength']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("試用", key=f"try_fav_{i}", use_container_width=True):
                            st.session_state['current_lipstick'] = fav.copy()
                            st.session_state['show_favorites'] = False
                            if 'processed_image' in st.session_state:
                                del st.session_state['processed_image']
                            st.rerun()
                    with col2:
                        if st.button("移除", key=f"del_fav_{i}", use_container_width=True):
                            st.session_state['favorites'].pop(i)
                            st.rerun()
            
            # 返回按鈕
            if st.button("返回試妝", use_container_width=True):
                st.session_state['show_favorites'] = False
                st.rerun()
    
    elif uploaded_file is None:
        # 提示上傳圖片 - 使用更視覺化的指示
        st.markdown(
            """
            <div style="
                background-color: #f8f9fa;
                border-radius: 15px;
                padding: 30px;
                text-align: center;
                margin: 20px 0;
                border: 2px dashed #ddd;
            ">
                <img src="https://cdn-icons-png.flaticon.com/512/4225/4225192.png" width="100">
                <h3 style="margin-top: 15px; color: #555;">開始您的虛擬試妝體驗</h3>
                <p>請從側邊欄上傳一張含有人臉的清晰照片</p>
                <p style="font-size: 0.8rem; color: #888;">支持格式: JPG, JPEG, PNG</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 功能說明區域
        st.markdown("## ✨ 功能特色")
        
        feature_cols = st.columns(3)
        
        features = [
            {
                "icon": "https://cdn-icons-png.flaticon.com/512/2421/2421213.png",
                "title": "即時唇部檢測",
                "desc": "精準識別唇部輪廓，多達3個人臉同時檢測"
            },
            {
                "icon": "https://cdn-icons-png.flaticon.com/512/4696/4696958.png",
                "title": "三種質地渲染",
                "desc": "霧面、珠光、絲絨效果逼真呈現，調整顯色強度"
            },
            {
                "icon": "https://cdn-icons-png.flaticon.com/512/5832/5832416.png",
                "title": "膚色適配推薦",
                "desc": "基於膚色智能推薦適合的色號，打造專屬妝容"
            }
        ]
        
        for i, feature in enumerate(features):
            with feature_cols[i]:
                st.markdown(f"""
                <div style="
                    background-color: white;
                    border-radius: 15px;
                    padding: 28px 20px 28px 20px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                    height: 220px;
                    color: #333;
                ">
                    <img src=\"{feature['icon']}\" width=\"70\" style=\"margin-bottom: 0px;\">
                    <h4 style=\"color: #FF4B4B; margin-bottom: 2px; margin-top: 2px; text-align: center; width: 100%;\">{feature['title']}</h4>
                    <p style=\"color: #333; margin: 6px 10px 0 10px;\">{feature['desc']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # 品牌色號展示區域
        st.markdown("## 💄 探索品牌色號庫")
        
        # 使用標籤頁顯示各品牌
        brand_tabs = st.tabs(all_brands)
        
        for i, brand in enumerate(all_brands):
            with brand_tabs[i]:
                st.markdown(f"<h3 style='text-align: center;'>{brand} 色號系列</h3>", unsafe_allow_html=True)
                
                # 獲取該品牌的所有色號
                brand_colors = get_colors_for_brand(brand)
                
                # 創建網格佈局展示色號
                num_cols = 3  # 每行顯示3個色號
                for j in range(0, len(brand_colors), num_cols):
                    cols = st.columns(num_cols)
                    for k, col in enumerate(cols):
                        if j + k < len(brand_colors):
                            color_name = brand_colors[j + k]
                            color_rgb = get_color_rgb(brand, color_name)
                            texture = get_texture(brand, color_name)
                            html_color = f"rgb{color_rgb}"
                            # 使用更現代的卡片設計
                            with col:
                                st.markdown(f"""
                                <div class="color-card">
                                    <div class="color-preview" style="background-color: {html_color};"></div>
                                    <div class="color-name">{color_name}</div>
                                    <div class="texture-badge">{texture}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                                # 使用按鈕選擇色號
                                if st.button("選擇", key=f"lib_btn_{brand}_{color_name}".replace(" ", "_"), use_container_width=True):
                                    st.session_state['current_lipstick']['brand'] = brand
                                    st.session_state['current_lipstick']['color'] = color_name
                                    st.session_state['current_lipstick']['texture'] = texture
                                    if 'processed_image' in st.session_state:
                                        del st.session_state['processed_image']
                                    st.rerun()
    
    else:
        # 讀取上傳的圖片
        image = Image.open(uploaded_file)
        
        # 轉換為OpenCV格式
        image_cv = np.array(image)
        if image_cv.shape[2] == 4:  # 如果是RGBA
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2BGR)
        else:
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)
        
        # 顯示處理進度指示器
        with st.spinner("正在檢測臉部..."):
            # 檢測面部 - 改為檢測多個人臉
            all_landmarks = face_detector.detect_multiple_faces(image_cv)
        
        # 檢查是否找到面部
            if not all_landmarks:
                st.error("⚠️ 未檢測到面部！請上傳包含清晰面部的圖片。")
                
                # 提供更多幫助信息
                st.markdown("""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 20px;">
                    <h4>💡 提示：</h4>
                    <ul>
                        <li>請確保照片中有清晰可見的人臉</li>
                        <li>照片光線充足，避免過暗或過曝</li>
                        <li>臉部朝向正面，避免角度過大</li>
                        <li>避免過多遮擋物（如口罩、太陽眼鏡等）</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                return
        
        # 處理每個檢測到的人臉
        processed_faces = []
        
        # 進度條展示處理進度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, landmarks in enumerate(all_landmarks):
            status_text.text(f"正在處理第 {i+1}/{len(all_landmarks)} 個人臉...")
            progress_value = (i) / len(all_landmarks)
            progress_bar.progress(progress_value)
            
            # 獲取唇部遮罩
            lip_mask = face_detector.get_lip_mask(image_cv, landmarks)
            if lip_mask is None:
                st.warning(f"⚠️ 未能準確識別第 {i+1} 個人臉的唇部區域")
                continue
            
            # 獲取當前口紅設置
            current = st.session_state['current_lipstick']
            color_rgb = get_color_rgb(current['brand'], current['color'])
            
            # 應用口紅效果
            try:
                result = lipstick_renderer.apply_lipstick(
                    image_cv.copy(),
                    lip_mask,
                    color_rgb,
                    texture_type=current['texture'],
                    opacity=current['strength']
                )
                
                # 將處理後的人臉保存到列表
                processed_faces.append(result)
            except Exception as e:
                st.error(f"處理第 {i+1} 個人臉時出錯: {str(e)}")
        
        # 完成進度
        progress_bar.progress(1.0)
        status_text.text("處理完成！")
        time.sleep(0.5)
        status_text.empty()
        progress_bar.empty()
        
        # 如果有成功處理的人臉
        if processed_faces:
            # 創建一個基於原始圖像的副本作為最終結果
            final_result = image_cv.copy()
            
            # 修正多個人臉的處理方式
            if len(processed_faces) == 1:
                # 只有一個人臉時直接使用處理後的結果
                final_result = processed_faces[0]
            else:
                # 多個人臉時，需要將每個人臉的修改合併到原圖
                for i, face_result in enumerate(processed_faces):
                    # 獲取當前臉部的唇部遮罩
                    current_mask = face_detector.get_lip_mask(image_cv, all_landmarks[i])
                    if current_mask is None:
                        continue
                        
                    # 將遮罩擴展為3通道以適應圖像合併
                    mask_3channel = cv2.merge([current_mask, current_mask, current_mask])
                    
                    # 使用遮罩將處理後的唇部區域合併到最終結果
                    mask_normalized = mask_3channel.astype(float) / 255.0
                    
                    # 在遮罩區域用處理後的臉部替換原圖
                    final_result = (final_result * (1.0 - mask_normalized) + 
                                   face_result * mask_normalized).astype(np.uint8)
            
            # 轉換回PIL格式以顯示
            result_rgb = cv2.cvtColor(final_result, cv2.COLOR_BGR2RGB)
            result_image = Image.fromarray(result_rgb)
            original_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
            original_image = Image.fromarray(original_rgb)
            
            # 保存到session state
            st.session_state['processed_image'] = result_image
            st.session_state['original_image'] = original_image
            
            # 添加到歷史記錄
            if 'processed_image' in st.session_state:
                history_item = {
                    'lipstick': st.session_state['current_lipstick'].copy(),
                    'timestamp': time.time()
                }
                if history_item not in st.session_state['history']:
                    st.session_state['history'].append(history_item)
                    # 限制歷史記錄數量
                    if len(st.session_state['history']) > 10:
                        st.session_state['history'].pop(0)
            
            # 結果展示區域
            if st.session_state['compare_mode']:
                # 對比模式 - 使用滑桿對比原圖和效果圖
                st.markdown("### 👁️ 前後對比")
                image_comparison(
                    img1=original_image,
                    img2=result_image,
                    label1="原始照片",
                    label2="套用效果",
                    width=700
                )
                
                # 顯示當前使用的口紅卡片
                current = st.session_state['current_lipstick']
                texture_display = reverse_texture_map.get(current['texture'], current['texture'])
                color_rgb = get_color_rgb(current['brand'], current['color'])
                
                st.markdown(f"""
                <div style="
                    background-color: white;
                    padding: 20px;
                    border-radius: 15px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    margin: 20px 0;
                    display: flex;
                    align-items: center;
                ">
                    <div style="
                        width: 80px;
                        height: 80px;
                        background-color: rgb{color_rgb};
                        border-radius: 50%;
                        margin-right: 20px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    "></div>
                    <div>
                        <h3 style="margin: 0; color: #333;">{current['brand']} {current['color']}</h3>
                        <p style="margin: 5px 0; color: #666;">質地: {texture_display} | 顯色強度: {current['strength']}</p>
                        <p style="margin: 5px 0; font-size: 0.8rem; color: #888;">處理人臉數: {len(processed_faces)}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            else:
                # 標準模式 - 並排顯示原圖和效果圖
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("<h3 style='text-align: center;'>🔍 原始照片</h3>", unsafe_allow_html=True)
                    st.image(original_image, use_container_width=True)
                
                with col2:
                    st.markdown("<h3 style='text-align: center;'>✨ 套用效果</h3>", unsafe_allow_html=True)
                    st.image(result_image, use_container_width=True)
                
                # 顯示當前使用的口紅信息 - 使用更美觀的卡片
                current = st.session_state['current_lipstick']
                texture_display = reverse_texture_map.get(current['texture'], current['texture'])
                color_rgb = get_color_rgb(current['brand'], current['color'])
                
                st.markdown(f"""
                <div style="
                    background-color: white;
                    padding: 20px;
                    border-radius: 15px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    margin: 20px 0;
                    display: flex;
                    align-items: center;
                ">
                    <div style="
                        width: 80px;
                        height: 80px;
                        background-color: rgb{color_rgb};
                        border-radius: 50%;
                        margin-right: 20px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    "></div>
                    <div>
                        <h3 style="margin: 0; color: #333;">{current['brand']} {current['color']}</h3>
                        <p style="margin: 5px 0; color: #666;">質地: {texture_display} | 顯色強度: {current['strength']}</p>
                        <p style="margin: 5px 0; font-size: 0.8rem; color: #888;">處理人臉數: {len(processed_faces)}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
            # 獲取膚色並提供推薦
            with st.spinner("分析膚色..."):
                # 使用第一個檢測到的人臉進行膚色分析
                hsv_values = face_detector.get_skin_tone(image_cv, all_landmarks[0])
            
                # 推薦區域
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #FF86A5, #FF4B4B);
                    padding: 2px;
                    border-radius: 15px;
                    margin: 30px 0 20px 0;
                ">
                    <div style="
                        background-color: #fff6fa;
                        border-radius: 13px;
                        padding: 20px;
                        color: #333;
                    ">
                        <h2 style="margin-top: 0; text-align: center; color: #333;">👸 基於您的膚色推薦</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 使用更美觀的標籤頁切換不同場景推薦
                occasion_tabs = st.tabs(["✨ 日常妝容", "🎉 派對妝容", "💼 職場妝容"])
            
            # 簡單定義各色調特徵，用於篩選
            warm_tones_range = [(160, 250), (50, 230), (30, 150)]  # H, S, V 範圍
            cool_tones_range = [(250, 340), (30, 200), (30, 150)]
            neutral_tones_range = [(0, 40), (30, 150), (80, 180)]
            
            # 根據膚色HSV值選擇適合的色調
            def is_in_range(color, ranges):
                for i, (min_val, max_val) in enumerate(ranges):
                    if i >= len(color) or color[i] < min_val or color[i] > max_val:
                        return False
                return True
                
            try:
                # 日常妝容推薦
                with occasion_tabs[0]:
                    shown_brands = set()
                    rec_items = []
                    
                    for brand in all_brands:
                        if len(shown_brands) >= 5:
                            break
                            
                        for color_name in get_colors_for_brand(brand):
                            rgb = get_color_rgb(brand, color_name)
                            hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                            
                            # 偏中性、不太艷麗的色調適合日常
                            if 30 < hsv_img[1] < 160 and 90 < hsv_img[2] < 220:
                                texture = get_texture(brand, color_name)
                                html_color = f"rgb{rgb}"
                                
                                rec_items.append({
                                    "brand": brand,
                                    "color": color_name,
                                    "texture": texture,
                                    "rgb": rgb,
                                    "html_color": html_color
                                })
                                
                                shown_brands.add(brand)
                                break
                    
                    # 顯示推薦項目
                    display_recommendations(rec_items)
                
                # 派對妝容推薦
                with occasion_tabs[1]:
                    shown_brands = set()
                    rec_items = []
                    
                    for brand in all_brands:
                        if len(shown_brands) >= 5:
                            break
                            
                        for color_name in get_colors_for_brand(brand):
                            rgb = get_color_rgb(brand, color_name)
                            hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                            
                            # 高飽和度、高亮度的色調適合派對
                            if hsv_img[1] > 150 and hsv_img[2] > 160:
                                texture = get_texture(brand, color_name)
                                html_color = f"rgb{rgb}"
                                
                                rec_items.append({
                                    "brand": brand,
                                    "color": color_name,
                                    "texture": texture,
                                    "rgb": rgb,
                                    "html_color": html_color
                                })
                                
                                shown_brands.add(brand)
                                break
                    
                    # 顯示推薦項目
                    display_recommendations(rec_items)
                
                # 職場妝容推薦
                with occasion_tabs[2]:
                    shown_brands = set()
                    rec_items = []
                    
                    for brand in all_brands:
                        if len(shown_brands) >= 5:
                            break
                            
                        for color_name in get_colors_for_brand(brand):
                            rgb = get_color_rgb(brand, color_name)
                            hsv_img = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
                            
                            # 低飽和度、中等亮度的色調適合職場
                            if 20 < hsv_img[1] < 120 and 50 < hsv_img[2] < 160:
                                texture = get_texture(brand, color_name)
                                html_color = f"rgb{rgb}"
                                
                                rec_items.append({
                                    "brand": brand,
                                    "color": color_name,
                                    "texture": texture,
                                    "rgb": rgb,
                                    "html_color": html_color
                                })
                                
                                shown_brands.add(brand)
                                break
                    
                    # 顯示推薦項目
                    display_recommendations(rec_items)
            except Exception as e:
                st.error(f"在生成膚色推薦時發生錯誤: {str(e)}")
                
            # 添加歷史記錄展示
            if st.session_state['history']:
                st.markdown("""
                <div style="margin: 30px 0 10px 0; color: #333;">
                    <h3 style='color: #333;'>🕒 最近試色歷史</h3>
                                </div>
                """, unsafe_allow_html=True)
                
                history_items = st.session_state['history'][-5:] # 只顯示最近5個
                history_cols = st.columns(min(5, len(history_items)))
                
                for i, (col, item) in enumerate(zip(history_cols, reversed(history_items))):
                    with col:
                        lipstick = item['lipstick']
                        brand = lipstick['brand']
                        color = lipstick['color']
                        color_rgb = get_color_rgb(brand, color)
                        
                        st.markdown(f"""
                        <div style="
                            background-color: white;
                            border-radius: 10px;
                            padding: 10px;
                            text-align: center;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                        ">
                            <div style="
                                background-color: rgb{color_rgb}; 
                                height: 40px; 
                                border-radius: 8px;
                                margin-bottom: 5px;
                            "></div>
                            <div style="font-size: 0.8rem; font-weight: bold; color: #333;">{brand}</div>
                            <div style="font-size: 0.7rem; color: #333;">{color}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("套用", key=f"history_{i}", use_container_width=True, type="secondary"):
                            st.session_state['current_lipstick'] = lipstick.copy()
                            if 'processed_image' in st.session_state:
                                del st.session_state['processed_image']
                            st.rerun()
    
    # 解決循環引用問題 - 懶加載API模組
    if 'flask_installed' not in st.session_state:
        try:
            import flask
            st.session_state['flask_installed'] = True
        except ImportError:
            if st.button("安裝Flask (僅首次運行需要)"):
                with st.spinner("正在安裝Flask..."):
                    import subprocess
                    subprocess.check_call(['pip', 'install', 'flask'])
                    st.success("安裝成功！請刷新頁面。")


# 顯示推薦項目的函數
def display_recommendations(rec_items):
    if not rec_items:
        st.info("無法找到適合的推薦色號")
        return
        
    # 使用更現代的卡片佈局
    rec_cols = st.columns(min(3, len(rec_items)))
    
    for i, (col, item) in enumerate(zip(rec_cols, rec_items)):
        with col:
            st.markdown(f"""
            <div style="
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                padding: 15px;
                text-align: center;
                transition: all 0.3s ease;
                height: 100%;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    background-color: {item['html_color']};
                    border-radius: 50%;
                    margin: 0 auto 15px auto;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                "></div>
                <h4 style="margin: 5px 0;">{item['brand']}</h4>
                <div style="font-weight: bold; margin-bottom: 5px;">{item['color']}</div>
                <div style="
                    display: inline-block;
                    background-color: #f0f2f6;
                    font-size: 0.8rem;
                    padding: 3px 10px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                ">{item['texture']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("立即試色", key=f"rec_btn_{item['brand']}_{item['color']}".replace(" ", "_"), use_container_width=True):
                st.session_state['current_lipstick']['brand'] = item['brand']
                st.session_state['current_lipstick']['color'] = item['color']
                st.session_state['current_lipstick']['texture'] = item['texture']
                if 'processed_image' in st.session_state:
                    del st.session_state['processed_image']
                st.rerun()


if __name__ == "__main__":
    main() 