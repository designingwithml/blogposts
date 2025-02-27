import os
import sys
import subprocess
import re

def extract_text_from_captions(caption_file):
    """
    Extract plain text from VTT or SRT caption files by removing timestamps and formatting.
    
    Args:
        caption_file (str): Path to the caption file
        
    Returns:
        str: Path to the new text-only file
    """
    if not os.path.exists(caption_file):
        return None
        
    with open(caption_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if it's a VTT file
    if caption_file.endswith('.vtt'):
        # Remove WEBVTT header
        content = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
        
    # Remove timestamps and line numbers (works for both SRT and VTT)
    # Pattern matches timestamp lines like: 00:00:00.000 --> 00:00:03.219
    clean_text = re.sub(r'\d+\s*\n\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*?\n', '\n', content)
    clean_text = re.sub(r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*?\n', '\n', clean_text)
    
    # Remove blank lines and empty parentheses
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    clean_text = re.sub(r'\(\s*\)', '', clean_text)
    
    # Remove any remaining numeric identifiers often found in SRT files
    clean_text = re.sub(r'^\d+$', '', clean_text, flags=re.MULTILINE)
    
    # Create a new file for the text-only version
    text_only_path = os.path.splitext(caption_file)[0] + '.txt'
    with open(text_only_path, 'w', encoding='utf-8') as f:
        f.write(clean_text.strip())
        
    return text_only_path

def download_youtube_content(url, output_dir="downloads", skip_existing=True):
    """
    Download a YouTube video, its audio, and captions using yt-dlp.
    Checks if files already exist and avoids redownloading them.
    
    Args:
        url (str): The YouTube video URL
        output_dir (str): Directory to save the downloaded files
        skip_existing (bool): Skip download if file already exists
        
    Returns:
        dict: Paths to the downloaded mp4, mp3, captions, and plain text captions
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    result = {
        "video_path": None,
        "audio_path": None,
        "caption_path": None,
        "text_only_captions": None,
        "error": None
    }
    
    try:
        # Get video ID from URL
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        else:
            video_id = url.split("v=")[1].split("&")[0]
        
        # Get video info including title
        info_command = ["yt-dlp", "--print", "title", "--no-playlist", url]
        video_title = subprocess.check_output(info_command, universal_newlines=True).strip()
        
        # Sanitize title for filename
        sanitized_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in video_title])
        base_filename = os.path.join(output_dir, sanitized_title)
        
        print(f"Processing: {video_title}")
        
        # Set up file paths
        video_path = f"{base_filename}.mp4"
        audio_path = f"{base_filename}.mp3"
        
        # Check for and download video if needed
        if not os.path.exists(video_path) or not skip_existing:
            print("Downloading video...")
            video_command = [
                "yt-dlp", 
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", 
                "-o", video_path,
                "--no-playlist",
                url
            ]
            subprocess.check_call(video_command)
            print(f"Video downloaded to: {video_path}")
        else:
            print(f"Video already exists at: {video_path}")
        
        result["video_path"] = os.path.abspath(video_path)
        
        # Check for and download audio if needed
        if not os.path.exists(audio_path) or not skip_existing:
            print("Extracting audio...")
            audio_command = [
                "yt-dlp",
                "-x", 
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", audio_path,
                "--no-playlist",
                url
            ]
            subprocess.check_call(audio_command)
            print(f"Audio extracted to: {audio_path}")
        else:
            print(f"Audio already exists at: {audio_path}")
        
        result["audio_path"] = os.path.abspath(audio_path)
        
        # Check for captions
        caption_formats = ['.en.vtt', '.en.srt', '.vtt', '.srt']
        existing_caption = None
        
        # Check if any caption file already exists
        for fmt in caption_formats:
            potential_path = base_filename + fmt
            if os.path.exists(potential_path):
                existing_caption = potential_path
                break
        
        # Download captions if not already available
        if not existing_caption or not skip_existing:
            print("Downloading captions...")
            # Try English captions first
            caption_command = [
                "yt-dlp",
                "--write-subs",
                "--sub-format", "vtt",
                "--sub-lang", "en",
                "--skip-download",
                "-o", base_filename,
                "--no-playlist",
                url
            ]
            
            try:
                subprocess.check_call(caption_command)
                
                # Look for the downloaded caption file
                for fmt in caption_formats:
                    potential_path = base_filename + fmt
                    if os.path.exists(potential_path):
                        existing_caption = potential_path
                        break
                        
                # If English captions not found, try any available captions
                if not existing_caption:
                    caption_command = [
                        "yt-dlp",
                        "--write-subs",
                        "--sub-format", "vtt",
                        "--skip-download",
                        "-o", base_filename,
                        "--no-playlist",
                        url
                    ]
                    subprocess.check_call(caption_command)
                    
                    # Check for any caption file
                    for file in os.listdir(output_dir):
                        if file.startswith(os.path.basename(base_filename)) and (file.endswith('.vtt') or file.endswith('.srt')):
                            existing_caption = os.path.join(output_dir, file)
                            break
            except subprocess.CalledProcessError:
                print("No captions available for this video.")
        
        # Process the caption file if found
        if existing_caption:
            result["caption_path"] = os.path.abspath(existing_caption)
            print(f"Captions available at: {result['caption_path']}")
            
            # Extract text-only captions
            text_only_path = extract_text_from_captions(existing_caption)
            if text_only_path:
                result["text_only_captions"] = os.path.abspath(text_only_path)
                print(f"Text-only captions extracted to: {result['text_only_captions']}")
        else:
            print("No captions available for this video.")
            
    except subprocess.CalledProcessError as e:
        result["error"] = f"Command failed: {e}"
        print(result["error"])
    except Exception as e:
        result["error"] = f"An error occurred: {str(e)}"
        print(result["error"])
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <youtube_url> [output_directory] [--force]")
        print("  --force: Redownload files even if they already exist")
        sys.exit(1)
        
    url = sys.argv[1]
    output_dir = "downloads"
    skip_existing = True
    
    # Process command line arguments
    for arg in sys.argv[2:]:
        if arg == "--force":
            skip_existing = False
        elif not arg.startswith("--"):
            output_dir = arg
    
    result = download_youtube_content(url, output_dir, skip_existing)
    
    if not result["error"]:
        print("\nDownload Summary:")
        print(f"Video: {result['video_path']}")
        print(f"Audio: {result['audio_path']}")
        print(f"Captions: {result['caption_path'] if result['caption_path'] else 'Not available'}")
        print(f"Text-only captions: {result['text_only_captions'] if result['text_only_captions'] else 'Not available'}")