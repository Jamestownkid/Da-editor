"""
Da Editor - Pro Video Creator
===============================
this is where we actually make the 3 video outputs
the most important part of the whole app fr

1a. landscape b-roll slideshow with ken burns + sfx
1b. portrait split (9:16) with white bottom for face
1c. youtube mix - scrambled clips from middle 80%

per spec rules 34-57 and 111-112:
- ken burns effect (slow zoom/pan)
- sound effects between images
- muted original audio
- white background default
"""

import os
import sys
import random
import math
import subprocess
from typing import List, Optional, Dict, Tuple


class VideoCreatorPro:
    """
    creates professional quality video outputs
    uses ffmpeg directly for more control and reliability
    
    the moviepy version kept breaking so we doing it raw with ffmpeg
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
        
        print(f"[VideoCreator] initialized - {len(self.sound_files)} sounds loaded")
    
    def create_slideshow(
        self,
        images: List[str],
        output_name: str = "slideshow.mp4"
    ) -> Optional[str]:
        """
        create landscape 16:9 slideshow with:
        - ken burns effect (zoom/pan)
        - sound effects between images
        - white background
        
        per spec rules 34-42, 47-49, 57
        """
        if not images:
            print("[VideoCreator] no images provided")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # settings
        duration = self.settings.get("secondsPerImage", 4.0)
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        sound_volume = self.settings.get("soundVolume", 0.8)
        
        # dimensions
        width = 1920
        height = 1080
        fps = 30
        
        print(f"[VideoCreator] creating slideshow with {len(images)} images")
        
        try:
            # step 1: create individual clips with ken burns
            temp_clips = []
            for i, img_path in enumerate(images):
                if not os.path.exists(img_path):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_temp_clip_{i}.mp4")
                
                # apply ken burns effect using ffmpeg
                effect = self._create_ken_burns_clip(
                    img_path, clip_path, duration, width, height, fps, bg_color
                )
                
                if effect and os.path.exists(clip_path):
                    temp_clips.append(clip_path)
                else:
                    print(f"[VideoCreator] failed to create clip for image {i}")
            
            if not temp_clips:
                print("[VideoCreator] no clips created")
                return None
            
            # step 2: create concat file
            concat_file = os.path.join(self.output_dir, "_concat.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")
            
            # step 3: concatenate all clips
            temp_video = os.path.join(self.output_dir, "_temp_concat.mp4")
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                temp_video
            ]
            subprocess.run(concat_cmd, capture_output=True, check=True)
            
            # step 4: add sound effects
            if self.sound_files:
                final_audio = self._create_sfx_track(
                    len(temp_clips), duration, sound_volume
                )
                
                if final_audio:
                    # merge video and audio
                    merge_cmd = [
                        "ffmpeg", "-y",
                        "-i", temp_video,
                        "-i", final_audio,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        output_path
                    ]
                    subprocess.run(merge_cmd, capture_output=True, check=True)
                    
                    # cleanup temp audio
                    if os.path.exists(final_audio):
                        os.unlink(final_audio)
                else:
                    # no audio, just rename
                    os.rename(temp_video, output_path)
            else:
                os.rename(temp_video, output_path)
            
            # step 5: cleanup temp files
            for clip in temp_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            if os.path.exists(concat_file):
                os.unlink(concat_file)
            if os.path.exists(temp_video):
                os.unlink(temp_video)
            
            print(f"[VideoCreator] slideshow saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] slideshow failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_portrait(
        self,
        images: List[str],
        output_name: str = "portrait.mp4"
    ) -> Optional[str]:
        """
        create portrait 9:16 video for tiktok/reels with:
        - images in top 2/3
        - white space at bottom 1/3 for face overlay
        - ken burns effect
        
        per spec rules 43-49
        """
        if not images:
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # settings
        duration = self.settings.get("secondsPerImage", 4.0)
        bg_color = self.settings.get("bgColor", "#FFFFFF").lstrip("#")
        
        # portrait dimensions (9:16)
        width = 1080
        height = 1920
        fps = 30
        
        # image area is top 66%
        image_height = int(height * 0.66)
        
        print(f"[VideoCreator] creating portrait with {len(images)} images")
        
        try:
            temp_clips = []
            
            for i, img_path in enumerate(images):
                if not os.path.exists(img_path):
                    continue
                
                clip_path = os.path.join(self.output_dir, f"_temp_portrait_{i}.mp4")
                
                # create portrait clip with image at top, white at bottom
                success = self._create_portrait_clip(
                    img_path, clip_path, duration, width, height, image_height, fps, bg_color
                )
                
                if success and os.path.exists(clip_path):
                    temp_clips.append(clip_path)
            
            if not temp_clips:
                return None
            
            # concat clips
            concat_file = os.path.join(self.output_dir, "_concat_portrait.txt")
            with open(concat_file, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")
            
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path
            ]
            subprocess.run(concat_cmd, capture_output=True, check=True)
            
            # cleanup
            for clip in temp_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            if os.path.exists(concat_file):
                os.unlink(concat_file)
            
            print(f"[VideoCreator] portrait saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] portrait failed: {e}")
            return None
    
    def create_youtube_mix(
        self,
        videos: List[str],
        output_name: str = "youtube_mix.mp4"
    ) -> Optional[str]:
        """
        create scrambled montage from youtube videos:
        - only use middle 80% (avoid first/last 10%)
        - random clip selection
        - muted audio
        
        per spec rules 50-56
        """
        if not videos:
            print("[VideoCreator] no youtube videos to mix")
            return None
        
        # filter to existing files
        videos = [v for v in videos if os.path.exists(v)]
        if not videos:
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # settings
        target_duration = self.settings.get("minBrollDuration", 60.0)
        max_clip_duration = 3.0
        avoid_percent = 0.10  # 10% at start and end
        
        print(f"[VideoCreator] creating youtube mix from {len(videos)} videos")
        
        try:
            all_clips = []
            
            for video_path in videos:
                # get video duration using ffprobe
                duration = self._get_video_duration(video_path)
                if not duration or duration < 10:
                    continue
                
                # calculate safe zone (middle 80%)
                start_safe = duration * avoid_percent
                end_safe = duration * (1 - avoid_percent)
                safe_duration = end_safe - start_safe
                
                if safe_duration < max_clip_duration * 2:
                    continue
                
                # extract 3-5 random clips from this video
                num_clips = random.randint(3, 5)
                
                for j in range(num_clips):
                    clip_start = random.uniform(start_safe, end_safe - max_clip_duration)
                    clip_duration = random.uniform(1.5, max_clip_duration)
                    
                    clip_path = os.path.join(self.output_dir, f"_temp_yt_{len(all_clips)}.mp4")
                    
                    # extract clip with ffmpeg, muted
                    extract_cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(clip_start),
                        "-i", video_path,
                        "-t", str(clip_duration),
                        "-an",  # mute audio
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        clip_path
                    ]
                    
                    result = subprocess.run(extract_cmd, capture_output=True)
                    if result.returncode == 0 and os.path.exists(clip_path):
                        all_clips.append(clip_path)
            
            if not all_clips:
                print("[VideoCreator] no clips extracted")
                return None
            
            # shuffle clips randomly (non-linear per spec)
            random.shuffle(all_clips)
            
            # take clips up to target duration
            total_duration = 0
            final_clips = []
            
            for clip in all_clips:
                if total_duration >= target_duration:
                    break
                clip_dur = self._get_video_duration(clip)
                if clip_dur:
                    final_clips.append(clip)
                    total_duration += clip_dur
            
            if not final_clips:
                return None
            
            # concat
            concat_file = os.path.join(self.output_dir, "_concat_yt.txt")
            with open(concat_file, "w") as f:
                for clip in final_clips:
                    f.write(f"file '{clip}'\n")
            
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path
            ]
            subprocess.run(concat_cmd, capture_output=True, check=True)
            
            # cleanup
            for clip in all_clips:
                if os.path.exists(clip):
                    os.unlink(clip)
            if os.path.exists(concat_file):
                os.unlink(concat_file)
            
            print(f"[VideoCreator] youtube mix saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] youtube mix failed: {e}")
            return None
    
    def _create_ken_burns_clip(
        self,
        img_path: str,
        output_path: str,
        duration: float,
        width: int,
        height: int,
        fps: int,
        bg_color: str
    ) -> bool:
        """
        create a single clip with ken burns effect using ffmpeg
        randomly chooses zoom in, zoom out, or pan
        
        per spec rule 38: slow zoom/pan "Ken Burns" vibe
        """
        # choose random effect
        effect_type = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
        
        # base filter to scale and pad image to fit canvas
        base_filter = f"scale={width*2}:{height*2}:force_original_aspect_ratio=decrease,pad={width*2}:{height*2}:(ow-iw)/2:(oh-ih)/2:color=#{bg_color}"
        
        # ken burns zoom expressions
        if effect_type == "zoom_in":
            # start at 100%, zoom to 120%
            zoom_filter = f"zoompan=z='min(zoom+0.0015,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        elif effect_type == "zoom_out":
            # start at 120%, zoom to 100%
            zoom_filter = f"zoompan=z='if(eq(on,1),1.2,max(zoom-0.0015,1))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        elif effect_type == "pan_right":
            # pan from left to right
            zoom_filter = f"zoompan=z='1.1':x='if(eq(on,1),0,min(x+2,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        else:  # pan_left
            # pan from right to left
            zoom_filter = f"zoompan=z='1.1':x='if(eq(on,1),iw-iw/zoom,max(x-2,0))':y='ih/2-(ih/zoom/2)':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-filter_complex", f"{base_filter},{zoom_filter}",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    
    def _create_portrait_clip(
        self,
        img_path: str,
        output_path: str,
        duration: float,
        width: int,
        height: int,
        image_height: int,
        fps: int,
        bg_color: str
    ) -> bool:
        """
        create portrait clip with image at top and white at bottom
        """
        # complex filter: create white background, overlay scaled image at top
        filter_complex = (
            f"[0:v]scale={width}:{image_height}:force_original_aspect_ratio=decrease,pad={width}:{image_height}:(ow-iw)/2:(oh-ih)/2:color=#{bg_color}[img];"
            f"color=#{bg_color}:s={width}x{height}:d={duration}[bg];"
            f"[bg][img]overlay=0:0[out]"
        )
        
        # add simple zoom effect
        zoom_filter = f",zoompan=z='min(zoom+0.001,1.1)':x='iw/2-(iw/zoom/2)':y='0':d={int(duration*fps)}:s={width}x{height}:fps={fps}"
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-filter_complex", filter_complex + zoom_filter.replace("[out]", ""),
            "-map", "[out]",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            # fallback without zoom if complex filter fails
            simple_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", img_path,
                "-vf", f"scale={width}:{image_height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:0:color=#{bg_color}",
                "-t", str(duration),
                "-r", str(fps),
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                output_path
            ]
            result = subprocess.run(simple_cmd, capture_output=True)
        
        return result.returncode == 0
    
    def _create_sfx_track(
        self,
        num_clips: int,
        clip_duration: float,
        volume: float
    ) -> Optional[str]:
        """
        create audio track with sound effects between clips
        
        per spec rule 41: ping -> image -> ping -> image
        """
        if not self.sound_files:
            return None
        
        # create silence + sfx pattern
        output_path = os.path.join(self.output_dir, "_temp_sfx.mp3")
        
        try:
            # get a few random sounds
            sounds = random.sample(self.sound_files, min(len(self.sound_files), 5))
            
            # total duration needed
            total_duration = num_clips * clip_duration
            
            # create silent base
            silence_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(total_duration),
                "-c:a", "libmp3lame",
                "-q:a", "2",
                output_path
            ]
            subprocess.run(silence_cmd, capture_output=True, check=True)
            
            # overlay sounds at each transition point
            current_time = clip_duration  # start after first clip
            
            for i in range(num_clips - 1):
                sound = random.choice(sounds)
                
                # overlay this sound
                temp_output = os.path.join(self.output_dir, f"_temp_sfx_{i}.mp3")
                
                overlay_cmd = [
                    "ffmpeg", "-y",
                    "-i", output_path,
                    "-i", sound,
                    "-filter_complex", 
                    f"[1:a]adelay={int(current_time*1000)}|{int(current_time*1000)},volume={volume}[sfx];[0:a][sfx]amix=inputs=2:duration=longest",
                    "-c:a", "libmp3lame",
                    "-q:a", "2",
                    temp_output
                ]
                
                result = subprocess.run(overlay_cmd, capture_output=True)
                
                if result.returncode == 0:
                    os.replace(temp_output, output_path)
                
                current_time += clip_duration
            
            return output_path
            
        except Exception as e:
            print(f"[VideoCreator] sfx track failed: {e}")
            return None
    
    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """get video duration using ffprobe"""
        try:
            result = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        return None


def test_creator():
    """test the video creator"""
    import tempfile
    
    creator = VideoCreatorPro(
        images_dir=tempfile.mkdtemp(),
        videos_dir=tempfile.mkdtemp(),
        output_dir=tempfile.mkdtemp()
    )
    
    print("[Test] VideoCreatorPro initialized")
    print("[Test] to fully test, provide images and run create_slideshow")


if __name__ == "__main__":
    test_creator()

