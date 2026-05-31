"""
Module 3: TTS Engine Wrapper
============================
Unified interface for Vietnamese Text-to-Speech engines.

Primary: VieNeu-TTS (local, open-source, giọng nữ Bắc "Trúc Ly")
Backup:  Edge TTS (free cloud), VBee (paid, best quality)

Voice Cloning: VieNeu-TTS supports zero-shot voice cloning with
3-5 seconds of reference audio (e.g., giọng Ngọc Huyền).

Usage:
    from module_3_tts import TTSEngine

    engine = TTSEngine(engine="vieneu", mode="standard")
    audio = engine.synthesize("Chào bạn, đây là giọng đọc truyện.")
    engine.save(audio, "output.wav")

    # Voice cloning (Ngọc Huyền style)
    engine.clone_voice_from_file("ngoc_huyen_sample.wav", "ref text")
    audio = engine.synthesize("Văn bản truyện cần đọc...")
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from loguru import logger


# ============================================================
# Engine Initialization
# ============================================================
class TTSEngine:
    """
    Unified TTS engine wrapper.

    Supports multiple backends with automatic fallback.
    Primary: VieNeu-TTS (local, free, high quality Vietnamese)
    """

    # Available voice presets in VieNeu-TTS
    VIENEU_PRESET_VOICES = {
        "truc_ly": {
            "name": "Trúc Ly",
            "gender": "female",
            "accent": "northern",
            "description": "Giọng nữ miền Bắc nhẹ nhàng, tự nhiên (mặc định)",
            "best_for": "Ngôn tình, kể chuyện đời thường",
        },
        "pham_tuyen": {
            "name": "Phạm Tuyên",
            "gender": "male",
            "accent": "northern",
            "description": "Giọng nam miền Bắc trầm ấm",
            "best_for": "Truyện trinh thám, lịch sử, bình luận",
        },
    }

    # Emotion modes
    EMOTIONS = {
        "natural": "Tự nhiên, đàm thoại hàng ngày",
        "storytelling": "Kể chuyện, truyền cảm, có ngữ điệu",
    }

    def __init__(
        self,
        engine: str = "vieneu",
        mode: str = "standard",
        emotion: str = "storytelling",
        voice_preset: str = "truc_ly",
        device: str = "cpu",
        sample_rate: int = 24000,
    ):
        """
        Initialize TTS Engine.

        Args:
            engine: Backend engine ("vieneu", "edge", "vbee")
            mode: VieNeu-TTS mode ("standard", "turbo", "remote")
            emotion: Voice emotion ("natural" or "storytelling")
            voice_preset: Preset voice ID ("truc_ly" or "pham_tuyen")
            device: Compute device ("cpu" or "cuda")
            sample_rate: Output sample rate (24000 for VieNeu-TTS)
        """
        self.engine = engine.lower()
        self.mode = mode.lower()
        self.emotion = emotion.lower()
        self.voice_preset = voice_preset.lower()
        self.device = device.lower()
        self.sample_rate = sample_rate

        self._tts = None           # VieNeu-TTS instance
        self._vbee_client = None   # VBee API client
        self._cloned_voice = None  # Cloned voice encoding
        self._voice_data = None    # Loaded preset voice data

        self._init_engine()

    def _init_engine(self):
        """Initialize the TTS backend."""
        if self.engine == "vieneu":
            self._init_vieneu()
        elif self.engine == "edge":
            self._init_edge_tts()
        elif self.engine == "vbee":
            self._init_vbee()
        else:
            raise ValueError(f"Unknown engine: {self.engine}")

    def _init_vieneu(self):
        """Initialize VieNeu-TTS engine."""
        try:
            from vieneu import Vieneu

            self._tts = Vieneu(
                mode=self.mode,
                emotion=self.emotion,
                device=self.device,
            )
            logger.info(
                f"VieNeu-TTS initialized: mode={self.mode}, "
                f"emotion={self.emotion}, device={self.device}"
            )

            # Load preset voice
            self._load_preset_voice()

        except ImportError:
            logger.error(
                "VieNeu-TTS not installed. Install it with:\n"
                "  git clone https://github.com/pnnbao97/VieNeu-TTS.git\n"
                "  cd VieNeu-TTS && pip install -e .\n"
                "Or: pip install vieneu"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize VieNeu-TTS: {e}")
            raise

    def _init_edge_tts(self):
        """Initialize Microsoft Edge TTS (free, cloud)."""
        try:
            import edge_tts
            self._edge_tts = edge_tts
            logger.info("Edge TTS initialized (free cloud TTS)")
        except ImportError:
            logger.error("edge-tts not installed: pip install edge-tts")
            raise

    def _init_vbee(self):
        """Initialize VBee API client (paid, best Vietnamese quality)."""
        # VBee integration placeholder
        # Requires VBee API key: https://vbee.vn
        logger.warning("VBee integration not yet implemented. Using VieNeu-TTS fallback.")
        self.engine = "vieneu"
        self._init_vieneu()

    # ============================================================
    # Voice Management
    # ============================================================
    def _load_preset_voice(self):
        """Load the selected preset voice."""
        if self._tts is None:
            return

        try:
            voices = self._tts.list_preset_voices()
            logger.info(f"Available preset voices: {len(voices)}")

            for desc, voice_id in voices:
                logger.debug(f"  Voice: '{desc}' (ID: {voice_id})")

                # Match voice preset
                if self.voice_preset in voice_id.lower() or \
                   self.voice_preset in desc.lower():
                    self._voice_data = self._tts.get_preset_voice(voice_id)
                    logger.info(f"Loaded preset voice: {desc}")
                    return

            # Default: use first voice if no match
            if voices:
                self._voice_data = self._tts.get_preset_voice(voices[0][1])
                logger.info(f"Using default voice: {voices[0][0]}")

        except Exception as e:
            logger.warning(f"Could not load preset voice: {e}")
            self._voice_data = None

    def list_preset_voices(self) -> List[Tuple[str, str]]:
        """List all available preset voices."""
        if self._tts is not None:
            return self._tts.list_preset_voices()
        return []

    def clone_voice_from_file(
        self,
        reference_audio_path: str,
        reference_text: Optional[str] = None,
    ):
        """
        Clone a voice from a reference audio file (zero-shot).

        Use this to clone giọng Ngọc Huyền or any custom voice.
        Requires only 3-5 seconds of clean reference audio.

        Args:
            reference_audio_path: Path to reference audio (WAV/MP3)
            reference_text: Text spoken in the reference audio
                           (required for standard mode, optional for turbo)

        Example:
            # Clone Ngọc Huyền voice
            engine.clone_voice_from_file(
                "examples/audio_ref/example_ngoc_huyen.wav",
                reference_text="Đây là tác phẩm dự thi..."
            )
        """
        if self._tts is None:
            raise RuntimeError("VieNeu-TTS not initialized")

        ref_path = Path(reference_audio_path)
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

        logger.info(f"Cloning voice from: {ref_path.name}")

        try:
            if self.mode == "turbo":
                # Turbo mode: no reference text needed
                self._cloned_voice = self._tts.encode_reference(str(ref_path))
            else:
                # Standard mode: reference text improves accuracy
                if reference_text is None:
                    logger.warning(
                        "No reference_text provided. "
                        "Standard mode clones better with ref_text."
                    )
                self._cloned_voice = self._tts.encode_reference(
                    str(ref_path),
                    ref_text=reference_text,
                )

            logger.info("✓ Voice cloned successfully")

        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            raise

    def clone_voice_from_bytes(
        self,
        audio_bytes: bytes,
        reference_text: Optional[str] = None,
    ):
        """Clone voice from audio bytes (useful for API uploads)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            self.clone_voice_from_file(temp_path, reference_text)
        finally:
            os.unlink(temp_path)

    # ============================================================
    # Synthesis
    # ============================================================
    def synthesize(
        self,
        text: str,
        voice_data=None,
        speed: float = 1.0,
    ) -> np.ndarray:
        """
        Synthesize speech from text.

        Args:
            text: Vietnamese text to speak
            voice_data: Override voice data (from clone_voice)
            speed: Speaking speed multiplier (0.8 - 1.2)

        Returns:
            Audio as numpy array (float32, shape: [samples])
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.debug(f"Synthesizing: '{text[:50]}...' ({len(text)} chars)")

        if self.engine == "vieneu":
            return self._synthesize_vieneu(text, voice_data, speed)
        elif self.engine == "edge":
            return self._synthesize_edge(text, voice_data)
        else:
            raise ValueError(f"Unknown engine: {self.engine}")

    def _synthesize_vieneu(
        self,
        text: str,
        voice_data=None,
        speed: float = 1.0,
    ) -> np.ndarray:
        """Synthesize using VieNeu-TTS."""
        # Determine which voice to use (priority order)
        use_voice = voice_data or self._cloned_voice or self._voice_data

        kwargs = {"text": text, "speed": speed}
        if use_voice is not None:
            kwargs["voice"] = use_voice

        audio = self._tts.infer(**kwargs)
        return audio

    def _synthesize_edge(self, text: str, voice_data=None) -> np.ndarray:
        """Synthesize using Microsoft Edge TTS."""
        import asyncio

        async def _edge_synth():
            voice = "vi-VN-HoaiMyNeural"  # Vietnamese female voice
            communicate = self._edge_tts.Communicate(text, voice)
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            return b"".join(audio_chunks)

        audio_bytes = asyncio.run(_edge_synth())

        # Convert bytes to numpy array
        import soundfile as sf
        audio, sr = sf.read(io.BytesIO(audio_bytes))
        if sr != self.sample_rate:
            # Resample if needed (simplified - use scipy or librosa in production)
            logger.warning(f"Sample rate mismatch: {sr} vs {self.sample_rate}")
        return audio

    # ============================================================
    # Audio I/O
    # ============================================================
    def save(self, audio: np.ndarray, filepath: str):
        """Save audio to file (WAV format)."""
        import soundfile as sf

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(filepath), audio, self.sample_rate)
        logger.debug(f"Audio saved: {filepath}")

    @staticmethod
    def load(filepath: str) -> np.ndarray:
        """Load audio from file."""
        import soundfile as sf
        audio, _ = sf.read(filepath)
        return audio

    def get_audio_duration(self, audio: np.ndarray) -> float:
        """Get audio duration in seconds."""
        return len(audio) / self.sample_rate

    # ============================================================
    # Convenience Methods
    # ============================================================
    def speak_and_save(self, text: str, output_path: str) -> str:
        """One-liner: synthesize and save to file."""
        audio = self.synthesize(text)
        self.save(audio, output_path)
        return output_path

    def get_info(self) -> Dict:
        """Get engine information."""
        return {
            "engine": self.engine,
            "mode": self.mode,
            "emotion": self.emotion,
            "voice_preset": self.voice_preset,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "cloned_voice_active": self._cloned_voice is not None,
            "preset_voice_loaded": self._voice_data is not None,
        }


# ============================================================
# Factory Function
# ============================================================
def create_engine(
    engine: str = "vieneu",
    mode: str = "standard",
    emotion: str = "storytelling",
    voice: str = "truc_ly",
    device: str = "cpu",
    **kwargs,
) -> TTSEngine:
    """
    Factory function to create TTS engine.

    Args:
        engine: "vieneu", "edge", or "vbee"
        mode: "standard" (max quality), "turbo" (speed), or "remote" (server)
        emotion: "natural" or "storytelling" (recommended for audiobooks)
        voice: "truc_ly" (nữ Bắc) or "pham_tuyen" (nam Bắc)
        device: "cpu" or "cuda"

    Returns:
        Initialized TTSEngine
    """
    return TTSEngine(
        engine=engine,
        mode=mode,
        emotion=emotion,
        voice_preset=voice,
        device=device,
        **kwargs,
    )


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for TTS synthesis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Vietnamese Text-to-Speech Synthesis"
    )
    parser.add_argument(
        "text", nargs="?", type=str,
        help="Text to synthesize (or use --file)"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Input text file"
    )
    parser.add_argument(
        "--output", type=str, default="output.wav",
        help="Output audio file"
    )
    parser.add_argument(
        "--engine", type=str, default="vieneu",
        choices=["vieneu", "edge"],
        help="TTS engine"
    )
    parser.add_argument(
        "--mode", type=str, default="standard",
        choices=["standard", "turbo", "remote"],
        help="VieNeu-TTS mode"
    )
    parser.add_argument(
        "--emotion", type=str, default="storytelling",
        choices=["natural", "storytelling"],
        help="Voice emotion (storytelling recommended for audiobooks)"
    )
    parser.add_argument(
        "--voice", type=str, default="truc_ly",
        help="Voice preset (truc_ly or pham_tuyen)"
    )
    parser.add_argument(
        "--clone", type=str, default=None,
        help="Clone voice from reference audio file"
    )
    parser.add_argument(
        "--clone-text", type=str, default=None,
        help="Reference text for voice cloning"
    )
    parser.add_argument(
        "--device", type=str, default="cpu",
        choices=["cpu", "cuda"],
        help="Compute device"
    )
    parser.add_argument(
        "--info", action="store_true",
        help="Print engine info and exit"
    )

    args = parser.parse_args()

    # Create engine
    engine = create_engine(
        engine=args.engine,
        mode=args.mode,
        emotion=args.emotion,
        voice=args.voice,
        device=args.device,
    )

    if args.info:
        info = engine.get_info()
        print("\nTTS Engine Info:")
        for k, v in info.items():
            print(f"  {k}: {v}")
        return

    # Clone voice if requested
    if args.clone:
        print(f"Cloning voice from: {args.clone}")
        engine.clone_voice_from_file(args.clone, args.clone_text)
        print("✓ Voice cloned")

    # Get text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.error("Either provide text argument or --file")

    # Synthesize
    print(f"Synthesizing: '{text[:60]}...'")
    audio = engine.synthesize(text)
    engine.save(audio, args.output)

    duration = engine.get_audio_duration(audio)
    print(f"✓ Audio saved: {args.output}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Sample rate: {engine.sample_rate} Hz")


if __name__ == "__main__":
    main()
