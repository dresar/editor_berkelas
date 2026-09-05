"""
downloader.py - High-Performance Multi-threaded HD Video Downloader
Downloads direct video streams from scraper datasets and names them sequentially (001.mp4 - N.mp4).
Includes smart CDN hostname fallback, direct file write (zero Windows file-lock errors), and multi-pass retry.
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure UTF-8 standard output
sys.stdout.reconfigure(encoding='utf-8')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

FALLBACK_NETLOCS = [
    None, # original first
    "instagram.fgla3-1.fna.fbcdn.net",
    "scontent.cdninstagram.com",
    "instagram.fsin9-1.fna.fbcdn.net",
    "instagram.fcgk28-1.fna.fbcdn.net"
]

def download_single_video(url: str, output_path: str, max_retries: int = 4) -> tuple:
    """Downloads a single video file directly with fallback CDN, retry, and size check."""
    if os.path.exists(output_path) and os.path.getsize(output_path) > 30000:
        return output_path, True, f"Skipped (Already exists: {os.path.getsize(output_path)/1024/1024:.2f} MB)"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive"
    }

    parsed_url = urllib.parse.urlparse(url)

    for netloc in FALLBACK_NETLOCS:
        current_url = url if netloc is None else urllib.parse.urlunparse(parsed_url._replace(netloc=netloc))
        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(current_url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP Status {resp.status}")
                    
                    with open(output_path, "wb") as f_out:
                        while True:
                            chunk = resp.read(1024 * 128)
                            if not chunk:
                                break
                            f_out.write(chunk)
                        f_out.flush()

                # Validate file size
                if os.path.exists(output_path) and os.path.getsize(output_path) > 25000:
                    size_mb = os.path.getsize(output_path) / 1024 / 1024
                    return output_path, True, f"HD OK ({size_mb:.2f} MB)"
                else:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise Exception("Downloaded file too small or incomplete")

            except Exception as e:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except Exception:
                        pass
                if netloc is None and "getaddrinfo failed" in str(e):
                    # Fast fail original on DNS error to immediately use fallback CDN
                    break
                if attempt == max_retries and netloc == FALLBACK_NETLOCS[-1]:
                    return output_path, False, f"Error: {e}"
                time.sleep(1.0 * attempt)

    return output_path, False, "Max retries exceeded across all CDN mirrors"

def download_dataset(json_path: str, output_dir: str, max_workers: int = 8, max_passes: int = 4):
    """
    Parses dataset JSON, extracts HD video URLs, and downloads all videos sequentially as 001.mp4, 002.mp4, ... N.mp4.
    Runs in multi-pass mode until 100% of files are completed.
    """
    json_p = Path(json_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean legacy temp files
    for tmp_file in out_dir.glob("*.part*"):
        try:
            tmp_file.unlink()
        except Exception:
            pass

    if not json_p.exists():
        print(f"[downloader.py] Error: JSON file not found: {json_p}")
        return

    with open(json_p, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Extract all video URLs
    items = []
    if isinstance(raw_data, list):
        for idx, entry in enumerate(raw_data):
            if isinstance(entry, dict):
                v_url = entry.get("video_url") or entry.get("url") or entry.get("videoUrl")
                if v_url:
                    items.append({"original_index": idx, "url": v_url, "meta": entry})
            elif isinstance(entry, str) and entry.startswith("http"):
                items.append({"original_index": idx, "url": entry, "meta": {}})
    elif isinstance(raw_data, dict):
        for k, entry in raw_data.items():
            if isinstance(entry, dict):
                v_url = entry.get("video_url") or entry.get("url")
                if v_url:
                    items.append({"original_index": k, "url": v_url, "meta": entry})

    total = len(items)
    print(f"\n================================================================================")
    print(f"[downloader.py] MEMULAI DOWNLOAD {total} VIDEO HD KE FOLDER: {out_dir.name}")
    print(f"================================================================================")
    print(f"Dataset : {json_p.name}")
    print(f"Output  : {out_dir}")
    print(f"Threads : {max_workers}\n")

    mapping = []
    download_tasks = []

    for idx, item in enumerate(items, start=1):
        filename = f"{idx:03d}.mp4"
        file_path = str(out_dir / filename)
        mapping.append({
            "number": idx,
            "filename": filename,
            "url": item["url"],
            "original_meta": item["meta"]
        })
        download_tasks.append((idx, item["url"], file_path))

    # Save mapping file
    mapping_file = out_dir / "download_mapping.json"
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

    start_time = time.time()

    for pass_num in range(1, max_passes + 1):
        pending_tasks = []
        already_done = 0
        for idx, url, fpath in download_tasks:
            if os.path.exists(fpath) and os.path.getsize(fpath) > 25000:
                already_done += 1
            else:
                pending_tasks.append((idx, url, fpath))

        if not pending_tasks:
            elapsed = time.time() - start_time
            print(f"\n================================================================================")
            print(f"[downloader.py] 100% SUKSES! Semua {total}/{total} video selesai di-download dalam {elapsed:.2f} detik.")
            print(f"================================================================================\n")
            return

        print(f"[Pass {pass_num}/{max_passes}] Status: {already_done}/{total} sudah selesai. Mengunduh {len(pending_tasks)} video sisanya...\n", flush=True)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(download_single_video, url, fpath): (idx, fpath)
                for idx, url, fpath in pending_tasks
            }

            for future in as_completed(future_map):
                idx, fpath = future_map[future]
                out_p, ok, msg = future.result()
                status_symbol = "✔ [HD OK]" if ok else "✖ [FAILED]"
                print(f"[Pass {pass_num}] {status_symbol} #{idx:03d}.mp4 -> {msg}", flush=True)

    elapsed = time.time() - start_time
    print(f"\n[downloader.py] Selesai dengan {already_done}/{total} terunduh dalam {elapsed:.2f} detik.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        j_path = sys.argv[1]
        o_path = sys.argv[2]
        workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        download_dataset(j_path, o_path, max_workers=workers)
    else:
        # Default run for alam dataset
        default_json = r"C:\Users\NCN0C\Music\editor_berkelas\dataset_ig-reels-scraper_2026-08-14_19-29-41-320.json"
        default_out = r"C:\Users\NCN0C\Music\editor_berkelas\alam"
        download_dataset(default_json, default_out, max_workers=8)
