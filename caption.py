"""
caption.py - Single Master Caption & Hashtag TXT Generator (TikTok / Reels Ready)
Consolidates all captions into a single copy-paste ready format per video with full caption & hashtag filenames.
"""

import os
import sys
import json
import re
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.resolve()

def extract_clean_hashtags(raw_hashtags: list, max_tags: int = 5) -> str:
    """Cleans, formats with #, and deduplicates hashtags."""
    seen = set()
    clean_tags = []
    for tag in raw_hashtags:
        t = tag.strip()
        if not t:
            continue
        if not t.startswith("#"):
            t = f"#{t}"
        if t.lower() not in seen:
            seen.add(t.lower())
            clean_tags.append(t)
    return " ".join(clean_tags[:max_tags]).strip()

def build_shoope_caption_150(item: dict, max_chars: int = 150) -> str:
    """
    Builds a caption strictly <= 150 characters (including hashtags & spaces) for Shopee Video Mobile.
    Format: [Hook / Brief Body] [Hashtags] (Total <= 150 chars)
    """
    ai = item.get("ai_analysis", {})
    hook = (ai.get("hook_text") or "").strip()
    reaction = (ai.get("reaction_caption") or "").strip()
    raw_hashtags = ai.get("hashtags", [])

    tags_str = extract_clean_hashtags(raw_hashtags, max_tags=3)
    if not tags_str:
        tags_str = "#BarangUnik #RacunShopee #ShopeeHaul"

    # Combine body
    if reaction.startswith(hook):
        body = reaction
    else:
        body = f"{hook} {reaction}".strip()

    # Remove hashtags from inside body text
    body_clean = re.sub(r'#\w+', '', body)
    body_clean = re.sub(r'\s+', ' ', body_clean).strip()

    # Reserve space for hashtags
    avail_body_space = max_chars - len(tags_str) - 1
    if avail_body_space < 25:
        tags_str = extract_clean_hashtags(raw_hashtags, max_tags=2)
        avail_body_space = max_chars - len(tags_str) - 1

    if len(body_clean) > avail_body_space:
        trimmed = body_clean[:avail_body_space].rstrip(' .,!?')
        last_space = trimmed.rfind(' ')
        if last_space > 20:
            body_clean = trimmed[:last_space].rstrip(' .,!?')
        else:
            body_clean = trimmed

    final_caption = f"{body_clean} {tags_str}".strip()
    if len(final_caption) > max_chars:
        final_caption = final_caption[:max_chars].rstrip(' .,!?')

    return final_caption

def build_full_caption_text(item: dict) -> str:
    """Builds the complete single-paragraph caption containing hook, reaction, and hashtags."""
    ai = item.get("ai_analysis", {})
    # If Shopee product analysis, enforce strict 150 characters limit
    if "product_name" in ai or "affiliate_keywords" in ai:
        return build_shoope_caption_150(item, max_chars=150)

    hook = (ai.get("hook_text") or ai.get("hook_overlay") or "").strip()
    reaction = (ai.get("reaction_caption") or "").strip()
    raw_hashtags = ai.get("hashtags", [])

    tags_str = extract_clean_hashtags(raw_hashtags, max_tags=6)

    parts = []
    if hook:
        parts.append(hook)
    if reaction:
        parts.append(reaction)
    if tags_str:
        parts.append(tags_str)

    full_text = " ".join(parts).strip()
    if not full_text:
        full_text = (ai.get("title_overlay") or ai.get("title") or "Tutorial PowerPoint Morph").strip()
    return full_text

def caption_to_filename(item_or_caption, max_total_chars: int = 185) -> str:
    """
    Constructs a valid Windows filename containing the full Hook/Caption AND Hashtags at the end,
    while safely respecting Windows MAX_PATH limits.
    """
    if isinstance(item_or_caption, dict):
        ai = item_or_caption.get("ai_analysis", {})
        hook = (ai.get("hook_text") or ai.get("hook_overlay") or "").strip()
        reaction = (ai.get("reaction_caption") or "").strip()
        raw_hashtags = ai.get("hashtags", [])
        tags_str = extract_clean_hashtags(raw_hashtags, max_tags=5)
        main_text = f"{hook} {reaction}".strip()
        if not main_text:
            main_text = (ai.get("title_overlay") or ai.get("title") or "Tutorial PowerPoint Morph").strip()
    else:
        # If passed string, extract hashtags from end
        full_s = str(item_or_caption).strip()
        tags = [w for w in full_s.split() if w.startswith('#')]
        tags_str = " ".join(tags[:5]).strip()
        main_text = " ".join([w for w in full_s.split() if not w.startswith('#')]).strip()

    # Sanitize illegal Windows characters
    main_clean = re.sub(r'[\/\\:\*\?\"<>\|\r\n\t]', ' ', main_text)
    main_clean = re.sub(r'\s+', ' ', main_clean).strip(' .')

    tags_clean = re.sub(r'[\/\\:\*\?\"<>\|\r\n\t]', ' ', tags_str)
    tags_clean = re.sub(r'\s+', ' ', tags_clean).strip(' .')

    # Reserve space for hashtags at the end of the filename
    space_for_main = max_total_chars - len(tags_clean) - 2
    if len(main_clean) > space_for_main:
        trimmed = main_clean[:space_for_main].rstrip(' .')
        last_space = trimmed.rfind(' ')
        if last_space > 30:
            main_clean = trimmed[:last_space].rstrip(' .')
        else:
            main_clean = trimmed

    if tags_clean:
        final_name = f"{main_clean} {tags_clean}".strip()
    else:
        final_name = main_clean

    return f"{final_name}.mp4"

def generate_master_caption_txt(json_path: str, output_txt_path: str = None) -> str:
    """Reads combined analysis JSON and writes a single clean CAPTION_SEMUA_VIDEO.txt file."""
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return ""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sorted_vids = sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else x)
    total_videos = len(sorted_vids)

    lines = []
    lines.append("=" * 80)
    lines.append(f"DESKRIPSI & HASHTAG TIKTOK / REELS - {total_videos} VIDEO (SIAP SALIN)")
    lines.append("=" * 80)
    lines.append("Format: Nama File Video (Dengan Hashtag) -> Paragraf Caption & Hashtag Siap Salin.")
    lines.append("-" * 80)
    lines.append("")

    for idx, vid_id in enumerate(sorted_vids, start=1):
        item = data[vid_id]
        ai = item.get("ai_analysis", {})
        title = ai.get("hook_text") or ai.get("title_overlay") or ai.get("title", f"Video {vid_id}")
        topic = ai.get("product_name") or ai.get("tutorial_topic", "")
        aff_query = ai.get("affiliate_search_query", "")
        aff_kws = ai.get("affiliate_keywords", [])
        aff_link = ai.get("affiliate_link", "")

        full_caption_paragraph = build_full_caption_text(item)
        out_filename = f"{vid_id}.mp4"

        lines.append("-" * 80)
        lines.append(f"NO. {idx:03d} | FILE: {out_filename}")
        lines.append(f"📦 PRODUK/TOPIK : {topic}")
        lines.append(f"🔥 HOOK VIDEO    : {title}")
        if aff_query:
            lines.append(f"🔍 SEARCH QUERY  : {aff_query}")
        if aff_kws:
            lines.append(f"🏷️ 5 KATA KUNCI AFFILIATE (SHOPEE SEARCH):")
            for k_idx, kw in enumerate(aff_kws, start=1):
                lines.append(f"   {k_idx}. {kw}")
        lines.append("")
        lines.append(f"📝 CAPTION SIAP SALIN (Panjang: {len(full_caption_paragraph)}/150 karakter):")
        lines.append(full_caption_paragraph)
        if aff_link:
            lines.append(f"🔗 {aff_link}")
        lines.append("")

    txt_content = "\n".join(lines)

    if output_txt_path is None:
        parent_dir = Path(json_path).parent
        output_txt_path = parent_dir / "outputs" / "CAPTION_SEMUA_VIDEO.txt"

    os.makedirs(Path(output_txt_path).parent, exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    print(f"[caption.py] Master caption file saved to: {output_txt_path}")
    return txt_content

if __name__ == "__main__":
    if len(sys.argv) > 1:
        jpath = sys.argv[1]
        out_p = sys.argv[2] if len(sys.argv) > 2 else None
        generate_master_caption_txt(jpath, out_p)
    else:
        default_json = BASE_DIR / "1_combined_analysis.json"
        if default_json.exists():
            generate_master_caption_txt(str(default_json), str(BASE_DIR / "ppt" / "1" / "outputs" / "CAPTION_SEMUA_VIDEO.txt"))
        else:
            print("[caption.py] Single Master Caption Generator Ready.")
