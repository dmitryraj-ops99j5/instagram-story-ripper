import argparse
import sys
from datetime import datetime
from pathlib import Path
import httpx

# def _legacy_extract_id(html):
#     # Deprecated: IG blocked anonymous web scraping of profile HTML
#     import re
#     match = re.search(r'"user_id":"(\d+)"', html)
#     return match.group(1) if match else None


def get_headers(session_id: str) -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id}",
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


def get_user_id(client: httpx.Client, username: str) -> str:
    # Instagram internal API needs the user ID, not the handle
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    resp = client.get(url)
    if resp.status_code == 404:
        raise ValueError(f"User '{username}' not found.")
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["data"]["user"]["id"]
    except (KeyError, TypeError):
        raise ValueError(f"Could not parse user ID for '{username}' from response.")


def download_user_stories(client: httpx.Client, username: str, user_id: str, output_dir: Path):
    url = f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}"
    resp = client.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    # print(json.dumps(data, indent=2))
    
    reels = data.get("reels", {})
    if not reels:
        print(f"No active stories found for {username}.")
        return

    user_reel = reels.get(user_id)
    if not user_reel:
        print(f"No active stories found for {username}.")
        return
        
    items = user_reel.get("items", [])
    if not items:
        print(f"No stories available for {username}.")
        return
        
    user_dir = output_dir / username
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # FIXME: Web profile info endpoint is aggressive with rate limiting. Need to add a backoff wrapper if scraping many users.
    downloadedCount = 0
    for item in items:
        item_id = item.get("id")
        taken_at = item.get("taken_at")
        
        # Windows doesn't allow colons in filenames, so we use hyphens instead
        timestamp = datetime.fromtimestamp(taken_at).strftime("%Y-%m-%d_%H-%M-%S")
        
        media_type = item.get("media_type")
        file_url = None
        ext = ""
        
        # 1 is image, 2 is video. Instagram sometimes returns other values for carousel posts,
        # but stories are only ever single image or single video.
        if media_type == 1:
            candidates = item.get("image_versions2", {}).get("candidates", [])
            if candidates:
                file_url = candidates[0].get("url")
                ext = "jpg"
        elif media_type == 2:
            videos = item.get("video_versions", [])
            if videos:
                file_url = videos[0].get("url")
                ext = "mp4"
                
        if not file_url:
            continue
            
        filename = f"{timestamp}_{item_id}.{ext}"
        dest = user_dir / filename
        
        if dest.exists():
            continue
            
        with client.stream("GET", file_url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        downloadedCount += 1
        
    print(f"Downloaded {downloadedCount} new stories for {username}.")


def main():
    parser = argparse.ArgumentParser(
        description="Archive Instagram stories for a list of users.",
        epilog="Example: python ripper.py --cookie 'sessionid=...' --users target_user1,target_user2"
    )
    parser.add_argument("--cookie", required=True, help="Instagram sessionid cookie value")
    parser.add_argument("--users", help="Comma-separated list of target usernames")
    parser.add_argument("--file", help="Path to a text file containing usernames (one per line)")
    parser.add_argument("--output", default="stories_archive", help="Output directory path")
    
    args = parser.parse_args()
    
    usernames = []
    if args.users:
        usernames.extend([u.strip() for u in args.users.split(",") if u.strip()])
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                usernames.extend([line.strip() for line in f if line.strip() and not line.startswith("#")])
        except FileNotFoundError:
            print(f"Error: User list file '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
            
    if not usernames:
        print("Error: No usernames specified. Use --users or --file.", file=sys.stderr)
        sys.exit(1)
        
    output_dir = Path(args.output)
    
    try:
        headers = get_headers(args.cookie)
        with httpx.Client(headers=headers, timeout=15.0) as client:
            for username in usernames:
                print(f"Processing {username}...")
                try:
                    user_id = get_user_id(client, username)
                    download_user_stories(client, username, user_id, output_dir)
                except ValueError as ve:
                    print(f"Skipping {username}: {ve}", file=sys.stderr)
                except httpx.HTTPStatusError as hse:
                    if hse.response.status_code == 401:
                        print("Error: Session cookie is invalid or expired.", file=sys.stderr)
                        sys.exit(1)
                    print(f"HTTP error for {username}: {hse.response.status_code}", file=sys.stderr)
    except httpx.RequestError as re:
        print(f"Network error: {re}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
