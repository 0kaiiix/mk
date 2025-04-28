from app.api.server import run_server
 
if __name__ == "__main__":
    print("啟動虛擬口紅試妝系統 API 服務器...")
    print("服務器運行於 http://127.0.0.1:5000/")
    run_server(host="127.0.0.1", port=5000, debug=True) 