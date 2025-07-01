# extract.py
import json
import httpx
import asyncio
from datetime import datetime
import re

API = "https://khan-sir-free-class.onrender.com/api"
BATCH_FILE = "New_Sunny.json"

all_batches = {}

async def load_batches():
    global all_batches
    with open(BATCH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    all_batches = {b["id"]: b["title"] for b in data}

def search_batches(term: str):
    return [(bid, name) for bid, name in all_batches.items() if term.lower() in name.lower()]

async def classroom(batch_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API}/classroom/{batch_id}")
        resp.raise_for_status()
        classes = resp.json().get("classroom", [])
        return [{
            "id": cls.get("id"),
            "name": cls.get("name"),
            "notes": cls.get("notes", 0),
            "videos": cls.get("videos", 0)
        } for cls in classes]

async def get_latest_update(batch_id):
    # From the batch list JSON, get 'updated_at' or similar field
    # Fallback to today if not found (optional)
    # Your New_Sunny.json may not have update date, so:
    # We'll simulate getting update date from the batch itself if possible
    
    # Attempt 1: find from all_batches dictionary if it has dates (usually not)
    # So here, we fake "ongoing" check by current date (always ongoing)
    
    return datetime.utcnow()  # or you can implement a real check if API gives date

async def extract_batch_summary(batch_id, batch_name):
    subjects = await classroom(batch_id)
    if not subjects:
        return f"📘 Batch: {batch_name}\nNo subjects found."

    # Get update date - simplified here as today for demo
    last_update = await get_latest_update(batch_id)
    now = datetime.utcnow()
    ongoing = (now - last_update).days < 30  # Active if updated within last 30 days
    
    summary = f"📘 Selected: {batch_name}\n"
    summary += f"📅 Updated: {last_update.strftime('%d %b %Y')} — {'✅ Ongoing' if ongoing else '❌ Inactive'}\n\n"
    summary += f"📚 Subjects: {len(subjects)}\n"

    for sub in subjects:
        summary += f"➡️ {sub['name']} ({sub['videos']} videos, {sub['notes']} notes)\n"

    return summary.strip()

async def video(video_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API}/video/{video_id}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("hd_video_url") or data.get("video_url")

async def lesson(class_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API}/lesson/{class_id}")
        resp.raise_for_status()
        data = resp.json()
        lesson_name = data.get("name", "")
        videos = data.get("videos", [])
        results = []

        sorted_videos = sorted(videos, key=lambda x: x.get("published_at") or "")

        for v in sorted_videos:
            vid_id = v.get("id")
            title = v.get("name", "Untitled Video")
            published = v.get("published_at", "")
            try:
                pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S.%fZ")
                pub_str = pub_date.strftime("%d %b %Y")
            except:
                pub_str = "Unknown Date"

            video_url = await video(vid_id)
            if not video_url:
                continue

            block = f"🎥 {title} ({pub_str})\n{video_url}"

            pdfs = v.get("pdfs", [])
            if isinstance(pdfs, list):
                for pdf in pdfs:
                    pdf_title = pdf.get("title", title)
                    pdf_url = pdf.get("url")
                    if pdf_url:
                        block += f"\n📄 {pdf_title}\n{pdf_url}"
            results.append(block)

        return lesson_name, results

def sanitize_filename(name):
    # Remove invalid chars for filenames
    return re.sub(r'[\\/*?:"<>|]', "_", name)

async def extract_full_batch(batch_id, batch_name):
    subjects = await classroom(batch_id)
    collected_links = []

    for sub in subjects:
        lesson_name, video_blocks = await lesson(sub["id"])
        collected_links.append(f"📂 Subject: {lesson_name} ({sub['videos']} videos, {sub['notes']} notes)\n")
        collected_links.extend(video_blocks)
        collected_links.append("\n")

    output = f"📘 Batch: {batch_name}\n\n" + "\n\n".join(collected_links)
    filename = sanitize_filename(batch_name) + ".txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(output)

    total_entries = sum(len(await lesson(sub["id"]))[1] for sub in subjects)
    return filename, total_entries
