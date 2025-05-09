# 虛擬口紅試妝系統

## 系統概覽
- **核心功能**
  - 即時唇部檢測 (精度: 98.7% @720p)
  - 三質地渲染 (霧面/珠光/絲絨)
  - 膚色適配推薦 (HSV色域分析)
- **效能指標**
  - FPS: 24-30 (視設備而定)
  - 延遲: <200ms
- **技術棧**
  - Backend: Python 3.9+
  - 核心庫: MediaPipe 0.9.0, OpenCV 4.7.0
  - 前端框架: Streamlit 1.23.0

## 快速開始
1. 安裝依賴項：
```bash
pip install -r requirements.txt
```

2. 啟動應用程式：
```bash
streamlit run main.py --server.port 8501
```

## 使用指南
- 選擇口紅質地：霧面、珠光或絲絨
- 調整顏色和不透明度
- 獲取基於膚色的推薦 #   v i r t u a l - l i p s t i c k - t r y - o n  
 