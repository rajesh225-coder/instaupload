import os
import cloudinary
import cloudinary.api
import requests
import time
import random
import traceback

# --- CONFIGURATION ---
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "YOUR_CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "YOUR_CLOUDINARY_API_SECRET")

INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "YOUR_INSTAGRAM_ACCESS_TOKEN")

VIDEO_SOURCE_FOLDER = "For_Youtube_Videos"

MOTIVATIONAL_TITLES = [
    "🚀 Unleash Your Potential! Your daily dose of inspiration is here.",
    "🌟 Dream Big, Work Hard. What's inspiring you today?",
    "💡 Find Your Spark! Every moment is a fresh beginning.",
    "💪 Conquer Your Goals! You are stronger than you think.",
    "✨ Believe in Yourself! Anything is possible with dedication.",
    "🌱 Grow Stronger Every Day. Embrace the journey!",
    "🌈 Chase Your Dreams! Don't let anything hold you back.",
    "💖 Inspire and Be Inspired. Share the positivity!"
]

FIXED_HASHTAGS = "#Motivation #Inspiration #Success #Mindset #Goals #DailyMotivation #PositiveVibes #Achieve"

# File to keep track of posted video public_ids
# GitHub Actions environment mein, yeh file action run ke beech persist nahi karti.
# Iske liye GitHub Actions artifacts ka upyog karna hoga.
# Abhi ke liye, yeh maan rahe hain ki yeh local run ya kisi aise setup mein chalega jahan file persist karti hai.
# GitHub Actions ke liye, niche YAML section dekhein.
POSTED_VIDEOS_FILE = "posted_videos.txt"
# --- END CONFIGURATION ---

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def get_posted_videos():
    """Reads the list of public_ids of videos that have already been posted."""
    if not os.path.exists(POSTED_VIDEOS_FILE):
        return set()
    try:
        with open(POSTED_VIDEOS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"Error reading {POSTED_VIDEOS_FILE}: {e}")
        return set()

def save_posted_video(public_id):
    """Saves the public_id of a successfully posted video to the file."""
    try:
        with open(POSTED_VIDEOS_FILE, "a") as f:
            f.write(public_id + "\n")
    except IOError as e:
        print(f"Error writing to {POSTED_VIDEOS_FILE}: {e}")

def clear_posted_videos_file():
    """Clears the posted_videos.txt file."""
    try:
        if os.path.exists(POSTED_VIDEOS_FILE):
            os.remove(POSTED_VIDEOS_FILE)
            print(f"Cleared {POSTED_VIDEOS_FILE} as all videos have been posted.")
    except Exception as e:
        print(f"Error clearing {POSTED_VIDEOS_FILE}: {e}")

def get_next_unposted_video(folder_name):
    """
    Fetches all videos from the specified folder and returns a random one
    that hasn't been posted yet. Manages repetition tracking.
    """
    print(f"Fetching videos from Cloudinary folder: '{folder_name}'...")
    try:
        if not cloudinary.config().cloud_name or \
           not cloudinary.config().api_key or \
           not cloudinary.config().api_secret:
            print("Error: Cloudinary credentials not set.")
            return None, None, None

        all_video_resources = []
        next_cursor = None
        while True:
            result = cloudinary.api.resources(
                type="upload",
                resource_type="video",
                prefix=f"{folder_name}/",
                max_results=100, # Fetch in batches
                next_cursor=next_cursor
            )
            all_video_resources.extend(result.get('resources', []))
            next_cursor = result.get('next_cursor')
            if not next_cursor:
                break
        
        if not all_video_resources:
            print(f"No videos found in Cloudinary folder: '{folder_name}'.")
            return None, None, None

        posted_public_ids = get_posted_videos()
        
        available_videos = [
            res for res in all_video_resources
            if res['public_id'] not in posted_public_ids
        ]

        if not available_videos:
            print("All videos have been posted. Resetting cycle.")
            clear_posted_videos_file()
            # After clearing, all videos are available again for the next cycle
            available_videos = all_video_resources
            if not available_videos: # Handle case where folder is empty even after reset
                print("No videos found even after resetting posted list.")
                return None, None, None

        selected_video = random.choice(available_videos)
        secure_url = selected_video['secure_url']
        public_id = selected_video['public_id']
        print(f"Selected unposted video: {public_id}")
        return secure_url, public_id, all_video_resources # all_video_resources return kiya ja raha hai for context

    except Exception as e:
        print(f"Error fetching videos from Cloudinary: {e}")
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
        resp.raise_for_status() # HTTP errors ke liye exception throw karega
        container_id = resp.json()["id"]
        print(f"Media container created: {container_id}")

        status_url = f"https://graph.facebook.com/v17.0/{container_id}?fields=status_code&access_token={ACCESS_TOKEN}"
        print("Waiting for media processing to finish...")
        for i in range(20): # 20 attempts, har 5 second mein = 100 seconds max wait
            time.sleep(5)
            status_resp = requests.get(status_url, timeout=30)
            status_resp.raise_for_status()
            status = status_resp.json()["status_code"]
            print(f"Media status check ({i+1}/20): {status}")
            if status == "FINISHED":
                print("Media processing finished. Ready to publish.")
                break
            if status == "ERROR":
                print(f"Media processing failed with ERROR status. Response: {status_resp.json()}")
                return False
        else:
            print("Media processing timed out after multiple checks.")
            return False
            
        publish_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_USER_ID}/media_publish"
        payload = {"creation_id": container_id, "access_token": ACCESS_TOKEN}
        resp = requests.post(publish_url, data=payload, timeout=60)

        resp.raise_for_status()
        print("Successfully posted to Instagram!", resp.json())
        return True

    except requests.exceptions.RequestException as e:
        print(f"An HTTP or network error occurred while posting to Instagram: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("API Response Content:", e.response.text)
        return False
    except Exception as e:
        print(f"An unexpected error occurred while posting to Instagram: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Get the next unposted video and the list of all videos for cycle management
    video_url, public_id, all_videos = get_next_unposted_video(VIDEO_SOURCE_FOLDER)

    if video_url:
        selected_title = random.choice(MOTIVATIONAL_TITLES)
        caption = f"{selected_title}\n\n{FIXED_HASHTAGS}"

        print(f"\n--- Posting video: {video_url} ---")
        print(f"--- With caption: {caption} ---")

        try:
            post_success = post_to_instagram(video_url, caption)

            if post_success:
                save_posted_video(public_id)
                print(f"Video '{public_id}' successfully posted and marked as posted.")
            else:
                print(f"Failed to post video '{public_id}' to Instagram.")
        except Exception as e:
            print(f"A critical error occurred during the posting process for video '{public_id}': {e}")
            traceback.print_exc()
    else:
        print(f"No new videos found in '{VIDEO_SOURCE_FOLDER}' or an error occurred. Exiting.")
