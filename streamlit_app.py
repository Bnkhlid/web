import os
import threading
import uuid
import yt_dlp
import streamlit as st
import time

# مكان حفظ التحميلات
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# حالات المهام (in-memory)
jobs = {}

def run_download(job_id, url, fmt, headers=None):
    try:
        outtmpl = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": False,
            "restrictfilenames": True,
        }
        if headers:
            ydl_opts["http_headers"] = headers

        jobs[job_id].update({"state": "starting", "progress": 0, "info": "Preparing download..."})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files_downloaded = []

        if "entries" in info:  # playlist
            for entry in info["entries"]:
                if not entry:
                    continue
                ext = entry.get("ext") or "mp4"
                filename = f"{entry.get('id')}.{ext}"
                if filename in os.listdir(DOWNLOAD_DIR):
                    files_downloaded.append(filename)
        else:  # فيديو واحد
            ext = info.get("ext") or "mp4"
            filename = f"{info.get('id')}.{ext}"
            if filename in os.listdir(DOWNLOAD_DIR):
                files_downloaded.append(filename)

        if files_downloaded:
            jobs[job_id].update({
                "state": "finished",
                "progress": 100.0,
                "files": files_downloaded,
                "info": f"{len(files_downloaded)} file(s) ready"
            })
        else:
            jobs[job_id].update({"state": "error", "info": "Downloaded but couldn't find output files."})
    except Exception as e:
        jobs[job_id].update({"state": "error", "info": str(e)})

# واجهة Streamlit
st.title("🎬 LinxGo")

url = st.text_input("Download videos from YouTube, TikTok, Facebook, Instagram and X.")
quality = st.selectbox("quality", ["high", "medium", "low", "audio"])

if st.button("Start Download"):
    if url:
        if quality == "high":
            fmt = "bestvideo+bestaudio/best"
        elif quality == "medium":
            fmt = "bv[height<=720]+ba/best[height<=720]"
        elif quality == "low":
            fmt = "worst"
        else:
            fmt = "bestaudio"

        job_id = str(uuid.uuid4())
        jobs[job_id] = {"state": "queued", "progress": 0, "info": "Queued", "files": [], "url": url}

        headers = None
        if "tiktok.com" in url or "vm.tiktok.com" in url:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/"
            }

        threading.Thread(target=run_download, args=(job_id, url, fmt, headers), daemon=True).start()
        st.success(f"🚀 Start Download. Job ID: {job_id}")

        # متابعة الحالة بشكل حي
        status_placeholder = st.empty()
        while jobs[job_id]["state"] not in ["finished", "error"]:
            status_placeholder.write(f"Job {job_id}: {jobs[job_id]['state']} - {jobs[job_id]['info']}")
            time.sleep(1)

        if jobs[job_id]["state"] == "finished":
            status_placeholder.success(f"✅ Job {job_id} finished! {len(jobs[job_id]['files'])} file(s) ready.")
            for f in jobs[job_id]["files"]:
                file_path = os.path.join(DOWNLOAD_DIR, f)
                with open(file_path, "rb") as file_data:
                    st.download_button("Download " + f, file_data, file_name=f)
        elif jobs[job_id]["state"] == "error":
            status_placeholder.error(f"❌ Job {job_id} failed: {jobs[job_id]['info']}")