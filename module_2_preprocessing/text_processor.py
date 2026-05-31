"""
Module 2: Text Preprocessing
============================
Làm sạch và chuẩn hóa text tiếng Việt để tối ưu cho TTS engine.
- Xóa rác (HTML tags, special chars)
- Tách câu thông minh
- Chuẩn hóa số, viết tắt
- Lọc nội dung nhạy cảm
- Generate SSML markup

Usage:
    from module_2_preprocessing import TextProcessor

    processor = TextProcessor(max_chars_per_segment=500)
    result = processor.process_chapter(raw_text)
    # result.sentences -> List[str] ready for TTS
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from loguru import logger


# ============================================================
# Data Classes
# ============================================================
@dataclass
class ProcessingResult:
    """Result of text processing for one chapter."""

    sentences: List[str]
    sentence_count: int
    total_chars: int
    estimated_duration_seconds: float
    warnings: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"ProcessingResult(sentences={self.sentence_count}, "
            f"chars={self.total_chars}, "
            f"est_duration={self.estimated_duration_seconds:.0f}s)"
        )


# ============================================================
# Text Processor Class
# ============================================================
class TextProcessor:
    """
    Clean, normalize, and prepare Vietnamese text for TTS synthesis.

    Features:
    - HTML tag removal
    - Whitespace normalization
    - Number-to-words conversion
    - Abbreviation expansion
    - Smart sentence splitting (TTS-optimized)
    - Sensitive content filtering
    - SSML markup generation
    """

    # Characters that mark sentence boundaries
    SENTENCE_END_MARKERS = r'(?<=[.!?…])\s+'

    # Vietnamese abbreviation mappings
    ABBREVIATION_MAP = {
        "tp": "thành phố",
        "đc": "được",
        "ko": "không",
        "k": "không",
        "vs": "với",
        "đt": "điện thoại",
        "ng": "người",
        "ntn": "như thế nào",
        "vsv": "vân vân",
        "cl": "cả lớp",
        "gv": "giáo viên",
        "sv": "sinh viên",
        "nv": "nhân viên",
        "gd": "gia đình",
        "đk": "được không",
        "bt": "bình thường",
        "ms": "mới",
        "r": "rồi",
        "j": "gì",
        "h": "giờ",
        "a": "anh",
        "e": "em",
        "c": "chị",
        "cb": "chuẩn bị",
        "tn": "tin nhắn",
        "hp": "hạnh phúc",
        "yc": "yêu cầu",
        "ql": "quản lý",
        "nx": "nhận xét",
        "tl": "trả lời",
        "th": "trường hợp",
        "đb": "đặc biệt",
        "nc": "nghiên cứu",
        "pt": "phát triển",
        "xh": "xã hội",
        "kt": "kinh tế",
        "ct": "công ty",
        "cp": "chính phủ",
    }

    def __init__(
        self,
        max_chars_per_segment: int = 500,
        pause_marker: str = "<break time='500ms'/>",
        long_pause_marker: str = "<break time='1s'/>",
        sentence_pause_ms: int = 350,
        paragraph_pause_ms: int = 800,
    ):
        """
        Initialize text processor.

        Args:
            max_chars_per_segment: Maximum characters per TTS call segment
            pause_marker: SSML marker for short pauses (between sentences)
            long_pause_marker: SSML marker for long pauses (between paragraphs)
            sentence_pause_ms: Pause duration between sentences (ms)
            paragraph_pause_ms: Pause duration between paragraphs (ms)
        """
        self.max_chars = max_chars_per_segment
        self.pause_marker = pause_marker
        self.long_pause_marker = long_pause_marker
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms

    # ============================================================
    # Main Processing Pipeline
    # ============================================================
    def process_chapter(self, raw_text: str) -> ProcessingResult:
        """
        Full processing pipeline for a chapter.

        Args:
            raw_text: Raw text from story generator

        Returns:
            ProcessingResult with sentence list and metadata
        """
        warnings = []

        # Step 1: Clean text
        text = self.clean_text(raw_text)

        # Step 2: Normalize for TTS
        text = self.normalize_for_tts(text)

        # Step 3: Filter sensitive content
        text, filter_warnings = self.filter_sensitive(text)
        warnings.extend(filter_warnings)

        # Step 4: Split into sentences optimized for TTS
        sentences = self.split_sentences(text)

        # Calculate stats
        total_chars = sum(len(s) for s in sentences)
        # Vietnamese TTS ~12-15 chars/second depending on engine
        chars_per_second = 13
        estimated_duration = total_chars / chars_per_second + (
            len(sentences) * self.sentence_pause_ms / 1000
        )

        logger.info(
            f"Processed chapter: {len(sentences)} sentences, "
            f"{total_chars} chars, ~{estimated_duration:.0f}s"
        )

        if warnings:
            logger.warning(f"Filter warnings: {warnings}")

        return ProcessingResult(
            sentences=sentences,
            sentence_count=len(sentences),
            total_chars=total_chars,
            estimated_duration_seconds=estimated_duration,
            warnings=warnings,
        )

    # ============================================================
    # Cleaning
    # ============================================================
    def clean_text(self, text: str) -> str:
        """
        Clean raw text: remove HTML, normalize whitespace, fix punctuation.

        Args:
            text: Raw input text

        Returns:
            Cleaned text
        """
        # Remove HTML/XML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'__([^_]+)__', r'\1', text)      # Bold
        text = re.sub(r'_([^_]+)_', r'\1', text)         # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)         # Code
        text = re.sub(r'#+\s*', '', text)                 # Headers

        # Normalize ellipsis
        text = re.sub(r'\.{2,}', '…', text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('«', '"').replace('»', '"')

        # Fix common OCR/encoding issues
        text = text.replace('​', '')  # Zero-width space
        text = text.replace('\xa0', ' ')    # Non-breaking space

        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)     # Collapse horizontal whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse multiple newlines
        text = re.sub(r' +\n', '\n', text)      # Remove trailing spaces at line end
        text = re.sub(r'\n +', '\n', text)      # Remove leading spaces at line start

        # Remove lines that are just special characters
        text = re.sub(r'^[~\-=_]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Remove lines that are just page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

        return text.strip()

    def normalize_for_tts(self, text: str) -> str:
        """
        Normalize text for optimal TTS reading.

        Args:
            text: Cleaned text

        Returns:
            TTS-optimized text
        """
        # Expand common abbreviations
        for abbr, full in self.ABBREVIATION_MAP.items():
            # Only expand standalone abbreviations (word boundaries)
            text = re.sub(
                rf'\b{re.escape(abbr)}\b',
                full,
                text,
                flags=re.IGNORECASE,
            )

        # Normalize numbers (keep small numbers for conversion)
        # Large numbers (>1000) are usually years/dates - keep as digits
        text = self._normalize_numbers(text)

        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?…:;])', r'\1', text)
        text = re.sub(r'([.,!?…:;])(?=[^\s\d])', r'\1 ', text)

        # Ensure sentences end with proper punctuation
        text = self._ensure_sentence_endings(text)

        # Replace paragraph breaks with pause markers
        text = text.replace('\n\n', f' {self.long_pause_marker} ')
        text = text.replace('\n', f' {self.pause_marker} ')

        # Add slight pause after sentence endings
        for marker in ['. ', '! ', '? ', '… ']:
            text = text.replace(marker, f'{marker.strip()}{self.pause_marker} ')

        # Clean up any double pause markers
        text = re.sub(
            r'(<break[^>]+>)\s*\1+',
            r'\1',
            text,
        )

        return text.strip()

    # ============================================================
    # Sentence Splitting
    # ============================================================
    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences optimized for TTS.

        Strategy:
        1. Split on sentence-ending punctuation (. ! ? …)
        2. If a segment is too long for TTS, split at commas/semicolons
        3. Ensure each segment ends with proper punctuation
        4. Minimum segment length for natural-sounding TTS

        Args:
            text: Normalized text

        Returns:
            List of sentence strings ready for TTS
        """
        # First pass: split on sentence endings
        raw_sentences = re.split(r'(?<=[.!?…])\s+', text)

        # Second pass: process each sentence
        result = []
        for sent in raw_sentences:
            sent = sent.strip()
            if not sent:
                continue

            # Remove SSML pause markers for length calculation
            clean_sent = re.sub(r'<[^>]+>', '', sent)

            if len(clean_sent) <= self.max_chars:
                # Sentence is short enough, just ensure punctuation
                sent = self._ensure_ending(sent)
                result.append(sent)
            else:
                # Sentence too long - split on commas/semicolons
                sub_sentences = self._split_long_sentence(sent)
                result.extend(sub_sentences)

        # Third pass: merge very short segments with neighbors
        result = self._merge_short_segments(result)

        return result

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Split a long sentence into smaller TTS-friendly segments."""
        # Split points in order of preference
        split_chars = [',', ';', ':', '—', '–', ' - ']

        for split_char in split_chars:
            if split_char in sentence:
                parts = sentence.split(split_char)
                chunks = []
                current = ""

                for i, part in enumerate(parts):
                    tentative = current + (f", " if current else "") + part.strip()

                    if len(tentative) <= self.max_chars:
                        current = tentative
                    else:
                        if current:
                            chunks.append(self._ensure_ending(current))
                        current = part.strip()

                if current:
                    chunks.append(self._ensure_ending(current))

                # If splitting worked, return
                if len(chunks) > 1:
                    return chunks

        # Fallback: force split at max_chars, at word boundary
        words = sentence.split()
        chunks = []
        current = ""

        for word in words:
            if len(current) + len(word) + 1 <= self.max_chars:
                current += (" " if current else "") + word
            else:
                if current:
                    chunks.append(self._ensure_ending(current))
                current = word

        if current:
            chunks.append(self._ensure_ending(current))

        return chunks

    def _merge_short_segments(self, sentences: List[str], min_chars: int = 20) -> List[str]:
        """Merge very short segments with neighbors for better TTS flow."""
        if not sentences:
            return sentences

        result = []
        i = 0
        while i < len(sentences):
            # Clean the sentence for length check
            clean = re.sub(r'<[^>]+>', '', sentences[i])

            if len(clean) < min_chars and i + 1 < len(sentences):
                # Merge with next sentence
                merged = sentences[i].rstrip() + " " + sentences[i + 1].lstrip()
                # Clean up double pause markers
                merged = re.sub(r'(<break[^>]+>)\s*\1', r'\1', merged)
                result.append(merged)
                i += 2
            else:
                result.append(sentences[i])
                i += 1

        return result

    # ============================================================
    # Content Filtering
    # ============================================================
    # Words/phrases that may trigger content flags
    SENSITIVE_PATTERNS = {
        "political": [
            r'\b(đảng|cộng\s*sản|chính\s*trị|nhà\s*nước|chính\s*phủ|quốc\s*hội)\b',
        ],
        "religious": [
            r'\b(tôn\s*giáo|phật\s*giáo|công\s*giáo|tin\s*lành|hồi\s*giáo)\b',
        ],
        "violence": [
            r'\b(giết|đâm|chém|bắn|đánh\s*đập|tàn\s*sát|khủng\s*bố)\b',
        ],
        "adult": [
            r'\b(khỏa\s*thân|tình\s*dục|khiêu\s*dâm|mại\s*dâm|ấu\s*dâm)\b',
        ],
        "hate_speech": [
            r'\b(phân\s*biệt\s*chủng\s*tộc|kỳ\s*thị|miệt\s*thị|xúc\s*phạm)\b',
        ],
    }

    def filter_sensitive(self, text: str) -> Tuple[str, List[str]]:
        """
        Filter sensitive content from text.

        Args:
            text: Text to filter

        Returns:
            Tuple of (filtered_text, list_of_warnings)
        """
        warnings = []

        for category, patterns in self.SENSITIVE_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    warnings.append(
                        f"Sensitive [{category}]: found '{matches[0]}' "
                        f"({len(matches)} occurrences)"
                    )
                    # Replace with generic placeholder
                    text = re.sub(pattern, '***', text, flags=re.IGNORECASE)

        return text, warnings

    # ============================================================
    # Helpers
    # ============================================================
    @staticmethod
    def _ensure_ending(text: str) -> str:
        """Ensure text ends with proper punctuation."""
        text = text.strip()
        if text and text[-1] not in '.!?…':
            text += '.'
        return text

    @staticmethod
    def _ensure_sentence_endings(text: str) -> str:
        """Ensure sentences end with proper punctuation markers."""
        lines = text.split('\n')
        result = []
        for line in lines:
            line = line.strip()
            if line and line[-1].isalpha():
                line += '.'
            result.append(line)
        return '\n'.join(result)

    @staticmethod
    def _normalize_numbers(text: str) -> str:
        """
        Normalize numbers in text.
        Small numbers (< 20) converted to words for natural reading.
        Large numbers kept as digits (years, phone numbers, etc.)
        """
        def replace_number(match):
            num_str = match.group(0)
            try:
                num = int(num_str)
                if num < 20:
                    return TextProcessor._number_to_vietnamese(num)
                return num_str
            except ValueError:
                return num_str

        # Only process standalone numbers (not part of larger text)
        return re.sub(r'\b\d+\b', replace_number, text)

    @staticmethod
    def _number_to_vietnamese(n: int) -> str:
        """Convert small integer to Vietnamese words."""
        words = [
            "không", "một", "hai", "ba", "bốn",
            "năm", "sáu", "bảy", "tám", "chín",
            "mười", "mười một", "mười hai", "mười ba", "mười bốn",
            "mười lăm", "mười sáu", "mười bảy", "mười tám", "mười chín",
        ]
        if 0 <= n < len(words):
            return words[n]
        return str(n)

    # ============================================================
    # SSML Generation
    # ============================================================
    def generate_ssml(
        self,
        sentences: List[str],
        voice_name: str = "vi-VN-female",
        speed: float = 1.0,
        pitch: str = "medium",
    ) -> str:
        """
        Generate SSML markup for TTS.

        Args:
            sentences: Processed sentences
            voice_name: Voice identifier
            speed: Speaking rate (0.5 - 2.0)
            pitch: Pitch level (low, medium, high)

        Returns:
            SSML string
        """
        pitch_values = {"low": "-15%", "medium": "+0%", "high": "+15%"}

        ssml_parts = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">']
        ssml_parts.append(f'  <voice name="{voice_name}">')
        ssml_parts.append(
            f'    <prosody rate="{speed}" pitch="{pitch_values.get(pitch, "+0%")}">'
        )

        for sentence in sentences:
            # Remove existing pause markers (we add SSML breaks instead)
            clean = re.sub(r'<[^>]+>', '', sentence).strip()
            ssml_parts.append(f'      <s>{clean}</s>')
            ssml_parts.append(f'      <break time="{self.sentence_pause_ms}ms"/>')

        ssml_parts.append('    </prosody>')
        ssml_parts.append('  </voice>')
        ssml_parts.append('</speak>')

        return '\n'.join(ssml_parts)

    # ============================================================
    # Statistics
    # ============================================================
    def get_text_stats(self, text: str) -> dict:
        """Get text statistics for analysis."""
        words = text.split()
        sentences = len(self.split_sentences(self.clean_text(text)))

        return {
            "char_count": len(text),
            "word_count": len(words),
            "sentence_count": sentences,
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "avg_sentence_length": len(words) / max(sentences, 1),
            "estimated_tts_duration_seconds": len(text) / 13,  # ~13 chars/sec for Vietnamese
        }


# ============================================================
# Convenience Functions
# ============================================================
def quick_process(text: str, max_chars: int = 500) -> List[str]:
    """Quick one-liner to process text for TTS."""
    processor = TextProcessor(max_chars_per_segment=max_chars)
    result = processor.process_chapter(text)
    return result.sentences


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for text preprocessing."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Preprocess Vietnamese text for TTS"
    )
    parser.add_argument(
        "input", nargs="?", type=str,
        help="Input text file (or stdin if not specified)"
    )
    parser.add_argument(
        "--max-chars", type=int, default=500,
        help="Max characters per TTS segment"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file (text with each sentence on new line)"
    )
    parser.add_argument(
        "--ssml", action="store_true",
        help="Output SSML markup instead of plain text"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print text statistics only"
    )

    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    processor = TextProcessor(max_chars_per_segment=args.max_chars)

    if args.stats:
        stats = processor.get_text_stats(text)
        print(f"Characters: {stats['char_count']}")
        print(f"Words: {stats['word_count']}")
        print(f"Sentences: {stats['sentence_count']}")
        print(f"Avg word length: {stats['avg_word_length']:.1f}")
        print(f"Avg sentence length: {stats['avg_sentence_length']:.1f} words")
        print(f"Est. TTS duration: {stats['estimated_tts_duration_seconds']:.0f}s")
        return

    # Process
    result = processor.process_chapter(text)

    if args.ssml:
        output = processor.generate_ssml(result.sentences)
    else:
        output = "\n".join(result.sentences)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {args.output}")
        print(f"  {result.sentence_count} sentences, {result.total_chars} chars")
    else:
        print(output)


if __name__ == "__main__":
    main()
