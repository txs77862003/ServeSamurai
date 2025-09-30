#!/usr/bin/env python3
"""
Web UI上で手動サーブ切り取りを行うサーバー
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
import base64

class UIClipperHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GETリクエストの処理"""
        if self.path == '/':
            self.send_ui_clipping_page()
        elif self.path.startswith('/video/'):
            self.serve_video()
        elif self.path.startswith('/download/'):
            self.download_file()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """POSTリクエストの処理"""
        if self.path == '/upload':
            self.handle_upload()
        elif self.path == '/clip':
            self.handle_clip()
        else:
            self.send_error(404, "Not Found")
    
    def send_ui_clipping_page(self):
        """UI切り取りページを送信"""
        html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web UI サーブ切り取りシステム</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-section {
            border: 2px dashed #3498db;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            transition: all 0.3s ease;
        }
        .upload-section:hover {
            background-color: #f8f9fa;
            border-color: #2980b9;
        }
        .upload-section.dragover {
            background-color: #e3f2fd;
            border-color: #1976d2;
        }
        .player-section {
            display: none;
            margin: 20px 0;
        }
        .video-container {
            position: relative;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
        }
        video {
            width: 100%;
            height: auto;
            display: block;
        }
        .controls {
            background: #34495e;
            padding: 15px;
            border-radius: 0 0 10px 10px;
            color: white;
        }
        .control-row {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 10px 0;
        }
        .control-row button {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s ease;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover {
            background: #2980b9;
        }
        .btn-success {
            background: #27ae60;
            color: white;
        }
        .btn-success:hover {
            background: #229954;
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .btn-warning {
            background: #f39c12;
            color: white;
        }
        .btn-warning:hover {
            background: #e67e22;
        }
        .btn-info {
            background: #17a2b8;
            color: white;
        }
        .btn-info:hover {
            background: #138496;
        }
        .time-display {
            font-family: monospace;
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }
        .segment-list {
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }
        .segment-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        }
        .segment-info {
            flex: 1;
        }
        .segment-actions {
            display: flex;
            gap: 10px;
        }
        .segment-actions button {
            padding: 5px 10px;
            font-size: 12px;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #ecf0f1;
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: #3498db;
            transition: width 0.1s ease;
        }
        input[type="file"] {
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 100%;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: bold;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎾 Web UI サーブ切り取りシステム</h1>
        
        <!-- アップロードセクション -->
        <div class="upload-section" id="uploadSection">
            <h3>📁 動画ファイルをアップロード</h3>
            <p>テニスのサーブ動画を選択してください</p>
            <input type="file" id="videoFile" accept="video/*" />
            <br><br>
            <button class="btn-primary" id="uploadBtn" onclick="uploadVideo()">🚀 動画をアップロード</button>
        </div>
        
        <!-- プレーヤーセクション -->
        <div class="player-section" id="playerSection">
            <div class="video-container">
                <video id="videoPlayer" controls>
                    <source id="videoSource" type="video/mp4">
                    お使いのブラウザは動画タグをサポートしていません。
                </video>
                <div class="controls">
                    <div class="control-row">
                        <button class="btn-primary" onclick="playPause()">▶️ 再生/停止</button>
                        <button class="btn-primary" onclick="seekBackward()">⏪ 5秒戻る</button>
                        <button class="btn-primary" onclick="seekForward()">⏩ 5秒進む</button>
                        <button class="btn-primary" onclick="seekFrameBackward()">⏮️ フレーム戻る</button>
                        <button class="btn-primary" onclick="seekFrameForward()">⏭️ フレーム進む</button>
                    </div>
                    <div class="control-row">
                        <span class="time-display" id="timeDisplay">00:00 / 00:00</span>
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                    </div>
                    <div class="control-row">
                        <button class="btn-success" onclick="markServeStart()">🎯 サーブ開始マーク（自動で48フレーム切り取り）</button>
                        <button class="btn-warning" onclick="cancelCurrentSegment()">❌ キャンセル</button>
                        <button class="btn-info" onclick="resetAllSegments()">🔄 リセット</button>
                    </div>
                </div>
            </div>
            
            <!-- セグメント一覧 -->
            <div class="segment-list">
                <h3>📋 サーブセグメント一覧（各セグメントは開始から48フレーム）</h3>
                <div id="segmentList">
                    <p style="color: #7f8c8d;">まだセグメントがありません。サーブの開始をマークしてください（自動で48フレーム切り取り）。</p>
                </div>
                <div class="control-row">
                    <button class="btn-success" onclick="downloadSegments()">💾 切り取り実行</button>
                    <button class="btn-info" onclick="downloadSegmentsAsOne()">📦 全てを1つの動画に</button>
                </div>
            </div>
        </div>
        
        <!-- ステータス表示 -->
        <div id="status" class="status hidden"></div>
    </div>

    <script>
        let videoPlayer;
        let videoFile;
        let segments = [];
        let currentSegmentStart = null;
        let videoDuration = 0;
        
        // 初期化
        document.addEventListener('DOMContentLoaded', function() {
            videoPlayer = document.getElementById('videoPlayer');
            videoFile = document.getElementById('videoFile');
            
            // 動画イベントリスナー
            videoPlayer.addEventListener('loadedmetadata', function() {
                videoDuration = videoPlayer.duration;
                updateTimeDisplay();
            });
            
            videoPlayer.addEventListener('timeupdate', function() {
                updateTimeDisplay();
                updateProgressBar();
            });
            
            // キーボードショートカット
            document.addEventListener('keydown', function(e) {
                if (e.target.tagName === 'INPUT') return;
                
                switch(e.code) {
                    case 'Space':
                        e.preventDefault();
                        playPause();
                        break;
                    case 'KeyS':
                        markServeStart();
                        break;
                    case 'KeyC':
                        cancelCurrentSegment();
                        break;
                    case 'KeyR':
                        resetAllSegments();
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        seekBackward();
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        seekForward();
                        break;
                }
            });
        });
        
        // 動画アップロード
        async function uploadVideo() {
            const file = videoFile.files[0];
            if (!file) {
                showStatus('動画ファイルを選択してください', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('video', file);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 動画をプレーヤーに設定
                    const videoSource = document.getElementById('videoSource');
                    videoSource.src = data.video_url;
                    videoPlayer.load();
                    
                    // UIを切り替え
                    document.getElementById('uploadSection').style.display = 'none';
                    document.getElementById('playerSection').style.display = 'block';
                    
                    showStatus('動画がアップロードされました', 'success');
                } else {
                    showStatus('アップロードエラー: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('アップロードエラー: ' + error.message, 'error');
            }
        }
        
        // 再生/停止
        function playPause() {
            if (videoPlayer.paused) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
        }
        
        // シーク操作
        function seekBackward() {
            videoPlayer.currentTime = Math.max(0, videoPlayer.currentTime - 5);
        }
        
        function seekForward() {
            videoPlayer.currentTime = Math.min(videoDuration, videoPlayer.currentTime + 5);
        }
        
        function seekFrameBackward() {
            videoPlayer.currentTime = Math.max(0, videoPlayer.currentTime - 1/30); // 30fps想定
        }
        
        function seekFrameForward() {
            videoPlayer.currentTime = Math.min(videoDuration, videoPlayer.currentTime + 1/30);
        }
        
        // 時間表示更新
        function updateTimeDisplay() {
            const current = formatTime(videoPlayer.currentTime);
            const total = formatTime(videoDuration);
            document.getElementById('timeDisplay').textContent = `${current} / ${total}`;
        }
        
        // プログレスバー更新
        function updateProgressBar() {
            const progress = (videoPlayer.currentTime / videoDuration) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
        }
        
        // 時間フォーマット
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // サーブ開始マーク（自動48フレーム）
        function markServeStart() {
            // すぐに48フレーム固定のセグメントを追加
            const start = videoPlayer.currentTime;
            const segment = { start: start, frames: 48 };
            segments.push(segment);
            currentSegmentStart = null;
            showStatus(`開始 ${formatTime(start)} から48フレームを追加`, 'success');
            updateSegmentList();
        }
        
        // 現在のセグメントをキャンセル
        function cancelCurrentSegment() {
            if (currentSegmentStart !== null) {
                showStatus(`セグメントをキャンセル: ${formatTime(currentSegmentStart)}`, 'info');
                currentSegmentStart = null;
                updateSegmentList();
            } else {
                showStatus('キャンセルするセグメントがありません', 'error');
            }
        }
        
        // 全てのセグメントをリセット
        function resetAllSegments() {
            segments = [];
            currentSegmentStart = null;
            showStatus('全てのセグメントをリセットしました', 'info');
            updateSegmentList();
        }
        
        // セグメント一覧更新
        function updateSegmentList() {
            const segmentList = document.getElementById('segmentList');
            
            if (segments.length === 0 && currentSegmentStart === null) {
                segmentList.innerHTML = '<p style="color: #7f8c8d;">まだセグメントがありません。サーブの開始をマークしてください（自動で48フレーム）。</p>';
                return;
            }
            
            let html = '';
            
            // 既存のセグメント
            segments.forEach((segment, index) => {
                html += `
                    <div class="segment-item">
                        <div class="segment-info">
                            <strong>セグメント ${index + 1}</strong><br>
                            開始: ${formatTime(segment.start)} / 48フレーム固定
                        </div>
                        <div class="segment-actions">
                            <button class="btn-info" onclick="jumpToSegment(${index})">📍 ジャンプ</button>
                            <button class="btn-danger" onclick="deleteSegment(${index})">🗑️ 削除</button>
                        </div>
                    </div>
                `;
            });
            
            // 編集中のセグメント（開始のみ）
            if (currentSegmentStart !== null) {
                html += `
                    <div class="segment-item" style="border-left-color: #f39c12;">
                        <div class="segment-info">
                            <strong>編集中...</strong><br>
                            開始: ${formatTime(currentSegmentStart)} / 48フレーム予定
                        </div>
                        <div class="segment-actions">
                            <button class="btn-warning" onclick="cancelCurrentSegment()">❌ キャンセル</button>
                        </div>
                    </div>
                `;
            }
            
            segmentList.innerHTML = html;
        }
        
        // セグメントにジャンプ
        function jumpToSegment(index) {
            if (segments[index]) {
                videoPlayer.currentTime = segments[index].start;
            }
        }
        
        // セグメントを削除
        function deleteSegment(index) {
            segments.splice(index, 1);
            updateSegmentList();
            showStatus(`セグメント ${index + 1} を削除しました`, 'info');
        }
        
        // 切り取り実行
        async function downloadSegments() {
            if (segments.length === 0) {
                showStatus('切り取るセグメントがありません', 'error');
                return;
            }
            
            try {
                const response = await fetch('/clip', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        segments: segments
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus(`${data.clipped_videos.length}個の動画が切り取られました`, 'success');
                    
                    // ダウンロードリンクを表示
                    data.clipped_videos.forEach((video, index) => {
                        const link = document.createElement('a');
                        link.href = `/download/${video.filename}`;
                        link.download = video.filename;
                        link.textContent = `ダウンロード: ${video.filename}`;
                        link.style.display = 'block';
                        link.style.margin = '10px 0';
                        link.style.padding = '10px';
                        link.style.backgroundColor = '#3498db';
                        link.style.color = 'white';
                        link.style.textDecoration = 'none';
                        link.style.borderRadius = '5px';
                        link.style.textAlign = 'center';
                        document.body.appendChild(link);
                    });
                } else {
                    showStatus('切り取りエラー: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('切り取りエラー: ' + error.message, 'error');
            }
        }
        
        // 全てを1つの動画に
        async function downloadSegmentsAsOne() {
            if (segments.length === 0) {
                showStatus('切り取るセグメントがありません', 'error');
                return;
            }
            
            try {
                const response = await fetch('/clip', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        segments: segments,
                        merge: true
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('結合された動画が作成されました', 'success');
                    
                    // ダウンロードリンクを表示
                    const link = document.createElement('a');
                    link.href = `/download/${data.filename}`;
                    link.download = data.filename;
                    link.textContent = `ダウンロード: ${data.filename}`;
                    link.style.display = 'block';
                    link.style.margin = '10px 0';
                    link.style.padding = '10px';
                    link.style.backgroundColor = '#3498db';
                    link.style.color = 'white';
                    link.style.textDecoration = 'none';
                    link.style.borderRadius = '5px';
                    link.style.textAlign = 'center';
                    document.body.appendChild(link);
                } else {
                    showStatus('結合エラー: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('結合エラー: ' + error.message, 'error');
            }
        }
        
        // ステータス表示
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.classList.remove('hidden');
            
            setTimeout(() => {
                status.classList.add('hidden');
            }, 3000);
        }
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_video(self):
        """動画ファイルを提供"""
        try:
            from urllib.parse import unquote
            
            video_filename = unquote(self.path.split('/video/')[1])
            video_path = Path(__file__).parent / "uploads" / video_filename
            
            print(f"動画ファイル要求: {video_filename}")
            print(f"動画パス: {video_path}")
            print(f"存在確認: {video_path.exists()}")
            
            if not video_path.exists():
                self.send_error(404, f"Video not found: {video_filename}")
                return
            
            # 動画ファイルのサイズを取得
            file_size = video_path.stat().st_size
            
            # Range リクエストの処理
            range_header = self.headers.get('Range')
            if range_header:
                # Range リクエストを処理
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1
                
                content_length = end - start + 1
                
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(content_length))
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                
                with open(video_path, 'rb') as f:
                    f.seek(start)
                    chunk_size = 8192
                    remaining = content_length
                    
                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                # 通常のリクエスト
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                
                with open(video_path, 'rb') as f:
                    chunk_size = 8192
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                
        except Exception as e:
            # BrokenPipeErrorやConnectionResetErrorは無視
            if "Broken pipe" in str(e) or "Connection reset" in str(e):
                print(f"接続が切れました（正常）: {e}")
                return
            print(f"動画提供エラー: {e}")
            self.send_error(500, f"Video serve error: {str(e)}")
    
    def download_file(self):
        """ファイルをダウンロード"""
        try:
            filename = self.path.split('/download/')[1]
            file_path = Path(__file__).parent / "outputs" / filename
            
            if not file_path.exists():
                self.send_error(404, "File not found")
                return
            
            self.send_response(200)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-type', 'application/octet-stream')
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            # BrokenPipeErrorやConnectionResetErrorは無視
            if "Broken pipe" in str(e) or "Connection reset" in str(e):
                print(f"ダウンロード接続が切れました（正常）: {e}")
                return
            print(f"ダウンロードエラー: {e}")
            self.send_error(500, f"Download error: {str(e)}")
    
    def handle_upload(self):
        """動画アップロードと処理"""
        try:
            content_type = self.headers.get('content-type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Invalid content type")
                return
            
            # アップロードディレクトリを作成
            upload_dir = Path(__file__).parent / "uploads"
            upload_dir.mkdir(exist_ok=True)
            
            # マルチパートデータを解析
            boundary = content_type.split('boundary=')[1]
            content_length = int(self.headers['content-length'])
            data = self.rfile.read(content_length)
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
                                    filename = f"upload_{int(time.time())}.mp4"
                        
                        if b'\r\n\r\n' in part:
                            video_data = part.split(b'\r\n\r\n', 1)[1].split(b'\r\n--')[0]
            
            if video_data and filename:
                # ファイルを保存
                file_path = upload_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(video_data)
                
                # レスポンスを返す
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response_data = {
                    "success": True,
                    "video_url": f"/video/{filename}",
                    "filename": filename,
                    "message": "動画がアップロードされました"
                }
                
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_error(400, "No video file uploaded")
                
        except Exception as e:
            self.send_error(500, f"Upload error: {str(e)}")
    
    def handle_clip(self):
        """動画切り取り処理"""
        try:
            content_length = int(self.headers['content-length'])
            data = self.rfile.read(content_length)
            request_data = json.loads(data.decode('utf-8'))
            
            segments = request_data.get('segments', [])
            merge = request_data.get('merge', False)
            
            if not segments:
                self.send_error(400, "No segments provided")
                return
            
            # 出力ディレクトリを作成
            output_dir = Path(__file__).parent / "outputs"
            output_dir.mkdir(exist_ok=True)
            
            # 動画ファイルを探す
            upload_dir = Path(__file__).parent / "uploads"
            video_files = list(upload_dir.glob("*.mp4"))
            
            if not video_files:
                self.send_error(404, "No video file found")
                return
            
            video_path = video_files[0]  # 最新の動画ファイルを使用
            
            if merge:
                # 結合モード
                result = self.merge_segments(str(video_path), segments, str(output_dir))
            else:
                # 個別切り取りモード
                result = self.clip_segments(str(video_path), segments, str(output_dir))
            
            # レスポンスを返す
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                
        except Exception as e:
            self.send_error(500, f"Clip error: {str(e)}")
    
    def clip_segments(self, video_path: str, segments: list, output_dir: str) -> dict:
        """セグメントを個別に切り取り"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"動画情報: FPS={fps}, 総フレーム数={total_frames}")
            
            clipped_videos = []
            
            for i, segment in enumerate(segments):
                start_time = segment['start']
                start_frame = int(start_time * fps)
                if 'frames' in segment and segment['frames']:
                    target_frames = int(segment['frames'])
                    if target_frames < 1:
                        target_frames = 1
                    end_frame = min(start_frame + target_frames - 1, total_frames - 1)
                    end_time = end_frame / fps
                else:
                    end_time = segment['end']
                    end_frame = int(end_time * fps)
                
                print(f"セグメント {i+1}: {start_time:.2f}s-{end_time:.2f}s (フレーム {start_frame}-{end_frame})")
                
                # 出力ファイル名
                if 'frames' in segment and segment['frames']:
                    output_filename = f"serve_{i+1}_{int(start_time)}s_{int(end_frame - start_frame + 1)}f.mp4"
                else:
                    output_filename = f"serve_{i+1}_{int(start_time)}_{int(end_time)}.mp4"
                output_path = Path(output_dir) / output_filename
                
                # 動画ライターを設定
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(str(output_path), fourcc, fps, 
                                    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                     int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
                
                # セグメントのフレーム範囲を読み込み
                # フレーム位置を設定
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
                # 設定が正しく反映されたか確認
                actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                print(f"設定フレーム: {start_frame}, 実際のフレーム: {actual_frame}")
                
                # フレーム位置が正しくない場合は手動でスキップ
                if actual_frame != start_frame:
                    print(f"フレーム位置を手動で調整: {start_frame - actual_frame} フレームスキップ")
                    for _ in range(start_frame - actual_frame):
                        ret, _ = cap.read()
                        if not ret:
                            print("フレームスキップ中にエラー")
                            break
                
                frames_written = 0
                target_frames = end_frame - start_frame + 1
                print(f"目標フレーム数: {target_frames}")
                
                for frame_idx in range(target_frames):
                    ret, frame = cap.read()
                    if not ret:
                        print(f"フレーム読み込み失敗: {frame_idx}/{target_frames}")
                        break
                    out.write(frame)
                    frames_written += 1
                    
                    # 進捗表示
                    if frame_idx % 10 == 0:
                        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                        print(f"処理中: {frame_idx}/{target_frames}, 現在フレーム: {current_frame}")
                
                out.release()
                
                print(f"書き込み完了: {frames_written} フレーム")
                
                clipped_videos.append({
                    'filename': output_filename,
                    'path': str(output_path),
                    'start': start_time,
                    'end': end_time,
                    'duration': end_time - start_time
                })
            
            cap.release()
            
            return {
                "success": True,
                "clipped_videos": clipped_videos,
                "message": f"{len(clipped_videos)}個の動画が切り取られました"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def merge_segments(self, video_path: str, segments: list, output_dir: str) -> dict:
        """セグメントを1つの動画に結合"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"結合処理: FPS={fps}, 総フレーム数={total_frames}")
            
            # 出力ファイル名
            output_filename = f"merged_serves_{int(time.time())}.mp4"
            output_path = Path(output_dir) / output_filename
            
            # 動画ライターを設定
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, 
                                (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                 int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
            
            frames_written = 0
            
            for i, segment in enumerate(segments):
                start_time = segment['start']
                end_time = segment['end']
                
                start_frame = int(start_time * fps)
                end_frame = int(end_time * fps)
                
                print(f"結合セグメント {i+1}: {start_time:.2f}s-{end_time:.2f}s (フレーム {start_frame}-{end_frame})")
                
                # セグメントのフレーム範囲を読み込み
                # フレーム位置を設定
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
                # 設定が正しく反映されたか確認
                actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                print(f"結合 - 設定フレーム: {start_frame}, 実際のフレーム: {actual_frame}")
                
                # フレーム位置が正しくない場合は手動でスキップ
                if actual_frame != start_frame:
                    print(f"結合 - フレーム位置を手動で調整: {start_frame - actual_frame} フレームスキップ")
                    for _ in range(start_frame - actual_frame):
                        ret, _ = cap.read()
                        if not ret:
                            print("結合 - フレームスキップ中にエラー")
                            break
                
                segment_frames = 0
                target_frames = end_frame - start_frame + 1
                print(f"結合 - 目標フレーム数: {target_frames}")
                
                for frame_idx in range(target_frames):
                    ret, frame = cap.read()
                    if not ret:
                        print(f"結合 - フレーム読み込み失敗: {frame_idx}/{target_frames}")
                        break
                    out.write(frame)
                    frames_written += 1
                    segment_frames += 1
                
                print(f"セグメント {i+1} 書き込み完了: {segment_frames} フレーム")
            
            cap.release()
            out.release()
            
            print(f"結合完了: 総フレーム数 {frames_written}")
            
            return {
                "success": True,
                "filename": output_filename,
                "path": str(output_path),
                "total_frames": frames_written,
                "duration": frames_written / fps,
                "message": "結合された動画が作成されました"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        print("使用方法: python3 web_server_ui_clipper.py <ポート番号>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, UIClipperHandler)
    print(f"Web UI 切り取りサーバーが http://localhost:{port} で起動しました")
    print("Ctrl+C で停止")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しています...")
        httpd.shutdown()


if __name__ == "__main__":
    main()
