"""
Module 2: Text Preprocessing
============================
Clean, normalize, and prepare Vietnamese text for TTS engines.

Usage:
    from module_2_preprocessing import TextProcessor, ProcessingResult

    processor = TextProcessor(max_chars_per_segment=500)
    result = processor.process_chapter(raw_text)
    for sentence in result.sentences:
        send_to_tts(sentence)
"""

from module_2_preprocessing.text_processor import (
    ProcessingResult,
    TextProcessor,
    quick_process,
)

__all__ = [
    "TextProcessor",
    "ProcessingResult",
    "quick_process",
]
