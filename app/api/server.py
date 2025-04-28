from app.api.api import app

def run_server(host='0.0.0.0', port=5000, debug=False):
    """運行API服務器
    
    Args:
        host: 主機地址
        port: 端口
        debug: 是否開啟調試模式
    """
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server(debug=True) 