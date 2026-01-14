"""
Da Editor - Whisper Transcriber
================================
1a. transcribes video/audio to SRT format
1b. uses openai whisper with GPU support
1c. handles model loading and caching
"""

import os
from typing import Optional


class WhisperTranscriber:
    """
    transcribe audio to SRT using openai whisper
    
    1a. loads specified model
    1b. extracts audio if needed
    1c. outputs SRT file
    """
    
    def __init__(
        self,
        model_name: str = "base",
        use_gpu: bool = True,
        output_dir: str = None
    ):
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.output_dir = output_dir or os.getcwd()
        self.model = None
        
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[Transcriber] init with model={model_name}, gpu={use_gpu}")
    
    def _load_model(self):
        """
        1a. load whisper model if not already loaded
        uses GPU if available and requested
        """
        if self.model is not None:
            return
        
        try:
            import whisper
            import torch
            
            # check GPU availability
            device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
            
            print(f"[Transcriber] loading {self.model_name} on {device}...")
            self.model = whisper.load_model(self.model_name, device=device)
            print(f"[Transcriber] model loaded")
            
        except ImportError:
            raise RuntimeError("whisper not installed - run: pip install openai-whisper")
        except Exception as e:
            raise RuntimeError(f"failed to load whisper model: {e}")
    
    def transcribe(self, video_path: str) -> Optional[str]:
        """
        1b. transcribe video to SRT
        returns path to SRT file
        """
        if not os.path.exists(video_path):
            print(f"[Transcriber] file not found: {video_path}")
            return None
        
        # load model
        self._load_model()
        
        # output path
        basename = os.path.splitext(os.path.basename(video_path))[0]
        # clean the filename - remove special chars
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in basename)
        srt_path = os.path.join(self.output_dir, f"{safe_name}.srt")
        
        try:
            print(f"[Transcriber] transcribing: {video_path}")
            
            # run transcription
            result = self.model.transcribe(
                video_path,
                language="en",  # could make this configurable
                task="transcribe",
                verbose=False
            )
            
            # convert to SRT format
            srt_content = self._to_srt(result["segments"])
            
            # save to file
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            print(f"[Transcriber] saved: {srt_path}")
            return srt_path
            
        except Exception as e:
            print(f"[Transcriber] failed: {e}")
            return None
    
    def _to_srt(self, segments: list) -> str:
        """
        2a. convert whisper segments to SRT format
        """
        srt_lines = []
        
        for i, seg in enumerate(segments, 1):
            start = self._format_timestamp(seg["start"])
            end = self._format_timestamp(seg["end"])
            text = seg["text"].strip()
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")  # blank line between entries
        
        return "\n".join(srt_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        2b. format seconds to SRT timestamp format
        00:00:00,000
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def test_transcriber():
    """quick test"""
    t = WhisperTranscriber(model_name="tiny", use_gpu=False)
    print("[Test] transcriber initialized")
    print("[Test] to actually test, provide a video file")


if __name__ == "__main__":
    test_transcriber()
