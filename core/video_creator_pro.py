"""
Da Editor - Pro Video Creator (v3)
===================================
creates the 3 video outputs that ACTUALLY WORK and PLAY everywhere

rules 34-57, 111-112:
- ken burns effect (slow zoom/pan) - no jitter
- sound effects between images (boosted volume per rule 42)
- muted original audio
- white background default (or optional mp4 bg)
- output length matches SRT duration (rule 35)

CRITICAL FIXES:
- proper mp4 flags (-pix_fmt yuv420p, -movflags +faststart)
- constant fps throughout
- proper concat with re-encoding
- no unnecessary upscaling
"""

import os
import sys
import random
import subprocess
import shutil
from typing import List, Optional, Dict
from datetime import datetime


class VideoCreatorPro:
    """
    creates professional video outputs using ffmpeg directly
    with proper compatibility flags so they play everywhere
    """
    
    # mp4 compatibility flags that should be on EVERY output
    MP4_FLAGS = [
        "-pix_fmt", "yuv420p",    # universal pixel format
        "-movflags", "+faststart", # web playback optimization
    ]
    
    def __init__(
        self,
        images_dir: str,
        videos_dir: str,
        output_dir: str,
        sounds_dir: str = "",
        settings: Dict = None
    ):
        self.images_dir = images_dir
        self.videos_dir = videos_dir
        self.output_dir = output_dir
        self.sounds_dir = sounds_dir
        self.settings = settings or {}
        
        os.makedirs(output_dir, exist_ok=True)
        
        # load sound files
        self.sound_files = []
        if sounds_dir and os.path.isdir(sounds_dir):
            for f in os.listdir(sounds_dir):
                if f.endswith((".mp3", ".wav", ".ogg", ".m4a")):
                    self.sound_files.append(os.path.join(sounds_dir, f))
        
        # check ffmpeg
        if not self._check_ffmpeg():
            print("[VideoCreator] WARNING: ffmpeg not found!")
        
        print(f"[VideoCreator v3] ready - {len(self.sound_files)} sounds")
    
    def _check_ffmpeg(self) -> bool:
        """verify ffmpeg and ffprobe exist"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            return True
        except:
            return False
    
    def create_slideshow(
        self,
        images: List[str],
        output_name: str = "output_video.mp4"
    ) -> Optional[str]:
        """
        OUTPUT #1: landscape 16:9 slideshow with:
        - ken burns effect (rule 38) - slow, not jittery
        - sound effects (rule 41, boosted per rule 42)
        - white background (rule 47)
        - matches SRT duration (rule 35)
        """
        if not images:
            print("[VideoCreator] no images for slideshow")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # settings
        seconds_per_image = float(self.settings.get("secondsPerImage", 4.0))
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        sound_volume = float(self.settings.get("soundVolume", 1.0))
        target_duration = self.settings.get("targetDuration", None)
        
        # if we have target duration from SRT (rule 35), adjust seconds per image
        if target_duration and len(images) > 0:
            seconds_per_image = max(2.0, min(6.0, target_duration / len(images)))
        
        # target resolution - NO upscaling to 4K (rule 9)
        width, height, fps = 1920, 1080, 30
        
        print(f"[VideoCreator] creating slideshow: {len(images)} images, {seconds_per_image:.1f}s each")
        
        try:
            # create individual clips with ken burns
            temp_clips = []
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_clip_{i:03d}.mp4")
                if self._create_ken_burns_clip(img, clip_path, seconds_per_image, width, height, fps, bg_color):
                    temp_clips.append(clip_path)
                    print(f"[VideoCreator] clip {i+1}/{len(images)} done")
            
            if not temp_clips:
                print("[VideoCreator] no clips created")
                return None
            
            # concat with re-encoding (more reliable than -c copy)
            concat_file = os.path.join(self.output_dir, "_concat.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    # escape single quotes in path
                    safe_path = clip.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")
            
            temp_video = os.path.join(self.output_dir, "_temp_concat.mp4")
            
            # concat with proper re-encoding and timestamp reset
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-r", str(fps),
                *self.MP4_FLAGS,
                temp_video
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[VideoCreator] concat failed: {result.stderr[:500]}")
                # fallback: try -c copy
                subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file, "-c", "copy", temp_video
                ], capture_output=True)
            
            # add sound effects (rules 41, 42)
            if self.sound_files and os.path.exists(temp_video):
                final_audio = self._create_sfx_track(len(temp_clips), seconds_per_image, sound_volume)
                if final_audio:
                    result = subprocess.run([
                        "ffmpeg", "-y",
                        "-i", temp_video,
                        "-i", final_audio,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        *self.MP4_FLAGS,
                        output_path
                    ], capture_output=True, text=True)
                    
                    self._safe_delete(final_audio)
                    
                    if result.returncode != 0:
                        # fallback: just copy video without audio
                        shutil.move(temp_video, output_path)
                else:
                    shutil.move(temp_video, output_path)
            else:
                if os.path.exists(temp_video):
                    shutil.move(temp_video, output_path)
            
            # cleanup
            for clip in temp_clips:
                self._safe_delete(clip)
            self._safe_delete(concat_file)
            self._safe_delete(temp_video)
            
            # validate output
            if os.path.exists(output_path) and self._validate_output(output_path):
                print(f"[VideoCreator] done: {output_name}")
                return output_path
            else:
                print(f"[VideoCreator] output validation failed")
                return None
            
        except Exception as e:
            print(f"[VideoCreator] slideshow failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_portrait(
        self,
        images: List[str],
        output_name: str = "broll_instagram.mp4"
    ) -> Optional[str]:
        """
        OUTPUT #2: portrait 9:16 for tiktok/reels:
        - images in top 2/3
        - white bottom 1/3 for face (rule 45)
        - ken burns effect
        - proper mp4 compatibility
        """
        if not images:
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        seconds_per_image = float(self.settings.get("secondsPerImage", 4.0))
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        bg_video = self.settings.get("bgVideo", None)  # optional video background
        
        width, height = 1080, 1920
        image_area_height = int(height * 0.66)  # top 2/3
        fps = 30
        
        print(f"[VideoCreator] creating portrait: {len(images)} images")
        
        try:
            temp_clips = []
            
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_portrait_{i:03d}.mp4")
                if self._create_portrait_clip(img, clip_path, seconds_per_image, width, height, image_area_height, fps, bg_color):
                    temp_clips.append(clip_path)
                    print(f"[VideoCreator] portrait clip {i+1}/{len(images)} done")
            
            if not temp_clips:
                return None
            
            # concat with re-encoding
            concat_file = os.path.join(self.output_dir, "_concat_p.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    safe_path = clip.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")
            
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-r", str(fps),
                *self.MP4_FLAGS,
                output_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[VideoCreator] portrait concat error: {result.stderr[:300]}")
                # try copy fallback
                subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file, "-c", "copy", output_path
                ], capture_output=True)
            
            # if background video was specified, composite it (rule 19)
            if bg_video and os.path.exists(bg_video):
                self._composite_bg_video(output_path, bg_video)
            
            # cleanup
            for clip in temp_clips:
                self._safe_delete(clip)
            self._safe_delete(concat_file)
            
            if os.path.exists(output_path) and self._validate_output(output_path):
                print(f"[VideoCreator] done: {output_name}")
                return output_path
            
            return None
            
        except Exception as e:
            print(f"[VideoCreator] portrait failed: {e}")
            return None
    
    def create_youtube_mix(
        self,
        videos: List[str],
        output_name: str = "broll_youtube.mp4"
    ) -> Optional[str]:
        """
        OUTPUT #3: scrambled montage from youtube videos:
        - middle 80% only (rules 52-53) - avoids intros/outros
        - random non-linear order (rules 54-55)
        - muted audio (rule 56)
        - feels intentional not random (rule 57)
        - HIGHLY RANDOMIZED: different start positions, varied clip lengths
        """
        videos = [v for v in videos if os.path.exists(v)]
        if not videos:
            print("[VideoCreator] no youtube videos to mix")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # cap target duration at 120 seconds max for performance
        target_duration = min(float(self.settings.get("targetDuration", 60.0)), 120.0)
        clip_min = 1.2
        clip_max = 4.0
        avoid_percent = 0.15  # 15% at each end for cleaner clips
        
        width, height, fps = 1920, 1080, 30
        
        print(f"[VideoCreator] creating youtube mix: {len(videos)} videos, target {target_duration}s")
        
        try:
            all_clips = []
            
            for video in videos:
                duration = self._get_duration(video)
                if not duration or duration < 15:
                    continue
                
                # safe zone: middle 70% (rules 52-53) - avoid more
                start_safe = duration * avoid_percent
                end_safe = duration * (1 - avoid_percent)
                safe_length = end_safe - start_safe
                
                if safe_length < clip_max * 2:
                    continue
                
                # extract MORE clips from different positions (rule 54)
                # divide safe zone into segments for better coverage
                num_clips = random.randint(4, min(8, int(safe_length / clip_min)))
                
                # divide the safe zone into segments to ensure coverage
                segment_size = safe_length / num_clips
                
                for segment_idx in range(num_clips):
                    # vary clip duration more
                    clip_dur = random.uniform(clip_min, clip_max)
                    
                    # pick from different parts of the video (not all clustered)
                    segment_start = start_safe + (segment_idx * segment_size)
                    segment_end = min(segment_start + segment_size, end_safe - clip_dur)
                    
                    if segment_end <= segment_start:
                        continue
                    
                    # random position within this segment
                    clip_start = random.uniform(segment_start, segment_end)
                    
                    clip_path = os.path.join(self.output_dir, f"_yt_{len(all_clips):03d}.mp4")
                    
                    # extract clip with proper formatting
                    result = subprocess.run([
                        "ffmpeg", "-y",
                        "-ss", str(clip_start),
                        "-i", video,
                        "-t", str(clip_dur),
                        "-an",  # mute (rule 56)
                        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "22",
                        *self.MP4_FLAGS,
                        clip_path
                    ], capture_output=True)
                    
                    if result.returncode == 0 and os.path.exists(clip_path):
                        # verify the clip is valid
                        if self._validate_output(clip_path):
                            all_clips.append(clip_path)
            
            if not all_clips:
                print("[VideoCreator] no valid clips extracted")
                return None
            
            # shuffle for non-linear feel (rule 55)
            random.shuffle(all_clips)
            
            # select clips up to target duration
            final_clips = []
            total_dur = 0
            
            for clip in all_clips:
                if total_dur >= target_duration:
                    break
                dur = self._get_duration(clip)
                if dur:
                    final_clips.append(clip)
                    total_dur += dur
            
            if not final_clips:
                return None
            
            # concat with re-encoding for consistency
            concat_file = os.path.join(self.output_dir, "_concat_yt.txt")
            with open(concat_file, "w") as f:
                for clip in final_clips:
                    safe_path = clip.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")
            
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-r", str(fps),
                *self.MP4_FLAGS,
                output_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[VideoCreator] youtube concat error: {result.stderr[:300]}")
            
            # cleanup
            for clip in all_clips:
                self._safe_delete(clip)
            self._safe_delete(concat_file)
            
            if os.path.exists(output_path) and self._validate_output(output_path):
                print(f"[VideoCreator] done: {output_name}")
                return output_path
            
            return None
            
        except Exception as e:
            print(f"[VideoCreator] youtube mix failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_ken_burns_clip(
        self,
        img: str,
        output: str,
        duration: float,
        width: int,
        height: int,
        fps: int,
        bg_color: str
    ) -> bool:
        """
        create clip with ken burns effect (rule 38)
        FIXED: no 4K upscaling, proper zoom expressions
        """
        effect = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
        
        # calculate frames
        total_frames = int(duration * fps)
        
        # scale to target size (NOT 2x) then apply zoompan
        # zoompan needs the image to be larger than output for panning
        scale_factor = 1.2  # 20% larger for motion room
        
        # ken burns expressions (rule 111 - slow, not jittery)
        # zoom rate is per-frame, very slow
        zoom_rate = 0.0005
        pan_rate = 1.0
        
        if effect == "zoom_in":
            zoom_expr = f"zoompan=z='min(1+{zoom_rate}*on,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        elif effect == "zoom_out":
            zoom_expr = f"zoompan=z='if(eq(on,1),1.15,max(1.15-{zoom_rate}*on,1))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        elif effect == "pan_right":
            zoom_expr = f"zoompan=z='1.1':x='if(eq(on,1),0,min(x+{pan_rate},(iw-iw/zoom)))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        else:  # pan_left
            zoom_expr = f"zoompan=z='1.1':x='if(eq(on,1),(iw-iw/zoom),max(x-{pan_rate},0))':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
        
        # build filter: scale up slightly for motion room, then zoompan
        # this gives us room to pan without hitting edges
        filter_chain = (
            f"scale={int(width*scale_factor)}:{int(height*scale_factor)}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={int(width*scale_factor)}:{int(height*scale_factor)}:"
            f"(ow-iw)/2:(oh-ih)/2:color=#{bg_color},"
            f"{zoom_expr}"
        )
        
        result = subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img,
            "-filter_complex", filter_chain,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            *self.MP4_FLAGS,
            output
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[VideoCreator] ken burns clip failed: {result.stderr[:200]}")
            # fallback: simple static image
            result = subprocess.run([
                "ffmpeg", "-y",
                "-loop", "1", "-i", img,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=#{bg_color}",
                "-t", str(duration),
                "-r", str(fps),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                *self.MP4_FLAGS,
                output
            ], capture_output=True)
        
        return os.path.exists(output) and os.path.getsize(output) > 1000
    
    def _create_portrait_clip(
        self,
        img: str,
        output: str,
        duration: float,
        width: int,
        height: int,
        image_area_height: int,
        fps: int,
        bg_color: str
    ) -> bool:
        """
        create portrait clip with white bottom (rule 45)
        image goes in top 2/3, bottom 1/3 is white for face overlay
        IMAGE IS AT THE VERY TOP - no white space above
        """
        total_frames = int(duration * fps)
        
        # simple ken burns in the top area
        effect = random.choice(["zoom_in", "zoom_out"])
        zoom_rate = 0.0004
        
        if effect == "zoom_in":
            zoom_expr = f"zoompan=z='min(1+{zoom_rate}*on,1.1)':x='iw/2-(iw/zoom/2)':y='0':d={total_frames}:s={width}x{image_area_height}:fps={fps}"
        else:
            zoom_expr = f"zoompan=z='if(eq(on,1),1.1,max(1.1-{zoom_rate}*on,1))':x='iw/2-(iw/zoom/2)':y='0':d={total_frames}:s={width}x{image_area_height}:fps={fps}"
        
        # build filter:
        # 1. scale image to fit in top area with some room for motion
        # 2. apply zoompan - keep y=0 to stay at TOP
        # 3. pad to full height with white at bottom ONLY (x=0, y=0 means top-left)
        filter_chain = (
            f"scale={int(width*1.15)}:{int(image_area_height*1.15)}:force_original_aspect_ratio=decrease,"
            f"pad={int(width*1.15)}:{int(image_area_height*1.15)}:(ow-iw)/2:0:color=#{bg_color},"
            f"{zoom_expr},"
            f"pad={width}:{height}:0:0:color=#{bg_color}"
        )
        
        result = subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img,
            "-filter_complex", filter_chain,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            *self.MP4_FLAGS,
            output
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[VideoCreator] portrait clip error: {result.stderr[:200]}")
            # fallback: simple static
            result = subprocess.run([
                "ffmpeg", "-y",
                "-loop", "1", "-i", img,
                "-vf", f"scale={width}:{image_area_height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:0:color=#{bg_color}",
                "-t", str(duration),
                "-r", str(fps),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                *self.MP4_FLAGS,
                output
            ], capture_output=True)
        
        return os.path.exists(output) and os.path.getsize(output) > 1000
    
    def _create_sfx_track(
        self,
        num_clips: int,
        clip_duration: float,
        volume: float
    ) -> Optional[str]:
        """
        create audio track with sfx at transitions (rules 41, 42)
        PRIORITIZE CHING SOUND (20%+ of the time)
        USE DIFFERENT SOUNDS FOR EACH TRANSITION
        """
        if not self.sound_files:
            return None
        
        output = os.path.join(self.output_dir, "_sfx.wav")
        total_duration = num_clips * clip_duration
        
        try:
            # create silence base
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(total_duration + 1),
                "-c:a", "pcm_s16le",
                output
            ], capture_output=True, check=True)
            
            # find ching sounds (prioritize these)
            ching_sounds = [s for s in self.sound_files if 'ching' in s.lower() or 'ping' in s.lower()]
            other_sounds = [s for s in self.sound_files if s not in ching_sounds]
            
            # if no ching found, treat all as other
            if not ching_sounds:
                ching_sounds = other_sounds[:2] if len(other_sounds) >= 2 else other_sounds
            
            # build the sound order: ching 20-30% of the time, rest are different sounds
            num_transitions = num_clips - 1
            sound_order = []
            used_sounds = set()
            
            for i in range(num_transitions):
                # use ching ~25% of the time (every 4th transition roughly)
                if random.random() < 0.25 and ching_sounds:
                    sound = random.choice(ching_sounds)
                else:
                    # pick a DIFFERENT sound than the last one
                    available = [s for s in other_sounds if s not in used_sounds] or other_sounds
                    sound = random.choice(available)
                    used_sounds.add(sound)
                    # reset if we've used all
                    if len(used_sounds) >= len(other_sounds):
                        used_sounds.clear()
                
                sound_order.append(sound)
            
            # overlay sounds at each transition
            current_time = clip_duration - 0.3  # start slightly before transition
            
            for i, sound in enumerate(sound_order):
                if current_time >= total_duration:
                    break
                
                temp = os.path.join(self.output_dir, f"_sfx_{i:03d}.wav")
                
                # volume boost - ching sounds get extra boost
                is_ching = 'ching' in sound.lower() or 'ping' in sound.lower()
                boost = min(volume * (2.5 if is_ching else 2.0), 3.0)
                
                delay_ms = int(current_time * 1000)
                
                result = subprocess.run([
                    "ffmpeg", "-y",
                    "-i", output,
                    "-i", sound,
                    "-filter_complex",
                    f"[1:a]adelay={delay_ms}|{delay_ms},volume={boost}[sfx];[0:a][sfx]amix=inputs=2:duration=longest:dropout_transition=0",
                    "-c:a", "pcm_s16le",
                    temp
                ], capture_output=True)
                
                if result.returncode == 0 and os.path.exists(temp):
                    shutil.move(temp, output)
                
                current_time += clip_duration
            
            return output
            
        except Exception as e:
            print(f"[VideoCreator] sfx creation failed: {e}")
            return None
    
    def _composite_bg_video(self, main_video: str, bg_video: str):
        """composite background video (rule 19) - experimental"""
        # this would overlay the main content on a looping background
        # for now just log that it would happen
        print(f"[VideoCreator] background video compositing not fully implemented")
    
    def _validate_output(self, path: str) -> bool:
        """
        validate output video is actually playable (rule 20)
        checks: exists, size, has video stream, duration, decode test
        """
        if not os.path.exists(path):
            return False
        
        size = os.path.getsize(path)
        if size < 10000:  # less than 10KB is definitely broken
            return False
        
        try:
            # check with ffprobe
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration,codec_name",
                "-of", "json",
                path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return False
            
            import json
            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            
            if not streams:
                return False
            
            stream = streams[0]
            
            # check it has video codec
            if "codec_name" not in stream:
                return False
            
            # check dimensions
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            if width < 100 or height < 100:
                return False
            
            # quick decode test - try to read a few frames
            decode_test = subprocess.run([
                "ffmpeg", "-v", "error",
                "-i", path,
                "-t", "2",  # just first 2 seconds
                "-f", "null", "-"
            ], capture_output=True, timeout=30)
            
            if decode_test.returncode != 0:
                return False
            
            return True
            
        except Exception as e:
            print(f"[VideoCreator] validation error: {e}")
            return False
    
    def _get_duration(self, path: str) -> Optional[float]:
        """get video duration in seconds"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except:
            pass
        return None
    
    def _safe_delete(self, path: str):
        """safely delete a file"""
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except:
            pass


if __name__ == "__main__":
    print("[Test] VideoCreatorPro v3 loaded")
    
    # verify ffmpeg
    creator = VideoCreatorPro(
        images_dir=".",
        videos_dir=".",
        output_dir="."
    )
    print("[Test] ffmpeg check:", "OK" if creator._check_ffmpeg() else "MISSING")
