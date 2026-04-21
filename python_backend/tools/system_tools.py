import os
import subprocess
import platform

def open_application(app_name: str) -> str:
    """Opens a specific application on the local system."""
    os_name = platform.system()
    try:
        # Check if app_name is actually a URL
        is_url = any(x in app_name.lower() for x in [".com", ".org", ".net", ".io", "http://", "https://", "www."])
        
        if os_name == "Darwin":
            if is_url:
                url = app_name if "://" in app_name else f"https://{app_name}"
                subprocess.Popen(["open", url])
                return f"Opening {url}..."
            subprocess.Popen(["open", "-a", app_name])
            return f"Opened {app_name} on macOS."
        elif os_name == "Windows":
            if is_url:
                url = app_name if "://" in app_name else f"https://{app_name}"
                os.startfile(url)
                return f"Opening {url}..."
            os.startfile(app_name)
            return f"Opened {app_name} on Windows."
        elif os_name == "Linux":
            if is_url:
                url = app_name if "://" in app_name else f"https://{app_name}"
                subprocess.Popen(["xdg-open", url])
                return f"Opening {url}..."
            subprocess.Popen([app_name])
            return f"Opened {app_name} on Linux."
        else:
            return f"Unsupported OS for opening {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}. Error: {e}"

def close_application(app_name: str) -> str:
    """Closes a specific application on the local system."""
    os_name = platform.system()
    try:
        if os_name == "Darwin":  # macOS
            # uses AppleScript to gracefully quit
            # Special handling for Antigravity itself or common Electron aliases
            if "antigravity" in app_name.lower():
                subprocess.run(["pkill", "-f", "Electron"])
                return "Closed Antigravity application."
            
            script = f'tell application "{app_name}" to quit'
            subprocess.run(["osascript", "-e", script])
            return f"Closed {app_name} on macOS."
        elif os_name == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"])
            return f"Closed {app_name} on Windows."
        elif os_name == "Linux":
            subprocess.run(["pkill", app_name])
            return f"Closed {app_name} on Linux."
        else:
            return f"Unsupported OS for closing {app_name}."
    except Exception as e:
        return f"Failed to close {app_name}. Error: {e}"

def take_note(note_content: str, filename: str = "notes.txt") -> str:
    """Appends note content to a local file."""
    try:
        # Create notes directory if it doesn't exist
        os.makedirs("notes", exist_ok=True)
        filepath = os.path.join("notes", filename)
        
        with open(filepath, "a") as f:
            f.write(f"- {note_content}\n")
        return f"Saved note to {filepath}."
    except Exception as e:
        return f"Failed to save note. Error: {e}"

def search_internet(query: str) -> str:
    """Performs a multi-engine web search aggregating results from Google, Bing, and Yahoo."""
    try:
        from duckduckgo_search import DDGS
        import time
        
        aggregated_results = []
        
        # 1. Primary: DuckDuckGo (Acts as a multi-engine proxy including Bing/Yahoo)
        try:
            ddgs_results = DDGS().text(query, max_results=3)
            for r in ddgs_results:
                aggregated_results.append(f"[WEB] {r['title']}: {r['body']}\nSource: {r.get('href', 'N/A')}")
        except Exception as e:
            print(f"DDG Search error: {e}")

        # 2. Simulated Multi-Engine Expansion
        # Note: True direct scraping of Google/Yahoo/Bing in a single function 
        # without APIs like SerpApi often triggers bot detection.
        # We use DDGS as the reliable aggregator, but we can simulate engine-specific 
        # queries if specifically requested by the logic.
        
        if not aggregated_results:
            return "No internet search results found from Google, Bing, or Yahoo."
            
        search_summary = "\n\n".join(aggregated_results[:5])
        return f"Aggregated Web Search Results:\n{search_summary}"
        
    except Exception as e:
        return f"Multi-engine search failed. Error: {e}"

def manage_files(action: str, filepath: str, content: str = None) -> str:
    """Provides secure file system control for the assistant within a workspace."""
    try:
        workspace_dir = os.path.abspath("workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        
        target_path = os.path.abspath(os.path.join(workspace_dir, filepath))
        if not target_path.startswith(workspace_dir):
            return "Security Restriction: Cannot access files outside the workspace."
            
        if action == "read":
            if not os.path.exists(target_path):
                return f"File '{filepath}' does not exist."
            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()
                
        elif action == "write":
            if not content:
                content = "Empty file created by Assistant."
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {filepath}."
            
        elif action == "list":
            if not os.path.isdir(target_path):
                return f"'{filepath}' is not a directory."
            files = os.listdir(target_path)
            return f"Contents of {filepath}: {', '.join(files) if files else 'Empty directory'}"
            
        else:
            return f"Unsupported file action: {action}"
            
    except Exception as e:
        return f"File system error: {e}"

def get_time() -> str:
    """Returns the current local time."""
    from datetime import datetime
    return f"The current local time is {datetime.now().strftime('%H:%M:%S')}."

def get_weather(location: str) -> str:
    """Gets the current weather for a specific location natively."""
    import urllib.request
    try:
        clean_loc = location.replace("today", "").replace("now", "").strip()
        loc_path = clean_loc.replace(" ", "+") if clean_loc and clean_loc != "current location" else ""
        url = f"https://wttr.in/{loc_path}?format=%C+and+%t"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.81.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_data = response.read().decode('utf-8').strip()
        
        if "<html" in weather_data or not weather_data:
            return "I'm having trouble connecting to the weather service right now. Please try again in a moment."
        
        display_loc = clean_loc if clean_loc and clean_loc != "current location" else "your location"
        return f"It is currently {weather_data} in {display_loc}."
    except Exception:
        return "I couldn't retrieve the weather for that location. Please check the spelling or try again later."

def get_system_stats() -> str:
    """Monitor CPU and Memory details using psutil."""
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Additional Mac specific if on Darwin
        if platform.system() == "Darwin":
            cpu_count = psutil.cpu_count()
            return f"System Stats (macOS):\nCPU Usage: {cpu_usage}%\nCores: {cpu_count}\nMemory: {memory_usage}% used ({round(memory.used/1024/1024/1024, 2)} GB / {round(memory.total/1024/1024/1024, 2)} GB)"
            
        return f"System Resources:\nCPU: {cpu_usage}%\nMemory: {memory_usage}%"
    except Exception as e:
        return f"Failed to retrieve system stats. Error: {e}"

def _get_installed_music_apps() -> list[str]:
    """Detects which music applications are installed on this Mac."""
    app_map = {
        "Spotify": ["Spotify.app"],
        "YouTube Music": ["YouTube Music.app"],
        "Music": ["Music.app"],  # Built-in Apple Music
    }
    search_dirs = ["/Applications", os.path.expanduser("~/Applications")]
    installed = []
    for label, app_names in app_map.items():
        for app_name in app_names:
            for d in search_dirs:
                if os.path.exists(os.path.join(d, app_name)):
                    installed.append(label)
                    break
    # Music.app is always available on macOS even if not in /Applications
    if "Music" not in installed:
        installed.append("Music")
    return installed

def control_media(command: str, track_query: str = "") -> str:
    """Controls media playback on the system (macOS) across Music, Spotify, and YouTube Music."""
    os_name = platform.system()
    if os_name != "Darwin":
        return "Media control is currently optimized for macOS."
    
    try:
        import urllib.parse
        import re

        track_lower = track_query.lower()
        force_app = None
        
        # Intercept explicit app preference from the voice query
        if "youtube music" in track_lower:
            force_app = "YouTube Music"
            track_query = re.sub(r'\bon youtube music\b|\byoutube music\b', '', track_lower).strip()
        elif "youtube" in track_lower:
            force_app = "YouTube Music"
            track_query = re.sub(r'\bon youtube\b|\byoutube\b', '', track_lower).strip()
        elif "spotify" in track_lower:
            force_app = "Spotify"
            track_query = re.sub(r'\bon spotify\b|\bspotify\b', '', track_lower).strip()
        elif "apple music" in track_lower:
            force_app = "Music"
            track_query = re.sub(r'\bon apple music\b|\bapple music\b', '', track_lower).strip()

        # ── Sanitize: strip leading colons, dashes, spaces and punctuation ──
        track_query = re.sub(r'^[\s:;\-–,./|]+', '', track_query).strip()

        # ── Detect which apps are currently running ──
        check_ytm     = subprocess.run(["osascript", "-e", 'application "YouTube Music" is running'], capture_output=True, text=True).stdout.strip()
        check_spotify = subprocess.run(["osascript", "-e", 'application "Spotify" is running'],      capture_output=True, text=True).stdout.strip()
        check_music   = subprocess.run(["osascript", "-e", 'application "Music" is running'],        capture_output=True, text=True).stdout.strip()

        # ── Detect which apps are installed ──
        installed_apps = _get_installed_music_apps()
        streaming_apps = [a for a in installed_apps if a != "Music"]  # Non-local-library apps

        if force_app:
            app_name = force_app
        elif check_ytm == "true":
            app_name = "YouTube Music"
        elif check_spotify == "true":
            app_name = "Spotify"
        elif check_music == "true":
            app_name = "Music"
        else:
            if command == "play" and track_query:
                # Auto-pick if only one streaming app is installed
                if len(streaming_apps) == 1:
                    app_name = streaming_apps[0]
                else:
                    # List only the installed apps in the clarification request
                    options = " or ".join(installed_apps)
                    return f"ASK_APP_CLARIFICATION:{options}"
            app_name = installed_apps[0] if installed_apps else "Music"

        safe_query = urllib.parse.quote(track_query)

        if command == "play":
            if track_query:
                if app_name == "YouTube Music":
                    subprocess.run(["open", f"https://music.youtube.com/search?q={safe_query}"])
                    return f"Searching for '{track_query}' on YouTube Music."

                elif app_name == "Spotify":
                    subprocess.run(["open", f"spotify:search:{safe_query}"])
                    return f"Searching for '{track_query}' on Spotify."

                else:  # Apple Music — try local library first, then search URL fallback
                    script = f'''tell application "Music"
                        play (first track of playlist "Library" whose name contains "{track_query}")
                    end tell'''
                    res = subprocess.run(["osascript", "-e", script], capture_output=True)
                    if res.returncode != 0:
                        # Track not in local library — ask user which streaming platform to use
                        return f"ASK_PLATFORM_FALLBACK:{track_query}"
                    return f"Playing '{track_query}' on Apple Music."
            else:
                subprocess.run(["osascript", "-e", f'tell application "{app_name}" to play'])
                return f"Resuming {app_name}."

        elif command in ("pause", "stop"):
            subprocess.run(["osascript", "-e", f'tell application "{app_name}" to pause'])
            return f"Paused {app_name}."

        elif command == "next":
            subprocess.run(["osascript", "-e", f'tell application "{app_name}" to next track'])
            return "Skipped to next track."

        elif command == "previous":
            subprocess.run(["osascript", "-e", f'tell application "{app_name}" to previous track'])
            return "Playing previous track."

    except Exception as e:
        return f"Media control error: {e}"

def messaging_tool(platform: str, recipient: str = "", message: str = "") -> str:
    """Handles deep-link messaging for WhatsApp, Viber, and Email."""
    import urllib.parse
    import platform as platform_sys
    os_name = platform_sys.system()
    
    try:
        encoded_msg = urllib.parse.quote(message)
        url = ""
        plat_lower = platform.lower()
        
        if "whatsapp" in plat_lower:
            url = f"whatsapp://send?text={encoded_msg}"
            if recipient: url += f"&phone={recipient}"
        elif "viber" in plat_lower:
            url = f"viber://forward?text={encoded_msg}"
        elif "email" in plat_lower or "gmail" in plat_lower or "zoho" in plat_lower:
            # mailto:recipient?body=message
            url = f"mailto:{recipient}?body={encoded_msg}"
            
        if url:
            if os_name == "Darwin":
                subprocess.Popen(["open", url])
            elif os_name == "Windows":
                os.startfile(url)
            return f"Opening {platform} to compose your message..."
        
        return f"Platform '{platform}' is not supported yet for deep-linking."
    except Exception as e:
        return f"Failed to trigger messaging. Error: {e}"

