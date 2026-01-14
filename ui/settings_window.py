"""
Da Editor - Settings Window
============================
1a. whisper model management (scan/download/set)
1b. GPU toggle
1c. sounds folder selection
1d. background color/video options
1e. revert deleted videos option
"""

import customtkinter as ctk
from tkinter import filedialog, colorchooser
import os
import threading
import subprocess
import sys

# same pink theme from main app
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


class SettingsWindow(ctk.CTkToplevel):
    """
    settings window - all the config options in one place
    
    1a. whisper section with model management
    1b. audio/video settings
    1c. output settings
    """
    
    def __init__(self, parent, settings, on_save_callback):
        super().__init__(parent)
        
        self.settings = settings.copy()  # work with a copy
        self.on_save = on_save_callback
        
        # 1a. window setup
        self.title("⚙️ Settings")
        self.geometry("600x700")
        self.configure(fg_color=PINK_THEME["bg_dark"])
        
        # 1b. scrollable content
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 2a. create all sections
        self._create_whisper_section()
        self._create_audio_section()
        self._create_video_section()
        self._create_output_section()
        
        # 2b. save button at bottom
        self.save_btn = ctk.CTkButton(
            self,
            text="💾 Save Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._save_and_close
        )
        self.save_btn.pack(pady=15, padx=20, fill="x")
        
        # initial scan for whisper
        self._scan_whisper()
    
    def _create_section_header(self, text):
        """create a styled section header"""
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(20, 10))
        
        ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=PINK_THEME["accent_pink"]
        ).pack(anchor="w")
        
        # divider line
        ctk.CTkFrame(
            frame,
            height=2,
            fg_color=PINK_THEME["accent_pink"]
        ).pack(fill="x", pady=5)
    
    def _create_whisper_section(self):
        """
        1a. whisper model management
        scan for models, download if needed, select which to use
        """
        self._create_section_header("🎤 WHISPER SETTINGS")
        
        # model selection
        model_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        model_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            model_frame,
            text="Model Size:",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.model_var = ctk.StringVar(value=self.settings.get("whisper_model", "base"))
        self.model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            values=["tiny", "base", "small", "medium", "large"],
            variable=self.model_var,
            fg_color=PINK_THEME["accent_pink"],
            button_color=PINK_THEME["accent_pink"],
            button_hover_color=PINK_THEME["accent_pink_hover"]
        )
        self.model_dropdown.grid(row=0, column=1, padx=10, pady=10)
        
        # model status
        self.model_status = ctk.CTkLabel(
            model_frame,
            text="● Checking...",
            font=ctk.CTkFont(size=12),
            text_color=PINK_THEME["warning"]
        )
        self.model_status.grid(row=0, column=2, padx=10, pady=10)
        
        # 1b. scan/download/set buttons
        btn_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        self.scan_btn = ctk.CTkButton(
            btn_frame,
            text="🔍 Scan",
            width=100,
            fg_color=PINK_THEME["bg_light"],
            hover_color=PINK_THEME["bg_medium"],
            command=self._scan_whisper
        )
        self.scan_btn.pack(side="left", padx=5)
        
        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="⬇️ Download",
            width=100,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._download_whisper
        )
        self.download_btn.pack(side="left", padx=5)
        
        # 1c. GPU toggle
        gpu_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        gpu_frame.pack(fill="x", pady=10)
        
        self.gpu_var = ctk.BooleanVar(value=self.settings.get("use_gpu", True))
        self.gpu_check = ctk.CTkCheckBox(
            gpu_frame,
            text="Use GPU (CUDA) for faster transcription",
            variable=self.gpu_var,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"]
        )
        self.gpu_check.pack(padx=15, pady=15)
        
        # gpu status
        self.gpu_status = ctk.CTkLabel(
            gpu_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=PINK_THEME["text_secondary"]
        )
        self.gpu_status.pack(padx=15, pady=(0, 10))
        self._check_gpu()
    
    def _create_audio_section(self):
        """
        2a. sound effects settings
        folder selection, volume control
        """
        self._create_section_header("🔊 AUDIO SETTINGS")
        
        # sounds folder
        folder_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        folder_frame.pack(fill="x", pady=5)
        folder_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            folder_frame,
            text="Sounds Folder:",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.sounds_entry = ctk.CTkEntry(
            folder_frame,
            placeholder_text="Select folder with sound effects..."
        )
        self.sounds_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        if self.settings.get("sounds_folder"):
            self.sounds_entry.insert(0, self.settings["sounds_folder"])
        
        ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=80,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._select_sounds_folder
        ).grid(row=0, column=2, padx=10, pady=10)
        
        # volume slider
        vol_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        vol_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            vol_frame,
            text="Sound Volume:",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.volume_slider = ctk.CTkSlider(
            vol_frame,
            from_=0,
            to=1,
            number_of_steps=20,
            progress_color=PINK_THEME["accent_pink"],
            button_color=PINK_THEME["accent_pink"],
            button_hover_color=PINK_THEME["accent_pink_hover"]
        )
        self.volume_slider.set(self.settings.get("sound_volume", 0.8))
        self.volume_slider.pack(fill="x", padx=15, pady=(0, 15))
    
    def _create_video_section(self):
        """
        3a. video output settings
        background color, seconds per image, etc
        """
        self._create_section_header("🎬 VIDEO SETTINGS")
        
        # background color
        bg_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        bg_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            bg_frame,
            text="Background Color:",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.bg_color = self.settings.get("bg_color", "#FFFFFF")
        self.color_btn = ctk.CTkButton(
            bg_frame,
            text="",
            width=60,
            height=30,
            fg_color=self.bg_color,
            hover_color=self.bg_color,
            command=self._pick_color
        )
        self.color_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # background video option
        ctk.CTkLabel(
            bg_frame,
            text="Background Video:",
            font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, padx=10, pady=10)
        
        self.bg_video_entry = ctk.CTkEntry(
            bg_frame,
            placeholder_text="Optional: Select video for background..."
        )
        self.bg_video_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        bg_frame.grid_columnconfigure(1, weight=1)
        
        if self.settings.get("bg_video"):
            self.bg_video_entry.insert(0, self.settings["bg_video"])
        
        ctk.CTkButton(
            bg_frame,
            text="Browse",
            width=80,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._select_bg_video
        ).grid(row=1, column=2, padx=10, pady=10)
        
        # seconds per image
        timing_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        timing_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            timing_frame,
            text="Seconds Per Image:",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.spi_var = ctk.StringVar(value=str(self.settings.get("seconds_per_image", 4.0)))
        self.spi_entry = ctk.CTkEntry(
            timing_frame,
            textvariable=self.spi_var,
            width=80
        )
        self.spi_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # min images
        ctk.CTkLabel(
            timing_frame,
            text="Minimum Images:",
            font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, padx=10, pady=10)
        
        self.min_img_var = ctk.StringVar(value=str(self.settings.get("min_images", 11)))
        self.min_img_entry = ctk.CTkEntry(
            timing_frame,
            textvariable=self.min_img_var,
            width=80
        )
        self.min_img_entry.grid(row=1, column=1, padx=10, pady=10)
    
    def _create_output_section(self):
        """
        4a. output and revert settings
        """
        self._create_section_header("📁 OUTPUT SETTINGS")
        
        # output folder
        out_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        out_frame.pack(fill="x", pady=5)
        out_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            out_frame,
            text="Output Folder:",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.output_entry = ctk.CTkEntry(out_frame)
        self.output_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        if self.settings.get("output_folder"):
            self.output_entry.insert(0, self.settings["output_folder"])
        
        ctk.CTkButton(
            out_frame,
            text="Browse",
            width=80,
            fg_color=PINK_THEME["accent_pink"],
            hover_color=PINK_THEME["accent_pink_hover"],
            command=self._select_output_folder
        ).grid(row=0, column=2, padx=10, pady=10)
        
        # revert button
        revert_frame = ctk.CTkFrame(self.scroll, fg_color=PINK_THEME["bg_medium"])
        revert_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(
            revert_frame,
            text="🔄 Revert Deleted Videos",
            font=ctk.CTkFont(size=14),
            fg_color=PINK_THEME["warning"],
            hover_color=PINK_THEME["error"],
            text_color=PINK_THEME["bg_dark"],
            command=self._revert_deleted
        ).pack(padx=15, pady=15)
        
        ctk.CTkLabel(
            revert_frame,
            text="Re-download videos that were deleted but links saved in JSON",
            font=ctk.CTkFont(size=11),
            text_color=PINK_THEME["text_secondary"]
        ).pack(padx=15, pady=(0, 10))
    
    def _scan_whisper(self):
        """check if whisper models are installed"""
        self.model_status.configure(text="● Scanning...", text_color=PINK_THEME["warning"])
        
        def scan():
            try:
                import whisper
                model_name = self.model_var.get()
                # check cache directory
                cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
                
                # whisper model files
                model_files = {
                    "tiny": "tiny.pt",
                    "base": "base.pt", 
                    "small": "small.pt",
                    "medium": "medium.pt",
                    "large": "large-v2.pt"
                }
                
                expected = model_files.get(model_name, f"{model_name}.pt")
                path = os.path.join(cache_dir, expected)
                
                if os.path.exists(path):
                    self.after(0, lambda: self.model_status.configure(
                        text="● Installed",
                        text_color=PINK_THEME["success"]
                    ))
                else:
                    self.after(0, lambda: self.model_status.configure(
                        text="● Not Found",
                        text_color=PINK_THEME["error"]
                    ))
            except ImportError:
                self.after(0, lambda: self.model_status.configure(
                    text="● Whisper not installed",
                    text_color=PINK_THEME["error"]
                ))
        
        threading.Thread(target=scan, daemon=True).start()
    
    def _download_whisper(self):
        """download the selected whisper model"""
        model = self.model_var.get()
        self.model_status.configure(text="● Downloading...", text_color=PINK_THEME["warning"])
        
        def download():
            try:
                import whisper
                whisper.load_model(model)
                self.after(0, lambda: self.model_status.configure(
                    text="● Downloaded!",
                    text_color=PINK_THEME["success"]
                ))
            except Exception as e:
                self.after(0, lambda: self.model_status.configure(
                    text=f"● Error: {str(e)[:30]}",
                    text_color=PINK_THEME["error"]
                ))
        
        threading.Thread(target=download, daemon=True).start()
    
    def _check_gpu(self):
        """check if CUDA is available"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                self.gpu_status.configure(text=f"✅ GPU detected: {gpu_name}")
            else:
                self.gpu_status.configure(text="⚠️ No CUDA GPU detected - will use CPU")
        except:
            self.gpu_status.configure(text="⚠️ PyTorch not installed or no GPU")
    
    def _select_sounds_folder(self):
        """select folder with sound effects"""
        folder = filedialog.askdirectory(title="Select Sounds Folder")
        if folder:
            self.sounds_entry.delete(0, "end")
            self.sounds_entry.insert(0, folder)
    
    def _select_bg_video(self):
        """select background video"""
        video = filedialog.askopenfilename(
            title="Select Background Video",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv")]
        )
        if video:
            self.bg_video_entry.delete(0, "end")
            self.bg_video_entry.insert(0, video)
    
    def _select_output_folder(self):
        """select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)
    
    def _pick_color(self):
        """open color picker for background"""
        color = colorchooser.askcolor(
            title="Pick Background Color",
            initialcolor=self.bg_color
        )
        if color[1]:
            self.bg_color = color[1]
            self.color_btn.configure(fg_color=self.bg_color, hover_color=self.bg_color)
    
    def _revert_deleted(self):
        """placeholder for revert functionality"""
        from tkinter import messagebox
        messagebox.showinfo(
            "Revert",
            "This will scan all job folders and re-download videos\n"
            "that have links in JSON but no downloaded file.\n\n"
            "Feature coming soon!"
        )
    
    def _save_and_close(self):
        """gather all settings and save"""
        self.settings["whisper_model"] = self.model_var.get()
        self.settings["use_gpu"] = self.gpu_var.get()
        self.settings["sounds_folder"] = self.sounds_entry.get()
        self.settings["sound_volume"] = self.volume_slider.get()
        self.settings["bg_color"] = self.bg_color
        self.settings["bg_video"] = self.bg_video_entry.get()
        self.settings["output_folder"] = self.output_entry.get()
        
        try:
            self.settings["seconds_per_image"] = float(self.spi_var.get())
        except:
            self.settings["seconds_per_image"] = 4.0
        
        try:
            self.settings["min_images"] = int(self.min_img_var.get())
        except:
            self.settings["min_images"] = 11
        
        # callback to main app
        if self.on_save:
            self.on_save(self.settings)
        
        self.destroy()
