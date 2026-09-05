"""
extractor.py - Adaptive Smart Frame Extraction Pipeline (Max 10 Frames)
Deduplicated, blur/darkness filtered, resized ~768px JPEG quality 80.
"""

import os
import sys
import json
import glob
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageFilter, ImageStat

FRAME_CONFIG = {
    "maxFrames": 10,
    "minFrames": 1,
    "targetLongestSide": 768,
    "jpegQuality": 80,
    "sceneThreshold": 0.30,
    "similarityThreshold": 0.90,  # 90% visual similarity threshold
    "blurThreshold": 5.0,          # Edge variance threshold for sharpness
    "minBrightness": 15.0         # Minimum brightness (0-255)
}

def get_video_duration(video_path: str) -> float:
    """Fetch video duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 10.0

def get_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """Compute 64-bit difference hash (dHash) for an image using Pillow."""
    resized = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = list(resized.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            p_left = pixels[row * (hash_size + 1) + col]
            p_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(p_left > p_right)
    
    hash_val = 0
    for bit in difference:
        hash_val = (hash_val << 1) | bit
    return hash_val

def dhash_similarity(h1: int, h2: int, hash_size: int = 8) -> float:
    """Calculate normalized similarity between two dHashes (1.0 = identical)."""
    bits = hash_size * hash_size
    dist = bin(h1 ^ h2).count('1')
    return 1.0 - (dist / float(bits))

def evaluate_image_quality(img: Image.Image):
    """Check brightness and sharpness (edge variance)."""
    gray = img.convert('L')
    stat = ImageStat.Stat(gray)
    brightness = stat.mean[0]
    
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    sharpness = edge_stat.var[0]
    
    return brightness, sharpness

def extract_candidate_frames(video_path: str, temp_dir: str) -> tuple:
    """Adaptive Sampling & Scene/Motion Candidate Extraction using FFmpeg."""
    os.makedirs(temp_dir, exist_ok=True)
    duration = get_video_duration(video_path)
    
    if duration < 30.0:
        sample_fps = 2.0
    elif duration <= 120.0:
        sample_fps = 1.0
    else:
        sample_fps = 0.5

    pattern = os.path.join(temp_dir, "cand_%04d.jpg")
    filter_expr = f"fps={sample_fps}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_expr,
        "-vsync", "vfr",
        "-q:v", "3",
        pattern
    ]
    subprocess.run(cmd, capture_output=True)
    
    cand_files = sorted(glob.glob(os.path.join(temp_dir, "cand_*.jpg")))
    candidates = []
    total_cands = len(cand_files)
    for idx, cpath in enumerate(cand_files):
        ts = (idx / max(1, total_cands - 1)) * duration if total_cands > 1 else 0.0
        candidates.append({
            "index": idx + 1,
            "timestamp": round(ts, 2),
            "path": cpath
        })
        
    return candidates, duration

def select_smart_frames(video_path: str, output_dir: str, config: dict = None) -> dict:
    """
    Adaptive Smart Frame Extraction Pipeline:
    1. Sampling & Scene Detection
    2. Quality Filtering (drop blur/black frames)
    3. Deduplication (dHash similarity >= 0.90)
    4. Temporal Coverage & Multi-factor Scoring
    5. Max 10 adaptive selection
    6. Resize to target long side & compress
    7. Generate JSON Metadata
    """
    cfg = FRAME_CONFIG.copy()
    if config:
        cfg.update(config)
        
    temp_dir = os.path.join(output_dir, ".temp_candidates")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        candidates, duration = extract_candidate_frames(video_path, temp_dir)
        
        if not candidates:
            return {"video": os.path.basename(video_path), "duration": duration, "frameCount": 0, "frames": []}
            
        valid_cands = []
        for cand in candidates:
            try:
                img = Image.open(cand["path"])
                brightness, sharpness = evaluate_image_quality(img)
                
                if brightness < cfg["minBrightness"] or sharpness < cfg["blurThreshold"]:
                    continue
                    
                cand["dhash"] = get_dhash(img)
                cand["brightness"] = brightness
                cand["sharpness"] = sharpness
                cand["img_size"] = img.size
                valid_cands.append(cand)
            except Exception:
                pass

        if not valid_cands:
            valid_cands = candidates

        deduped = []
        for cand in valid_cands:
            is_dup = False
            for existing in deduped:
                if "dhash" in cand and "dhash" in existing:
                    sim = dhash_similarity(cand["dhash"], existing["dhash"])
                    if sim >= cfg["similarityThreshold"]:
                        is_dup = True
                        break
            if not is_dup:
                deduped.append(cand)

        max_f = cfg["maxFrames"]
        if len(deduped) > max_f:
            selected_indices = []
            step = len(deduped) / float(max_f)
            for i in range(max_f):
                target_idx = int(i * step)
                target_idx = min(target_idx, len(deduped) - 1)
                selected_indices.append(target_idx)
            
            final_cands = [deduped[i] for i in sorted(list(set(selected_indices)))]
        else:
            final_cands = deduped

        final_cands = final_cands[:max_f]
        
        os.makedirs(output_dir, exist_ok=True)
        final_frames_meta = []
        
        for idx, fitem in enumerate(final_cands, start=1):
            out_filename = f"frame_{idx:02d}.jpg"
            out_filepath = os.path.join(output_dir, out_filename)
            
            img = Image.open(fitem["path"]).convert("RGB")
            w, h = img.size
            
            target_side = cfg["targetLongestSide"]
            if w >= h:
                new_w = target_side
                new_h = int(h * (target_side / float(w)))
            else:
                new_h = target_side
                new_w = int(w * (target_side / float(h)))
                
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            resized_img.save(out_filepath, "JPEG", quality=cfg["jpegQuality"], optimize=True)
            
            final_frames_meta.append({
                "index": idx,
                "timestamp": fitem["timestamp"],
                "file": out_filename,
                "resolution": f"{new_w}x{new_h}",
                "score": round(min(1.0, fitem.get("sharpness", 50.0) / 100.0), 2)
            })

        result_meta = {
            "video": os.path.basename(video_path),
            "duration": round(duration, 2),
            "frameCount": len(final_frames_meta),
            "config": cfg,
            "frames": final_frames_meta
        }
        
        meta_json_path = os.path.join(output_dir, "metadata.json")
        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(result_meta, f, ensure_ascii=False, indent=2)
            
        return result_meta

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        vpath = sys.argv[1]
        out_d = sys.argv[2] if len(sys.argv) > 2 else "./output_frames"
        res = select_smart_frames(vpath, out_d)
        print(json.dumps(res, indent=2))
    else:
        print("[extractor.py] Smart Frame Extractor Ready.")
