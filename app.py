import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import pygame
import os
import numpy as np
from PIL import Image, ImageTk
import tempfile
import json
import datetime
import platform
import webbrowser
import sqlite3
from pathlib import Path
import re

class FocusBuddyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FOCUSBuddy")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Initialize pygame for audio
        pygame.mixer.init()
        
        # Set theme and style
        self.set_theme()
        
        # Control variables
        self.running = False
        self.person_present = False
        self.alert_active = False
        self.alert_thread = None
        self.warning_count = 0
        self.last_detection_time = time.time()
        self.grace_period = 3  # seconds before alerting
        self.session_start_time = None
        self.total_focus_time = 0
        self.hardcore_mode = False
        self.distracting_sites = ["youtube.com", "facebook.com", "twitter.com", "instagram.com", 
                                "reddit.com", "tiktok.com", "netflix.com", "twitch.tv"]
        
        # Video frame size control
        self.video_width = 480
        self.video_height = 360
        
        # User data
        self.data_dir = os.path.join(os.path.expanduser("~"), ".focusbuddy")
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "focusbuddy.db")
        self.setup_database()
        
        # Badge system
        self.badges = {
            "focus_rookie": {"name": "Focus Rookie", "desc": "Complete your first 30-minute session", "icon": "🥉"},
            "focus_adept": {"name": "Focus Adept", "desc": "Complete a 1-hour session", "icon": "🥈"},
            "focus_master": {"name": "Focus Master", "desc": "Complete a 2-hour session", "icon": "🥇"},
            "early_bird": {"name": "Early Bird", "desc": "Start a session before 8 AM", "icon": "🐦"},
            "night_owl": {"name": "Night Owl", "desc": "Complete a session after 10 PM", "icon": "🦉"},
            "hat_trick": {"name": "Hat Trick", "desc": "Complete 3 sessions in one day", "icon": "🎩"},
            "iron_will": {"name": "Iron Will", "desc": "Complete a hardcore mode session", "icon": "⚔️"},
            "streak_week": {"name": "Streak Week", "desc": "Focus every day for a week", "icon": "🔥"},
            "journaler": {"name": "Journaler", "desc": "Complete 5 session journals", "icon": "📓"}
        }
        
        # Create UI elements
        self.create_ui()
        
        # OpenCV variables
        self.cap = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Create default sound
        self.create_default_sound()
        
        # Background monitor for distracting sites
        self.site_monitor_thread = threading.Thread(target=self.monitor_distracting_sites)
        self.site_monitor_thread.daemon = True
        self.site_monitor_thread.start()
        
        # On closing window
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Stabilization buffers
        self.focus_buffer = [False] * 5  # Last 5 focus states
        self.focus_index = 0
        
        # Update focus scores display
        self.update_focus_stats()
        self.update_badges_display()

    def setup_database(self):
        """Set up SQLite database for storing user data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create focus sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY,
            start_time TEXT,
            duration INTEGER,
            focus_score REAL,
            hardcore_mode INTEGER,
            journal_text TEXT
        )
        ''')
        
        # Create badges table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS earned_badges (
            id INTEGER PRIMARY KEY,
            badge_id TEXT,
            earn_date TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    def set_theme(self):
        """Set up a modern theme for the application"""
        style = ttk.Style()
        
        # Try to use a modern theme if available
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
            
        # Configure styles
        style.configure("TButton", padding=6, relief="flat", background="#3498db", foreground="black")
        style.map("TButton", 
            background=[("pressed", "#2980b9"), ("active", "#3498db")],
            foreground=[("pressed", "white"), ("active", "black")])
        
        style.configure("Start.TButton", background="#27ae60", foreground="white", font=("Arial", 11, "bold"))
        style.map("Start.TButton",
            background=[("pressed", "#219651"), ("active", "#2ecc71")],
            foreground=[("pressed", "white"), ("active", "white")])
        
        style.configure("Stop.TButton", background="#e74c3c", foreground="white", font=("Arial", 11, "bold"))
        style.map("Stop.TButton",
            background=[("pressed", "#c0392b"), ("active", "#e74c3c")],
            foreground=[("pressed", "white"), ("active", "white")])
        
        style.configure("Hardcore.TButton", background="#8e44ad", foreground="white", font=("Arial", 11, "bold"))
        style.map("Hardcore.TButton",
            background=[("pressed", "#6c3483"), ("active", "#9b59b6")],
            foreground=[("pressed", "white"), ("active", "white")])
        
        style.configure("TLabel", padding=2)
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Status.TLabel", font=("Arial", 14))
        style.configure("Badge.TLabel", font=("Arial", 24))
        
    def create_default_sound(self):
        """Create a default alert sound file"""
        try:
            beep_file = os.path.join(tempfile.gettempdir(), "focus_monitor_beep.wav")
            
            sample_rate = 44100
            duration = 0.8
            frequency = 880
            
            num_samples = int(sample_rate * duration)
            amplitude = 32000
            
            buf = np.zeros((num_samples, 2), dtype=np.int16)
            for i in range(num_samples):
                t = i / sample_rate
                value = int(amplitude * np.sin(2 * np.pi * frequency * t))
                buf[i][0] = value
                buf[i][1] = value
            
            sound = pygame.sndarray.make_sound(buf)
            pygame.mixer.Sound.write(sound, beep_file)
            
            self.alarm_sound_file = beep_file
            
        except Exception as e:
            print(f"Error creating default sound: {e}")
            self.alarm_sound_file = None
    
    def create_ui(self):
        """Create the UI for the application"""
        # Use notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main monitoring tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Focus Monitor")
        
        # Stats tab
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Stats & Badges")
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Main tab content
        main_frame = ttk.Frame(self.main_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - Video and controls
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Video frame with improved styling
        self.video_frame = ttk.LabelFrame(left_frame, text="Camera Feed")
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status indicators
        status_frame = ttk.Frame(left_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.focus_indicator = ttk.Label(status_frame, text="🔴 Not Focused", font=("Arial", 16, "bold"))
        self.focus_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.time_indicator = ttk.Label(status_frame, text="Time: 00:00", font=("Arial", 16))
        self.time_indicator.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="Start Focus Session", 
                                     style="Start.TButton",
                                     command=self.toggle_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        self.hardcore_button = ttk.Button(control_frame, text="Hardcore Mode", 
                                        style="Hardcore.TButton",
                                        command=self.toggle_hardcore)
        self.hardcore_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Right side - Current session info
        right_frame = ttk.LabelFrame(main_frame, text="Current Session")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5, expand=False, ipadx=5, ipady=5)
        
        # Session info
        ttk.Label(right_frame, text="Session Status:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=2)
        self.status_label = ttk.Label(right_frame, text="Not Started", style="Status.TLabel")
        self.status_label.pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(right_frame, text="Focus Score:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=(10, 2))
        self.score_label = ttk.Label(right_frame, text="0%", font=("Arial", 18, "bold"))
        self.score_label.pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(right_frame, text="Focus Streak:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=(10, 2))
        self.streak_label = ttk.Label(right_frame, text="0 days", style="Status.TLabel")
        self.streak_label.pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(right_frame, text="Today's Sessions:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=(10, 2))
        self.today_sessions_label = ttk.Label(right_frame, text="0", style="Status.TLabel")
        self.today_sessions_label.pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(right_frame, text="Mode:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=(10, 2))
        self.mode_label = ttk.Label(right_frame, text="Normal", style="Status.TLabel")
        self.mode_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Stats tab content
        stats_frame = ttk.Frame(self.stats_tab)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - Focus history
        history_frame = ttk.LabelFrame(stats_frame, text="Focus History")
        history_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Week summary (placeholder for chart)
        week_chart_label = ttk.Label(history_frame, text="Weekly Focus Scores")
        week_chart_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.week_chart_frame = ttk.Frame(history_frame, height=200)
        self.week_chart_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Session history
        ttk.Label(history_frame, text="Recent Sessions:", style="Header.TLabel").pack(anchor=tk.W, padx=5, pady=5)
        
        history_list_frame = ttk.Frame(history_frame)
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.history_tree = ttk.Treeview(history_list_frame, columns=("date", "duration", "score"), show="headings")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("duration", text="Duration")
        self.history_tree.heading("score", text="Score")
        self.history_tree.column("date", width=120)
        self.history_tree.column("duration", width=80)
        self.history_tree.column("score", width=80)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        history_scrollbar = ttk.Scrollbar(history_list_frame, orient="vertical", command=self.history_tree.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        # Right side - Badges
        # Create the frame with width specified at creation time, not in pack
        badges_frame = ttk.LabelFrame(stats_frame, text="Badges", width=300)
        badges_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5, expand=False, ipadx=5, ipady=5)
        # Prevent frame from resizing to child widgets' size
        badges_frame.pack_propagate(False)
        
        self.badges_canvas = tk.Canvas(badges_frame)
        self.badges_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        badges_scrollbar = ttk.Scrollbar(badges_frame, orient="vertical", command=self.badges_canvas.yview)
        badges_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.badges_canvas.configure(yscrollcommand=badges_scrollbar.set)
        self.badges_canvas.bind('<Configure>', lambda e: self.badges_canvas.configure(scrollregion=self.badges_canvas.bbox("all")))
        
        self.badges_frame = ttk.Frame(self.badges_canvas)
        self.badges_canvas.create_window((0, 0), window=self.badges_frame, anchor="nw")
        
        # Settings tab content
        settings_frame = ttk.Frame(self.settings_tab)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Focus settings
        focus_settings = ttk.LabelFrame(settings_frame, text="Focus Settings")
        focus_settings.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(focus_settings, text="Grace Period (seconds):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.grace_var = tk.StringVar(value=str(self.grace_period))
        grace_entry = ttk.Entry(focus_settings, textvariable=self.grace_var, width=5)
        grace_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(focus_settings, text="Detection Sensitivity:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.sensitivity_var = tk.StringVar(value="Medium")
        sensitivity_combo = ttk.Combobox(focus_settings, textvariable=self.sensitivity_var, 
                                        values=["Low", "Medium", "High"], width=10, state="readonly")
        sensitivity_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Distracting Sites settings
        sites_frame = ttk.LabelFrame(settings_frame, text="Distracting Sites")
        sites_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(sites_frame, text="Enter one site per line (e.g., youtube.com):").pack(anchor=tk.W, padx=5, pady=5)
        
        self.sites_text = scrolledtext.ScrolledText(sites_frame, height=8)
        self.sites_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.sites_text.insert("1.0", "\n".join(self.distracting_sites))
        
        ttk.Label(sites_frame, text="Auto-start focus when distracting site detected:").pack(anchor=tk.W, padx=5, pady=5)
        self.auto_focus_var = tk.BooleanVar(value=True)
        auto_focus_check = ttk.Checkbutton(sites_frame, variable=self.auto_focus_var)
        auto_focus_check.pack(anchor=tk.W, padx=5, pady=0)
        
        # Sound settings
        sound_frame = ttk.LabelFrame(settings_frame, text="Alert Sound")
        sound_frame.pack(fill=tk.X, padx=5, pady=5)
        
        sound_buttons = ttk.Frame(sound_frame)
        sound_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(sound_buttons, text="Select Sound", 
                 command=self.select_sound).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(sound_buttons, text="Test Sound", 
                 command=self.test_sound).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.sound_label = ttk.Label(sound_frame, text="Using default alert sound")
        self.sound_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Apply settings button
        ttk.Button(settings_frame, text="Apply Settings", 
                 command=self.apply_settings).pack(anchor=tk.E, padx=5, pady=10)
        
        # Load saved sessions into history
        self.load_session_history()
    
    def toggle_monitoring(self):
        """Toggle between start and stop monitoring"""
        if not self.running:
            self.start_monitoring()
        else:
            if self.hardcore_mode:
                messagebox.showinfo("Hardcore Mode", "You can't stop in hardcore mode! Stay focused!")
                return
            self.stop_monitoring()
    
    def toggle_hardcore(self):
        """Toggle hardcore mode on/off"""
        if self.running:
            messagebox.showinfo("Already Running", "Can't change mode during an active session!")
            return
            
        self.hardcore_mode = not self.hardcore_mode
        
        if self.hardcore_mode:
            self.hardcore_button.config(text="Normal Mode")
            self.mode_label.config(text="Hardcore 😱")
            messagebox.showwarning("Hardcore Mode", 
                                 "Warning: In hardcore mode you cannot stop the session until the minimum time (25 minutes) has passed!")
        else:
            self.hardcore_button.config(text="Hardcore Mode")
            self.mode_label.config(text="Normal")
    
    def start_monitoring(self):
        """Start the camera monitoring"""
        if self.running:
            return
            
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Cannot access camera! Please check your camera connection.")
            self.status_label.config(text="Error - Cannot access camera!")
            return
            
        self.running = True
        self.start_button.config(text="Stop Session", style="Stop.TButton")
        self.status_label.config(text="Session Active")
        self.session_start_time = time.time()
        self.total_focus_time = 0
        
        # Block distracting sites
        self.block_distracting_sites()
        
        # Start video processing thread
        self.video_thread = threading.Thread(target=self.process_video)
        self.video_thread.daemon = True
        self.video_thread.start()
        
        # Start timer update thread
        self.timer_thread = threading.Thread(target=self.update_timer)
        self.timer_thread.daemon = True
        self.timer_thread.start()
    
    def stop_monitoring(self):
        """Stop the camera monitoring"""
        if not self.running:
            return
            
        # Calculate total session time
        session_time = time.time() - self.session_start_time
        
        # Calculate focus score (percentage of time focused)
        focus_score = min(100, int((self.total_focus_time / session_time) * 100)) if session_time > 0 else 0
        
        # Update UI
        self.running = False
        self.start_button.config(text="Start Focus Session", style="Start.TButton")
        self.status_label.config(text="Session Completed")
        self.score_label.config(text=f"{focus_score}%")
        
        # Release camera
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        # Reset indicators
        self.focus_indicator.config(text="🔴 Not Focused")
        
        # Stop any active alerts
        self.stop_alert()
        
        # Unblock sites
        self.unblock_distracting_sites()
        
        # Save session data
        self.save_session(session_time, focus_score)
        
        # Update stats
        self.update_focus_stats()
        
        # Check for badges
        self.check_badges(session_time, focus_score)
        
        # Show journal dialog if session was longer than 5 minutes
        if session_time > 300:  # 5 minutes
            self.show_journal_dialog()
    
    def update_timer(self):
        """Update the session timer display"""
        while self.running:
            if self.session_start_time:
                elapsed = time.time() - self.session_start_time
                mins, secs = divmod(int(elapsed), 60)
                hours, mins = divmod(mins, 60)
                
                if hours > 0:
                    time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
                else:
                    time_str = f"{mins:02d}:{secs:02d}"
                
                self.time_indicator.config(text=f"Time: {time_str}")
            
            time.sleep(1)
    
    def process_video(self):
        """Process video frames and detect faces"""
        frame_count = 0
        last_focus_check = time.time()
        focused_time = 0
        
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                self.status_label.config(text="Error - Camera disconnected!")
                if not self.hardcore_mode:
                    self.stop_monitoring()
                break
                
            # Process every 2nd frame for better performance
            frame_count += 1
            if frame_count % 2 != 0:
                continue
                
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization for better contrast
            gray = cv2.equalizeHist(gray)
            
            # Detect faces with adjusted parameters based on sensitivity
            sensitivity = self.sensitivity_var.get()
            if sensitivity == "Low":
                min_neighbors = 3
                scale_factor = 1.2
            elif sensitivity == "High":
                min_neighbors = 7
                scale_factor = 1.05
            else:  # Medium
                min_neighbors = 5
                scale_factor = 1.1
            
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=scale_factor, 
                minNeighbors=min_neighbors, 
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Update focused status based on face detection
            focused = len(faces) > 0
            
            # Draw rectangles on detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Update focus buffer for stabilization
            self.focus_buffer[self.focus_index] = focused
            self.focus_index = (self.focus_index + 1) % len(self.focus_buffer)
            
            # Determine stable focus state (majority vote)
            stable_focused = sum(self.focus_buffer) > len(self.focus_buffer) / 2
            
            # Update time of last detection
            if stable_focused:
                self.last_detection_time = time.time()
                
                # Update total focus time every second
                current_time = time.time()
                if current_time - last_focus_check >= 1:
                    focused_time = current_time - last_focus_check
                    self.total_focus_time += focused_time
                    last_focus_check = current_time
                    
                    # Update focus score in UI
                    session_time = current_time - self.session_start_time
                    focus_score = min(100, int((self.total_focus_time / session_time) * 100)) if session_time > 0 else 0
                    self.score_label.config(text=f"{focus_score}%")
            else:
                last_focus_check = time.time()
            
            # Check if person is not focused for too long
            time_since_focus = time.time() - self.last_detection_time
            if not stable_focused and time_since_focus > self.grace_period:
                if not self.alert_active:
                    self.start_alert()
                self.focus_indicator.config(text="🔴 Not Focused")
            else:
                if self.alert_active:
                    self.stop_alert()
                if stable_focused:
                    self.focus_indicator.config(text="🟢 Focused")
                else:
                    remaining = max(0, self.grace_period - time_since_focus)
                    self.focus_indicator.config(text=f"🟡 Grace Period: {remaining:.1f}s")
            
            # Add status text to frame
            status_text = "Focused" if stable_focused else "Not Focused"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                      (0, 255, 0) if stable_focused else (0, 0, 255), 2)
            
            # Convert frame for display
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            
            # Resize to specified size
            img = img.resize((self.video_width, self.video_height), Image.LANCZOS)
                
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
            
            # Check for hardcore mode minimum time
            if self.hardcore_mode:
                session_time = time.time() - self.session_start_time
                # Allow stopping after 25 minutes
                if session_time >= 1500:  # 25 minutes
                    self.hardcore_mode = False
                    self.hardcore_button.config(text="Hardcore Mode")
                    self.mode_label.config(text="Normal (Completed Hardcore)")
                    messagebox.showinfo("Hardcore Completed", 
                                      "You've completed the minimum hardcore session time! You can now end the session if needed.")
            
            # Short delay to reduce CPU usage
            time.sleep(0.03)
    
    def start_alert(self):
        """Start the alert when the person is not focusing"""
        if self.alert_active:
            return
            
        self.alert_active = True
        self.alert_thread = threading.Thread(target=self.alert_loop)
        self.alert_thread.daemon = True
        self.alert_thread.start()
    
    def stop_alert(self):
        """Stop the alert when the person focuses again"""
        self.alert_active = False
    
    def alert_loop(self):
        """Loop that plays alerts until person focuses or monitoring stops"""
        alert_messages = [
            "Hey, the work is not done yet!",
            "Please focus on your screen!",
            "Let's get back to work!",
            "Your attention is needed!",
            "You're getting distracted!"
        ]
        
        while self.alert_active and self.running:
            # Display a rotating message
            message = alert_messages[self.warning_count % len(alert_messages)]
            self.warning_count += 1
            
            # Play sound
            self.play_alert_sound()
            
            # Wait before next alert
            time.sleep(3)
    
    def play_alert_sound(self):
        """Play the alert sound"""
        try:
            if self.alarm_sound_file and os.path.exists(self.alarm_sound_file):
                sound = pygame.mixer.Sound(self.alarm_sound_file)
                sound.set_volume(1.0)  # Max volume
                sound.play()
        except Exception as e:
            print(f"Error playing sound: {e}")
            # Try system beep as fallback
            try:
                if platform.system() == "Windows":
                    import winsound
                    winsound.Beep(1000, 500)
            except:
                pass
    
    def select_sound(self):
        """Let the user select a custom sound file"""
        file_path = filedialog.askopenfilename(
            title="Select Alert Sound",
            filetypes=[("Sound Files", "*.wav *.mp3")]
        )
        
        if file_path:
            self.alarm_sound_file = file_path
            self.sound_label.config(text=f"Selected: {os.path.basename(file_path)}")
    
    def test_sound(self):
        """Test the currently selected sound"""
        self.play_alert_sound()
    
    def apply_settings(self):
        """Apply the settings from the settings tab"""
        try:
            # Update grace period
            new_grace = float(self.grace_var.get())
            if new_grace > 0:
                self.grace_period = new_grace
            
            # Update distracting sites
            sites_text = self.sites_text.get("1.0", "end-1c")
            sites = [site.strip() for site in sites_text.split('\n') if site.strip()]
            if sites:
                self.distracting_sites = sites
            
            messagebox.showinfo("Settings", "Settings applied successfully!")
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter valid numbers: {e}")
    
    def block_distracting_sites(self):
        """Block distracting sites by modifying hosts file"""
        try:
            # Get hosts file path based on OS
            if platform.system() == "Windows":
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            else:
                hosts_path = "/etc/hosts"
            
            # Check if we have permission to modify the hosts file
            if not os.access(hosts_path, os.W_OK):
                if platform.system() != "Windows":
                    messagebox.showwarning("Permission Error", 
                                         "FOCUSBuddy needs administrator privileges to block sites.\n"
                                         "Try running as administrator or with sudo.")
                else:
                    messagebox.showwarning("Permission Error", 
                                         "FOCUSBuddy needs administrator privileges to block sites.\n"
                                         "Try running as administrator.")
                return
            
            # Read current hosts file
            with open(hosts_path, 'r') as file:
                hosts_content = file.read()
            
            # Add comment markers
            start_marker = "# FOCUSBuddy Start"
            end_marker = "# FOCUSBuddy End"
            
            # Remove any existing FOCUSBuddy entries
            if start_marker in hosts_content and end_marker in hosts_content:
                start_idx = hosts_content.find(start_marker)
                end_idx = hosts_content.find(end_marker) + len(end_marker)
                hosts_content = hosts_content[:start_idx] + hosts_content[end_idx:]
            
            # Add new entries
            hosts_content += f"\n{start_marker}\n"
            for site in self.distracting_sites:
                hosts_content += f"127.0.0.1 {site}\n"
                if not site.startswith("www."):
                    hosts_content += f"127.0.0.1 www.{site}\n"
            hosts_content += f"{end_marker}\n"
            
            # Write back to hosts file
            with open(hosts_path, 'w') as file:
                file.write(hosts_content)
                
        except Exception as e:
            print(f"Error blocking sites: {e}")
            messagebox.showwarning("Site Blocking", "Could not block distracting sites. You may need administrator privileges.")
    
    def unblock_distracting_sites(self):
        """Unblock sites by removing entries from hosts file"""
        try:
            # Get hosts file path based on OS
            if platform.system() == "Windows":
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            else:
                hosts_path = "/etc/hosts"
            
            # Check if we have permission to modify the hosts file
            if not os.access(hosts_path, os.W_OK):
                return
            
            # Read current hosts file
            with open(hosts_path, 'r') as file:
                hosts_content = file.read()
            
            # Remove FOCUSBuddy entries
            start_marker = "# FOCUSBuddy Start"
            end_marker = "# FOCUSBuddy End"
            
            if start_marker in hosts_content and end_marker in hosts_content:
                start_idx = hosts_content.find(start_marker)
                end_idx = hosts_content.find(end_marker) + len(end_marker)
                hosts_content = hosts_content[:start_idx] + hosts_content[end_idx:]
                
                # Write back to hosts file
                with open(hosts_path, 'w') as file:
                    file.write(hosts_content)
                    
        except Exception as e:
            print(f"Error unblocking sites: {e}")
    
    def monitor_distracting_sites(self):
        """Background thread to monitor if user opens distracting sites"""
        check_interval = 5  # seconds between checks
        
        while True:
            # Only monitor when not in a focus session and auto-focus is enabled
            if not self.running and self.auto_focus_var.get():
                try:
                    # Check if any distracting site is open in browser
                    # This is a simplified check - in reality, we can't directly check
                    # browser tabs without browser extensions or OS-specific APIs
                    
                    # For Windows, we can check running processes
                    if platform.system() == "Windows":
                        import subprocess
                        result = subprocess.check_output('tasklist /fo csv', shell=True).decode()
                        browsers = ["chrome.exe", "firefox.exe", "msedge.exe", "iexplore.exe", "opera.exe", "brave.exe"]
                        
                        # If any browser is running, we'll show a notification
                        browser_running = any(browser in result for browser in browsers)
                        if browser_running:
                            # We can't know exactly what sites are open, so we'll just prompt
                            # the user to start a focus session if they're browsing
                            self.root.after(0, self.show_distraction_warning)
                            
                except Exception as e:
                    print(f"Error in site monitoring: {e}")
                    
            time.sleep(check_interval)
    
    def show_distraction_warning(self):
        """Show a warning about potential distractions"""
        if not self.running and messagebox.askyesno("Distraction Alert", 
                                                 "It looks like you might be browsing the web. "
                                                 "Would you like to start a focus session?"):
            self.start_monitoring()
    
    def save_session(self, duration, focus_score):
        """Save session data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            cursor.execute('''
            INSERT INTO focus_sessions (start_time, duration, focus_score, hardcore_mode)
            VALUES (?, ?, ?, ?)
            ''', (now, int(duration), focus_score, 1 if self.hardcore_mode else 0))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def update_journal(self, session_id, journal_text):
        """Update a session with journal text"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE focus_sessions SET journal_text = ? WHERE id = ?
            ''', (journal_text, session_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating journal: {e}")
    
    def load_session_history(self):
        """Load session history from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent sessions
            cursor.execute('''
            SELECT id, start_time, duration, focus_score
            FROM focus_sessions
            ORDER BY start_time DESC
            LIMIT 20
            ''')
            
            # Clear existing entries
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # Add sessions to tree view
            for row in cursor.fetchall():
                session_id, start_time, duration, score = row
                
                # Parse the ISO timestamp
                dt = datetime.datetime.fromisoformat(start_time)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
                
                # Format duration
                mins, secs = divmod(duration, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    duration_str = f"{hours}h {mins}m"
                else:
                    duration_str = f"{mins}m {secs}s"
                
                # Add to tree
                self.history_tree.insert("", "end", values=(date_str, duration_str, f"{score}%"))
            
            conn.close()
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def update_focus_stats(self):
        """Update focus statistics display"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get today's session count
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            cursor.execute('''
            SELECT COUNT(*) FROM focus_sessions
            WHERE date(start_time) = ?
            ''', (today,))
            today_count = cursor.fetchone()[0]
            self.today_sessions_label.config(text=str(today_count))
            
            # Calculate streak
            streak = 0
            current_date = datetime.datetime.now().date()
            
            # Check up to 100 previous days for sessions
            for i in range(100):
                check_date = (current_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                cursor.execute('''
                SELECT COUNT(*) FROM focus_sessions
                WHERE date(start_time) = ?
                ''', (check_date,))
                
                if cursor.fetchone()[0] > 0:
                    if i == 0 or streak > 0:  # Either today or continuing streak
                        streak += 1
                else:
                    if i > 0:  # Not today, streak broken
                        break
            
            self.streak_label.config(text=f"{streak} days")
            
            # Get weekly data for chart
            self.generate_weekly_chart()
            
            conn.close()
            
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def generate_weekly_chart(self):
        """Generate a simple text-based chart of weekly focus scores"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear previous chart
            for widget in self.week_chart_frame.winfo_children():
                widget.destroy()
            
            # Get last 7 days data
            days = []
            scores = []
            
            for i in range(6, -1, -1):
                date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                day_name = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%a")
                
                cursor.execute('''
                SELECT AVG(focus_score) FROM focus_sessions
                WHERE date(start_time) = ?
                ''', (date,))
                
                avg_score = cursor.fetchone()[0]
                if avg_score is None:
                    avg_score = 0
                else:
                    avg_score = round(avg_score)
                
                days.append(day_name)
                scores.append(avg_score)
            
            # Create a simple bar chart
            max_height = 150
            bar_width = 30
            spacing = 10
            
            chart_canvas = tk.Canvas(self.week_chart_frame, height=max_height + 30, bg='white')
            chart_canvas.pack(fill=tk.X, expand=True)
            
            # Draw bars
            for i, score in enumerate(scores):
                bar_height = int((score / 100) * max_height) if score > 0 else 1
                x1 = i * (bar_width + spacing) + 20
                y1 = max_height - bar_height
                x2 = x1 + bar_width
                y2 = max_height
                
                # Bar with gradient color based on score
                if score >= 80:
                    color = "#27ae60"  # Green
                elif score >= 50:
                    color = "#f39c12"  # Orange
                else:
                    color = "#e74c3c"  # Red
                
                chart_canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                chart_canvas.create_text(x1 + bar_width/2, y2 + 10, text=days[i])
                chart_canvas.create_text(x1 + bar_width/2, y1 - 10, text=f"{score}%")
            
            conn.close()
            
        except Exception as e:
            print(f"Error generating chart: {e}")
    
    def show_journal_dialog(self):
        """Show dialog for session journaling"""
        journal_window = tk.Toplevel(self.root)
        journal_window.title("Session Journal")
        journal_window.geometry("500x400")
        journal_window.grab_set()  # Make window modal
        
        ttk.Label(journal_window, text="Reflect on your focus session:", 
                style="Header.TLabel").pack(pady=10, padx=10, anchor=tk.W)
        
        # Journal prompts
        prompts_frame = ttk.Frame(journal_window)
        prompts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        prompts = [
            "What did I accomplish?",
            "What distractions did I face?",
            "How could I improve my focus next time?",
            "What am I proud of from this session?"
        ]
        
        for prompt in prompts:
            ttk.Label(prompts_frame, text=f"• {prompt}").pack(anchor=tk.W, pady=2)
        
        # Journal text area
        journal_text = scrolledtext.ScrolledText(journal_window, height=10)
        journal_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buttons
        buttons_frame = ttk.Frame(journal_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Skip", 
                 command=journal_window.destroy).pack(side=tk.LEFT, padx=5)
        
        # Get the session ID of the most recent session
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(id) FROM focus_sessions')
        session_id = cursor.fetchone()[0]
        conn.close()
        
        save_btn = ttk.Button(buttons_frame, text="Save Journal", 
                            command=lambda: [
                                self.update_journal(session_id, journal_text.get("1.0", "end-1c")),
                                self.check_journaler_badge(),
                                journal_window.destroy()
                            ])
        save_btn.pack(side=tk.RIGHT, padx=5)
    
    def check_badges(self, session_time, focus_score):
        """Check if user earned any badges from this session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get already earned badges
            cursor.execute('SELECT badge_id FROM earned_badges')
            earned_badges = [row[0] for row in cursor.fetchall()]
            
            now = datetime.datetime.now()
            today = now.strftime("%Y-%m-%d")
            new_badges = []
            
            # Check time-based badges
            if session_time >= 1800 and "focus_rookie" not in earned_badges:  # 30 minutes
                new_badges.append("focus_rookie")
                
            if session_time >= 3600 and "focus_adept" not in earned_badges:  # 1 hour
                new_badges.append("focus_adept")
                
            if session_time >= 7200 and "focus_master" not in earned_badges:  # 2 hours
                new_badges.append("focus_master")
            
            # Check hardcore mode badge
            if self.hardcore_mode and "iron_will" not in earned_badges:
                new_badges.append("iron_will")
            
            # Check time of day badges
            if now.hour < 8 and "early_bird" not in earned_badges:
                new_badges.append("early_bird")
                
            if now.hour >= 22 and "night_owl" not in earned_badges:
                new_badges.append("night_owl")
            
            # Check multiple sessions badge
            cursor.execute('''
            SELECT COUNT(*) FROM focus_sessions
            WHERE date(start_time) = ?
            ''', (today,))
            
            today_sessions = cursor.fetchone()[0]
            if today_sessions >= 3 and "hat_trick" not in earned_badges:
                new_badges.append("hat_trick")
            
            # Check streak badge
            days_with_sessions = set()
            cursor.execute('''
            SELECT DISTINCT date(start_time) FROM focus_sessions
            WHERE start_time >= date('now', '-7 days')
            ''')
            
            for row in cursor.fetchall():
                days_with_sessions.add(row[0])
            
            # Check if they have sessions for 7 consecutive days
            streak_days = 0
            for i in range(7):
                check_date = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                if check_date in days_with_sessions:
                    streak_days += 1
                else:
                    break
                    
            if streak_days >= 7 and "streak_week" not in earned_badges:
                new_badges.append("streak_week")
            
            # Save new badges
            for badge_id in new_badges:
                cursor.execute('''
                INSERT INTO earned_badges (badge_id, earn_date)
                VALUES (?, ?)
                ''', (badge_id, now.isoformat()))
            
            conn.commit()
            conn.close()
            
            # Show badge notifications
            if new_badges:
                self.show_badge_notification(new_badges)
                self.update_badges_display()
                
        except Exception as e:
            print(f"Error checking badges: {e}")
    
    def check_journaler_badge(self):
        """Check if user earned the journaler badge"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count sessions with journal entries
            cursor.execute("SELECT COUNT(*) FROM focus_sessions WHERE journal_text IS NOT NULL AND journal_text != ''")
            journal_count = cursor.fetchone()[0]
            
            # Check if already earned
            cursor.execute("SELECT COUNT(*) FROM earned_badges WHERE badge_id = 'journaler'")
            already_earned = cursor.fetchone()[0] > 0
            
            if journal_count >= 5 and not already_earned:
                now = datetime.datetime.now().isoformat()
                cursor.execute('''
                INSERT INTO earned_badges (badge_id, earn_date)
                VALUES (?, ?)
                ''', ("journaler", now))
                
                conn.commit()
                self.show_badge_notification(["journaler"])
                self.update_badges_display()
            
            conn.close()
        except Exception as e:
            print(f"Error checking journaler badge: {e}")
    
    def show_badge_notification(self, badge_ids):
        """Show a notification for earned badges"""
        badge_window = tk.Toplevel(self.root)
        badge_window.title("New Badge Earned!")
        badge_window.geometry("400x300")
        badge_window.grab_set()
        
        ttk.Label(badge_window, text="Congratulations!", 
                font=("Arial", 18, "bold")).pack(pady=(20, 10))
        
        ttk.Label(badge_window, text="You've earned new badges:", 
                font=("Arial", 12)).pack(pady=(0, 20))
        
        for badge_id in badge_ids:
            badge = self.badges.get(badge_id)
            if badge:
                badge_frame = ttk.Frame(badge_window)
                badge_frame.pack(fill=tk.X, padx=20, pady=5)
                
                ttk.Label(badge_frame, text=badge["icon"], 
                        font=("Arial", 24), style="Badge.TLabel").pack(side=tk.LEFT, padx=10)
                
                ttk.Label(badge_frame, text=badge["name"], 
                        font=("Arial", 14, "bold")).pack(side=tk.TOP, anchor=tk.W)
                ttk.Label(badge_frame, text=badge["desc"]).pack(side=tk.TOP, anchor=tk.W)
        
        ttk.Button(badge_window, text="Awesome!", 
                 command=badge_window.destroy).pack(pady=20)
    
    def update_badges_display(self):
        """Update the badges display in the stats tab"""
        try:
            # Clear existing badges
            for widget in self.badges_frame.winfo_children():
                widget.destroy()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get earned badges
            cursor.execute('SELECT badge_id, earn_date FROM earned_badges ORDER BY earn_date DESC')
            earned_badges = cursor.fetchall()
            
            if not earned_badges:
                ttk.Label(self.badges_frame, text="No badges earned yet. Keep focusing!",
                        wraplength=250).pack(padx=10, pady=20)
            else:
                for i, (badge_id, earn_date) in enumerate(earned_badges):
                    badge = self.badges.get(badge_id)
                    if badge:
                        badge_frame = ttk.Frame(self.badges_frame)
                        badge_frame.pack(fill=tk.X, padx=10, pady=5)
                        
                        ttk.Label(badge_frame, text=badge["icon"], 
                                font=("Arial", 24), style="Badge.TLabel").grid(row=0, column=0, rowspan=2, padx=10)
                        
                        ttk.Label(badge_frame, text=badge["name"], 
                                font=("Arial", 12, "bold")).grid(row=0, column=1, sticky=tk.W)
                        
                        ttk.Label(badge_frame, text=badge["desc"],
                                wraplength=200).grid(row=1, column=1, sticky=tk.W)
                        
                        # Format date
                        dt = datetime.datetime.fromisoformat(earn_date)
                        date_str = dt.strftime("%Y-%m-%d")
                        ttk.Label(badge_frame, text=f"Earned: {date_str}").grid(row=2, column=1, sticky=tk.W)
                        
                        ttk.Separator(self.badges_frame, orient="horizontal").pack(fill=tk.X, padx=10, pady=5)
            
            conn.close()
            
        except Exception as e:
            print(f"Error updating badges: {e}")
    
    def on_closing(self):
        """Clean up resources when closing the app"""
        self.running = False
        if self.cap is not None:
            self.cap.release()
            
        # Ensure sites are unblocked
        self.unblock_distracting_sites()
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = FocusBuddyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()