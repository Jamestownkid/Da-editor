"""
Da Editor - Pro Video Creator (v2)
===================================
creates the 3 video outputs that actually work

rules 34-57, 111-112:
- ken burns effect (slow zoom/pan)
- sound effects between images (boosted volume per rule 42)
- muted original audio
- white background default
- output length matches SRT duration (rule 35)
"""

import os
import sys
import random
import subprocess
from typing import List, Optional, Dict
from datetime import datetime


class VideoCreatorPro:
    """
    creates professional video outputs using ffmpeg directly
    more reliable than moviepy fr
    """
    
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
        
        print(f"[VideoCreator] ready - {len(self.sound_files)} sounds")
    
    def create_slideshow(
        self,
        images: List[str],
        output_name: str = "output_video.mp4"
    ) -> Optional[str]:
        """
        create landscape 16:9 slideshow with:
        - ken burns effect (rule 38)
        - sound effects (rule 41, boosted per rule 42)
        - white background (rule 47)
        - matches SRT duration (rule 35)
        """
        if not images:
            print("[VideoCreator] no images")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # settings
        seconds_per_image = self.settings.get("secondsPerImage", 4.0)
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        sound_volume = self.settings.get("soundVolume", 1.0)  # rule 42 - boosted
        target_duration = self.settings.get("targetDuration", None)
        
        # if we have target duration from SRT (rule 35), adjust seconds per image
        if target_duration and len(images) > 0:
            seconds_per_image = max(2.0, target_duration / len(images))
        
        width, height, fps = 1920, 1080, 30
        
        print(f"[VideoCreator] creating slideshow: {len(images)} images, {seconds_per_image}s each")
        
        try:
            # create individual clips with ken burns
            temp_clips = []
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_clip_{i}.mp4")
                if self._create_ken_burns_clip(img, clip_path, seconds_per_image, width, height, fps, bg_color):
                    temp_clips.append(clip_path)
            
            if not temp_clips:
                print("[VideoCreator] no clips created")
                return None
            
            # concat clips
            concat_file = os.path.join(self.output_dir, "_concat.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")
            
            temp_video = os.path.join(self.output_dir, "_temp.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", temp_video
            ], capture_output=True, check=True)
            
            # add sound effects (rules 41, 42)
            if self.sound_files:
                final_audio = self._create_sfx_track(len(temp_clips), seconds_per_image, sound_volume)
                if final_audio:
                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", temp_video,
                        "-i", final_audio,
                        "-c:v", "copy", "-c:a", "aac",
                        "-shortest", output_path
                    ], capture_output=True, check=True)
                    os.unlink(final_audio)
                else:
                    os.rename(temp_video, output_path)
            else:
                os.rename(temp_video, output_path)
            
            # cleanup
            for clip in temp_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            for f in [concat_file, temp_video]:
                if os.path.exists(f):
                    os.unlink(f)
            
            print(f"[VideoCreator] done: {output_name}")
            return output_path
            
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
        create portrait 9:16 for tiktok/reels:
        - images in top 2/3
        - white bottom 1/3 for face (rule 45)
        - ken burns effect
        """
        if not images:
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        seconds_per_image = self.settings.get("secondsPerImage", 4.0)
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        
        width, height = 1080, 1920
        image_height = int(height * 0.66)  # top 2/3
        fps = 30
        
        print(f"[VideoCreator] creating portrait: {len(images)} images")
        
        try:
            temp_clips = []
            
            for i, img in enumerate(images):
                if not os.path.exists(img):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_portrait_{i}.mp4")
                if self._create_portrait_clip(img, clip_path, seconds_per_image, width, height, image_height, fps, bg_color):
                    temp_clips.append(clip_path)
            
            if not temp_clips:
                return None
            
            # concat
            concat_file = os.path.join(self.output_dir, "_concat_p.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")
            
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", output_path
            ], capture_output=True, check=True)
            
            # cleanup
            for clip in temp_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            if os.path.exists(concat_file):
                os.unlink(concat_file)
            
            print(f"[VideoCreator] done: {output_name}")
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] portrait failed: {e}")
            return None
    
    def create_youtube_mix(
        self,
        videos: List[str],
        output_name: str = "broll_youtube.mp4"
    ) -> Optional[str]:
        """
        create scrambled montage from youtube videos:
        - middle 80% only (rules 52-53)
        - random non-linear order (rules 54-55)
        - muted audio (rule 56)
        """
        videos = [v for v in videos if os.path.exists(v)]
        if not videos:
            print("[VideoCreator] no youtube videos")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        target_duration = self.settings.get("targetDuration", 60.0)
        max_clip = 3.0
        avoid = 0.10  # 10% at each end
        
        print(f"[VideoCreator] creating youtube mix: {len(videos)} videos")
        
        try:
            all_clips = []
            
            for video in videos:
                duration = self._get_duration(video)
                if not duration or duration < 10:
                    continue
                
                # safe zone: middle 80% (rules 52-53)
                start_safe = duration * avoid
                end_safe = duration * (1 - avoid)
                
                if end_safe - start_safe < max_clip * 2:
                    continue
                
                # extract 3-5 random clips (rule 54)
                for _ in range(random.randint(3, 5)):
                    clip_start = random.uniform(start_safe, end_safe - max_clip)
                    clip_dur = random.uniform(1.5, max_clip)
                    
                    clip_path = os.path.join(self.output_dir, f"_yt_{len(all_clips)}.mp4")
                    
                    result = subprocess.run([
                        "ffmpeg", "-y",
                        "-ss", str(clip_start),
                        "-i", video,
                        "-t", str(clip_dur),
                        "-an",  # mute (rule 56)
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        clip_path
                    ], capture_output=True)
                    
                    if result.returncode == 0 and os.path.exists(clip_path):
                        all_clips.append(clip_path)
            
            if not all_clips:
                return None
            
            # shuffle (rule 55 - non-linear)
            random.shuffle(all_clips)
            
            # take up to target duration
            final_clips = []
            total = 0
            for clip in all_clips:
                if total >= target_duration:
                    break
                dur = self._get_duration(clip)
                if dur:
                    final_clips.append(clip)
                    total += dur
            
            if not final_clips:
                return None
            
            # concat
            concat_file = os.path.join(self.output_dir, "_concat_yt.txt")
            with open(concat_file, "w") as f:
                for clip in final_clips:
                    f.write(f"file '{clip}'\n")
            
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", output_path
            ], capture_output=True, check=True)
            
            # cleanup
            for clip in all_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            if os.path.exists(concat_file):
                os.unlink(concat_file)
            
            print(f"[VideoCreator] done: {output_name}")
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] youtube mix failed: {e}")
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
        """create clip with ken burns effect (rule 38)"""
        effect = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
        
        # base filter
        base = f"scale={width*2}:{height*2}:force_original_aspect_ratio=decrease,pad={width*2}:{height*2}:(ow-iw)/2:(oh-ih)/2:color=#{bg_color}"
        
        # ken burns expressions (rule 111 - slow, not jittery)
        if effect == "zoom_in":
            zoom = f"zoompan=z='min(zoom+0.001,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        elif effect == "zoom_out":
            zoom = f"zoompan=z='if(eq(on,1),1.15,max(zoom-0.001,1))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        elif effect == "pan_right":
            zoom = f"zoompan=z='1.1':x='if(eq(on,1),0,min(x+1.5,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        else:
            zoom = f"zoompan=z='1.1':x='if(eq(on,1),iw-iw/zoom,max(x-1.5,0))':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        
        result = subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", img,
            "-filter_complex", f"{base},{zoom}",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output
        ], capture_output=True)
        
        return result.returncode == 0
    
    def _create_portrait_clip(
        self,
        img: str,
        output: str,
        duration: float,
        width: int,
        height: int,
        image_height: int,
        fps: int,
        bg_color: str
    ) -> bool:
        """create portrait clip with white bottom"""
        # scale image to fit top portion, white background (rule 46)
        result = subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", img,
            "-vf", f"scale={width}:{image_height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:0:color=#{bg_color}",
            "-t", str(duration),
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output
        ], capture_output=True)
        
        return result.returncode == 0
    
    def _create_sfx_track(
        self,
        num_clips: int,
        clip_duration: float,
        volume: float
    ) -> Optional[str]:
        """create audio track with sfx (rules 41, 42)"""
        if not self.sound_files:
            return None
        
        output = os.path.join(self.output_dir, "_sfx.mp3")
        total_duration = num_clips * clip_duration
        
        try:
            # create silence base
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(total_duration),
                "-c:a", "libmp3lame", "-q:a", "2",
                output
            ], capture_output=True, check=True)
            
            # overlay sounds at transitions (rule 41: ping -> image -> ping)
            current_time = clip_duration
            sounds = random.sample(self.sound_files, min(len(self.sound_files), 5))
            
            for i in range(num_clips - 1):
                sound = random.choice(sounds)
                temp = os.path.join(self.output_dir, f"_sfx_{i}.mp3")
                
                # volume boost (rule 42)
                boost = min(volume * 1.5, 2.0)
                
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", output,
                    "-i", sound,
                    "-filter_complex",
                    f"[1:a]adelay={int(current_time*1000)}|{int(current_time*1000)},volume={boost}[sfx];[0:a][sfx]amix=inputs=2:duration=longest",
                    "-c:a", "libmp3lame", "-q:a", "2",
                    temp
                ], capture_output=True)
                
                if os.path.exists(temp):
                    os.replace(temp, output)
                
                current_time += clip_duration
            
            return output
            
        except Exception as e:
            print(f"[VideoCreator] sfx failed: {e}")
            return None
    
    def _get_duration(self, path: str) -> Optional[float]:
        """get video duration"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        return None


if __name__ == "__main__":
    print("[Test] VideoCreatorPro ready")
