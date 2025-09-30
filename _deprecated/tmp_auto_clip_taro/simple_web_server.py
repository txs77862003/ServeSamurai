#!/usr/bin/env python3
"""
シンプルなWebサーバー
tmp_auto_clip_taroディレクトリ内で完結するサーブ動画自動切り取り機能
"""

import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tempfile
import shutil
import email
import email.message

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from serve_auto_clipper import ServeAutoClipper

class AutoClipHandler(BaseHTTPRequestHandler):
    """サーブ動画自動切り取り用のHTTPハンドラー"""
    
    def do_GET(self):
        """GETリクエストの処理"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_html()
        elif parsed_path.path == '/status':
            self.serve_status()
        else:
            self.send_error(404, "File not found")
    
    def do_POST(self):
        """POSTリクエストの処理"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/upload':
            self.handle_upload()
        elif parsed_path.path == '/process':
            self.handle_process()
        else:
            self.send_error(404, "Endpoint not found")
    
    def serve_html(self):
        """メインHTMLページを提供"""
        html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>サーブ動画自動切り取り</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            background-color: #fafafa;
        }
        .upload-area:hover {
            border-color: #007bff;
            background-color: #f0f8ff;
        }
        input[type="file"] {
            margin: 10px 0;
        }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .progress {
            width: 100%;
            height: 20px;
            background-color: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background-color: #007bff;
            width: 0%;
            transition: width 0.3s;
        }
        .status {
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .status.success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .status.error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .status.info {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .results {
            margin-top: 20px;
            display: none;
        }
        .video-item {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            background-color: #f9f9f9;
        }
        .video-info {
            font-size: 14px;
            color: #666;
            margin: 5px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎾 サーブ動画自動切り取り</h1>
        
        <div class="upload-area">
            <h3>動画ファイルをアップロード</h3>
            <p>テニスサーブの動画をアップロードしてください。LSTMモデルが自動的にサーブを検出して切り取ります。</p>
            <input type="file" id="videoFile" accept="video/*" />
            <br>
            <button onclick="uploadAndProcess()" id="processBtn">動画を処理</button>
        </div>
        
        <div class="progress" id="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        
        <div class="status" id="status"></div>
        
        <div class="results" id="results"></div>
    </div>

    <script>
        let isProcessing = false;
        
        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }
        
        function hideStatus() {
            document.getElementById('status').style.display = 'none';
        }
        
        function showProgress(percent) {
            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progressBar');
            progress.style.display = 'block';
            progressBar.style.width = percent + '%';
        }
        
        function hideProgress() {
            document.getElementById('progress').style.display = 'none';
        }
        
        function showResults(data) {
            const results = document.getElementById('results');
            results.innerHTML = `
                <h3>処理結果</h3>
                <p>検出されたサーブ数: ${data.total_serves}個</p>
                ${data.clipped_videos.map((video, index) => `
                    <div class="video-item">
                        <strong>サーブ ${index + 1}</strong>
                        <div class="video-info">時間: ${video.start_time.toFixed(2)}s - ${video.end_time.toFixed(2)}s</div>
                        <div class="video-info">信頼度: ${(video.confidence * 100).toFixed(1)}%</div>
                        <div class="video-info">継続時間: ${video.duration.toFixed(2)}s</div>
                        <div class="video-info">ファイル: ${video.path}</div>
                    </div>
                `).join('')}
            `;
            results.style.display = 'block';
        }
        
        async function uploadAndProcess() {
            if (isProcessing) return;
            
            const fileInput = document.getElementById('videoFile');
            const file = fileInput.files[0];
            
            if (!file) {
                showStatus('動画ファイルを選択してください', 'error');
                return;
            }
            
            isProcessing = true;
            document.getElementById('processBtn').disabled = true;
            
            try {
                showStatus('動画をアップロード中...', 'info');
                showProgress(10);
                
                const formData = new FormData();
                formData.append('video', file);
                
                showProgress(30);
                showStatus('サーブを検出中...', 'info');
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                showProgress(70);
                showStatus('動画を切り取り中...', 'info');
                
                const result = await response.json();
                
                showProgress(100);
                
                if (result.success) {
                    showStatus('処理が完了しました！', 'success');
                    showResults(result.result);
                } else {
                    showStatus(`エラー: ${result.error}`, 'error');
                }
                
            } catch (error) {
                showStatus(`エラー: ${error.message}`, 'error');
            } finally {
                isProcessing = false;
                document.getElementById('processBtn').disabled = false;
                setTimeout(() => {
                    hideProgress();
                    hideStatus();
                }, 3000);
            }
        }
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_status(self):
        """ステータス情報を提供"""
        status = {
            "server": "Serve Auto Clipper",
            "version": "1.0.0",
            "status": "running"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode('utf-8'))
    
    def handle_upload(self):
        """ファイルアップロードの処理"""
        try:
            # マルチパートフォームデータを解析
            content_type = self.headers.get('content-type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Invalid content type")
                return
            
            # アップロードディレクトリを作成
            upload_dir = Path(__file__).parent / "uploads"
            upload_dir.mkdir(exist_ok=True)
            
            # ファイルを保存
            boundary = content_type.split('boundary=')[1]
            content_length = int(self.headers['content-length'])
            
            data = self.rfile.read(content_length)
            
            # 簡単なマルチパート解析
            parts = data.split(f'--{boundary}'.encode())
            video_data = None
            filename = None
            
            for part in parts:
                if b'Content-Disposition: form-data' in part:
                    if b'filename=' in part:
                        lines = part.split(b'\r\n')
                        for line in lines:
                            if b'filename=' in line:
                                try:
                                    filename = line.decode().split('filename="')[1].split('"')[0]
                                except:
                                    # フォールバック: エンコードされたファイル名
                                    filename = f"upload_{int(time.time())}.mp4"
                        # ファイルデータを取得
                        if b'\r\n\r\n' in part:
                            video_data = part.split(b'\r\n\r\n', 1)[1].split(b'\r\n--')[0]
            
            if video_data and filename:
                # ファイルを保存
                file_path = upload_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(video_data)
                
                # 自動切り取りを実行
                result = self.process_video(str(file_path))
                
                # レスポンスを返す
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response_data = {
                    "success": True,
                    "result": result,
                    "message": "動画の処理が完了しました"
                } if result else {
                    "success": False,
                    "error": "動画の処理に失敗しました"
                }
                
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
                # 動画ファイルは処理結果に含まれているので保持
                # 一時ファイルは処理完了後に削除される
            else:
                self.send_error(400, "No video file uploaded")
                
        except Exception as e:
            self.send_error(500, f"Upload error: {str(e)}")
    
    def process_video(self, video_path):
        """動画を処理"""
        try:
            clipper = ServeAutoClipper()
            result = clipper.process_video(video_path)
            return result
        except Exception as e:
            print(f"Processing error: {e}")
            return None

def run_server(port=8080):
    """Webサーバーを起動"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, AutoClipHandler)
    
    print(f"=== サーブ動画自動切り取りWebサーバー ===")
    print(f"URL: http://localhost:{port}")
    print(f"ディレクトリ: {Path(__file__).parent}")
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止します...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
