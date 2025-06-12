import os
import cloudinary
import cloudinary.api
import requests
import time
import traceback

# --- CONFIGURATION ---
# Yeh values GitHub Secrets se aayengi, ya agar wahan nahi milin to local default istemal hongi
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "decqrz2gm")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "288795273313996")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "Q2anv-1fJKaF6zMSyfhzVEz-kWc")

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841470212310237")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "EAAIOK87vxkgBO5SZAT8O3F6rzb23wNBgZBSVZCHJOQApd5KZAaA2gAXjjAFCMvZC4TkRK4ad0UVQoQw36vtgVQ3b6l3SYDbAsXVTudxbzTQ774tvvvWZCOmMbmZAFgABhpt35ziE6lHeuB5sf5jV3XqHiEBeZCJpNORjXs5olccpStZAshIa6WZBzVFpTzEzHvVKkV14sohkEZAuglr5TFY")

# Agar script GitHub par chal rahi hai to relative path, varna local PC ka path istemal hoga
if os.getenv("GITHUB_ACTIONS"):
    POSTED_PARTS_FILE = "posted_parts.txt"
else:
    POSTED_PARTS_FILE = r"C:\Users\ADMIN\Desktop\WHATSAPP\movie\posted_parts.txt"
# --- END CONFIGURATION ---

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)


def get_posted_parts():
    """posted_parts.txt se un sabhi parts ki list laata hai jo pehle hi post ho chuke hain."""
    if not os.path.exists(POSTED_PARTS_FILE):
        return set()
    try:
        with open(POSTED_PARTS_FILE, "r") as f:
            return set(line.strip().lower() for line in f if line.strip())
    except IOError as e:
        print(f"Error reading {POSTED_PARTS_FILE}: {e}")
        return set()


def save_posted_part(part_name):
    """Safalta se post hue part ka naam file mein save karta hai."""
    try:
        with open(POSTED_PARTS_FILE, "a") as f:
            f.write(part_name.lower() + "\n")
    except IOError as e:
        print(f"Error writing to {POSTED_PARTS_FILE}: {e}")


def get_next_unposted_video():
    """Agla video dhoondhta hai jo abhi tak post nahi hua hai."""
    print("Finding next unposted video...")
    posted_parts = get_posted_parts()
    part_number = 1
    # Ek limit laga di hai taaki anant loop na chale
    while part_number < 10000: 
        part_name = f"part_{part_number}"
        
        # Step 1: Local file mein check karein
        if part_name in posted_parts:
            # Agar yeh part pehle hi post ho chuka hai, to agla check karein
            part_number += 1
            continue
        
        # Step 2: Agar post nahi hua hai, to Cloudinary par check karein
        print(f"Checking for 'Part_{part_number}' on Cloudinary...")
        prefix_to_search = f"my_videos/Part_{part_number}"
        
        resources = cloudinary.api.resources(
            type="upload", resource_type="video", prefix=prefix_to_search, max_results=1
        )
        
        if 'resources' in resources and len(resources['resources']) > 0:
            res = resources['resources'][0]
            public_id = res['public_id']
            secure_url = res['secure_url']
            print(f"Found video to process: {public_id}")
            return secure_url, part_number, public_id
        else:
            # Agar Cloudinary par agla part nahi milta hai, to process rok dein
            print(f"No video found for 'Part_{part_number}' in 'my_videos/'. Stopping.")
            return None, None, None
            
    print("Reached search limit of 10000 parts. Stopping.")
    return None, None, None


def post_to_instagram(video_url, caption):
    """Video ko Instagram par as a Reel post karta hai."""
    print("Posting to Instagram...")
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
            time.sleep(5)
            status_resp = requests.get(status_url, timeout=30)
            status_resp.raise_for_status()
            status = status_resp.json()["status_code"]
            print(f"Media status check ({i+1}/20): {status}")
            if status == "FINISHED": break
            if status == "ERROR":
                print("Media processing failed with ERROR status.")
                return False
        else:
            print("Media processing timed out.")
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
    video_url, part_number, public_id = get_next_unposted_video()

    if video_url:
        video_title_from_id = os.path.basename(public_id).replace("_", " ").replace("-", " ").capitalize()
        caption = f"""🔥 This scene will blow your mind! 😱 ({video_title_from_id})

🎬 #ViralClip | 💥 #BlockbusterMoment | ❤️ #MustWatch

👉 What do you think happens next? Let me know below! 👇

#MovieScene #FilmCommunity #Reels #TrendingNow #MustSee"""

        try:
            post_success = post_to_instagram(video_url, caption)

            if post_success:
                save_posted_part(f"part_{part_number}")
                print(f"Successfully posted Part {part_number} and progress saved.")
        except Exception as e:
            print(f"A critical error occurred in the main process: {e}")
            traceback.print_exc()
    else:
        print("No new videos found to process. Exiting.")
