"""
Orchestrator: Main Pipeline Runner
==================================
Điều phối toàn bộ pipeline sản xuất audiobook.

Usage:
    python -m orchestrator.run --full          # Full pipeline
    python -m orchestrator.run --generate      # Story generation
    python -m orchestrator.run --tts --story X # TTS synthesis
    python -m orchestrator.run --assemble --story-id X  # Video assembly
    python -m orchestrator.run --upload --story-id X    # YouTube upload
    python -m orchestrator.run --list-stories  # List all stories
"""

from orchestrator.run import PipelineRunner

__all__ = ["PipelineRunner"]
