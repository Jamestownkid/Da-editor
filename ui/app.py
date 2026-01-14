"""
Da Editor - Main App UI
========================
1a. pink themed customtkinter app
1b. sidebar for jobs, main area for links
1c. settings panel, error box, the whole nine
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import threading
from datetime import datetime

# 1a. set up the pink vibes globally
ctk.set_appearance_mode("dark")

# 1b. custom pink color theme - we ball different
PINK_THEME = {
    "bg_dark": "#1a1a2e",
    "bg_medium": "#16213e", 
    "bg_light": "#0f3460",
    "accent_pink": "#e94560",
    "accent_pink_hover": "#ff6b6b",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "success": "#4ecca3",
    "error": "#ff6b6b",
    "warning": "#feca57"
}


class DaEditorApp(ctk.CTk):
    """
    main app window - this is the whole gui right here
    
    1a. left sidebar with jobs
    1b. center area for links
    1c. settings accessible via button
    """
    
    def __init__(self):
        super().__init__()
        
        # 1a. window setup
        self.title("Da Editor - B-Roll Automation")
        self.geometry("1400x800")
        self.minsize(1200, 700)
        
        # 1b. configure the pink theme colors
        self.configure(fg_color=PINK_THEME["bg_dark"])
        
        # 1c. state variables
        self.jobs = []  # list of all jobs
        self.current_job = None
        self.output_folder = os.path.expanduser("~/DaEditor_Output")
        self.settings = self._load_settings()
        self.error_log = []
        
        # 2a. set up the grid layout
        self.grid_columnconfigure(0, weight=0)  # sidebar fixed
        self.grid_columnconfigure(1, weight=1)  # main area expands
        self.grid_rowconfigure(0, weight=1)
        
        # 2b. create all the ui components
        self._create_sidebar()
        self._create_main_area()
        self._create_top_bar()
        
        # 2c. load any existing jobs
        self._scan_for_jobs()
        
        print("[UI] app initialized - we ready to rock")
    
    def _load_settings(self):
        """
        load settings from json or return defaults
        keeping it simple fr
        """
        settings_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
        defaults = {
            "whisper_model": "base",
            "whisper_path": "",
            "sounds_folder": "",
            "use_gpu": True,
            "bg_color": "#FFFFFF",
            "bg_video": "",
            "seconds_per_image": 4.0,
            "sound_volume": 0.8,
            "min_images": 11,
            "output_folder": os.path.expanduser("~/DaEditor_Output")
        }
        
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
        except Exception as e:
            print(f"[Settings] couldn't load settings: {e}")
        
        return defaults
    
    def _save_settings(self):
        """save current settings to json"""
        settings_path = os.path.join(os.path.dirname(__file__), "..", "settings.json")
        try:
            with open(settings_path, "w") as f:
                json.dump(self.settings, f, indent=2)
            print("[Settings] saved successfully")
        except Exception as e:
            self._log_error(f"Failed to save settings: {e}")
    
    def _log_error(self, msg):
        """add error to the log so user can see it"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.error_log.append(f"[{timestamp}] {msg}")
        print(f"[ERROR] {msg}")
        # update error display if it exists
        if hasattr(self, "error_text"):
            self.error_text.configure(state="normal")
            self.error_text.insert("end", f"[{timestamp}] {msg}\n")
            self.error_text.configure(state="disabled")
            self.error_text.see("end")
    
    def _create_sidebar(self):
        """
        1a. left sidebar with job list
        shows all jobs, their status, resume button etc
        """
        # sidebar frame
        self.sidebar = ctk.CTkFrame(
            self, 
            width=280, 
            corner_radius=0,
            fg_color=PINK_THEME["bg_medium"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # 1b. logo/title at top
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🎬 DA EDITOR",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=PINK_THEME["accent_pink"]
        )
        self.logo_label.pack(pady=20)
        
        # 1c. resume all button
        self.resume_btn = ctk.CTkButton(
            self.sidebar,
            text="▶️ Resume All Jobs",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._resume_all_jobs
        )
        self.resume_btn.pack(pady=10, padx=15, fill="x")
        
        # 2a. jobs list label
        self.jobs_label = ctk.CTkLabel(
            self.sidebar,
            text="JOBS QUEUE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=PINK_THEME["text_secondary"]
        )
        self.jobs_label.pack(pady=(20, 5), padx=15, anchor="w")
        
        # 2b. scrollable frame for jobs
        self.jobs_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=PINK_THEME["accent_pink"]
        )
        self.jobs_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 2c. placeholder for when no jobs
        self.no_jobs_label = ctk.CTkLabel(
            self.jobs_scroll,
            text="No jobs yet\nPaste some links to get started!",
            font=ctk.CTkFont(size=12),
            text_color=PINK_THEME["text_secondary"]
        )
        self.no_jobs_label.pack(pady=50)
    
    def _create_main_area(self):
        """
        1a. main content area
        where user pastes links and sees output options
        """
        # main frame
        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=PINK_THEME["bg_dark"]
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # 1b. folder selection area
        folder_frame = ctk.CTkFrame(self.main_frame, fg_color=PINK_THEME["bg_medium"])
        folder_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(70, 10))
        folder_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            folder_frame,
            text="📁 Output Folder:",
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.folder_entry = ctk.CTkEntry(
            folder_frame,
            placeholder_text="Select output folder...",
            font=ctk.CTkFont(size=13)
        )
        self.folder_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.folder_entry.insert(0, self.output_folder)
        
        self.folder_btn = ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=80,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._select_folder
        )
        self.folder_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # 1c. job name input
        ctk.CTkLabel(
            folder_frame,
            text="📝 Job Name:",
            font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, padx=10, pady=10)
        
        self.job_name_entry = ctk.CTkEntry(
            folder_frame,
            placeholder_text="Enter job name (creates subfolder)...",
            font=ctk.CTkFont(size=13)
        )
        self.job_name_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # 2a. links input area
        links_label = ctk.CTkLabel(
            self.main_frame,
            text="🔗 PASTE LINKS (YouTube, TikTok, Instagram, etc.)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PINK_THEME["text_secondary"]
        )
        links_label.grid(row=1, column=0, sticky="w", padx=25, pady=(15, 5))
        
        # 2b. text area for links
        self.links_text = ctk.CTkTextbox(
            self.main_frame,
            font=ctk.CTkFont(size=13),
            fg_color=PINK_THEME["bg_medium"],
            border_color=PINK_THEME["accent_pink"],
            border_width=2,
            height=200
        )
        self.links_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        
        # 2c. options frame
        options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        options_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        options_frame.grid_columnconfigure(1, weight=1)
        
        # srt toggle
        self.srt_var = ctk.BooleanVar(value=True)
        self.srt_check = ctk.CTkCheckBox(
            options_frame,
            text="Generate SRT from TikTok",
            variable=self.srt_var,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"]
        )
        self.srt_check.grid(row=0, column=0, padx=10, pady=5)
        
        # download videos toggle
        self.download_var = ctk.BooleanVar(value=True)
        self.download_check = ctk.CTkCheckBox(
            options_frame,
            text="Download All Videos",
            variable=self.download_var,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"]
        )
        self.download_check.grid(row=0, column=1, padx=10, pady=5)
        
        # 3a. start button - THE BIG ONE
        self.start_btn = ctk.CTkButton(
            self.main_frame,
            text="🚀 START JOB",
            font=ctk.CTkFont(size=20, weight="bold"),
            height=60,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._start_job
        )
        self.start_btn.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        
        # 3b. error log area
        error_label = ctk.CTkLabel(
            self.main_frame,
            text="📋 ERROR LOG (click to copy)",
            font=ctk.CTkFont(size=12),
            text_color=PINK_THEME["text_secondary"]
        )
        error_label.grid(row=5, column=0, sticky="w", padx=25, pady=(15, 2))
        
        self.error_text = ctk.CTkTextbox(
            self.main_frame,
            font=ctk.CTkFont(size=11),
            fg_color=PINK_THEME["bg_medium"],
            height=100,
            state="disabled"
        )
        self.error_text.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.error_text.bind("<Button-1>", self._copy_errors)
    
    def _create_top_bar(self):
        """
        1a. top bar with dropdown and settings
        floating over the main area
        """
        self.top_bar = ctk.CTkFrame(
            self,
            height=50,
            fg_color=PINK_THEME["bg_medium"],
            corner_radius=10
        )
        self.top_bar.place(relx=0.5, rely=0.01, anchor="n", relwidth=0.7)
        
        # 1b. dropdown menu
        self.menu_var = ctk.StringVar(value="Quick Actions")
        self.menu_dropdown = ctk.CTkOptionMenu(
            self.top_bar,
            values=["Quick Actions", "Scan Jobs", "Clear Queue", "View Output"],
            variable=self.menu_var,
            fg_color=PINK_THEME["accent_pink"],
            button_color=PINK_THEME["accent_pink"],
            button_hover_color=PINK_THEME["accent_pink_hover"],
            command=self._handle_menu
        )
        self.menu_dropdown.pack(side="left", padx=15, pady=10)
        
        # 1c. settings button
        self.settings_btn = ctk.CTkButton(
            self.top_bar,
            text="⚙️ Settings",
            width=100,
            fg_color="transparent",
            border_width=2,
            border_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["bg_light"],
            command=self._open_settings
        )
        self.settings_btn.pack(side="right", padx=15, pady=10)
        
        # 1d. status indicator
        self.status_label = ctk.CTkLabel(
            self.top_bar,
            text="⏸️ Ready",
            font=ctk.CTkFont(size=13),
            text_color=PINK_THEME["success"]
        )
        self.status_label.pack(side="right", padx=20, pady=10)
    
    def _select_folder(self):
        """open folder dialog and update entry"""
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.output_folder
        )
        if folder:
            self.output_folder = folder
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.settings["output_folder"] = folder
            self._save_settings()
    
    def _start_job(self):
        """
        1a. start processing a new job
        this is where we validate, create folder, queue it up
        """
        # get the links
        links_text = self.links_text.get("1.0", "end").strip()
        if not links_text:
            messagebox.showwarning("No Links", "Paste some links first!")
            return
        
        # parse links (one per line)
        links = [l.strip() for l in links_text.split("\n") if l.strip()]
        if not links:
            messagebox.showwarning("No Links", "No valid links found!")
            return
        
        # get job name
        job_name = self.job_name_entry.get().strip()
        if not job_name:
            job_name = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # create job folder
        job_folder = os.path.join(self.output_folder, job_name)
        os.makedirs(job_folder, exist_ok=True)
        
        # 1b. save links to json
        job_data = {
            "id": job_name,
            "created": datetime.now().isoformat(),
            "links": links,
            "generate_srt": self.srt_var.get(),
            "download_videos": self.download_var.get(),
            "status": "queued",
            "progress": 0,
            "outputs": {
                "slideshow": None,
                "portrait": None,
                "youtube_mix": None
            }
        }
        
        json_path = os.path.join(job_folder, "job.json")
        with open(json_path, "w") as f:
            json.dump(job_data, f, indent=2)
        
        # 1c. add to jobs list
        self.jobs.append(job_data)
        self._refresh_jobs_list()
        
        # 2a. CONFETTI TIME - show the user we hyped
        self._show_confetti()
        
        # 2b. clear the input
        self.links_text.delete("1.0", "end")
        self.job_name_entry.delete(0, "end")
        
        # 2c. start processing (in background)
        self._process_next_job()
        
        print(f"[Job] created: {job_name} with {len(links)} links")
    
    def _show_confetti(self):
        """
        show confetti animation when job starts
        just a simple popup for now - can be fancier later
        """
        # create overlay window
        confetti = ctk.CTkToplevel(self)
        confetti.geometry("400x200")
        confetti.title("")
        confetti.overrideredirect(True)
        
        # center it
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        confetti.geometry(f"+{x}+{y}")
        
        confetti.configure(fg_color=PINK_THEME["bg_medium"])
        
        # big text
        label = ctk.CTkLabel(
            confetti,
            text="🎉 JOB STARTED! 🎉",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=PINK_THEME["accent_pink"]
        )
        label.pack(expand=True)
        
        # auto close after 1.5 sec
        confetti.after(1500, confetti.destroy)
    
    def _refresh_jobs_list(self):
        """update the sidebar jobs list"""
        # clear existing
        for widget in self.jobs_scroll.winfo_children():
            widget.destroy()
        
        if not self.jobs:
            self.no_jobs_label = ctk.CTkLabel(
                self.jobs_scroll,
                text="No jobs yet\nPaste some links to get started!",
                font=ctk.CTkFont(size=12),
                text_color=PINK_THEME["text_secondary"]
            )
            self.no_jobs_label.pack(pady=50)
            return
        
        # add job cards
        for job in self.jobs:
            self._create_job_card(job)
    
    def _create_job_card(self, job):
        """create a card widget for a single job"""
        card = ctk.CTkFrame(
            self.jobs_scroll,
            fg_color=PINK_THEME["bg_light"],
            corner_radius=10
        )
        card.pack(fill="x", padx=5, pady=5)
        
        # job name
        name_label = ctk.CTkLabel(
            card,
            text=job.get("id", "Unknown"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PINK_THEME["text_primary"]
        )
        name_label.pack(anchor="w", padx=10, pady=(8, 2))
        
        # status
        status = job.get("status", "unknown")
        status_colors = {
            "queued": PINK_THEME["warning"],
            "processing": PINK_THEME["accent_pink"],
            "done": PINK_THEME["success"],
            "error": PINK_THEME["error"]
        }
        
        status_label = ctk.CTkLabel(
            card,
            text=f"● {status.upper()}",
            font=ctk.CTkFont(size=11),
            text_color=status_colors.get(status, PINK_THEME["text_secondary"])
        )
        status_label.pack(anchor="w", padx=10, pady=(0, 8))
    
    def _scan_for_jobs(self):
        """
        scan the output folder for existing jobs
        this is for the resume functionality
        """
        if not os.path.exists(self.output_folder):
            return
        
        for folder_name in os.listdir(self.output_folder):
            folder_path = os.path.join(self.output_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            json_path = os.path.join(folder_path, "job.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        job_data = json.load(f)
                    self.jobs.append(job_data)
                except Exception as e:
                    print(f"[Scan] failed to load {json_path}: {e}")
        
        self._refresh_jobs_list()
        print(f"[Scan] found {len(self.jobs)} existing jobs")
    
    def _resume_all_jobs(self):
        """resume processing any incomplete jobs"""
        incomplete = [j for j in self.jobs if j.get("status") != "done"]
        if not incomplete:
            messagebox.showinfo("All Done", "No incomplete jobs to resume!")
            return
        
        messagebox.showinfo(
            "Resuming", 
            f"Resuming {len(incomplete)} incomplete job(s)..."
        )
        self._process_next_job()
    
    def _process_next_job(self):
        """
        find next queued job and process it
        runs in background thread
        """
        # find next queued job
        for job in self.jobs:
            if job.get("status") == "queued":
                job["status"] = "processing"
                self._save_job(job)
                self._refresh_jobs_list()
                
                # update status
                self.status_label.configure(
                    text=f"🔄 Processing: {job['id']}",
                    text_color=PINK_THEME["accent_pink"]
                )
                
                # run in thread
                thread = threading.Thread(
                    target=self._run_job_processor,
                    args=(job,),
                    daemon=True
                )
                thread.start()
                return
        
        # no more jobs
        self.status_label.configure(
            text="⏸️ Ready",
            text_color=PINK_THEME["success"]
        )
    
    def _run_job_processor(self, job):
        """
        actual job processing - runs in background
        this is where we call the core modules
        """
        try:
            from core.processor import JobProcessor
            
            processor = JobProcessor(
                job=job,
                output_folder=self.output_folder,
                settings=self.settings,
                on_progress=lambda msg: self._update_status(msg),
                on_error=lambda msg: self._log_error(msg)
            )
            
            processor.run()
            
            job["status"] = "done"
            self._save_job(job)
            
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            self._save_job(job)
            self._log_error(f"Job {job['id']} failed: {e}")
        
        # refresh ui and process next
        self.after(0, self._refresh_jobs_list)
        self.after(100, self._process_next_job)
    
    def _save_job(self, job):
        """save job state to json"""
        job_folder = os.path.join(self.output_folder, job["id"])
        json_path = os.path.join(job_folder, "job.json")
        try:
            with open(json_path, "w") as f:
                json.dump(job, f, indent=2)
        except Exception as e:
            print(f"[Job] failed to save: {e}")
    
    def _update_status(self, msg):
        """update status label from worker thread"""
        self.after(0, lambda: self.status_label.configure(text=f"🔄 {msg}"))
    
    def _copy_errors(self, event=None):
        """copy error log to clipboard"""
        if self.error_log:
            self.clipboard_clear()
            self.clipboard_append("\n".join(self.error_log))
            messagebox.showinfo("Copied", "Error log copied to clipboard!")
    
    def _handle_menu(self, choice):
        """handle dropdown menu selections"""
        if choice == "Scan Jobs":
            self._scan_for_jobs()
            messagebox.showinfo("Scan Complete", f"Found {len(self.jobs)} jobs")
        elif choice == "Clear Queue":
            self.jobs = [j for j in self.jobs if j.get("status") == "done"]
            self._refresh_jobs_list()
        elif choice == "View Output":
            if os.path.exists(self.output_folder):
                os.startfile(self.output_folder) if os.name == 'nt' else os.system(f'xdg-open "{self.output_folder}"')
        
        # reset dropdown
        self.menu_var.set("Quick Actions")
    
    def _open_settings(self):
        """open the settings window"""
        from ui.settings_window import SettingsWindow
        settings_win = SettingsWindow(self, self.settings, self._on_settings_save)
        settings_win.grab_set()
    
    def _on_settings_save(self, new_settings):
        """callback when settings are saved"""
        self.settings.update(new_settings)
        self._save_settings()
        print("[Settings] updated")


if __name__ == "__main__":
    app = DaEditorApp()
    app.mainloop()
