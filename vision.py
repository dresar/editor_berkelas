"""
vision.py - Gemini Vision AI Batch Analysis Engine
Features: Multi-Threaded Parallel Processing, Multi-Key Smart Pool Rotation, Auto-Failover,
PowerPoint Morph Tutorial Analyzer, Per-Folder JSON Persistence, Combined Master JSON Builder.
"""

import os
import sys
import json
import glob
import time
import base64
import threading
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure UTF-8 standard output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.resolve()
KEYS_FILE = BASE_DIR / "valid_gemini_keys.json"

MODELS_PRIORITY = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]

SYSTEM_PROMPT = """Kamu adalah seorang AI Master Content Strategist & Video Editor profesional spesialis konten tutorial PowerPoint Morph, Animasi Slide, dan Desain Presentasi untuk TikTok, Instagram Reels, dan YouTube Shorts.

Tugasmu: Analisis frame-frame tutorial PowerPoint ini dengan teliti (perhatikan slide apa yang dibuat, bentuk/shape, efek morph, ikon, teks judul slide, warna, transisi, animasi).
Gunakan gaya bahasa SUPER NON-FORMAL (gaul, santai, seru, kekinian, tidak kaku).
Hasilkan output JSON murni (TANPA MARKDOWN ```json, HANYA PURE JSON OBJECT) dengan struktur berikut:

{
  "video_id": "001",
  "tutorial_topic": "Topik spesifik tutorial (contoh: Bikin Slide Animasi Timeline dan Latar Belakang dengan Morph)",
  "step_by_step_summary": "Rangkuman singkat apa yang dikerjakan di video langkah demi langkah",
  "title_overlay": "Judul headline singkat, padat, dan super catchy untuk ditaruh di samping logo (3-5 kata huruf kapital)",
  "subtitle_overlay": "Subjudul pendek",
  "hook_text": "Teks hook memancing perhatian penonton",
  "reaction_caption": "Caption TikTok/Reels lengkap, santai, gaul, persuasif, dan WAJIB diakhiri dengan ajakan cek bio seperti: 'Mau template PPT kece ini? Cek link di bio ya! ✨'",
  "hashtags": ["#PowerPoint", "#MorphTransition", "#TutorialPPT", "#PresentasiKeren", "#FYP"]
}

Aturan Penting:
1. Analisis detail visual secara akurat dari gambar/frame tutorial PowerPoint yang diberikan.
2. Gunakan bahasa Indonesia super santai & non-formal.
3. WAJIB sertakan ajakan 'cek link di bio' pada teks caption.
4. Output HARUS MURNI JSON tanpa pembungkus markdown ```json.
"""

SYSTEM_PROMPT_SHOOPE = """Kamu adalah seorang AI Master Content Strategist, Copywriter Voiceover, & Affiliate Product Researcher profesional spesialis konten Video Produk Unik, Gadget Canggih, Alat Praktis, dan Racun Belanja Shopee/TikTok Shop (Channel: "KOK ADA? BARANG UNIK YANG BIKIN PENASARAN!").

Tugasmu:
1. Analisis frame-frame video produk ini dengan sangat teliti (identifikasi barang apa itu secara spesifik, nama produk marketplace di Shopee, fungsi utama, keunikan, dan masalah yang diselesaikan).
2. Buat teks narasi TTS (voiceover) bahasa Indonesia yang agak panjang, super NON-FORMAL, gaul, santai, seru, penasaran, dan persuasif (2-3 kalimat mengalir natural yang menjelaskan fungsi barang unik ini dan WAJIB ditutup dengan kalimat ajakan: "Yuk langsung kepoin, cek link di bio sekarang ya!"). JANGAN PERNAH sebut kata "keranjang kuning".
3. Tentukan nama produk marketplace yang akurat dan 5 KATA KUNCI PENCARIAN SHOPEE AFFILIATE (search keywords) agar user bisa langsung mencari dan menemukan link affiliate produk tersebut di Shopee dengan mudah.
4. Tentukan Hook 2-3 kata huruf kapital yang super heboh dan memicu rasa penasaran.

Hasilkan output JSON murni (TANPA MARKDOWN ```json, HANYA PURE JSON OBJECT) dengan format PERSIS berikut:

{
  "video_id": "101",
  "product_name": "Nama produk spesifik di marketplace (contoh: Tas Ransel Wanita Anti Maling Oxford Backpack Back Opening Waterproof)",
  "category": "Kategori produk (pilih salah satu: Barang Unik / Rumah Tangga / Dapur & Masak / Elektronik & Gadget / Fashion & Aksesoris / Kecantikan & Perawatan / Otomotif & Kendaraan / Mainan & Hobi)",
  "affiliate_search_query": "Kata kunci pencarian utama di Shopee (contoh: tas ransel anti maling wanita resleting belakang)",
  "affiliate_keywords": [
    "Kata kunci 1 (paling spesifik, contoh: tas ransel anti maling)",
    "Kata kunci 2 (nama model/fungsi, contoh: ransel resleting belakang)",
    "Kata kunci 3 (fitur unggulan, contoh: tas ransel waterproof wanita)",
    "Kata kunci 4 (kategori populer, contoh: tas punggung anti copet)",
    "Kata kunci 5 (istilah racun shopee, contoh: tas ransel korea casual)"
  ],
  "hook_text": "Hook 2-3 KATA SAJA super singkat, heboh, bikin penasaran, HURUF KAPITAL (contoh: INI BARANG APA?! / COPET AUTO NANGIS?! / ALAT AJAIB APA?! / KOK BISA GINI?! / GOKIL BANGET INI?! / KECIL TAPI SAKTI?!)",
  "tts_narrative": "Teks narasi suara voiceover lengkap & agak panjang (2-3 kalimat super non-formal santai menjelaskan keunikan/solusi barang, diakhiri: 'Yuk langsung kepoin, cek link di bio sekarang ya!')",
  "desc_line1": "Ringkasan fungsi/keunggulan utama 1 (maksimal 50 karakter, contoh: Resleting ngumpet di punggung, 100% aman copet!)",
  "desc_line2": "Ringkasan fungsi/keunggulan utama 2 (maksimal 50 karakter, contoh: Bahan tebal waterproof & muat banyak barang!)",
  "reaction_caption": "Caption Shopee Video/TikTok super santai racun belanja + Cek bio ya! #BarangUnik #RacunShopee #SpillBarangUnik",
  "hashtags": ["#BarangUnik", "#RacunShopee", "#SpillBarangUnik", "#BarangViral"]
}

Aturan Ketat:
1. tts_narrative WAJIB menggunakan gaya bahasa super santai, non-formal, asik didengar, dan WAJIB ditutup dengan 'cek link di bio'. DILARANG menyebut keranjang kuning.
2. affiliate_keywords WAJIB BERISI TEPAT 5 KATA KUNCI PENCARIAN SHOPEE yang akurat & efektif untuk mencari produk affiliate di kolom search Shopee.
3. hook_text WAJIB SANGAT SINGKAT (hanya 2 sampai 3 kata saja, huruf kapital).
4. desc_line1 dan desc_line2 WAJIB singkat & padat (maksimal 50 karakter per baris).
5. Output HARUS MURNI JSON tanpa pembungkus markdown ```json.
"""

class SmartKeyRotator:
    def __init__(self, keys_file=KEYS_FILE):
        self.keys_file = Path(keys_file)
        self.lock = threading.Lock()
        self.load_keys()
        self.current_idx = 0
        
    def load_keys(self):
        with self.lock:
            if self.keys_file.exists():
                with open(self.keys_file, "r", encoding="utf-8") as f:
                    self.healthy_keys = json.load(f)
            else:
                self.healthy_keys = []
            print(f"[SMART ROTATOR] Loaded {len(self.healthy_keys)} active healthy keys.", flush=True)

    def save_keys(self):
        with self.lock:
            with open(self.keys_file, "w", encoding="utf-8") as f:
                json.dump(self.healthy_keys, f, indent=2)

    def get_current_key(self):
        with self.lock:
            if not self.healthy_keys:
                raise Exception("No active healthy API keys remaining!")
            key = self.healthy_keys[self.current_idx % len(self.healthy_keys)]
            self.current_idx = (self.current_idx + 1) % len(self.healthy_keys)
            return key

    def mark_unhealthy_and_rotate(self, failed_key):
        with self.lock:
            print(f"[KEY WARNING] API Key ID {failed_key.get('id')} error/rate-limited. Rotating...", flush=True)
            self.healthy_keys = [k for k in self.healthy_keys if k["api_key"] != failed_key["api_key"]]
            self.save_keys()
            if not self.healthy_keys:
                raise Exception("All API keys have been exhausted or rate limited!")
            self.current_idx = self.current_idx % len(self.healthy_keys)

def call_gemini_vision(image_paths, rotator, vid_id="001", prompt_mode="ppt"):
    """Analyze frames using Gemini Vision API with automatic key rotation and failover."""
    prompt_to_use = SYSTEM_PROMPT_SHOOPE if prompt_mode.lower() in ["shoope", "shopee"] else SYSTEM_PROMPT
    parts = [{"text": f"Video ID: {vid_id}\n\n" + prompt_to_use}]
    
    for img_p in image_paths:
        try:
            with open(img_p, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64_data
                    }
                })
        except Exception as e:
            print(f"Error reading image {img_p}: {e}", flush=True)
            
    payload_data = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
    max_retries = max(10, len(rotator.healthy_keys))
    retry_count = 0
    
    while retry_count < max_retries:
        key_obj = rotator.get_current_key()
        api_key = key_obj["api_key"]
        
        for model in MODELS_PRIORITY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=payload_data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_body = response.read().decode("utf-8")
                    data = json.loads(res_body)
                    text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    if text_out.startswith("```json"):
                        text_out = text_out[7:]
                    if text_out.startswith("```"):
                        text_out = text_out[3:]
                    if text_out.endswith("```"):
                        text_out = text_out[:-3]
                    text_out = text_out.strip()
                    
                    parsed = json.loads(text_out)
                    return parsed
            except urllib.error.HTTPError as e:
                if e.code in [429, 403, 400]:
                    rotator.mark_unhealthy_and_rotate(key_obj)
                    break
                else:
                    time.sleep(0.5)
            except Exception as e:
                time.sleep(0.5)
        retry_count += 1
        
    raise Exception(f"Failed to analyze video {vid_id} after {retry_count} retries.")

def analyze_single_video(video_path, frame_dir=None, vid_id="001", rotator=None, prompt_mode="ppt"):
    """Extracts frames and analyzes a single video with Gemini Vision AI."""
    from extractor import select_smart_frames
    
    if rotator is None:
        rotator = SmartKeyRotator()
        
    if frame_dir is None:
        video_name = Path(video_path).stem
        frame_dir = os.path.join(BASE_DIR, "frames", video_name)
    os.makedirs(frame_dir, exist_ok=True)
    
    single_json_p = os.path.join(frame_dir, "ai_analysis.json")
    meta_json_p = os.path.join(frame_dir, "metadata.json")
    
    if os.path.exists(single_json_p) and os.path.exists(meta_json_p):
        with open(single_json_p, "r", encoding="utf-8") as f:
            return json.load(f)
            
    meta = select_smart_frames(video_path, frame_dir)
    frame_files = [os.path.join(frame_dir, f["file"]) for f in meta.get("frames", [])]
    ai_res = call_gemini_vision(frame_files, rotator, vid_id, prompt_mode=prompt_mode)
    
    with open(single_json_p, "w", encoding="utf-8") as f:
        json.dump(ai_res, f, ensure_ascii=False, indent=2)
        
    return ai_res

def analyze_folder(folder_path, output_json_path=None, max_workers=8, prompt_mode="ppt", force_refresh=False):
    """Batch analyze all extracted frame folders in parallel and generate combined master JSON."""
    from extractor import select_smart_frames
    
    # Sort files naturally by numeric stem if possible
    raw_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.avi')) and not f.startswith('preview_') and not f.startswith('sample_')]
    def sort_key(p):
        stem = Path(p).stem
        return int(stem) if stem.isdigit() else 999999
    vids = sorted(raw_files, key=sort_key)
    
    folder_clean_name = Path(folder_path).name
    parent_clean_name = Path(folder_path).parent.name
    frames_dir = os.path.join(BASE_DIR, "frames", f"{parent_clean_name}_{folder_clean_name}" if parent_clean_name in ["ppt", "shoope"] else folder_clean_name)
    os.makedirs(frames_dir, exist_ok=True)

    rotator = SmartKeyRotator()
    combined_results = {}
    
    # Auto detect prompt mode if not explicitly set
    if "shoope" in str(folder_path).lower() or "shopee" in str(folder_path).lower():
        prompt_mode = "shoope"
        
    print(f"[vision.py] Starting parallel extraction + AI analysis for {len(vids)} videos in {folder_path} (mode={prompt_mode}, workers={max_workers}, force_refresh={force_refresh})...", flush=True)

    def process_single(idx, vp):
        stem = Path(vp).stem
        vid_id = f"{int(stem):03d}" if stem.isdigit() else f"{idx:03d}"
        v_frame_dir = os.path.join(frames_dir, vid_id)
        os.makedirs(v_frame_dir, exist_ok=True)
        
        single_json_p = os.path.join(v_frame_dir, "ai_analysis.json")
        meta_json_p = os.path.join(v_frame_dir, "metadata.json")
        
        if not force_refresh and os.path.exists(single_json_p) and os.path.exists(meta_json_p):
            try:
                with open(single_json_p, "r", encoding="utf-8") as f:
                    ai_res = json.load(f)
                with open(meta_json_p, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if prompt_mode == "shoope" and "affiliate_keywords" in ai_res and len(ai_res["affiliate_keywords"]) >= 3:
                    return idx, vid_id, vp, meta, ai_res, True, "Cached"
            except Exception:
                pass
            
        try:
            meta = select_smart_frames(vp, v_frame_dir)
            frame_files = [os.path.join(v_frame_dir, f["file"]) for f in meta.get("frames", [])]
            ai_res = call_gemini_vision(frame_files, rotator, vid_id, prompt_mode=prompt_mode)
            
            with open(single_json_p, "w", encoding="utf-8") as f:
                json.dump(ai_res, f, ensure_ascii=False, indent=2)
                
            return idx, vid_id, vp, meta, ai_res, True, "AI Done"
        except Exception as e:
            return idx, vid_id, vp, {}, {}, False, str(e)

    completed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(process_single, idx, vp): (idx, vp) for idx, vp in enumerate(vids, start=1)}
        for future in as_completed(futures):
            idx, vid_id, vp, meta, ai_res, ok, msg = future.result()
            completed += 1
            if ok:
                combined_results[vid_id] = {
                    "metadata": meta,
                    "ai_analysis": ai_res,
                    "source_file": vp
                }
                title_preview = ai_res.get("hook_text") or ai_res.get("title_overlay") or ai_res.get("product_name", "")
                print(f"[{completed:03d}/{len(vids)}] Video #{vid_id} -> {title_preview} ({msg})", flush=True)
            else:
                print(f"[{completed:03d}/{len(vids)}] Video #{vid_id} -> FAILED: {msg}", flush=True)

    # Sort combined results by key numeric
    sorted_keys = sorted(combined_results.keys(), key=lambda k: int(k) if k.isdigit() else 9999)
    sorted_combined = {k: combined_results[k] for k in sorted_keys}

    if output_json_path is None:
        output_json_path = os.path.join(folder_path, "combined_analysis.json")

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(sorted_combined, f, ensure_ascii=False, indent=2)

    db_path = os.path.join(folder_path, "database.json")
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(sorted_combined, f, ensure_ascii=False, indent=2)

    # If Shopee mode, generate search keywords documentation & template JSON
    if prompt_mode == "shoope":
        txt_doc_path = os.path.join(folder_path, "KATA_KUNCI_PENCARIAN_SHOPEE.txt")
        md_doc_path = os.path.join(folder_path, "KATA_KUNCI_PENCARIAN_SHOPEE.md")
        template_json_path = os.path.join(folder_path, "shopee_links_template.json")

        txt_lines = [
            "=" * 80,
            f"DOKUMENTASI KATA KUNCI PENCARIAN SHOPEE AFFILIATE & AREA LINK ({len(sorted_combined)} PRODUK)",
            "=" * 80,
            "Petunjuk:",
            "1. Salin kata kunci pencarian di bawah ke kolom pencarian Shopee Affiliate.",
            "2. Ambil link affiliate produk (s.shopee.co.id/...).",
            "3. Tempel link affiliate di bagian 'Link Shopee: ' atau di file shopee_links_template.json.",
            "=" * 80,
            ""
        ]

        md_lines = [
            f"# 🛒 Dokumentasi Kata Kunci Pencarian Shopee Affiliate ({len(sorted_combined)} Produk)\n",
            "> Gunakan kata kunci pencarian berikut untuk menemukan produk di Shopee Affiliate, lalu tempel link affiliate pada area yang tersedia.\n",
            "---\n"
        ]

        template_items = []

        for vid_id, data in sorted_combined.items():
            ai = data.get("ai_analysis", {})
            prod_name = ai.get("product_name", f"Produk #{vid_id}")
            cat = ai.get("category", "Barang Unik")
            hook = ai.get("hook_text", "INI BARANG APA?!")
            query = ai.get("affiliate_search_query", prod_name)
            keywords = ai.get("affiliate_keywords", [query])
            tts = ai.get("tts_narrative") or ai.get("reaction_caption", "")
            d1 = ai.get("desc_line1", "")
            d2 = ai.get("desc_line2", "")

            # TXT Format
            txt_lines.append("-" * 80)
            txt_lines.append(f"NO. {vid_id} | {prod_name}")
            txt_lines.append(f"Kategori : {cat}")
            txt_lines.append(f"Hook     : {hook}")
            txt_lines.append(f"Pencarian Utama Shopee : {query}")
            txt_lines.append("5 Kata Kunci Shopee   :")
            for k_idx, kw in enumerate(keywords, 1):
                txt_lines.append(f"   {k_idx}. {kw}")
            txt_lines.append(f"Narasi Voiceover (TTS) : {tts}")
            txt_lines.append(f"Link Shopee Affiliate  : [TEMPEL LINK SHOPEE DISINI]")
            txt_lines.append("")

            # MD Format
            md_lines.append(f"### 📦 NO. {vid_id} — {prod_name}")
            md_lines.append(f"- **Kategori:** `{cat}`")
            md_lines.append(f"- **Hook:** **{hook}**")
            md_lines.append(f"- **Pencarian Utama:** `{query}`")
            md_lines.append("- **5 Kata Kunci Shopee:**")
            for kw in keywords:
                md_lines.append(f"  - `{kw}`")
            md_lines.append(f"- **Narasi Voiceover:** *\"{tts}\"*")
            md_lines.append(f"- **Link Shopee Affiliate:** `[TEMPEL LINK SHOPEE DISINI]`\n")

            template_items.append({
                "spillNumber": vid_id,
                "title": prod_name,
                "category": cat,
                "hook": hook,
                "search_query": query,
                "search_keywords": keywords,
                "affiliateUrl": ""
            })

        with open(txt_doc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines))

        with open(md_doc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        with open(template_json_path, "w", encoding="utf-8") as f:
            json.dump(template_items, f, ensure_ascii=False, indent=2)

        print(f"[vision.py] Generated Keyword Documentation TXT: {txt_doc_path}")
        print(f"[vision.py] Generated Keyword Documentation MD:  {md_doc_path}")
        print(f"[vision.py] Generated Link Template JSON:       {template_json_path}")
        
    elapsed = time.time() - t0
    print(f"[vision.py] Finished AI batch analysis for {len(sorted_combined)} videos in {elapsed:.2f}s! Saved: {output_json_path}", flush=True)
    return sorted_combined

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gemini Vision Batch Analyzer")
    parser.add_argument("folder", nargs="?", default=None, help="Target folder to analyze")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--mode", type=str, default="shoope", help="Analysis mode (shoope / ppt)")
    parser.add_argument("--force", action="store_true", help="Force refresh cached AI analysis")
    args = parser.parse_args()

    if args.folder:
        analyze_folder(args.folder, max_workers=args.workers, prompt_mode=args.mode, force_refresh=args.force)
    else:
        print("[vision.py] Gemini Vision AI Batch Engine Ready.")
