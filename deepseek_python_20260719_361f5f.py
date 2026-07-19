import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
import xml.etree.ElementTree as ET
import threading
try:
    import vlc
except Exception:
    vlc = None
import os
import json
import re
from datetime import datetime
from urllib.parse import urlparse
import base64

class IPTVPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("IPTV Panel - Smart TV Player")
        self.root.geometry("1200x700")
        
        # Store IPTV sources
        self.m3u_sources = []
        self.mac_sources = []
        self.channels = []
        self.current_stream_url = None
        self.vlc_instance = None
        self.player = None
        self.fullscreen = False
        self.main_frame = None
        self.left_frame = None
        self.right_frame = None
        
        # Colors and styling
        self.bg_color = "#1a1a2e"
        self.fg_color = "#ffffff"
        self.accent_color = "#16213e"
        self.highlight_color = "#0f3460"
        self.button_color = "#e94560"
        
        self.root.configure(bg=self.bg_color)
        
        # Initialize VLC (optional)
        if vlc is not None:
            try:
                self.vlc_instance = vlc.Instance()
                self.player = self.vlc_instance.media_player_new()
            except Exception:
                messagebox.showwarning("Warning", "VLC Python bindings present but VLC failed to initialize. Video playback may not work.")
                self.vlc_instance = None
                self.player = None
        else:
            self.vlc_instance = None
            self.player = None
            messagebox.showwarning("Warning", "python-vlc not installed. Video playback disabled.")
        
        self.create_widgets()
        self.load_sources()
        
    def create_widgets(self):
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.main_frame = main_frame
        
        # Left panel - Sources management
        left_frame = tk.Frame(main_frame, bg=self.accent_color, width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_frame.pack_propagate(False)
        self.left_frame = left_frame
        
        # Title
        tk.Label(left_frame, text="📺 IPTV Sources", font=("Arial", 16, "bold"), 
                bg=self.accent_color, fg=self.fg_color).pack(pady=10)
        
        # Buttons frame
        btn_frame = tk.Frame(left_frame, bg=self.accent_color)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="+ Add M3U URL", command=self.add_m3u,
                 bg=self.button_color, fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="🔎 Scan URL", command=self.scan_m3u,
             bg="#2b7a78", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="+ Add MAC", command=self.add_mac,
                 bg=self.button_color, fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="📁 Load File", command=self.load_m3u_file,
                 bg=self.highlight_color, fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        # Sources list
        tk.Label(left_frame, text="Sources", font=("Arial", 12, "bold"),
                bg=self.accent_color, fg=self.fg_color).pack(pady=(10, 5))
        
        self.sources_listbox = tk.Listbox(left_frame, bg=self.bg_color, fg=self.fg_color,
                                         selectbackground=self.highlight_color,
                                         height=15, font=("Arial", 10))
        self.sources_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.sources_listbox.bind('<<ListboxSelect>>', self.on_source_select)
        
        # Right panel - Channels and Player
        right_frame = tk.Frame(main_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_frame = right_frame
        
        # Channels list
        tk.Label(right_frame, text="📡 Channels", font=("Arial", 14, "bold"),
                bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        
        # Search box
        search_frame = tk.Frame(right_frame, bg=self.bg_color)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        self.search_frame = search_frame
        
        tk.Label(search_frame, text="🔍 Search:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        try:
            # modern tkinter (Tcl 9+) prefers trace_add
            self.search_var.trace_add('write', lambda *args: self.filter_channels())
        except Exception:
            # fallback for older tkinter
            self.search_var.trace('w', lambda *args: self.filter_channels())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Filter buttons
        tk.Button(search_frame, text="All", command=lambda: self.filter_channels("all"),
                 bg=self.highlight_color, fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="TV", command=lambda: self.filter_channels("tv"),
                 bg=self.highlight_color, fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Radio", command=lambda: self.filter_channels("radio"),
                 bg=self.highlight_color, fg="white").pack(side=tk.LEFT, padx=2)
        
        # Channel list with scrollbar
        list_frame = tk.Frame(right_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_frame = list_frame
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.channels_listbox = tk.Listbox(list_frame, bg=self.bg_color, fg=self.fg_color,
                                          selectbackground=self.highlight_color,
                                          yscrollcommand=scrollbar.set,
                                          font=("Arial", 10), height=15)
        self.channels_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.channels_listbox.yview)
        self.channels_listbox.bind('<Double-Button-1>', self.play_channel)
        
        # Player controls
        player_frame = tk.Frame(right_frame, bg=self.accent_color)
        player_frame.pack(fill=tk.X, padx=5, pady=5)
        self.player_frame = player_frame
        
        # Video display area
        self.video_frame = tk.Frame(player_frame, bg="black", height=250)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.video_frame.bind("<f>", lambda e: self.toggle_fullscreen())
        self.video_frame.bind("<F>", lambda e: self.toggle_fullscreen())
        self.video_frame.bind("<Escape>", lambda e: self.exit_fullscreen())
        
        # Control buttons
        control_frame = tk.Frame(player_frame, bg=self.accent_color)
        control_frame.pack(fill=tk.X, pady=5)
        self.control_frame = control_frame
        
        tk.Button(control_frame, text="▶ Play", command=self.play_selected,
                 bg="green", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="⏹ Stop", command=self.stop_playback,
                 bg="red", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="⏸ Pause", command=self.pause_playback,
                 bg="orange", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="🔧 Test URL", command=self.test_selected_url,
                 bg="#444444", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=6)
        tk.Button(control_frame, text="⚶ Fullscreen", command=self.toggle_fullscreen,
                 bg="#555555", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=6)
        self.volume_scale = tk.Scale(control_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                    bg=self.accent_color, fg=self.fg_color, length=100)
        self.volume_scale.set(50)
        self.volume_scale.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_label = tk.Label(self.root, text="Ready", bg=self.bg_color, fg=self.fg_color,
                                    bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<F>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())
        
    def add_m3u(self):
        url = tk.simpledialog.askstring("Add M3U URL", "Enter M3U URL:")
        if url:
            if url not in self.m3u_sources:
                self.m3u_sources.append({"url": url, "name": url.split('/')[-1] or url})
                self.update_sources_list()
                self.status_label.config(text=f"Added M3U source: {url}")
                self.save_sources()
                # Load channels from this URL
                threading.Thread(target=self.load_m3u_channels, args=(url,), daemon=True).start()
            else:
                messagebox.showinfo("Info", "This URL already exists")
                
    def add_mac(self):
        mac = tk.simpledialog.askstring("Add MAC Address", "Enter MAC Address (XX:XX:XX:XX:XX:XX):")
        if mac:
            if mac not in self.mac_sources:
                self.mac_sources.append(mac)
                self.update_sources_list()
                self.status_label.config(text=f"Added MAC: {mac}")
                self.save_sources()
                threading.Thread(target=self.load_mac_channels, args=(mac,), daemon=True).start()
            else:
                messagebox.showinfo("Info", "This MAC already exists")
                
    def load_m3u_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.parse_m3u_content(content, file_path.split('/')[-1])
                self.status_label.config(text=f"Loaded file: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                
    def parse_m3u_content(self, content, source_name):
        lines = content.split('\n')
        channels = []
        current_channel = {}
        group_title = "General"
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Extract channel info
                match = re.search(r'#EXTINF:(-?\d+)\s*(.*?),(.*?)$', line)
                if match:
                    duration = match.group(1)
                    info = match.group(2)
                    name = match.group(3)
                    
                    # Extract group title
                    group_match = re.search(r'group-title="([^"]*)"', info)
                    if group_match:
                        group_title = group_match.group(1)
                    
                    current_channel = {
                        'name': name.strip(),
                        'group': group_title,
                        'duration': duration,
                        'source': source_name
                    }
            elif line and not line.startswith('#') and current_channel:
                # This is the URL
                current_channel['url'] = line
                channels.append(current_channel)
                current_channel = {}
                
        if channels:
            self.channels.extend(channels)
            self.update_channels_list()
            self.status_label.config(text=f"Loaded {len(channels)} channels from {source_name}")
            
    def load_m3u_channels(self, url):
        # Detect Xtream-style or provider APIs and try additional endpoints
        try:
            self.status_label.config(text=f"Loading channels from {url}...")

            # If URL looks like xtream/get.php or contains username/password, try direct GET first
            response = requests.get(url, timeout=12)
            if response.status_code == 200:
                text = response.text
                # If content looks like M3U
                if '#EXTM3U' in text or 'EXTINF' in text:
                    self.parse_m3u_content(text, url.split('/')[-1])
                    return
                # If JSON, try parse
                try:
                    j = response.json()
                    parsed = self.try_parse_playlist_from_json(j, url)
                    if parsed:
                        self.channels.extend(parsed)
                        self.update_channels_list()
                        self.status_label.config(text=f"Loaded {len(parsed)} channels from {url}")
                        return
                except Exception:
                    pass

            # If direct GET didn't yield channels, try Xtream-API style variants
            if 'username=' in url and 'password=' in url and ('player_api.php' in url or 'get.php' in url or 'type=' in url):
                # try variants
                tried = self.try_xtream_variants(url)
                if tried:
                    return

            # If still not found, just report HTTP status or error
            if response is not None and response.status_code != 200:
                self.status_label.config(text=f"Failed to load: HTTP {response.status_code}")
            else:
                self.status_label.config(text=f"Loaded content but no channels detected from {url}")
        except Exception as e:
            self.status_label.config(text=f"Error loading M3U: {str(e)}")

    def try_xtream_variants(self, url):
        """Try common Xtream/portal endpoint variants derived from the provided URL."""
        # extract base and username/password
        parsed = None
        try:
            # parse query for username/password
            from urllib.parse import urlparse, parse_qs, urlunparse
            p = urlparse(url)
            qs = parse_qs(p.query)
            username = qs.get('username', [None])[0]
            password = qs.get('password', [None])[0]
            base = urlunparse((p.scheme, p.netloc, '', '', '', ''))
            candidates = []

            if 'player_api.php' in p.path or 'get.php' in p.path:
                candidates.append(url)
            # common xtream endpoints
            if username and password:
                candidates.extend([
                    f"{base}/player_api.php?username={username}&password={password}&type=m3u",
                    f"{base}/player_api.php?username={username}&password={password}&type=m3u&output=ts",
                    f"{base}/get.php?username={username}&password={password}&type=m3u",
                    f"{base}/get.php?username={username}&password={password}&type=m3u_plus&output=ts",
                ])

            for c in candidates:
                try:
                    r = requests.get(c, timeout=12)
                    if r.status_code == 200:
                        text = r.text
                        if '#EXTM3U' in text or 'EXTINF' in text:
                            self.parse_m3u_content(text, c.split('/')[-1])
                            self.status_label.config(text=f"Loaded playlist from {c}")
                            return True
                        try:
                            j = r.json()
                            parsed = self.try_parse_playlist_from_json(j, c)
                            if parsed:
                                self.channels.extend(parsed)
                                self.update_channels_list()
                                self.status_label.config(text=f"Loaded {len(parsed)} channels from {c}")
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def scan_m3u(self):
        url = tk.simpledialog.askstring("Scan M3U URL", "Enter URL to scan/check:")
        if not url:
            return
        threading.Thread(target=self.scan_url_worker, args=(url,), daemon=True).start()

    def scan_url_worker(self, url):
        """Check whether a URL is reachable, try to detect playlist content, extract channels and add them."""
        try:
            self.status_label.config(text=f"Scanning URL: {url}")

            # First try a HEAD request to quickly check reachability
            try:
                head = requests.head(url, timeout=8, allow_redirects=True)
                if head.status_code >= 400:
                    # fallback to GET to capture server behavior
                    pass
            except Exception:
                head = None

            # Do a GET to inspect content
            resp = requests.get(url, timeout=12)
            if resp.status_code != 200:
                self.status_label.config(text=f"Scan failed: HTTP {resp.status_code}")
                return

            content_type = resp.headers.get('Content-Type','').lower()
            text = resp.text

            found_channels = []

            # If it's clearly an M3U playlist
            if '#EXTM3U' in text or 'extinf' in text or 'audio/x-mpegurl' in content_type or 'application/vnd.apple.mpegurl' in content_type:
                self.parse_m3u_content(text, url.split('/')[-1])
                self.status_label.config(text=f"Scan: M3U playlist detected and parsed from {url}")
                return

            # If content looks like JSON with channels
            try:
                j = resp.json()
                parsed = self.try_parse_playlist_from_json(j, url)
                if parsed:
                    self.channels.extend(parsed)
                    self.update_channels_list()
                    self.status_label.config(text=f"Scan: extracted {len(parsed)} channels from JSON at {url}")
                    return
            except Exception:
                pass

            # Try to find .m3u links inside HTML
            m3u_links = self.extract_m3u_links_from_html(text)
            if m3u_links:
                total = 0
                for link in m3u_links:
                    try:
                        r2 = requests.get(link, timeout=10)
                        if r2.status_code == 200 and ("#EXTM3U" in r2.text or 'extinf' in r2.text):
                            self.parse_m3u_content(r2.text, link.split('/')[-1])
                            total += 1
                    except:
                        continue
                if total:
                    self.status_label.config(text=f"Scan: found and parsed {total} playlists referenced by {url}")
                    return

            # Try to extract base64 encoded playlist blobs
            try:
                parsed = self.try_extract_base64_m3u(text, url)
                if parsed:
                    self.channels.extend(parsed)
                    self.update_channels_list()
                    self.status_label.config(text=f"Scan: extracted {len(parsed)} channels from encoded playlist at {url}")
                    return
            except Exception:
                pass

            # If nothing found, report status and show a small sample
            sample = text[:400].replace('\n', ' ') if text else ''
            self.status_label.config(text=f"Scan complete: no playlist detected. Sample: {sample}")
        except Exception as e:
            self.status_label.config(text=f"Scan error: {str(e)}")

    def extract_m3u_links_from_html(self, html_text):
        """Return list of candidate .m3u/.m3u8 URLs found inside HTML."""
        links = re.findall(r'https?://[^\s"\'>]+\.(?:m3u|m3u8)(?:\?[^\s"\'>]+)?', html_text, flags=re.IGNORECASE)
        # Also look for urls inside attribute-like strings
        if not links:
            links = re.findall(r'"(https?://[^"\']+\.m3u(?:8)?(?:\?[^"\']+)?)"', html_text, flags=re.IGNORECASE)
            links = [l.strip('"') for l in links]
        return list(dict.fromkeys(links))

    def try_parse_playlist_from_json(self, j, source_url):
        channels = []
        # Common shapes: {'channels':[...]} or {'playlist':[...]} or nested keys
        candidates = []
        if isinstance(j, dict):
            for key in ('channels', 'playlist', 'items'):
                if key in j and isinstance(j[key], list):
                    candidates = j[key]
                    break
            # Sometimes response is a list directly
        elif isinstance(j, list):
            candidates = j

        for item in candidates:
            if isinstance(item, dict):
                name = item.get('name') or item.get('title') or item.get('t') or 'Unknown'
                url = item.get('url') or item.get('stream') or item.get('stream_url') or item.get('file') or ''
                group = item.get('group') or item.get('category') or 'General'
                if url:
                    channels.append({'name': name, 'group': group, 'url': url, 'source': source_url})
        return channels

    def try_extract_base64_m3u(self, text, source_url):
        """Look for base64 blobs that decode to M3U content."""
        found = []
        # find long base64 strings (heuristic)
        blobs = re.findall(r'([A-Za-z0-9+/=]{200,})', text)
        for b in blobs:
            try:
                dec = base64.b64decode(b).decode('utf-8', errors='ignore')
                if '#EXTM3U' in dec or 'EXTINF' in dec:
                    # parse and return channels from decoded content
                    # reuse parse_m3u_content but capture current count
                    before = len(self.channels)
                    self.parse_m3u_content(dec, source_url)
                    after = len(self.channels)
                    if after > before:
                        return self.channels[before:after]
            except Exception:
                continue
        return []
            
    def load_mac_channels(self, mac):
        try:
            self.status_label.config(text=f"Loading MAC channels for {mac}...")
            # Try common MAC portal URLs
            portals = [
                f"http://portal.{mac}/server/load.php",
                f"http://{mac}/server/load.php",
                f"http://portal.{mac}/c/",
                f"http://{mac}/c/"
            ]
            
            for portal in portals:
                try:
                    response = requests.get(portal, timeout=5)
                    if response.status_code == 200:
                        # Parse response (usually JSON or XML)
                        try:
                            data = response.json()
                            # Extract channels from JSON
                            channels = self.parse_mac_json(data, mac)
                            self.channels.extend(channels)
                            self.update_channels_list()
                            self.status_label.config(text=f"Loaded {len(channels)} channels from MAC {mac}")
                            return
                        except:
                            # Try XML
                            channels = self.parse_mac_xml(response.text, mac)
                            self.channels.extend(channels)
                            self.update_channels_list()
                            self.status_label.config(text=f"Loaded {len(channels)} channels from MAC {mac}")
                            return
                except:
                    continue
                    
            self.status_label.config(text=f"Could not load MAC channels for {mac}")
        except Exception as e:
            self.status_label.config(text=f"Error loading MAC: {str(e)}")
            
    def parse_mac_json(self, data, mac):
        channels = []
        try:
            if 'channels' in data:
                for ch in data['channels']:
                    channels.append({
                        'name': ch.get('name', 'Unknown'),
                        'group': ch.get('group', 'General'),
                        'url': ch.get('stream_url', ''),
                        'source': f"MAC-{mac}"
                    })
        except:
            pass
        return channels
        
    def parse_mac_xml(self, xml_data, mac):
        channels = []
        try:
            root = ET.fromstring(xml_data)
            for item in root.findall('.//channel'):
                name = item.find('name')
                url = item.find('url')
                group = item.find('group')
                if name is not None and url is not None:
                    channels.append({
                        'name': name.text,
                        'group': group.text if group is not None else 'General',
                        'url': url.text,
                        'source': f"MAC-{mac}"
                    })
        except:
            pass
        return channels
        
    def update_sources_list(self):
        self.sources_listbox.delete(0, tk.END)
        for source in self.m3u_sources:
            self.sources_listbox.insert(tk.END, f"📡 {source['name']}")
        for mac in self.mac_sources:
            self.sources_listbox.insert(tk.END, f"🔗 MAC: {mac}")
            
    def on_source_select(self, event):
        selection = self.sources_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.m3u_sources):
                source = self.m3u_sources[idx]
                self.status_label.config(text=f"Selected source: {source['name']}")
            else:
                mac_idx = idx - len(self.m3u_sources)
                if mac_idx < len(self.mac_sources):
                    self.status_label.config(text=f"Selected MAC: {self.mac_sources[mac_idx]}")
                    
    def update_channels_list(self):
        self.channels_listbox.delete(0, tk.END)
        for channel in self.channels:
            name = channel.get('name', 'Unknown')
            group = channel.get('group', 'General')
            self.channels_listbox.insert(tk.END, f"{name} [{group}]")
            
    def filter_channels(self, filter_type="all"):
        self.channels_listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower()
        
        for channel in self.channels:
            name = channel.get('name', 'Unknown').lower()
            group = channel.get('group', 'General').lower()
            
            # Filter by type
            if filter_type == "tv" and "radio" in group:
                continue
            elif filter_type == "radio" and "radio" not in group:
                continue
                
            # Filter by search
            if search_text and search_text not in name and search_text not in group:
                continue
                
            display_name = channel.get('name', 'Unknown')
            display_group = channel.get('group', 'General')
            self.channels_listbox.insert(tk.END, f"{display_name} [{display_group}]")
            
    def play_channel(self, event=None):
        selection = self.channels_listbox.curselection()
        if selection:
            idx = selection[0]
            # Find the actual channel from filtered list
            filtered_channels = [ch for ch in self.channels]
            # Apply same filtering logic
            search_text = self.search_var.get().lower()
            if search_text:
                filtered_channels = [ch for ch in filtered_channels if 
                                   search_text in ch.get('name', '').lower() or 
                                   search_text in ch.get('group', '').lower()]
            
            if idx < len(filtered_channels):
                channel = filtered_channels[idx]
                url = channel.get('url')
                if url:
                    self.play_stream(url)
                else:
                    messagebox.showerror("Error", "No URL found for this channel")
                    
    def play_selected(self):
        self.play_channel()
        
    def play_stream(self, url):
        try:
            if self.player:
                self.stop_playback()
                media = self.vlc_instance.media_new(url)
                self.player.set_media(media)
                # Use platform-appropriate window handle
                try:
                    # Windows
                    self.player.set_hwnd(self.video_frame.winfo_id())
                except Exception:
                    try:
                        # X11
                        self.player.set_xwindow(self.video_frame.winfo_id())
                    except Exception:
                        pass
                self.player.play()
                self.status_label.config(text=f"Playing: {url}")
                self.current_stream_url = url
        except Exception as e:
            messagebox.showerror("Playback Error", f"Failed to play stream: {str(e)}")

    def test_selected_url(self):
        selection = self.channels_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "No channel selected to test")
            return
        idx = selection[0]
        # map through filtering same as play_channel
        filtered_channels = [ch for ch in self.channels]
        search_text = self.search_var.get().lower()
        if search_text:
            filtered_channels = [ch for ch in filtered_channels if search_text in ch.get('name','').lower() or search_text in ch.get('group','').lower()]
        if idx >= len(filtered_channels):
            messagebox.showerror("Error", "Selected index out of range")
            return
        url = filtered_channels[idx].get('url')
        threading.Thread(target=self.test_stream_url, args=(url,), daemon=True).start()

    def test_stream_url(self, url):
        try:
            self.status_label.config(text=f"Testing URL: {url}")
            # quick HEAD
            try:
                h = requests.head(url, timeout=8, allow_redirects=True)
                status = h.status_code
            except Exception:
                h = None
                status = None
            # try a small range GET to ensure server responds
            headers = {'Range': 'bytes=0-1023'}
            try:
                g = requests.get(url, headers=headers, timeout=10, stream=True)
                g_status = g.status_code
            except Exception as e:
                g = None
                g_status = None
            msg = f"HEAD: {status}, GET(range): {g_status}"
            self.status_label.config(text=f"Test result - {msg}")
            messagebox.showinfo("Test Result", msg)
        except Exception as e:
            self.status_label.config(text=f"Test error: {str(e)}")
            messagebox.showerror("Test Error", str(e))

    def toggle_fullscreen(self):
        """Toggle fullscreen mode - hides UI, maximizes video player."""
        if not self.fullscreen:
            self.fullscreen = True
            # Hide UI elements
            self.left_frame.pack_forget()
            self.search_frame.pack_forget()
            self.list_frame.pack_forget()
            self.status_label.pack_forget()
            # Maximize window to fill screen
            try:
                self.root.state('zoomed')  # Windows
            except Exception:
                self.root.state('normal')
                self.root.attributes('-zoomed', True)  # Fallback
            # Resize video frame to fill entire window
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.player_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.video_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.control_frame.pack(fill=tk.X, pady=5, side=tk.BOTTOM)
            self.status_label.config(text="Fullscreen mode. Press ESC or F to exit.")
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        else:
            self.exit_fullscreen()

    def exit_fullscreen(self):
        """Exit fullscreen mode and restore normal UI layout."""
        if self.fullscreen:
            self.fullscreen = False
            # Restore window state
            self.root.state('normal')
            # Restore original geometry
            self.root.geometry("1200x700")
            # Restore UI elements with proper packing
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
            self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            self.search_frame.pack(fill=tk.X, padx=5, pady=5)
            self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.player_frame.pack(fill=tk.X, padx=5, pady=5)
            self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.control_frame.pack(fill=tk.X, pady=5)
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
            self.status_label.config(text="Ready")
            
    def stop_playback(self):
        if self.player:
            self.player.stop()
            self.status_label.config(text="Stopped")
            
    def pause_playback(self):
        if self.player:
            self.player.pause()
            
    def save_sources(self):
        data = {
            'm3u_sources': self.m3u_sources,
            'mac_sources': self.mac_sources
        }
        try:
            with open('iptv_sources.json', 'w') as f:
                json.dump(data, f)
        except:
            pass
            
    def load_sources(self):
        try:
            with open('iptv_sources.json', 'r') as f:
                data = json.load(f)
                self.m3u_sources = data.get('m3u_sources', [])
                self.mac_sources = data.get('mac_sources', [])
                self.update_sources_list()
                
                # Auto-load channels from saved sources
                for source in self.m3u_sources:
                    threading.Thread(target=self.load_m3u_channels, args=(source['url'],), daemon=True).start()
                for mac in self.mac_sources:
                    threading.Thread(target=self.load_mac_channels, args=(mac,), daemon=True).start()
        except:
            pass

def main():
    root = tk.Tk()
    app = IPTVPanel(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        try:
            if app and hasattr(app, 'stop_playback'):
                app.stop_playback()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    main()
