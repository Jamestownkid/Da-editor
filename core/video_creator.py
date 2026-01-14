"""
Da Editor - Video Creator
==========================
creates the 3 video outputs:

1a. landscape slideshow - images with ken burns + sound effects
1b. portrait split - for tiktok/ig with space for face at bottom
1c. youtube mix - random clips from youtube videos

NOTE: this file is a stub - cursor should fill in the detailed implementation
"""

import os
import random
from typing import List, Optional, Dict


class VideoCreator:
    """
    create all 3 video outputs from collected assets
    
    1a. slideshow: images + sounds + ken burns
    1b. portrait: 9:16 split screen
    1c. youtube mix: scrambled clips
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
        
        # load sound files if dir exists
        self.sound_files = []
        if sounds_dir and os.path.isdir(sounds_dir):
            for f in os.listdir(sounds_dir):
                if f.endswith((".mp3", ".wav", ".ogg")):
                    self.sound_files.append(os.path.join(sounds_dir, f))
            print(f"[VideoCreator] found {len(self.sound_files)} sound effects")
        
        print(f"[VideoCreator] ready - output: {output_dir}")
    
    def create_slideshow(
        self,
        images: List[str],
        audio_source: Optional[str] = None,
        srt_path: Optional[str] = None,
        output_name: str = "slideshow.mp4"
    ) -> Optional[str]:
        """
        1a. create landscape slideshow with:
        - ken burns effect (zoom/pan on images)
        - transition sound effects
        - optional audio from source video
        - white background
        """
        try:
            from moviepy import (
                ImageClip, AudioFileClip, CompositeAudioClip,
                concatenate_videoclips, CompositeVideoClip
            )
        except ImportError:
            print("[VideoCreator] moviepy not installed!")
            return None
        
        if not images:
            print("[VideoCreator] no images provided")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # get settings
        seconds_per_image = self.settings.get("seconds_per_image", 4.0)
        bg_color = self.settings.get("bg_color", "#FFFFFF")
        sound_volume = self.settings.get("sound_volume", 0.8)
        
        # convert hex to RGB tuple
        bg_rgb = tuple(int(bg_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        
        print(f"[VideoCreator] creating slideshow with {len(images)} images")
        
        # ===== CURSOR: FILL IN THE DETAILED IMPLEMENTATION =====
        # this is where the actual video creation happens
        # using moviepy to:
        # 1. create clips from each image with ken burns effect
        # 2. add transition sounds between clips
        # 3. composite everything together
        # 4. render to output file
        
        clips = []
        audio_clips = []
        current_time = 0
        
        for i, img_path in enumerate(images):
            try:
                # create image clip
                clip = ImageClip(img_path, duration=seconds_per_image)
                
                # apply ken burns effect
                clip = self._apply_ken_burns(clip)
                
                # resize to 1920x1080
                clip = clip.resized((1920, 1080))
                
                clips.append(clip)
                
                # add transition sound if available
                if self.sound_files and i > 0:
                    sound_path = random.choice(self.sound_files)
                    try:
                        sound = AudioFileClip(sound_path)
                        sound = sound.with_start(current_time)
                        sound = sound.with_volume_scaled(sound_volume)
                        if sound.duration > 1.5:
                            sound = sound.subclipped(0, 1.5)
                        audio_clips.append(sound)
                    except:
                        pass
                
                current_time += seconds_per_image
                
            except Exception as e:
                print(f"[VideoCreator] failed to process {img_path}: {e}")
                continue
        
        if not clips:
            print("[VideoCreator] no clips created")
            return None
        
        # concatenate clips
        final = concatenate_videoclips(clips, method="compose")
        
        # add sounds
        if audio_clips:
            composite_audio = CompositeAudioClip(audio_clips)
            final = final.with_audio(composite_audio)
        
        # render
        print(f"[VideoCreator] rendering slideshow to {output_path}")
        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            preset="medium",
            threads=4
        )
        
        # cleanup
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        
        print(f"[VideoCreator] slideshow saved: {output_path}")
        return output_path
    
    def create_portrait(
        self,
        images: List[str],
        output_name: str = "portrait.mp4"
    ) -> Optional[str]:
        """
        1b. create portrait (9:16) video for tiktok/instagram
        - images at top 2/3
        - white space at bottom 1/3 for face overlay
        """
        try:
            from moviepy import (
                ImageClip, ColorClip, CompositeVideoClip,
                concatenate_videoclips
            )
        except ImportError:
            return None
        
        if not images:
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # portrait dimensions (9:16)
        width = 1080
        height = 1920
        
        # top section for b-roll (2/3 of height)
        top_height = int(height * 0.66)
        
        # bottom section for face (1/3) - just white
        seconds_per_image = self.settings.get("seconds_per_image", 4.0)
        bg_color = self.settings.get("bg_color", "#FFFFFF")
        bg_rgb = tuple(int(bg_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        
        print(f"[VideoCreator] creating portrait with {len(images)} images")
        
        # ===== CURSOR: FILL IN SPLIT SCREEN LOGIC =====
        # 1. create white background
        # 2. resize images to fit top portion
        # 3. composite image on top of white background
        # 4. add ken burns effect
        # 5. render
        
        clips = []
        
        for img_path in images:
            try:
                # create white background
                bg = ColorClip(size=(width, height), color=bg_rgb, duration=seconds_per_image)
                
                # load and resize image to fit top portion
                img = ImageClip(img_path, duration=seconds_per_image)
                img = img.resized(height=top_height)
                
                # center horizontally
                if img.w > width:
                    # crop if too wide
                    x_center = img.w / 2
                    img = img.cropped(x1=x_center - width/2, x2=x_center + width/2)
                
                # position at top
                img = img.with_position(("center", 0))
                
                # composite
                composite = CompositeVideoClip([bg, img])
                clips.append(composite)
                
            except Exception as e:
                print(f"[VideoCreator] portrait clip failed: {e}")
                continue
        
        if not clips:
            return None
        
        final = concatenate_videoclips(clips, method="compose")
        
        print(f"[VideoCreator] rendering portrait to {output_path}")
        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="6000k",
            preset="medium"
        )
        
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        
        print(f"[VideoCreator] portrait saved: {output_path}")
        return output_path
    
    def create_youtube_mix(
        self,
        videos: List[str],
        output_name: str = "youtube_mix.mp4"
    ) -> Optional[str]:
        """
        1c. create scrambled b-roll from youtube videos
        - only use youtube videos (not tiktok)
        - pick random portions from middle (avoid first/last 10%)
        - mute all audio
        - non-linear editing
        """
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
        except ImportError:
            return None
        
        if not videos:
            print("[VideoCreator] no youtube videos to mix")
            return None
        
        output_path = os.path.join(self.output_dir, output_name)
        
        # target duration
        target_duration = self.settings.get("min_broll_duration", 60.0)
        
        # max seconds per clip
        max_clip_duration = self.settings.get("broll_clip_max_seconds", 3.0)
        
        # percent of video to avoid at start/end
        avoid_percent = self.settings.get("broll_avoid_percent", 10) / 100
        
        print(f"[VideoCreator] creating youtube mix from {len(videos)} videos")
        
        # ===== CURSOR: FILL IN CLIP EXTRACTION LOGIC =====
        # 1. for each video, extract random clips from middle portion
        # 2. mute audio
        # 3. shuffle clips randomly
        # 4. concatenate to target duration
        # 5. render
        
        all_clips = []
        sources = []
        
        for video_path in videos:
            try:
                src = VideoFileClip(video_path)
                sources.append(src)
                
                duration = src.duration
                
                # calculate safe zone (middle 80%)
                start_safe = duration * avoid_percent
                end_safe = duration * (1 - avoid_percent)
                safe_duration = end_safe - start_safe
                
                if safe_duration < max_clip_duration:
                    continue
                
                # extract 3-5 random clips from each video
                num_clips = random.randint(3, 5)
                
                for _ in range(num_clips):
                    clip_start = random.uniform(start_safe, end_safe - max_clip_duration)
                    clip_end = clip_start + random.uniform(1.5, max_clip_duration)
                    
                    clip = src.subclipped(clip_start, min(clip_end, end_safe))
                    
                    # mute audio
                    clip = clip.without_audio()
                    
                    # resize to 1920x1080
                    clip = clip.resized(height=1080)
                    if clip.w > 1920:
                        x_center = clip.w / 2
                        clip = clip.cropped(x1=x_center - 960, x2=x_center + 960)
                    
                    all_clips.append(clip)
                    
            except Exception as e:
                print(f"[VideoCreator] failed to process {video_path}: {e}")
                continue
        
        if not all_clips:
            return None
        
        # shuffle randomly
        random.shuffle(all_clips)
        
        # take clips up to target duration
        final_clips = []
        total_duration = 0
        
        for clip in all_clips:
            if total_duration >= target_duration:
                break
            final_clips.append(clip)
            total_duration += clip.duration
        
        if not final_clips:
            return None
        
        final = concatenate_videoclips(final_clips, method="compose")
        
        print(f"[VideoCreator] rendering youtube mix ({final.duration:.1f}s) to {output_path}")
        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            bitrate="10000k",
            preset="medium"
        )
        
        # cleanup
        for clip in all_clips:
            try:
                clip.close()
            except:
                pass
        for src in sources:
            try:
                src.close()
            except:
                pass
        
        print(f"[VideoCreator] youtube mix saved: {output_path}")
        return output_path
    
    def _apply_ken_burns(self, clip):
        """
        2a. apply ken burns effect (zoom/pan) to clip
        randomly chooses zoom in or out + direction
        """
        try:
            # get clip dimensions
            w, h = clip.size
            
            # random effect type
            effect = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right"])
            
            if effect == "zoom_in":
                # start at full size, zoom to 120%
                def resize_func(t):
                    progress = t / clip.duration
                    scale = 1 + (0.2 * progress)
                    return scale
                
                clip = clip.resized(resize_func)
                
            elif effect == "zoom_out":
                # start at 120%, zoom to full size
                def resize_func(t):
                    progress = t / clip.duration
                    scale = 1.2 - (0.2 * progress)
                    return scale
                
                clip = clip.resized(resize_func)
            
            # pan effects would need position changes
            # leaving as is for now - cursor can enhance
            
        except Exception as e:
            print(f"[VideoCreator] ken burns failed: {e}")
        
        return clip


def test_creator():
    """quick test"""
    import tempfile
    
    creator = VideoCreator(
        images_dir=tempfile.mkdtemp(),
        videos_dir=tempfile.mkdtemp(),
        output_dir=tempfile.mkdtemp()
    )
    
    print("[Test] VideoCreator initialized")
    print("[Test] to fully test, provide images and videos")


if __name__ == "__main__":
    test_creator()
