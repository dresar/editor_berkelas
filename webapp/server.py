import os
import sys
import json
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = r"C:\Users\NCN0C\Music\editor_berkelas"
INPUT_FOLDER = os.path.join(BASE_DIR, "1")
OUTPUT_FOLDER = os.path.join(INPUT_FOLDER, "outputs")
PYTHON_EXE = r"C:\Users\NCN0C\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe"

active_process = None

@app.route('/api/videos', methods=['GET'])
def get_videos():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.mp4')]
    files.sort()
    return jsonify({"count": len(files), "videos": files})

@app.route('/api/preview', methods=['POST'])
def generate_preview():
    data = request.json or {}
    video_name = data.get("video_name", "Da4v-LRzfru.mp4")
    badge_text = data.get("badge_text", "EDITOR BERKELAS")
    headline_text = data.get("headline_text", "PPT Sidang Skripsi Anti Dosen Baper!")
    
    video_x = data.get("video_x", 40)
    video_y = data.get("video_y", 460)
    video_w = data.get("video_w", 1000)
    video_h = data.get("video_h", 1360)
    video_radius = data.get("video_radius", 30)
    
    show_logo = data.get("show_logo", True)
    # If logo_scale is small (e.g. 200 from web UI screen scale), convert or default to 450 when prompt calibration matches
    logo_w = data.get("logo_scale", 450)
    if logo_w < 300:
        logo_w = 450  # Ensure large visible logo matching prompt spec scale_w = 450
        
    logo_x = data.get("logo_x", 626)
    if logo_x > 700 or logo_x < 500:
        logo_x = 626
    logo_y = data.get("logo_y", 101)
    
    text_x = data.get("text_x", 45)
    text_y = data.get("text_y", 200)
    white_size = data.get("white_size", 68)
    yellow_size = data.get("yellow_size", 76)
    
    input_path = os.path.join(INPUT_FOLDER, video_name)
    art_jpg = r"C:\Users\NCN0C\.gemini\antigravity\brain\29b9b03a-7893-4074-9a9c-a5581a26a972\main_thumbnail_1.jpg"
    local_jpg = os.path.join(OUTPUT_FOLDER, f"THUMBNAIL_1_{os.path.splitext(video_name)[0]}.jpg")
    bg_path = os.path.join(BASE_DIR, "assets", "baground", "3.png")
    logo_path = os.path.join(BASE_DIR, "assets", "logos", "LOGO.png")
    font_path = "C\\:/Windows/Fonts/impact.ttf"
    
    line1 = data.get("line1", "PPT Sidang Skripsi Anti")
    line2 = data.get("line2", "Dosen Baper!")
    
    lines = [line1, line2]
    start_y = text_y
    line_height = 84
    
    R = video_radius
    VID_W = video_w
    VID_H = video_h
    geq_a = (
        f"if(lte(X,{R})*lte(Y,{R})*gt(pow(X-{R}\\,2)+pow(Y-{R}\\,2)\\,pow({R}\\,2))\\,0\\,"
        f"if(gte(X,{VID_W-R})*lte(Y,{R})*gt(pow(X-{VID_W-R}\\,2)+pow(Y-{R}\\,2)\\,pow({R}\\,2))\\,0\\,"
        f"if(lte(X,{R})*gte(Y,{VID_H-R})*gt(pow(X-{R}\\,2)+pow(Y-{VID_H-R}\\,2)\\,pow({R}\\,2))\\,0\\,"
        f"if(gte(X,{VID_W-R})*gte(Y,{VID_H-R})*gt(pow(X-{VID_W-R}\\,2)+pow(Y-{VID_H-R}\\,2)\\,pow({R}\\,2))\\,0\\,255))))"
    )
    
    filter_complex = (
        f"[1:v]scale=1080:1920[bg];"
        f"[0:v]scale={video_w}:{video_h}:force_original_aspect_ratio=increase,crop={video_w}:{video_h},format=rgba,"
        f"geq=r='r(X\\,Y)':g='g(X\\,Y)':b='b(X\\,Y)':a='{geq_a}'[vid];"
        f"[bg][vid]overlay={video_x}:{video_y}[bg_vid];"
    )
    curr_stream = "[bg_vid]"
    
    if show_logo and os.path.exists(logo_path):
        filter_complex += f"[2:v]scale={logo_w}:-1[logo];{curr_stream}[logo]overlay={logo_x}:{logo_y}[with_logo];"
        curr_stream = "[with_logo]"
        
    badge_y = text_y - 70 if text_y >= 70 else 10
    draw_filters = [
        f"drawtext=fontfile='{font_path}':text='{badge_text}':fontcolor=white:fontsize=44:x={text_x}:y={badge_y}:box=1:boxcolor=0x000000@0.95:boxborderw=12"
    ]
    
    line1_esc = lines[0].replace("'", "").replace(":", "\\:").replace("%", "\\%")
    draw_filters.append(f"drawtext=fontfile='{font_path}':text='{line1_esc}':fontcolor=white:fontsize={white_size}:x={text_x}:y={start_y}:box=1:boxcolor=black@0.0")
    
    line2_esc = lines[1].replace("'", "").replace(":", "\\:").replace("%", "\\%")
    draw_filters.append(f"drawtext=fontfile='{font_path}':text='{line2_esc}':fontcolor=yellow:fontsize={yellow_size}:x={text_x}:y={start_y + line_height}:box=1:boxcolor=black@0.0")
        
    filter_complex += f"{curr_stream}" + "," + ",".join(draw_filters) + "[final_v]"
    
    cmd = [
        "ffmpeg", "-y", "-ss", "3.0",
        "-i", input_path, "-i", bg_path, "-i", logo_path,
        "-filter_complex", filter_complex,
        "-map", "[final_v]", "-vframes", "1", "-q:v", "2", local_jpg
    ]
    subprocess.run(cmd, check=True)
    import shutil
    shutil.copy2(local_jpg, art_jpg)
    return jsonify({"status": "success", "image_url": f"/outputs/{os.path.basename(local_jpg)}"})

@app.route('/outputs/<filename>')
def serve_outputs(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(port=5000, debug=False)
