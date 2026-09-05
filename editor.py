"""
editor.py - Master Video Processing & Presentation / Reaction Card Batch Renderer
Features:
- Dynamic Aspect Ratio Detection & Blurred Fill for Landscape/Square
- PowerPoint Presentation Layout Engine (HD Upscale, Top-Right In-Video Logo, Bottom Banner, High Top Video Frame)
- Dynamic AI Title Card Engine (Custom Title, Subtitle, Auto-Fit Typography next to logo)
- Reaction Card Layout Engine (Badge, Headline Text, Hook Banner, Rounded Corners)
- Blazing-fast Template Overlay & Multi-threaded Batch Rendering
- Sequential 3-Digit Renaming (001.mp4 - N.mp4)
"""

import os
import sys
import json
import glob
import shutil
import subprocess
import time
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from extractor import select_smart_frames, FRAME_CONFIG

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = BASE_DIR / ".temp_analysis"

def ensure_dirs():
    """Ensure asset subdirectories exist."""
    for s in ["logos", "baground", "fonts", "outputs", "templates", "logos_clean"]:
        os.makedirs(ASSETS_DIR / s, exist_ok=True)

def cleanup_temp():
    """Clean temporary analysis directory."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

def get_video_metadata(video_path: str) -> dict:
    """Fetch video duration, dimensions, bitrates via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,codec_name,duration",
        "-show_entries", "format=duration,size,bit_rate",
        "-of", "json",
        video_path
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(res.stdout)

def trim_alpha(im_path: str, threshold: int = 20) -> Image.Image:
    """Trims empty transparent borders from PNG logo/banner."""
    im = Image.open(im_path).convert('RGBA')
    r, g, b, a = im.split()
    mask = a.point(lambda p: 255 if p > threshold else 0)
    bbox = mask.getbbox()
    if bbox:
        x1, y1, x2, y2 = bbox
        return im.crop((max(0, x1-2), max(0, y1-2), min(im.width, x2+2), min(im.height, y2+2)))
    return im

def prepare_white_frame_template(
    logo_path: str = None,
    banner_path: str = None,
    template_path: str = None,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    vid_x: int = 40,
    vid_y: int = 60,
    vid_w: int = 1000,
    vid_h: int = 1520,
    corner_radius: int = 24
) -> str:
    """
    Creates a pre-rendered 1080x1920 White Frame Template overlay with:
    - Pure white borders & margins (video placed high starting at y=60)
    - Transparent rounded window for the video container
    - Crisp circular LOGO overlaid at TOP-RIGHT inside the video frame
    - Crisp BANNER at bottom center
    """
    ensure_dirs()
    if logo_path is None:
        logo_path = str(ASSETS_DIR / "logos" / "LOGO.png")
    if banner_path is None:
        banner_path = str(ASSETS_DIR / "logos" / "BANNER.png")
    if template_path is None:
        template_path = str(ASSETS_DIR / "templates" / "white_frame_template.png")

    template = Image.new('RGBA', (canvas_w, canvas_h), (255, 255, 255, 255))
    
    # Mask to punch rounded hole for video
    mask = Image.new('L', (canvas_w, canvas_h), 255)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle(
        [(vid_x, vid_y), (vid_x + vid_w, vid_y + vid_h)],
        corner_radius,
        fill=0
    )
    template.putalpha(mask)

    # Place Logo inside video at TOP-RIGHT
    if os.path.exists(logo_path):
        logo = trim_alpha(logo_path)
        logo_h = 175
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = vid_x + vid_w - logo_w - 30
        logo_y = vid_y + 30

        # White circle badge backing with soft shadow
        badge = Image.new('RGBA', (logo_w + 10, logo_h + 10), (0,0,0,0))
        b_draw = ImageDraw.Draw(badge)
        b_draw.ellipse([(5, 5), (logo_w + 5, logo_h + 5)], fill=(255, 255, 255, 245))
        badge = badge.filter(ImageFilter.GaussianBlur(1))

        b_shadow = Image.new('RGBA', (logo_w + 30, logo_h + 30), (0,0,0,0))
        bs_draw = ImageDraw.Draw(b_shadow)
        bs_draw.ellipse([(15, 17), (logo_w + 15, logo_h + 17)], fill=(0, 0, 0, 50))
        b_shadow = b_shadow.filter(ImageFilter.GaussianBlur(8))

        template.paste(b_shadow, (logo_x - 15, logo_y - 15), b_shadow)
        template.paste(badge, (logo_x - 5, logo_y - 5), badge)
        template.paste(logo_resized, (logo_x, logo_y), logo_resized)

    # Place Banner at bottom center (y: 1620, width ~920)
    if os.path.exists(banner_path):
        banner = trim_alpha(banner_path)
        banner_w = 920
        banner_h = int(banner.height * (banner_w / banner.width))
        banner_resized = banner.resize((banner_w, banner_h), Image.Resampling.LANCZOS)
        banner_y = (vid_y + vid_h) + ((canvas_h - (vid_y + vid_h)) - banner_h) // 2
        template.paste(banner_resized, ((canvas_w - banner_w) // 2, banner_y), banner_resized)

    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    template.save(template_path, format="PNG")
    return template_path

def create_presentation_overlay_with_title(
    title: str,
    subtitle: str,
    badge_text: str = "TUTORIAL MORPH PPT",
    base_template_path: str = None,
    output_overlay_path: str = None,
    logo_path: str = None,
    banner_path: str = None
) -> str:
    """Creates a custom 1080x1920 overlay combining frame, logo, banner, and AI title card."""
    if base_template_path is None or not os.path.exists(base_template_path):
        base_template_path = prepare_white_frame_template(logo_path=logo_path, banner_path=banner_path)

    base_tpl = Image.open(base_template_path).convert('RGBA')
    
    card_w = 690
    card_h = 155
    card_x = 40 + 30
    card_y = 60 + 35

    card = Image.new('RGBA', (card_w, card_h), (0,0,0,0))
    c_draw = ImageDraw.Draw(card)
    c_draw.rounded_rectangle([(0,0), (card_w, card_h)], 20, fill=(15, 23, 42, 238))

    font_badge = ImageFont.truetype('arialbd.ttf', 22)
    font_sub = ImageFont.truetype('arialbd.ttf', 24)

    # Auto-fit title font
    max_w = card_w - 44
    title_font = ImageFont.truetype('impact.ttf', 44)
    for sz in range(44, 26, -2):
        tf = ImageFont.truetype('impact.ttf', sz)
        bb = tf.getbbox(title)
        if (bb[2] - bb[0]) <= max_w:
            title_font = tf
            break

    # Draw Badge
    bbox_b = font_badge.getbbox(badge_text)
    bw = bbox_b[2] - bbox_b[0] + 24
    c_draw.rounded_rectangle([(22, 16), (22 + bw, 46)], 8, fill=(234, 88, 12, 255))
    c_draw.text((34, 19), badge_text, font=font_badge, fill=(255, 255, 255))

    # Draw Title
    c_draw.text((22, 54), title, font=title_font, fill=(255, 255, 255))

    # Draw Subtitle
    c_draw.text((22, 112), subtitle, font=font_sub, fill=(253, 224, 71))

    # Card shadow
    c_shadow = Image.new('RGBA', (card_w + 20, card_h + 20), (0,0,0,0))
    ImageDraw.Draw(c_shadow).rounded_rectangle([(10, 10), (card_w + 10, card_h + 10)], 20, fill=(0,0,0,60))
    c_shadow = c_shadow.filter(ImageFilter.GaussianBlur(8))

    base_tpl.paste(c_shadow, (card_x - 10, card_y - 8), c_shadow)
    base_tpl.paste(card, (card_x, card_y), card)

    if output_overlay_path is None:
        import uuid
        output_overlay_path = str(ASSETS_DIR / "templates" / f"overlay_{uuid.uuid4().hex[:8]}.png")
    os.makedirs(os.path.dirname(os.path.abspath(output_overlay_path)), exist_ok=True)
    base_tpl.save(output_overlay_path, format="PNG")
    return output_overlay_path

def get_video_aspect_ratio(video_path: str) -> float:
    """Returns width / height aspect ratio of video using ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            w = data["streams"][0]["width"]
            h = data["streams"][0]["height"]
            return w / float(h)
    except Exception:
        pass
    return 0.5625

def render_presentation_video(
    input_path: str,
    output_path: str,
    template_path: str = None,
    title: str = None,
    subtitle: str = None,
    logo_path: str = None,
    banner_path: str = None,
    crf: int = 17,
    preset: str = "fast"
):
    """
    Renders HD 1080x1920 video with clean white frame layout, top-right logo, title card, and bottom banner.
    Automatically adapts to Portrait (9:16) and Landscape (16:9/YouTube/Square) with blurred background container fill.
    """
    temp_overlay = None
    if title and subtitle:
        overlay_p = create_presentation_overlay_with_title(
            title=title,
            subtitle=subtitle,
            logo_path=logo_path,
            banner_path=banner_path
        )
        temp_overlay = overlay_p
    elif template_path and os.path.exists(template_path):
        overlay_p = template_path
    else:
        overlay_p = prepare_white_frame_template(logo_path=logo_path, banner_path=banner_path)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    aspect_ratio = get_video_aspect_ratio(input_path)
    if aspect_ratio >= 0.95:
        # Landscape / Square: Blur background fill + crisp centered video (Reels Portrait 9:16)
        filter_complex = (
            "[0:v]scale=1000:1520:force_original_aspect_ratio=increase,crop=1000:1520,boxblur=25:5[v_blur];"
            "[0:v]scale=1000:-2:flags=lanczos,unsharp=5:5:0.7:5:5:0.3[v_fg];"
            "[v_blur][v_fg]overlay=0:(1520-h)/2[vid];"
            "[vid]pad=1080:1920:40:60:color=white[v_padded];"
            "[v_padded][1:v]overlay=0:0:shortest=1[outv]"
        )
    else:
        # Portrait (9:16): Full HD Lanczos upscale + unsharp filter
        filter_complex = (
            "[0:v]scale=1000:1778:flags=lanczos,crop=1000:1520:0:(ih-1520)*0.4,unsharp=5:5:0.7:5:5:0.3[vid];"
            "[vid]pad=1080:1920:40:60:color=white[v_padded];"
            "[v_padded][1:v]overlay=0:0:shortest=1[outv]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-loop", "1", "-i", overlay_p,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "256k",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_preview_frame(
    video_path: str,
    output_image_path: str,
    title: str = None,
    subtitle: str = None,
    template_path: str = None,
    logo_path: str = None,
    banner_path: str = None,
    timestamp: str = "00:00:15"
):
    """Extracts a frame at timestamp and generates a high-res 1080x1920 preview image with title."""
    if title and subtitle:
        overlay_p = create_presentation_overlay_with_title(
            title=title,
            subtitle=subtitle,
            logo_path=logo_path,
            banner_path=banner_path
        )
    elif template_path and os.path.exists(template_path):
        overlay_p = template_path
    else:
        overlay_p = prepare_white_frame_template(logo_path=logo_path, banner_path=banner_path)

    os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)

    aspect_ratio = get_video_aspect_ratio(video_path)
    if aspect_ratio >= 0.95:
        filter_complex = (
            "[0:v]scale=1000:1520:force_original_aspect_ratio=increase,crop=1000:1520,boxblur=25:5[v_blur];"
            "[0:v]scale=1000:-2:flags=lanczos,unsharp=5:5:0.7:5:5:0.3[v_fg];"
            "[v_blur][v_fg]overlay=0:(1520-h)/2[vid];"
            "[vid]pad=1080:1920:40:60:color=white[v_padded];"
            "[v_padded][1:v]overlay=0:0:shortest=1[outv]"
        )
    else:
        filter_complex = (
            "[0:v]scale=1000:1778:flags=lanczos,crop=1000:1520:0:(ih-1520)*0.4,unsharp=5:5:0.7:5:5:0.3[vid];"
            "[vid]pad=1080:1920:40:60:color=white[v_padded];"
            "[v_padded][1:v]overlay=0:0:shortest=1[outv]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-ss", timestamp,
        "-i", video_path,
        "-i", overlay_p,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-vframes", "1",
        output_image_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def clean_filename_str(title_str: str) -> str:
    """Removes invalid Windows filesystem characters and cleans whitespace."""
    import re
    s = re.sub(r'[\/\\:\*\?\"<>\|]', '', title_str)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def batch_render_presentation(
    input_folder: str,
    output_folder: str = None,
    analysis_json_path: str = None,
    logo_path: str = None,
    banner_path: str = None,
    max_workers: int = 4
):
    """Batch renders all videos in input_folder with AI caption-derived filenames saved in input_folder/outputs/."""
    master_analysis = {}
    if analysis_json_path and os.path.exists(analysis_json_path):
        with open(analysis_json_path, "r", encoding="utf-8") as f:
            master_analysis = json.load(f)

    if output_folder is None:
        output_folder = os.path.join(input_folder, "outputs")

    os.makedirs(output_folder, exist_ok=True)
    video_files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(('.mp4', '.mov', '.avi'))])
    
    print(f"[editor.py] Found {len(video_files)} videos in {input_folder} to render into {output_folder}.", flush=True)

    def process_item(idx, filename):
        import caption
        in_p = os.path.join(input_folder, filename)

        # Check AI analysis
        vid_id_str = f"{idx:03d}"
        item_data = master_analysis.get(vid_id_str, {})
        ai_info = item_data.get("ai_analysis", {})
        title = ai_info.get("title_overlay", "TUTORIAL MORPH PPT")
        subtitle = ai_info.get("subtitle_overlay", "Trik Presentasi Estetik & Simpel")

        full_caption = caption.build_full_caption_text(item_data)
        out_name = caption.caption_to_filename(full_caption)
        out_p = os.path.join(output_folder, out_name)

        if os.path.exists(out_p) and os.path.getsize(out_p) > 100000:
            return idx, filename, True, "Skipped (already exists)"

        try:
            render_presentation_video(
                input_path=in_p,
                output_path=out_p,
                title=title,
                subtitle=subtitle,
                logo_path=logo_path,
                banner_path=banner_path
            )
            return idx, filename, True, "OK"
        except Exception as e:
            return idx, filename, False, str(e)

    completed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(process_item, idx, f): (idx, f) for idx, f in enumerate(video_files, start=1)}
        for future in as_completed(futures):
            idx, filename, ok, msg = future.result()
            completed += 1
            status = "OK" if ok else f"FAILED: {msg}"
            print(f"[{completed:03d}/{len(video_files)}] #{idx:03d} ({filename}) -> {status}", flush=True)

    elapsed = time.time() - t0
    print(f"[editor.py] Batch rendering finished in {elapsed:.2f}s!", flush=True)

def organize_ppt_outputs(source_folder="ppt/1", analysis_json_path="1_combined_analysis.json"):
    """Organizes and renames all rendered videos into source_folder/outputs/ using direct full AI captions as filenames (without numbers)."""
    import shutil
    import caption

    dst_folder = os.path.abspath(os.path.join(source_folder, "outputs"))
    os.makedirs(dst_folder, exist_ok=True)
    src_folder = os.path.abspath(os.path.join(BASE_DIR, "outputs"))

    master_analysis = {}
    if os.path.exists(analysis_json_path):
        with open(analysis_json_path, "r", encoding="utf-8") as f:
            master_analysis = json.load(f)

    video_files = sorted([f for f in os.listdir(source_folder) if f.lower().endswith(('.mp4', '.mov', '.avi'))])
    
    # Collect existing files in dst_folder
    existing_files = [os.path.join(dst_folder, f) for f in os.listdir(dst_folder) if f.endswith('.mp4')]
    
    print(f"[editor.py] Renaming {len(video_files)} videos into full caption filenames in {dst_folder}...", flush=True)
    
    # Build a map from index to target caption filename with hashtags
    targets = []
    for idx, orig_name in enumerate(video_files, start=1):
        vid_id_str = f"{idx:03d}"
        item_data = master_analysis.get(vid_id_str, {})
        ai_info = item_data.get("ai_analysis", {})
        title = ai_info.get("title_overlay") or ai_info.get("title", f"Video {vid_id_str}")
        dst_name = caption.caption_to_filename(item_data, max_total_chars=185)
        dst_path = os.path.join(dst_folder, dst_name)
        targets.append((idx, orig_name, title, ai_info, dst_path, dst_name))

    # Existing files currently in dst_folder sorted
    current_mp4s = sorted([os.path.join(dst_folder, f) for f in os.listdir(dst_folder) if f.endswith('.mp4')])
    
    # If count matches, rename sequentially
    if len(current_mp4s) == len(targets):
        for (idx, orig_name, title, ai_info, dst_path, dst_name), cur_p in zip(targets, current_mp4s):
            if cur_p != dst_path:
                try:
                    os.rename(cur_p, dst_path)
                except Exception:
                    shutil.copy2(cur_p, dst_path)
                    try:
                        os.remove(cur_p)
                    except Exception:
                        pass
    else:
        # Fallback for individual renaming / copying
        for idx, orig_name, title, ai_info, dst_path, dst_name in targets:
            if os.path.exists(dst_path) and os.path.getsize(dst_path) > 100000:
                continue
            src_num_p = os.path.join(src_folder, f"{idx:03d}.mp4")
            if os.path.exists(src_num_p) and os.path.getsize(src_num_p) > 100000:
                shutil.copy2(src_num_p, dst_path)
            elif not os.path.exists(dst_path):
                print(f"[editor.py] Rendering {dst_name[:50]}...", flush=True)
                render_presentation_video(
                    input_path=os.path.join(source_folder, orig_name),
                    output_path=dst_path,
                    title=title,
                    subtitle=ai_info.get("subtitle_overlay", "Trik Presentasi Estetik & Simpel")
                )

    final_count = len([f for f in os.listdir(dst_folder) if f.endswith('.mp4')])
    print(f"[editor.py] Successfully organized {final_count} videos with full caption & hashtag filenames into {dst_folder}!", flush=True)

    # Generate master caption file inside ppt/1/outputs/
    txt_path = os.path.join(dst_folder, "CAPTION_SEMUA_VIDEO.txt")
    caption.generate_master_caption_txt(analysis_json_path, txt_path)
    return dst_folder

def create_shoope_32_overlay(
    hook_text: str,
    desc_line1: str,
    desc_line2: str,
    output_overlay_path: str,
    template_path: str = None,
    logo_path: str = None
) -> str:
    """
    Creates a 1080x1920 overlay PNG for Shopee Unique Products using template 32.png:
    - Transparent punch-out for video container (X=52, Y=215, W=976, H=1084)
    - Top-left badge: BARANG UNIK /// + Headline: BARANG UNIK / YANG BIKIN PENASARAN
    - Top-right logo: p (2).png (KOK ADA?)
    - Hook box (beside flame): 2-3 words (white + neon yellow)
    - Desc box: 2 clean lines of product benefits (white text)
    """
    ensure_dirs()
    if template_path is None:
        template_path = str(ASSETS_DIR / "logos" / "32.png")
    if logo_path is None:
        logo_path = str(ASSETS_DIR / "logos" / "p (2).png")
    if output_overlay_path is None:
        output_overlay_path = str(ASSETS_DIR / "templates" / "shoope_32_overlay.png")

    fonts_dir = ASSETS_DIR / "fonts"
    
    im32 = Image.open(template_path).convert('RGBA').resize((1080, 1920), Image.Resampling.LANCZOS)

    # Punch out video window
    vid_x, vid_y, vid_w, vid_h = 52, 215, 976, 1084
    pixels = im32.load()
    for y in range(vid_y, vid_y + vid_h):
        for x in range(vid_x, vid_x + vid_w):
            r, g, b, a = pixels[x, y]
            if 35 <= r <= 95 and abs(r-g) < 10 and abs(g-b) < 10:
                pixels[x, y] = (0, 0, 0, 0)

    draw = ImageDraw.Draw(im32)

    # --- 1. TOP HEADER ---
    draw.rectangle([(40, 30), (780, 205)], fill=(0, 0, 0, 255))
    draw.rounded_rectangle([(52, 45), (330, 85)], radius=6, fill=(255, 210, 0, 255))
    
    try:
        font_badge = ImageFont.truetype('C:/Windows/Fonts/impact.ttf', 26)
        font_head_1 = ImageFont.truetype('C:/Windows/Fonts/impact.ttf', 44)
        font_head_2 = ImageFont.truetype('C:/Windows/Fonts/impact.ttf', 38)
        font_hook = ImageFont.truetype('C:/Windows/Fonts/impact.ttf', 50)
    except Exception:
        font_badge = ImageFont.truetype(str(fonts_dir / "Montserrat-Black.ttf"), 26)
        font_head_1 = ImageFont.truetype(str(fonts_dir / "Montserrat-Black.ttf"), 44)
        font_head_2 = ImageFont.truetype(str(fonts_dir / "Montserrat-Black.ttf"), 38)
        font_hook = ImageFont.truetype(str(fonts_dir / "Montserrat-Black.ttf"), 50)

    draw.text((68, 50), 'BARANG UNIK  ///', font=font_badge, fill=(0, 0, 0, 255))
    draw.text((54, 98), 'BARANG UNIK', font=font_head_1, fill=(255, 255, 255, 255))
    draw.text((54, 148), 'YANG BIKIN PENASARAN', font=font_head_2, fill=(255, 210, 0, 255))

    # Top-Right Logo: p (2).png
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert('RGBA')
        logo_size = 195
        logo_res = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        im32.paste(logo_res, (835, 18), logo_res)

    # --- 2. HOOK TEXT (Inside Top Box beside Flame) ---
    clean_hook = re.sub(r'[\r\n\t]+', ' ', str(hook_text).strip()).upper()
    words = clean_hook.split()
    cur_x = 265
    cur_y = 1395
    for i, w in enumerate(words):
        color = (255, 210, 0, 255) if i == len(words) - 1 else (255, 255, 255, 255)
        w_text = w + ' '
        draw.text((cur_x + 2, cur_y + 2), w_text, font=font_hook, fill=(0, 0, 0, 230))
        draw.text((cur_x, cur_y), w_text, font=font_hook, fill=color)
        cur_x += int(font_hook.getlength(w_text))

    # --- 3. DESCRIPTION TEXT (Inside Bottom Box) ---
    font_desc_p = str(fonts_dir / "Poppins-Bold.ttf")
    font_desc_reg_p = str(fonts_dir / "Poppins-SemiBold.ttf")
    try:
        font_desc = ImageFont.truetype(font_desc_p, 24)
        font_desc_reg = ImageFont.truetype(font_desc_reg_p, 23)
    except Exception:
        font_desc = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
        font_desc_reg = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 23)

    d_line1 = re.sub(r'[\r\n\t]+', ' ', str(desc_line1).strip())
    d_line2 = re.sub(r'[\r\n\t]+', ' ', str(desc_line2).strip())

    draw.text((90 + 1, 1568 + 1), d_line1, font=font_desc, fill=(0, 0, 0, 220))
    draw.text((90, 1568), d_line1, font=font_desc, fill=(255, 255, 255, 255))

    draw.text((90 + 1, 1608 + 1), d_line2, font=font_desc_reg, fill=(0, 0, 0, 220))
    draw.text((90, 1608), d_line2, font=font_desc_reg, fill=(235, 235, 240, 255))

    os.makedirs(os.path.dirname(output_overlay_path), exist_ok=True)
    im32.save(output_overlay_path, format="PNG")
    return output_overlay_path

import asyncio

async def _generate_tts_async(text: str, output_path: str, voice_name: str, rate: str, pitch: str):
    import edge_tts
    comm = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
    await comm.save(output_path)
    return output_path

def generate_tts_audio(text: str, output_path: str, voice_type: str = "gadis") -> str:
    """
    Generates high-quality Indonesian neural TTS voiceover using edge-tts.
    - voice_type: 'gadis' (Female - energetic TikTok creator) or 'ardi' (Male - friendly reviewer)
    """
    is_male = voice_type.lower() in ["ardi", "male", "pria", "cowok"]
    voice_name = "id-ID-ArdiNeural" if is_male else "id-ID-GadisNeural"
    rate = "+8%" if is_male else "+10%"
    pitch = "+0Hz"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(_generate_tts_async(text, output_path, voice_name, rate, pitch))
    return output_path

def render_shoope_video(
    input_path: str,
    output_path: str,
    hook_text: str,
    desc_line1: str,
    desc_line2: str,
    temp_overlay_path: str = None,
    tts_text: str = None,
    voice_type: str = "gadis",
    bgm_path: str = None
) -> str:
    """Renders a single Shopee video with the 32.png template overlay, custom Voltage.mp3 BGM, and TTS voiceover."""
    if temp_overlay_path is None:
        stem = Path(input_path).stem
        temp_overlay_path = str(ASSETS_DIR / "templates" / f"shoope_overlay_{stem}.png")

    if bgm_path is None:
        default_bgm = ASSETS_DIR / "Voltage.mp3"
        if default_bgm.exists():
            bgm_path = str(default_bgm)

    create_shoope_32_overlay(
        hook_text=hook_text,
        desc_line1=desc_line1,
        desc_line2=desc_line2,
        output_overlay_path=temp_overlay_path
    )

    temp_tts_path = None
    if tts_text and len(tts_text.strip()) > 5:
        stem = Path(input_path).stem
        temp_tts_path = str(ASSETS_DIR / "templates" / f"shoope_tts_{stem}.mp3")
        try:
            generate_tts_audio(tts_text, temp_tts_path, voice_type=voice_type)
        except Exception as e:
            print(f"[TTS Warning] Could not generate TTS: {e}", flush=True)
            temp_tts_path = None

    if temp_tts_path and os.path.exists(temp_tts_path) and bgm_path and os.path.exists(bgm_path):
        # Mute original video audio, mix Voltage.mp3 (0.35 volume / 35%) + TTS voice (1.6 volume)
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-loop', '1', '-i', temp_overlay_path,
            '-stream_loop', '-1', '-i', bgm_path,
            '-i', temp_tts_path,
            '-filter_complex',
            '[0:v]scale=976:1084:force_original_aspect_ratio=increase,crop=976:1084,unsharp=5:5:0.7:5:5:0.3[vid];'
            '[vid]pad=1080:1920:52:215:color=black[padded];'
            '[padded][1:v]overlay=0:0:shortest=1[outv];'
            '[2:a]volume=0.35[bgm];[3:a]volume=1.6[vc];[bgm][vc]amix=inputs=2:duration=longest:dropout_transition=2[outa]',
            '-map', '[outv]',
            '-map', '[outa]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-shortest',
            output_path
        ]
    elif temp_tts_path and os.path.exists(temp_tts_path):
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-loop', '1', '-i', temp_overlay_path,
            '-i', temp_tts_path,
            '-filter_complex',
            '[0:v]scale=976:1084:force_original_aspect_ratio=increase,crop=976:1084,unsharp=5:5:0.7:5:5:0.3[vid];'
            '[vid]pad=1080:1920:52:215:color=black[padded];'
            '[padded][1:v]overlay=0:0:shortest=1[outv];'
            '[0:a]volume=0.20[bg];[2:a]volume=1.5[vc];[bg][vc]amix=inputs=2:duration=first:dropout_transition=2[outa]',
            '-map', '[outv]',
            '-map', '[outa]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            output_path
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-loop', '1', '-i', temp_overlay_path,
            '-filter_complex',
            '[0:v]scale=976:1084:force_original_aspect_ratio=increase,crop=976:1084,unsharp=5:5:0.7:5:5:0.3[vid];'
            '[vid]pad=1080:1920:52:215:color=black[padded];'
            '[padded][1:v]overlay=0:0:shortest=1[outv]',
            '-map', '[outv]',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            output_path
        ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for tmp in [temp_overlay_path, temp_tts_path]:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    return output_path

def render_shoope_batch(
    folder_path: str,
    analysis_json_path: str,
    output_dir: str = None,
    max_workers: int = 6,
    enable_tts: bool = False,
    voice_type: str = "gadis",
    bgm_path: str = None
):
    """Batch renders all Shopee videos in parallel using 32.png template with custom BGM and optional TTS voiceovers."""
    with open(analysis_json_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    if output_dir is None:
        output_dir = os.path.join(folder_path, "outputs")
    os.makedirs(output_dir, exist_ok=True)

    if bgm_path is None:
        default_bgm = ASSETS_DIR / "Voltage.mp3"
        if default_bgm.exists():
            bgm_path = str(default_bgm)

    # Sort files naturally
    raw_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.mp4') and not f.startswith('preview_') and not f.startswith('sample_')]
    def sort_key(p):
        stem = Path(p).stem
        return int(stem) if stem.isdigit() else 999999
    vids = sorted(raw_files, key=sort_key)

    print(f"[editor.py] Starting batch render of {len(vids)} Shopee videos to {output_dir} (workers={max_workers}, tts={enable_tts}, bgm={bgm_path})...", flush=True)

    def process_render(idx, v_path):
        vid_id_str = f"{idx:03d}"
        item = master_data.get(vid_id_str, {})
        ai = item.get("ai_analysis", {})

        hook = ai.get("hook_text") or "INI BARANG APA?!"
        d1 = ai.get("desc_line1") or "Kelihatannya kecil, tapi fungsinya praktis!"
        d2 = ai.get("desc_line2") or "Bikin aktivitas harian jadi lebih simpel!"
        tts_script = ai.get("reaction_caption") or f"{hook} {d1} {d2} Cek link di bio ya!"

        out_name = f"{vid_id_str}.mp4"
        out_path = os.path.join(output_dir, out_name)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 100000 and not enable_tts:
            return idx, vid_id_str, out_path, True, "Cached"

        # Determine voice
        if voice_type in ["alternate", "both", "random"]:
            actual_voice = "ardi" if idx % 2 == 0 else "gadis"
        else:
            actual_voice = voice_type

        temp_overlay = str(ASSETS_DIR / "templates" / f"shoope_overlay_{vid_id_str}.png")
        try:
            render_shoope_video(
                input_path=v_path,
                output_path=out_path,
                hook_text=hook,
                desc_line1=d1,
                desc_line2=d2,
                temp_overlay_path=temp_overlay,
                tts_text=tts_script if enable_tts else None,
                voice_type=actual_voice,
                bgm_path=bgm_path
            )
            return idx, vid_id_str, out_path, True, f"Rendered ({actual_voice})"
        except Exception as e:
            return idx, vid_id_str, out_path, False, str(e)

    completed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(process_render, idx, vp): (idx, vp) for idx, vp in enumerate(vids, start=1)}
        for future in as_completed(futures):
            idx, vid_id_str, out_path, ok, msg = future.result()
            completed += 1
            if ok:
                print(f"[RENDER {completed:03d}/{len(vids)}] Video #{vid_id_str} -> {msg} ({os.path.basename(out_path)})", flush=True)
            else:
                print(f"[RENDER {completed:03d}/{len(vids)}] Video #{vid_id_str} -> FAILED: {msg}", flush=True)

    elapsed = time.time() - t0
    print(f"[editor.py] Finished batch render in {elapsed:.2f}s! All videos saved in {output_dir}", flush=True)
    return output_dir

if __name__ == "__main__":
    print("[editor.py] Video Processing & Presentation Engine Ready.")
