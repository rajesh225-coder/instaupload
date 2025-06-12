# Yeh GitHub ke liye final, corrected code hai

import os
import cloudinary
import cloudinary.api
import cloudinary.uploader
import requests
import time
import tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageClip, VideoFileClip, ColorClip, CompositeVideoClip
import traceback

# --- CONFIGURATION (Yeh ab GitHub Secrets se aayega) ---
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "decqrz2gm")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "288795273313996")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "Q2anv-1fJKaF6zMSyfhzVEz-kWc")

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841470212310237")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "EAAIOK87vxkgBO5SZAT8O3F6rzb23wNBgZBSVZCHJOQApd5KZAaA2gAXjjAFCMvZC4TkRK4ad0UVQoQw36vtgVQ3b6l3SYDbAsXVTudxbzTQ774tvvvWZCOmMbmZAFgABhpt35ziE6lHeuB5sf5jV3XqHiEBeZCJpNORjXs5olccpStZAshIa6WZBzVFpTzEzHvVKkV14sohkEZAuglr5TFY")

# File ka path ab relative hoga, absolute (C:\...) nahi
# Agar GitHub par chal raha hai to relative, varna local PC ka path
if os.getenv("GITHUB_ACTIONS"):
    LAST_UPLOADED_FILE = "last_uploaded.txt"
else:
    LAST_UPLOADED_FILE = r"C:\Users\ADMIN\Desktop\WHATSAPP\movie\last_uploaded.txt"
# --- END OF CONFIGURATION ---

# Cloudinary ko configure karein
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def download_video(url, output_path):
    """Video ko URL se download karne ke liye function."""
    print(f"Downloading video from: {url}")
    try:
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Video downloaded successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading video: {e}")
        return False

def edit_video(input_path, output_path, video_title):
    """
    Video ko mobile format (1080x1920) mein edit karta hai.
    Upar title aur neeche text add karta hai.
    """
    try:
        print(f"Editing video with title: '{video_title}'")
        mobile_width, mobile_height = 1080, 1920

        # Font ka path ab relative hai, C:\... nahi
        try:
            # Agar GitHub par chal raha hai to relative path, varna local PC ka path
            if os.getenv("GITHUB_ACTIONS"):
                font_path = "nunitomedium.ttf"
            else:
                font_path = r"C:\Users\ADMIN\Desktop\WHATSAPP\movie\nunitomedium.ttf"
            
            title_font = ImageFont.truetype(font_path, 80)
            bottom_font = ImageFont.truetype(font_path, 55)
            print(f"Successfully loaded font: {font_path}")
        except IOError:
            print(f"ERROR: Font file '{font_path}' not found.")
            print("Using tiny default font instead.")
            title_font = ImageFont.load_default()
            bottom_font = ImageFont.load_default()

        with VideoFileClip(input_path) as clip:
            # === BADLAV 1: Background aur Text ka color badla gaya ===
            # Title banayein (Black background, White text)
            img = Image.new('RGB', (mobile_width, 150), color=(0, 0, 0)) # Black background
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), video_title, font=title_font)
            draw.text(((mobile_width - (bbox[2] - bbox[0])) / 2, (150 - (bbox[3] - bbox[1])) / 2), video_title, fill="white", font=title_font) # White text
            title_clip = ImageClip(np.array(img)).set_duration(clip.duration)
            
            w, h = clip.size
            crop_x = int(w * 0.15)
            cropped_clip = clip.crop(x1=crop_x, x2=w - crop_x)
            scale = min(mobile_width / cropped_clip.w, mobile_height / cropped_clip.h)
            clip_resized = cropped_clip.resize(scale)
            
            # Poori video ka background black kar diya
            background = ColorClip(size=(mobile_width, mobile_height), color=(0, 0, 0), duration=clip.duration) # Black background
            
            video_center_y = (mobile_height - clip_resized.h) // 2
            title_clip = title_clip.set_position(("center", video_center_y - 120))
            video_bottom_y = video_center_y + clip_resized.h
            
            # Bottom text (Black background, White text)
            bottom_text = "The next part will be out within 2 hours (keep watching)"
            bottom_img = Image.new('RGB', (mobile_width - 200, 160), color=(0, 0, 0)) # Black background
            bottom_draw = ImageDraw.Draw(bottom_img)
            lines = []
            words = bottom_text.split()
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if bottom_draw.textbbox((0, 0), test_line, font=bottom_font)[2] <= bottom_img.width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
            total_text_height = sum(bottom_draw.textbbox((0,0), line, font=bottom_font)[3] - bottom_draw.textbbox((0,0), line, font=bottom_font)[1] for line in lines)
            current_y = (bottom_img.height - total_text_height) / 2
            for line in lines:
                bbox = bottom_draw.textbbox((0, 0), line, font=bottom_font)
                bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
                bottom_draw.text(((bottom_img.width - bw) / 2, current_y), line, fill="white", font=bottom_font) # White text
                current_y += bh
            bottom_clip = ImageClip(np.array(bottom_img)).set_duration(clip.duration)
            bottom_clip = bottom_clip.set_position(("center", video_bottom_y + 10))
            
            final_clip = CompositeVideoClip(
                [background, clip_resized.set_position("center"), title_clip, bottom_clip],
                size=(mobile_width, mobile_height)
            )
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset="medium",
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                verbose=True,
                logger='bar'
            )
        print("Video editing finished successfully.")
        return True
    except Exception as e:
        print(f"An error occurred during video editing: {e}")
        traceback.print_exc()
        return False

def get_next_part_video_url():
    """Cloudinary se agla video dhoondhta hai jise process karna hai."""
    print("Step 1: Finding the next video to process...")
    last_part = 0
    if os.path.exists(LAST_UPLOADED_FILE):
        try:
            with open(LAST_UPLOADED_FILE, "r") as f:
                last_part = int(f.read().strip())
        except (IOError, ValueError):
            print(f"Warning: Could not read '{LAST_UPLOADED_FILE}'. Starting from part 1.")
            last_part = 0
    next_part = last_part + 1
    while True:
        next_part_str = f"part_{next_part}"
        print(f"Searching for '{next_part_str}'...")
        edited_prefix = f"edited_videos/Part_{next_part}"
        original_prefix = f"my_videos/Part_{next_part}"

        edited_resources = cloudinary.api.resources(
            type="upload", resource_type="video", prefix=edited_prefix, max_results=1
        )
        if 'resources' in edited_resources and len(edited_resources['resources']) > 0:
            print(f"'{next_part_str}' has already been edited. Checking next part.")
            next_part += 1
            continue
        resources = cloudinary.api.resources(
            type="upload", resource_type="video", prefix=original_prefix, max_results=1
        )
        if 'resources' in resources and len(resources['resources']) > 0:
            res = resources['resources'][0]
            public_id = res['public_id']
            secure_url = res['secure_url']
            print(f"Found video to process: {public_id}")
            return secure_url, next_part, public_id
        else:
            print(f"No video found for 'Part_{next_part}' in 'my_videos/'. Trying next part.")
            next_part += 1
            if next_part > last_part + 50:
                print("Searched for 50 parts and found nothing. Stopping.")
                return None, None, None

def post_to_instagram(video_url, caption):
    """Edited video ko Instagram par as a Reel post karta hai."""
    print("Step 4: Posting to Instagram...")
    try:
        create_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_USER_ID}/media"
        payload = {
            "video_url": video_url, "caption": caption, "media_type": "REELS", "access_token": ACCESS_TOKEN
        }
        resp = requests.post(create_url, data=payload, timeout=60)
        resp.raise_for_status()
        container_id = resp.json()["id"]
        print(f"Media container created: {container_id}")
        status_url = f"https://graph.facebook.com/v17.0/{container_id}?fields=status_code&access_token={ACCESS_TOKEN}"
        for i in range(20):
            status_resp = requests.get(status_url, timeout=30)
            status_resp.raise_for_status()
            status = status_resp.json()["status_code"]
            print(f"Media status check ({i+1}/20): {status}")
            if status == "FINISHED": break
            if status == "ERROR":
                print("Media processing failed with ERROR status.")
                return False
            time.sleep(5)
        else:
            print("Media processing timed out after 100 seconds.")
            return False
        publish_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_USER_ID}/media_publish"
        payload = {"creation_id": container_id, "access_token": ACCESS_TOKEN}
        resp = requests.post(publish_url, data=payload, timeout=60)
        resp.raise_for_status()
        print("Successfully posted to Instagram!", resp.json())
        return True
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while posting to Instagram: {e}")
        if 'response' in locals() and hasattr(locals()['response'], 'text'):
            print("API Response:", locals()['response'].text)
        return False

if __name__ == "__main__":
    video_url, part_number, public_id = get_next_part_video_url()
    if video_url:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input_video.mp4")
            output_path = os.path.join(tmpdir, "output_video.mp4")
            video_title_from_id = os.path.basename(public_id).replace("_", " ").replace("-", " ").capitalize()
            
            if not download_video(video_url, input_path): exit() 
            if not edit_video(input_path, output_path, video_title_from_id): exit() 
            
            try:
                print("Uploading edited video to Cloudinary...")
                cloudinary_public_id = os.path.basename(public_id) 
                uploaded = cloudinary.uploader.upload_large(
                    output_path, resource_type="video", folder="edited_videos/", public_id=cloudinary_public_id
                )
                edited_video_url = uploaded["secure_url"]
                print(f"Edited video uploaded: {edited_video_url}")
                
                caption = f"""🔥 This movie scene will blow your mind! 😱 ({video_title_from_id})

🎬 #ViralClip | 💥 #BlockbusterMoment | ❤️ #MustWatch

👉 Watch, share & tell me your reaction in the comments!
📌 Full movie link in bio!

#ShortFilm #MovieMagic #TrendingNow #Cinematic #InstaReels #FilmScene"""
                
                # Yeh line uncomment karein jab aap asli mein post karna chahte hain
                post_success = post_to_instagram(edited_video_url, caption)
                
                if post_success:
                    with open(LAST_UPLOADED_FILE, "w") as f:
                        f.write(str(part_number))
                    print(f"Successfully processed and uploaded Part {part_number}. Progress saved.")
            except Exception as e:
                print(f"An error occurred during upload or posting: {e}")
                traceback.print_exc()
    else:
        print("No new videos to process. Exiting.")
