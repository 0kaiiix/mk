import cv2
import numpy as np
from flask import Flask, request, jsonify

from app.utils.face_detection import FaceDetector
from app.utils.lipstick_renderer import LipstickRenderer
from app.utils.recommendation import LipstickRecommender

# 初始化API
app = Flask(__name__)

# 初始化組件
face_detector = FaceDetector()
lipstick_renderer = LipstickRenderer()
recommender = LipstickRecommender()

@app.route('/api/v1/apply_lipstick', methods=['POST'])
def apply_lipstick():
    """應用口紅試妝API
    
    請求格式:
    {
        "texture_type": "matte",  // [matte|gloss|velvet]
        "color_rgb": [255, 100, 80],
        "opacity": 0.7  // 0-1
    }
    
    回應:
    {
        "status": "success",
        "processed_image_url": "path/to/image.jpg"
    }
    """
    try:
        # 獲取請求數據
        data = request.json
        texture_type = data.get('texture_type', 'matte')
        color_rgb = data.get('color_rgb', [255, 0, 0])
        opacity = float(data.get('opacity', 0.7))
        
        # 檢查參數有效性
        if texture_type not in ['matte', 'gloss', 'velvet']:
            return jsonify({"status": "error", "message": "無效的質地類型"}), 400
        
        if not isinstance(color_rgb, list) or len(color_rgb) != 3:
            return jsonify({"status": "error", "message": "無效的顏色格式"}), 400
        
        if opacity < 0 or opacity > 1:
            return jsonify({"status": "error", "message": "不透明度必須在0-1範圍內"}), 400
        
        # 獲取上傳的圖片
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "未找到圖片"}), 400
        
        image_file = request.files['image']
        image_data = image_file.read()
        image_array = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # 檢測面部及唇部
        landmarks, _ = face_detector.detect_face(image)
        if landmarks is None:
            return jsonify({"status": "error", "message": "未檢測到面部"}), 404
        
        # 獲取唇部遮罩
        lip_mask = face_detector.get_lip_mask(image, landmarks)
        if lip_mask is None:
            return jsonify({"status": "error", "message": "未檢測到唇部"}), 404
        
        # 應用口紅效果
        result = lipstick_renderer.apply_lipstick(
            image, 
            lip_mask, 
            color_rgb, 
            texture_type=texture_type, 
            opacity=opacity
        )
        
        # 保存處理後的圖片
        output_filename = "processed_image.jpg"
        cv2.imwrite(output_filename, result)
        
        return jsonify({
            "status": "success",
            "processed_image_url": output_filename
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"處理錯誤: {str(e)}"
        }), 500

@app.route('/api/v1/get_recommendations', methods=['POST'])
def get_recommendations():
    """獲取口紅推薦
    
    請求格式:
    {
        "hsv_values": [0, 50, 200]  // 可選，如未提供會使用圖片分析
    }
    或上傳圖片用於膚色分析
    
    回應:
    {
        "status": "success",
        "recommendations": {
            "warm_tones": [101, 102, 103],
            "cool_tones": [201, 202, 203],
            "neutral_tones": [301, 302, 303]
        }
    }
    """
    try:
        hsv_values = None
        
        # 檢查是否直接提供了HSV值
        if request.json and 'hsv_values' in request.json:
            hsv_values = request.json['hsv_values']
            if not isinstance(hsv_values, list) or len(hsv_values) != 3:
                return jsonify({"status": "error", "message": "無效的HSV格式"}), 400
        
        # 否則從上傳的圖片分析膚色
        elif 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()
            image_array = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            # 檢測面部
            landmarks, _ = face_detector.detect_face(image)
            if landmarks is None:
                return jsonify({"status": "error", "message": "未檢測到面部"}), 404
            
            # 獲取膚色
            hsv_values = face_detector.get_skin_tone(image, landmarks)
        else:
            # 如果既沒有提供HSV值也沒有上傳圖片，使用預設推薦
            pass
        
        # 獲取推薦
        recommendations = recommender.get_recommendations(hsv_values)
        
        return jsonify({
            "status": "success",
            "recommendations": recommendations
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"處理錯誤: {str(e)}"
        }), 500

@app.route('/api/v1/lipstick_details/<int:lipstick_id>', methods=['GET'])
def get_lipstick_details(lipstick_id):
    """獲取特定口紅詳情
    
    回應:
    {
        "status": "success",
        "details": {
            "id": 101,
            "color_rgb": [255, 69, 0],
            "texture": "matte",
            "tone": "warm"
        }
    }
    """
    try:
        details = recommender.get_lipstick_details(lipstick_id)
        if details is None:
            return jsonify({"status": "error", "message": "未找到該口紅色號"}), 404
        
        return jsonify({
            "status": "success",
            "details": details
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"處理錯誤: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 