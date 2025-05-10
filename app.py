import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
import pygame
import os
import numpy as np
from PIL import Image, ImageTk
import tempfile
import json
import datetime
import calendar
import platform
import subprocess
import re
import hashlib
import base64
from urllib.parse import urlparse
import webbrowser

class FOCUSBuddyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FOCUSBuddy")
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)
        
        # Configure the inner frame
        self.journal_frame_inner.bind("<Configure>", 
                                  lambda e: self.journal_canvas.configure(
                                      scrollregion=self.journal_canvas.bbox("all")))
        
        # Load journal entries
        self.load_journal_entries()
        
    def create_settings_tab(self):
        """Create the settings tab content"""
        # Configure grid weights
        self.settings_tab.columnconfigure(0, weight=1)
        self.settings_tab.rowconfigure(0, weight=0)
        self.settings_tab.rowconfigure(1, weight=0)
        self.settings_tab.rowconfigure(2, weight=0)
        self.settings_tab.rowconfigure(3, weight=0)
        self.settings_tab.rowconfigure(4, weight=1)
        
        # Focus Settings
        focus_frame = ttk.LabelFrame(self.settings_tab, text="Focus Settings")
        focus_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        focus_frame.columnconfigure(1, weight=1)
        
        # Grace period
        ttk.Label(focus_frame, text="Grace Period (seconds):").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.grace_var = tk.StringVar(value=str(self.grace_period))
        grace_entry = ttk.Entry(focus_frame, textvariable=self.grace_var, width=5)
        grace_entry.grid(row=0, column=1, padx=15, pady=10, sticky="w")
        
        # Detection sensitivity
        ttk.Label(focus_frame, text="Detection Sensitivity:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.sensitivity_var = tk.StringVar(value="Medium")
        sensitivity_combo = ttk.Combobox(focus_frame, textvariable=self.sensitivity_var, 
                                        values=["Low", "Medium", "High"], width=10, state="readonly")
        sensitivity_combo.grid(row=1, column=1, padx=15, pady=10, sticky="w")
        
        # Break duration
        ttk.Label(focus_frame, text="Break Duration (minutes):").grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.break_var = tk.StringVar(value=str(self.break_duration // 60))
        break_entry = ttk.Entry(focus_frame, textvariable=self.break_var, width=5)
        break_entry.grid(row=2, column=1, padx=15, pady=10, sticky="w")
        
        # Video Settings
        video_frame = ttk.LabelFrame(self.settings_tab, text="Camera Settings")
        video_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        video_frame.columnconfigure(1, weight=1)
        
        # Camera size
        ttk.Label(video_frame, text="Camera Width:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.width_var = tk.StringVar(value=str(self.video_width))
        width_entry = ttk.Entry(video_frame, textvariable=self.width_var, width=5)
        width_entry.grid(row=0, column=1, padx=15, pady=10, sticky="w")
        
        ttk.Label(video_frame, text="Camera Height:").grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.height_var = tk.StringVar(value=str(self.video_height))
        height_entry = ttk.Entry(video_frame, textvariable=self.height_var, width=5)
        height_entry.grid(row=1, column=1, padx=15, pady=10, sticky="w")
        
        # Distracting Websites
        websites_frame = ttk.LabelFrame(self.settings_tab, text="Distracting Websites")
        websites_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        websites_frame.columnconfigure(0, weight=1)
        websites_frame.rowconfigure(0, weight=1)
        
        # Add scrollbar for websites list
        self.websites_text = tk.Text(websites_frame, height=6, width=50)
        self.websites_text.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        websites_scroll = ttk.Scrollbar(websites_frame, orient="vertical", command=self.websites_text.yview)
        websites_scroll.grid(row=0, column=1, sticky="ns", pady=15)
        self.websites_text.configure(yscrollcommand=websites_scroll.set)
        
        # Populate with current websites
        self.websites_text.insert("1.0", "\n".join(self.distracting_websites))
        
        # Alert messages
        message_frame = ttk.LabelFrame(self.settings_tab, text="Focus Reminder Messages")
        message_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        message_frame.columnconfigure(0, weight=1)
        message_frame.rowconfigure(0, weight=1)
        
        self.message_text = tk.Text(message_frame, height=6, width=50)
        self.message_text.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        message_scroll = ttk.Scrollbar(message_frame, orient="vertical", command=self.message_text.yview)
        message_scroll.grid(row=0, column=1, sticky="ns", pady=15)
        self.message_text.configure(yscrollcommand=message_scroll.set)
        
        # Populate with alert messages
        self.message_text.insert("1.0", "\n".join(self.alert_messages))
        
        # Sound settings
        sound_frame = ttk.LabelFrame(self.settings_tab, text="Alert Sound")
        sound_frame.grid(row=4, column=0, sticky="new", padx=15, pady=(0, 15))
        sound_frame.columnconfigure(0, weight=1)
        
        sound_controls = ttk.Frame(sound_frame)
        sound_controls.grid(row=1, column=0, sticky="ew", padx=15, pady=15)
        
        ttk.Button(sound_controls, text="Select Sound File", 
                 command=self.select_sound).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(sound_controls, text="Test Sound", 
                 command=self.test_sound).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(sound_controls, text="Reset to Default", 
                 command=self.reset_sound).grid(row=0, column=2, padx=5, pady=5)
        
        self.sound_label = ttk.Label(sound_frame, text="Using default alert sound")
        self.sound_label.grid(row=0, column=0, padx=15, pady=(15, 0), sticky="w")
        
        # Apply and data management buttons
        button_frame = ttk.Frame(self.settings_tab)
        button_frame.grid(row=5, column=0, sticky="se", padx=15, pady=(0, 15))
        
        ttk.Button(button_frame, text="Reset All Stats", 
                 command=self.confirm_reset_stats).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Export Data", 
                 command=self.export_data).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Apply Settings", 
                 command=self.apply_settings).grid(row=0, column=2, padx=5, pady=5)
    
    def update_latest_badges(self):
        """Update the display of latest badges in the main tab"""
        # Clear current badges
        for widget in self.badges_frame.winfo_children():
            widget.destroy()
        
        # Get latest 3 badges
        latest_badges = []
        for badge_id, earned_date in sorted(self.earned_badges.items(), key=lambda x: x[1], reverse=True)[:3]:
            badge_file = os.path.join(self.badges_dir, f"{badge_id}.svg")
            if os.path.exists(badge_file):
                latest_badges.append((badge_id, badge_file))
        
        # Display badges horizontally
        for i, (badge_id, badge_file) in enumerate(latest_badges):
            try:
                # Load SVG using PIL with Cairosvg if available
                try:
                    import cairosvg
                    import io
                    png_data = cairosvg.svg2png(url=badge_file, output_width=64, output_height=64)
                    img = Image.open(io.BytesIO(png_data))
                except ImportError:
                    # Fallback to direct loading (may not work well with SVG)
                    img = Image.open(badge_file)
                    img = img.resize((64, 64), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                # Keep a reference to avoid garbage collection
                badge_frame = ttk.Frame(self.badges_frame)
                badge_frame.grid(row=0, column=i, padx=5, pady=5)
                
                label = ttk.Label(badge_frame, image=photo)
                label.image = photo  # Keep a reference
                label.pack(padx=5, pady=5)
                
                # Get badge name from file naming
                badge_name = " ".join(badge_id.split('_')).title()
                ttk.Label(badge_frame, text=badge_name).pack(padx=5)
                
            except Exception as e:
                print(f"Error displaying badge {badge_id}: {e}")
    
    def update_session_display(self):
        """Update the display of today's sessions and totals"""
        # Get today's date as string
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # Count today's sessions
        today_sessions = len(self.daily_sessions.get(today, []))
        self.sessions_today_label.config(text=str(today_sessions))
        
        # Format total focus time
        hours = self.total_focus_time // 3600
        minutes = (self.total_focus_time % 3600) // 60
        self.total_focus_label.config(text=f"{hours}h {minutes}m")
        
        # Calculate current streak
        streak = self.calculate_streak()
        self.streak_label.config(text=f"{streak} days")
    
    def calculate_streak(self):
        """Calculate the current streak of consecutive days using the app"""
        if not self.daily_sessions:
            return 0
            
        today = datetime.date.today()
        streak = 0
        
        # Check each day backwards from today
        for i in range(100):  # Limit to reasonable number
            check_date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            if check_date in self.daily_sessions and self.daily_sessions[check_date]:
                streak += 1
            else:
                # Break on first day without sessions
                if i > 0:  # Don't break on today if there are no sessions yet
                    break
                    
        return streak
    
    def draw_weekly_stats(self):
        """Draw the weekly stats chart"""
        self.weekly_canvas.delete("all")
        
        # Get dates for the last 7 days
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
        
        # Collect focus minutes for each day
        focus_minutes = []
        max_minutes = 1  # Minimum to avoid division by zero
        
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            day_sessions = self.daily_sessions.get(date_str, [])
            
            # Sum up session durations
            day_minutes = sum(session["duration"] for session in day_sessions) // 60
            focus_minutes.append(day_minutes)
            
            # Update max for scaling
            max_minutes = max(max_minutes, day_minutes)
        
        # Drawing dimensions
        canvas_width = self.weekly_canvas.winfo_width()
        canvas_height = self.weekly_canvas.winfo_height()
        if canvas_width < 10:  # Not yet properly laid out
            canvas_width = 400
            canvas_height = 300
            
        bar_width = canvas_width / 9  # Space for 7 bars with margins
        max_bar_height = canvas_height - 60  # Leave space for labels
        
        # Draw title
        self.weekly_canvas.create_text(canvas_width / 2, 15, text="Focus Minutes by Day", 
                                     font=("Arial", 12, "bold"))
        
        # Draw bars
        for i, (date, minutes) in enumerate(zip(dates, focus_minutes)):
            # Calculate bar dimensions
            x1 = (i + 1) * bar_width
            y1 = canvas_height - 30
            x2 = x1 + bar_width * 0.7
            
            if minutes > 0:
                bar_height = (minutes / max_minutes) * max_bar_height
            else:
                bar_height = 1  # Minimum height for zero values
                
            y2 = y1 - bar_height
            
            # Draw bar
            day_name = calendar.day_name[date.weekday()][:3]
            color = "#3498db"  # Default color
            
            # Highlight today
            if date == today:
                color = "#27ae60"
            
            self.weekly_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            
            # Draw day label
            self.weekly_canvas.create_text((x1 + x2) / 2, y1 + 15, text=day_name)
            
            # Draw value label if there are minutes
            if minutes > 0:
                self.weekly_canvas.create_text((x1 + x2) / 2, y2 - 15, text=str(minutes))
        
        # Draw y-axis labels
        self.weekly_canvas.create_line(bar_width * 0.5, 30, bar_width * 0.5, canvas_height - 30)
        
        # Draw some reference lines
        for i in range(5):
            y = canvas_height - 30 - (i / 4) * max_bar_height
            self.weekly_canvas.create_line(bar_width * 0.4, y, bar_width * 0.6, y, dash=(2, 2))
            self.weekly_canvas.create_text(bar_width * 0.25, y, 
                                        text=str(int(i / 4 * max_minutes)), 
                                        font=("Arial", 8))
    
    def draw_badges_collection(self):
        """Draw all earned badges in the collection view"""
        # Clear current badges
        for widget in self.badges_frame_inner.winfo_children():
            widget.destroy()
        
        # Display all earned badges in a grid
        if not self.earned_badges:
            ttk.Label(self.badges_frame_inner, text="No badges earned yet. Start focusing to earn badges!",
                    font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=20)
            return
            
        # Calculate number of columns based on canvas width
        canvas_width = self.badges_canvas.winfo_width()
        if canvas_width < 10:  # Not yet properly laid out
            canvas_width = 400
            
        cols = max(1, canvas_width // 150)
        
        # Sort badges by earned date
        sorted_badges = sorted(self.earned_badges.items(), key=lambda x: x[1])
        
        # Display badges in grid
        for i, (badge_id, earned_date) in enumerate(sorted_badges):
            badge_file = os.path.join(self.badges_dir, f"{badge_id}.svg")
            if not os.path.exists(badge_file):
                continue
                
            row = i // cols
            col = i % cols
            
            badge_frame = ttk.Frame(self.badges_frame_inner, style="Badge.TLabel")
            badge_frame.grid(row=row, column=col, padx=10, pady=10, sticky="n")
            
            try:
                # Load SVG
                try:
                    import cairosvg
                    import io
                    png_data = cairosvg.svg2png(url=badge_file, output_width=100, output_height=100)
                    img = Image.open(io.BytesIO(png_data))
                except ImportError:
                    # Fallback
                    img = Image.open(badge_file)
                    img = img.resize((100, 100), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                # Badge image
                label = ttk.Label(badge_frame, image=photo)
                label.image = photo  # Keep a reference
                label.pack(padx=5, pady=5)
                
                # Badge name and date
                badge_name = " ".join(badge_id.split('_')).title()
                ttk.Label(badge_frame, text=badge_name, font=("Arial", 10, "bold")).pack(padx=5)
                
                # Format date
                try:
                    earned_date_obj = datetime.datetime.strptime(earned_date, "%Y-%m-%d")
                    earned_date_str = earned_date_obj.strftime("%b %d, %Y")
                except:
                    earned_date_str = earned_date
                    
                ttk.Label(badge_frame, text=f"Earned: {earned_date_str}", font=("Arial", 8)).pack(padx=5)
                
            except Exception as e:
                print(f"Error displaying badge {badge_id}: {e}")
    
    def load_journal_entries(self):
        """Load and display journal entries"""
        # Clear current entries
        for widget in self.journal_frame_inner.winfo_children():
            widget.destroy()
            
        if not self.journal_entries:
            ttk.Label(self.journal_frame_inner, text="No journal entries yet. Add reflections after focus sessions!",
                    font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=20)
            return
        
        # Sort entries by date (newest first)
        sorted_entries = sorted(self.journal_entries, key=lambda x: x.get("date", ""), reverse=True)
        
        # Display entries
        for i, entry in enumerate(sorted_entries):
            entry_frame = ttk.Frame(self.journal_frame_inner)
            entry_frame.grid(row=i, column=0, sticky="ew", padx=10, pady=5)
            
            # Configure inner frame to expand
            entry_frame.columnconfigure(0, weight=1)
            
            # Entry header with date
            header_frame = ttk.Frame(entry_frame)
            header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            # Format date
            try:
                entry_date = datetime.datetime.strptime(entry["date"], "%Y-%m-%d %H:%M:%S")
                date_str = entry_date.strftime("%b %d, %Y at %I:%M %p")
            except:
                date_str = entry.get("date", "Unknown date")
                
            ttk.Label(header_frame, text=date_str, font=("Arial", 10, "bold")).pack(side="left", padx=5)
            
            # Session details
            if "duration" in entry:
                duration_min = entry["duration"] // 60
                ttk.Label(header_frame, text=f"{duration_min} min session",
                        font=("Arial", 9)).pack(side="left", padx=5)
                
            if "focus_score" in entry:
                ttk.Label(header_frame, text=f"Focus: {entry['focus_score']}%",
                        font=("Arial", 9)).pack(side="left", padx=5)
            
            # Entry content
            if "text" in entry and entry["text"]:
                content_frame = ttk.Frame(entry_frame, padding=5)
                content_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
                content_frame.columnconfigure(0, weight=1)
                
                text_widget = tk.Text(content_frame, wrap="word", height=4, width=50, bg="#f9f9f9", relief="flat")
                text_widget.grid(row=0, column=0, sticky="ew")
                text_widget.insert("1.0", entry["text"])
                text_widget.config(state="disabled")  # Make read-only
                
                # Add small action buttons
                action_frame = ttk.Frame(entry_frame)
                action_frame.grid(row=2, column=0, sticky="e", padx=5, pady=5)
                
                ttk.Button(action_frame, text="Edit", width=8,
                        command=lambda e=entry, i=i: self.edit_journal_entry(e, i)).pack(side="left", padx=2)
                        
                ttk.Button(action_frame, text="Delete", width=8,
                        command=lambda i=i: self.delete_journal_entry(i)).pack(side="left", padx=2)
            
            # Separator
            ttk.Separator(self.journal_frame_inner, orient="horizontal").grid(
                row=i+1, column=0, sticky="ew", padx=10, pady=5)
                
        # Configure the scrolling
        self.journal_frame_inner.update_idletasks()
        self.journal_canvas.config(scrollregion=self.journal_canvas.bbox("all"))
    
    def add_journal_entry(self):
        """Add a new journal entry"""
        entry_window = tk.Toplevel(self.root)
        entry_window.title("New Journal Entry")
        entry_window.geometry("500x400")
        entry_window.transient(self.root)
        entry_window.resizable(True, True)
        
        # Entry form
        entry_window.columnconfigure(0, weight=1)
        entry_window.rowconfigure(1, weight=1)
        
        header_frame = ttk.Frame(entry_window)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        
        ttk.Label(header_frame, text="New Reflection Entry", 
                font=("Arial", 12, "bold")).pack(side="left")
        
        # Date is auto-generated
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Text entry
        text_frame = ttk.Frame(entry_window)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        
        ttk.Label(text_frame, text="What are your reflections on this focus session?").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
            
        text_widget = tk.Text(text_frame, wrap="word", height=10)
        text_widget.grid(row=1, column=0, sticky="nsew")
        
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_scroll.grid(row=1, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=text_scroll.set)
        
        # Prompt questions to help reflection
        prompts_frame = ttk.LabelFrame(entry_window, text="Reflection Prompts")
        prompts_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        prompts = [
            "What helped you stay focused during this session?",
            "What distracted you the most?",
            "What will you do differently next time?",
            "What did you accomplish during this session?"
        ]
        
        for i, prompt in enumerate(prompts):
            ttk.Label(prompts_frame, text=f"• {prompt}", 
                    font=("Arial", 9, "italic")).grid(row=i, column=0, sticky="w", padx=10, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(entry_window)
        button_frame.grid(row=3, column=0, sticky="e", padx=15, pady=(0, 15))
        
        ttk.Button(button_frame, text="Cancel", 
                 command=entry_window.destroy).pack(side="left", padx=5)
                 
        def save_entry():
            text = text_widget.get("1.0", "end-1c").strip()
            if text:
                entry = {
                    "date": date_str,
                    "text": text
                }
                
                # Add last session data if available
                if hasattr(self, 'last_session_data'):
                    entry.update(self.last_session_data)
                
                self.journal_entries.append(entry)
                self.save_user_data()
                self.load_journal_entries()
                
                # Check for journal badge
                self.check_for_journal_badge()
                
                entry_window.destroy()
            else:
                messagebox.showwarning("Empty Entry", "Please enter some text for your reflection.")
        
        ttk.Button(button_frame, text="Save Entry", 
                 command=save_entry).pack(side="left", padx=5)
    
    def edit_journal_entry(self, entry, index):
        """Edit an existing journal entry"""
        entry_window = tk.Toplevel(self.root)
        entry_window.title("Edit Journal Entry")
        entry_window.geometry("500x400")
        entry_window.transient(self.root)
        entry_window.resizable(True, True)
        
        # Entry form
        entry_window.columnconfigure(0, weight=1)
        entry_window.rowconfigure(1, weight=1)
        
        header_frame = ttk.Frame(entry_window)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        
        # Format date for display
        try:
            entry_date = datetime.datetime.strptime(entry["date"], "%Y-%m-%d %H:%M:%S")
            date_str = entry_date.strftime("%b %d, %Y at %I:%M %p")
        except:
            date_str = entry.get("date", "Unknown date")
        
        ttk.Label(header_frame, text=f"Edit Entry from {date_str}", 
                font=("Arial", 12, "bold")).pack(side="left")
        
        # Text entry
        text_frame = ttk.Frame(entry_window)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        text_widget = tk.Text(text_frame, wrap="word", height=10)
        text_widget.grid(row=0, column=0, sticky="nsew")
        
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_scroll.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=text_scroll.set)
        
        # Load existing text
        if "text" in entry:
            text_widget.insert("1.0", entry["text"])
        
        # Buttons
        button_frame = ttk.Frame(entry_window)
        button_frame.grid(row=2, column=0, sticky="e", padx=15, pady=(0, 15))
        
        ttk.Button(button_frame, text="Cancel", 
                 command=entry_window.destroy).pack(side="left", padx=5)
                 
        def save_edit():
            text = text_widget.get("1.0", "end-1c").strip()
            if text:
                self.journal_entries[index]["text"] = text
                self.save_user_data()
                self.load_journal_entries()
                entry_window.destroy()
            else:
                messagebox.showwarning("Empty Entry", "Please enter some text for your reflection.")
        
        ttk.Button(button_frame, text="Save Changes", 
                 command=save_edit).pack(side="left", padx=5)
    
    def delete_journal_entry(self, index):
        """Delete a journal entry"""
        confirm = messagebox.askyesno("Confirm Delete", 
                                    "Are you sure you want to delete this journal entry?")
        if confirm:
            if 0 <= index < len(self.journal_entries):
                del self.journal_entries[index]
                self.save_user_data()
                self.load_journal_entries()
    
    def check_for_journal_badge(self):
        """Check if user has earned a journal badge"""
        if len(self.journal_entries) >= 5 and "journal_5" not in self.earned_badges:
            self.award_badge("journal_5")
    
    def toggle_monitoring(self):
        """Legacy function for backward compatibility"""
        self.start_focus_session()
    
    def start_focus_session(self):
        """Start a focus session with timer and monitoring"""
        if self.running:
            return
            
        # Get session duration
        try:
            duration_min = int(self.duration_var.get())
            self.session_duration = duration_min * 60
        except ValueError:
            self.session_duration = 25 * 60  # Default to 25 minutes
        
        # Check if in hardcore mode
        self.hardcore_mode = self.hardcore_var.get()
        
        # Enable distraction blocking
        if self.hardcore_mode:
            # Show warning for hardcore mode
            confirm = messagebox.askyesno("Hardcore Mode", 
                                        "You're enabling Hardcore Mode!\n\n"
                                        "This will block distracting websites and prevent stopping the session early.\n"
                                        " Set theme and style
        self.set_theme()
        
        # Initialize pygame for audio
        pygame.mixer.init()
        
        # Control variables
        self.running = False
        self.person_present = False
        self.alert_active = False
        self.alert_thread = None
        self.warning_count = 0
        self.last_detection_time = time.time()
        self.grace_period = 3  # seconds before alerting
        self.session_start_time = None
        self.session_end_time = None
        self.session_duration = 25 * 60  # Default 25 minutes (Pomodoro)
        self.break_duration = 5 * 60  # Default 5 minutes break
        self.focus_score = 100  # Start with perfect focus
        self.break_active = False
        self.hardcore_mode = False
        self.distracting_websites = [
            "youtube.com", "facebook.com", "twitter.com", "instagram.com", 
            "reddit.com", "tiktok.com", "netflix.com", "twitch.tv"
        ]
        
        # App data paths
        self.app_data_dir = os.path.join(os.path.expanduser("~"), ".focusbuddy")
        self.ensure_app_dirs()
        
        # Load user data
        self.load_user_data()
        
        # Video frame size control
        self.video_width = 320
        self.video_height = 240
        
        # Create the UI elements
        self.create_ui()
        
        # OpenCV variables
        self.cap = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Create default sound
        self.create_default_sound()
        
        # On closing window
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Stabilization buffers
        self.focus_buffer = [False] * 5  # Last 5 focus states
        self.focus_index = 0
        
        # Start background monitoring for distracting sites
        self.start_background_monitor()

    def ensure_app_dirs(self):
        """Ensure application directories exist"""
        if not os.path.exists(self.app_data_dir):
            os.makedirs(self.app_data_dir)
            
        # Badge images directory
        self.badges_dir = os.path.join(self.app_data_dir, "badges")
        if not os.path.exists(self.badges_dir):
            os.makedirs(self.badges_dir)
            
        # Create default data file if it doesn't exist
        self.data_file = os.path.join(self.app_data_dir, "user_data.json")
        if not os.path.exists(self.data_file):
            default_data = {
                "total_focus_time": 0,
                "daily_sessions": {},
                "badges": {},
                "focus_history": {},
                "distracting_websites": self.distracting_websites,
                "journal_entries": []
            }
            with open(self.data_file, "w") as f:
                json.dump(default_data, f, indent=2)
        
        # Backup the hosts file if not already done
        self.hosts_file = self.get_hosts_file_path()
        self.hosts_backup = os.path.join(self.app_data_dir, "hosts.backup")
        if not os.path.exists(self.hosts_backup) and os.path.exists(self.hosts_file):
            try:
                with open(self.hosts_file, "r") as src, open(self.hosts_backup, "w") as dst:
                    dst.write(src.read())
            except Exception as e:
                print(f"Warning: Could not backup hosts file: {e}")
                
        # Create badge SVGs
        self.create_default_badges()

    def create_default_badges(self):
        """Create default badge SVG files"""
        badges = {
            "focus_1h": {
                "title": "1 Hour Focus",
                "desc": "Focused for a cumulative 1 hour",
                "color": "#3498db",
                "icon": "🕐"
            },
            "focus_5h": {
                "title": "5 Hour Champion",
                "desc": "Focused for a cumulative 5 hours",
                "color": "#2ecc71",
                "icon": "🕔"
            },
            "focus_10h": {
                "title": "10 Hour Master",
                "desc": "Focused for a cumulative 10 hours",
                "color": "#e74c3c",
                "icon": "🕙"
            },
            "streak_3": {
                "title": "3-Day Streak",
                "desc": "Used FOCUSBuddy for 3 days in a row",
                "color": "#9b59b6",
                "icon": "🔥"
            },
            "streak_7": {
                "title": "7-Day Streak",
                "desc": "Used FOCUSBuddy for 7 days in a row",
                "color": "#f39c12",
                "icon": "🔥"
            },
            "sessions_3": {
                "title": "3 Sessions Pro",
                "desc": "Completed 3 focus sessions in one day",
                "color": "#1abc9c",
                "icon": "🏆"
            },
            "sessions_5": {
                "title": "5 Sessions Master",
                "desc": "Completed 5 focus sessions in one day",
                "color": "#d35400",
                "icon": "🎯"
            },
            "perfect_focus": {
                "title": "Perfect Focus",
                "desc": "Maintained 100% focus in a session",
                "color": "#f1c40f",
                "icon": "⭐"
            },
            "hardcore_1": {
                "title": "Hardcore Mode Survivor",
                "desc": "Completed a session in Hardcore Mode",
                "color": "#c0392b",
                "icon": "💪"
            },
            "journal_5": {
                "title": "Reflective Mind",
                "desc": "Completed 5 journal entries",
                "color": "#16a085",
                "icon": "📝"
            }
        }
        
        for badge_id, badge in badges.items():
            badge_file = os.path.join(self.badges_dir, f"{badge_id}.svg")
            if not os.path.exists(badge_file):
                svg = self.generate_badge_svg(badge["title"], badge["desc"], badge["color"], badge["icon"])
                with open(badge_file, "w") as f:
                    f.write(svg)
    
    def generate_badge_svg(self, title, desc, color, icon):
        """Generate an SVG badge with the given parameters"""
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="60" r="50" fill="{color}" />
            <circle cx="60" cy="60" r="45" fill="white" opacity="0.3" />
            <text x="60" y="75" font-family="Arial" font-size="32" text-anchor="middle" fill="white">{icon}</text>
            <text x="60" y="105" font-family="Arial" font-size="10" text-anchor="middle" fill="white">{title}</text>
        </svg>'''
        return svg

    def set_theme(self):
        """Set up a modern theme for the application"""
        style = ttk.Style()
        
        # Try to use a modern theme if available
        try:
            style.theme_use("clam")  # Use clam theme as base
        except tk.TclError:
            pass  # Fall back to default if not available

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
        style.configure("Badge.TLabel", background="#f0f0f0", padding=10)
        
        # Progress bar style
        style.configure("TProgressbar", thickness=20)
    
    def create_default_sound(self):
        """Create a louder default alert sound file"""
        try:
            beep_file = os.path.join(self.app_data_dir, "focus_monitor_beep.wav")
            
            # If file already exists, don't recreate
            if os.path.exists(beep_file):
                self.alarm_sound_file = beep_file
                return
                
            # Parameters for a loud beep
            sample_rate = 44100
            duration = 0.8  # longer sound
            frequency = 880  # A5 note (higher pitch)
            
            # Generate sine wave with higher amplitude
            num_samples = int(sample_rate * duration)
            amplitude = 32000  # Higher amplitude for louder sound
            
            # Create the samples with higher amplitude
            buf = np.zeros((num_samples, 2), dtype=np.int16)
            for i in range(num_samples):
                t = i / sample_rate
                value = int(amplitude * np.sin(2 * np.pi * frequency * t))
                buf[i][0] = value  # Left channel
                buf[i][1] = value  # Right channel
            
            # Save as WAV file with pygame
            sound = pygame.sndarray.make_sound(buf)
            pygame.mixer.Sound.write(sound, beep_file)
            
            self.alarm_sound_file = beep_file
            print(f"Created default beep sound at {beep_file}")
            
        except Exception as e:
            print(f"Error creating default sound: {e}")
            self.alarm_sound_file = None
    
    def load_user_data(self):
        """Load user data from the JSON file"""
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
                
            self.total_focus_time = data.get("total_focus_time", 0)
            self.daily_sessions = data.get("daily_sessions", {})
            self.earned_badges = data.get("badges", {})
            self.focus_history = data.get("focus_history", {})
            self.distracting_websites = data.get("distracting_websites", self.distracting_websites)
            self.journal_entries = data.get("journal_entries", [])
            
        except Exception as e:
            print(f"Error loading user data: {e}")
            # Use defaults
            self.total_focus_time = 0
            self.daily_sessions = {}
            self.earned_badges = {}
            self.focus_history = {}
            self.journal_entries = []
    
    def save_user_data(self):
        """Save user data to the JSON file"""
        data = {
            "total_focus_time": self.total_focus_time,
            "daily_sessions": self.daily_sessions,
            "badges": self.earned_badges,
            "focus_history": self.focus_history,
            "distracting_websites": self.distracting_websites,
            "journal_entries": self.journal_entries
        }
        
        try:
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving user data: {e}")
            messagebox.showerror("Data Error", f"Could not save user data: {e}")
    
    def create_ui(self):
        """Create the modern UI for the application"""
        # Use Grid layout with proper weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Main monitoring tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Focus")
        
        # Stats tab
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Stats & Badges")
        
        # Journal tab
        self.journal_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.journal_tab, text="Journal")
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Create main tab content
        self.create_main_tab()
        
        # Create stats tab content
        self.create_stats_tab()
        
        # Create journal tab content
        self.create_journal_tab()
        
        # Create settings tab content
        self.create_settings_tab()

    def create_main_tab(self):
        """Create the main monitoring tab content"""
        # Main tab layout
        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.columnconfigure(1, weight=1)
        self.main_tab.rowconfigure(0, weight=0)  # Timer row
        self.main_tab.rowconfigure(1, weight=1)  # Video and status row
        self.main_tab.rowconfigure(2, weight=0)  # Controls row
        
        # Timer frame at the top
        timer_frame = ttk.Frame(self.main_tab)
        timer_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        timer_frame.columnconfigure(0, weight=1)
        
        # Timer display
        self.time_display = ttk.Label(timer_frame, text="25:00", font=("Arial", 36, "bold"))
        self.time_display.grid(row=0, column=0, pady=10)
        
        # Timer progress bar
        self.timer_progress = ttk.Progressbar(timer_frame, orient="horizontal", length=600, mode="determinate")
        self.timer_progress.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        # Left side - Video frame
        video_frame = ttk.LabelFrame(self.main_tab, text="Face Tracking")
        video_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        self.video_label = ttk.Label(video_frame)
        self.video_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Focus indicators under video
        focus_indicators = ttk.Frame(video_frame)
        focus_indicators.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        focus_indicators.columnconfigure(0, weight=1)
        
        self.focus_indicator = ttk.Label(focus_indicators, text="🔴 Not Focused", font=("Arial", 14, "bold"))
        self.focus_indicator.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.message_label = ttk.Label(focus_indicators, text="", font=("Arial", 12))
        self.message_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Right side - Status and stats
        status_frame = ttk.LabelFrame(self.main_tab, text="Session Stats")
        status_frame.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(3, weight=1)  # Make the latest badges stretch
        
        # Focus score indicator
        score_frame = ttk.Frame(status_frame)
        score_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        score_frame.columnconfigure(1, weight=1)
        
        ttk.Label(score_frame, text="Focus Score:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.focus_score_label = ttk.Label(score_frame, text="100%", font=("Arial", 12))
        self.focus_score_label.grid(row=0, column=1, sticky="w", padx=10)
        
        # Focus score progress bar
        self.score_progress = ttk.Progressbar(score_frame, orient="horizontal", length=200, mode="determinate")
        self.score_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.score_progress["value"] = 100
        
        # Current session stats
        session_frame = ttk.Frame(status_frame)
        session_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        session_frame.columnconfigure(1, weight=1)
        
        ttk.Label(session_frame, text="Sessions Today:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.sessions_today_label = ttk.Label(session_frame, text="0", font=("Arial", 12))
        self.sessions_today_label.grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(session_frame, text="Total Focus Time:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w")
        self.total_focus_label = ttk.Label(session_frame, text="0h 0m", font=("Arial", 12))
        self.total_focus_label.grid(row=1, column=1, sticky="w", padx=10)
        
        ttk.Label(session_frame, text="Current Streak:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w")
        self.streak_label = ttk.Label(session_frame, text="0 days", font=("Arial", 12))
        self.streak_label.grid(row=2, column=1, sticky="w", padx=10)
        
        # Recent badges
        ttk.Label(status_frame, text="Latest Badges:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
        
        self.badges_frame = ttk.Frame(status_frame)
        self.badges_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        
        # Display latest badges
        self.update_latest_badges()
        
        # Controls at the bottom
        controls_frame = ttk.Frame(self.main_tab)
        controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.columnconfigure(2, weight=1)
        
        # Set session duration
        duration_frame = ttk.Frame(controls_frame)
        duration_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        ttk.Label(duration_frame, text="Duration:").grid(row=0, column=0, padx=5)
        self.duration_var = tk.StringVar(value="25")
        self.duration_combo = ttk.Combobox(duration_frame, textvariable=self.duration_var, 
                                          values=["5", "15", "25", "30", "45", "60", "90"], width=5, state="readonly")
        self.duration_combo.grid(row=0, column=1, padx=5)
        ttk.Label(duration_frame, text="min").grid(row=0, column=2, padx=5)
        
        # Control buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        
        self.start_button = ttk.Button(buttons_frame, text="Start Focus Session", 
                                     style="Start.TButton", width=20,
                                     command=self.start_focus_session)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="Stop Session", 
                                    style="Stop.TButton", width=15,
                                    command=self.stop_session, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Hardcore mode checkbox
        hardcore_frame = ttk.Frame(controls_frame)
        hardcore_frame.grid(row=0, column=2, sticky="e", padx=10, pady=10)
        
        self.hardcore_var = tk.BooleanVar(value=False)
        self.hardcore_check = ttk.Checkbutton(hardcore_frame, text="Hardcore Mode", 
                                            variable=self.hardcore_var)
        self.hardcore_check.grid(row=0, column=0, padx=5)
        
        ttk.Button(hardcore_frame, text="?", width=2,
                 command=lambda: messagebox.showinfo("Hardcore Mode", 
                                                   "In Hardcore Mode, you cannot stop the session before it completes. "
                                                   "All distracting websites will be blocked, and the app cannot be closed. "
                                                   "Use with caution!")).grid(row=0, column=1)
        
        # Status message at bottom
        self.status_label = ttk.Label(self.main_tab, text="Ready to start a focus session", 
                                    font=("Arial", 10))
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        
        # Update the display of today's sessions
        self.update_session_display()

    def create_stats_tab(self):
        """Create the stats and badges tab content"""
        # Configure grid weights
        self.stats_tab.columnconfigure(0, weight=1)
        self.stats_tab.columnconfigure(1, weight=1)
        self.stats_tab.rowconfigure(0, weight=0)
        self.stats_tab.rowconfigure(1, weight=1)
        
        # Weekly stats header
        weekly_header = ttk.Frame(self.stats_tab)
        weekly_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 0))
        
        ttk.Label(weekly_header, text="Weekly Focus Summary", 
                font=("Arial", 14, "bold")).pack(side="left", padx=5)
        
        # Weekly summary chart
        self.weekly_frame = ttk.LabelFrame(self.stats_tab, text="Focus Time by Day")
        self.weekly_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        # Create a canvas for the weekly chart
        self.weekly_canvas = tk.Canvas(self.weekly_frame, bg="white", height=300)
        self.weekly_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Badges header
        badges_header = ttk.Frame(self.stats_tab)
        badges_header.grid(row=0, column=1, sticky="ew", padx=15, pady=(15, 0))
        
        ttk.Label(badges_header, text="Your Badges", 
                font=("Arial", 14, "bold")).pack(side="left", padx=5)
        
        # Badges collection
        self.badges_collection = ttk.LabelFrame(self.stats_tab, text="Earned Badges")
        self.badges_collection.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        
        # Create a canvas with scrollbar for badges
        self.badges_canvas_frame = ttk.Frame(self.badges_collection)
        self.badges_canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.badges_canvas_frame.grid_rowconfigure(0, weight=1)
        self.badges_canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.badges_canvas = tk.Canvas(self.badges_canvas_frame, bg="#f9f9f9")
        self.badges_canvas.grid(row=0, column=0, sticky="nsew")
        
        badges_scrollbar = ttk.Scrollbar(self.badges_canvas_frame, orient="vertical", 
                                       command=self.badges_canvas.yview)
        badges_scrollbar.grid(row=0, column=1, sticky="ns")
        self.badges_canvas.configure(yscrollcommand=badges_scrollbar.set)
        
        # Create a frame inside the canvas to hold badges
        self.badges_frame_inner = ttk.Frame(self.badges_canvas)
        self.badges_canvas.create_window((0, 0), window=self.badges_frame_inner, anchor="nw")
        
        # Configure the inner frame
        self.badges_frame_inner.bind("<Configure>", 
                                  lambda e: self.badges_canvas.configure(
                                      scrollregion=self.badges_canvas.bbox("all")))
        
        # Draw weekly stats and badges
        self.draw_weekly_stats()
        self.draw_badges_collection()
        
    def create_journal_tab(self):
        """Create the journal tab content"""
        # Configure grid weights
        self.journal_tab.columnconfigure(0, weight=1)
        self.journal_tab.rowconfigure(0, weight=0)
        self.journal_tab.rowconfigure(1, weight=1)
        self.journal_tab.rowconfigure(2, weight=0)
        
        # Journal header
        journal_header = ttk.Frame(self.journal_tab)
        journal_header.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        
        ttk.Label(journal_header, text="Reflection Journal", 
                font=("Arial", 14, "bold")).pack(side="left", padx=5)
        
        ttk.Button(journal_header, text="New Entry", 
                 command=self.add_journal_entry).pack(side="right", padx=5)
        
        # Journal entries list
        journal_frame = ttk.Frame(self.journal_tab)
        journal_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        journal_frame.columnconfigure(0, weight=1)
        journal_frame.rowconfigure(0, weight=1)
        
        # Create a canvas with scrollbar for journal entries
        self.journal_canvas_frame = ttk.Frame(journal_frame)
        self.journal_canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.journal_canvas_frame.grid_rowconfigure(0, weight=1)
        self.journal_canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.journal_canvas = tk.Canvas(self.journal_canvas_frame, bg="#f9f9f9")
        self.journal_canvas.grid(row=0, column=0, sticky="nsew")
        
        journal_scrollbar = ttk.Scrollbar(self.journal_canvas_frame, orient="vertical", 
                                       command=self.journal_canvas.yview)
        journal_scrollbar.grid(row=0, column=1, sticky="ns")
        self.journal_canvas.configure(yscrollcommand=journal_scrollbar.set)
        
        # Create a frame inside the canvas to hold journal entries
        self.journal_frame_inner = ttk.Frame(self.journal_canvas)
        self.journal_canvas.create_window((0, 0), window=self.journal_frame_inner, anchor="nw")
        
        #