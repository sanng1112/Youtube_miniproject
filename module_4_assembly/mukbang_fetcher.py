"""
Module 4: Mukbang Video Fetcher
===============================
Tìm và tải video mukbang/cooking ASMR làm nền cho video audiobook.

Nguồn:
- YouTube search (dùng API key)
- yt-dlp để tải video
- Thư viện local đã tải sẵn

Usage:
    from module_4_assembly import MukbangFetcher

    fetcher = MukbangFetcher(youtube_api_key="...")
    videos = fetcher.search("mukbang cooking ASMR")
    fetcher.download(videos[0]["id"], "data/mukbang_library/")
"""

import json
import random
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import requests
from loguru import logger


class MukbangFetcher:
    """
    Fetch and manage background mukbang/cooking videos.

    Sources:
    - YouTube search via API v3
    - yt-dlp download
    - Local video library
    """

    # YouTube channels known for good mukbang/cooking content
    # (Creative Commons or channels that commonly grant permission)
    SUGGESTED_CHANNELS = [
        # Add channel IDs for mukbang channels
        # These should be CC-licensed or you should obtain permission
    ]

    SUGGESTED_SEARCH_QUERIES = [
        "mukbang no talking cooking",
        "cooking ASMR no music",
        "Korean mukbang eating show",
        "street food cooking ASMR",
        "satisfying cooking video no music",
        "mukbang seafood cooking",
        "home cooking ASMR no talking",
        "food preparation ASMR",
    ]

    def __init__(
        self,
        youtube_api_key: str,
        library_dir: str = "data/mukbang_library",
    ):
        """
        Initialize fetcher.

        Args:
            youtube_api_key: YouTube Data API v3 key
            library_dir: Local directory for downloaded videos
        """
        self.api_key = youtube_api_key
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)

        self._library_cache = None  # Lazily loaded

    # ============================================================
    # Search
    # ============================================================
    def search(
        self,
        query: str = "mukbang cooking ASMR",
        max_results: int = 10,
        min_duration_minutes: int = 5,
        language: str = "",
    ) -> List[Dict]:
        """
        Search YouTube for mukbang/cooking videos.

        Args:
            query: Search query
            max_results: Maximum results (1-50)
            language: Language filter (e.g., 'ko' for Korean)

        Returns:
            List of video info dicts
        """
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "videoDuration": "medium",  # 4-20 minutes
            "videoEmbeddable": "true",
            "safeSearch": "moderate",
            "key": self.api_key,
        }

        if language:
            params["relevanceLanguage"] = language

        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        videos = []
        for item in data.get("items", []):
            if item["id"]["kind"] != "youtube#video":
                continue

            snippet = item["snippet"]
            videos.append({
                "id": item["id"]["videoId"],
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "channel_id": snippet["channelId"],
                "published_at": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
            })

        logger.info(f"Found {len(videos)} videos for query: '{query[:50]}...'")
        return videos

    def search_multiple(
        self,
        queries: Optional[List[str]] = None,
        results_per_query: int = 5,
    ) -> List[Dict]:
        """Search with multiple queries to build diverse library."""
        if queries is None:
            queries = self.SUGGESTED_SEARCH_QUERIES

        all_videos = []
        seen_ids = set()

        for query in queries:
            try:
                results = self.search(query, max_results=results_per_query)
                for video in results:
                    if video["id"] not in seen_ids:
                        seen_ids.add(video["id"])
                        all_videos.append(video)
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")

        logger.info(f"Total unique videos found: {len(all_videos)}")
        return all_videos

    # ============================================================
    # Download
    # ============================================================
    def download(
        self,
        video_id: str,
        output_path: Optional[str] = None,
        max_height: int = 1080,
        max_filesize_mb: int = 500,
    ) -> str:
        """
        Download a YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID
            output_path: Output path (auto-generated if None)
            max_height: Maximum video height
            max_filesize_mb: Maximum file size

        Returns:
            Output file path
        """
        if output_path is None:
            output_path = str(self.library_dir / f"{video_id}.mp4")

        # Skip if already downloaded
        if Path(output_path).exists():
            logger.info(f"Video already downloaded: {output_path}")
            return output_path

        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Downloading: {url}")

        cmd = [
            "yt-dlp",
            url,
            "-f", f"best[height<={max_height}][filesize<{max_filesize_mb}M]/best",
            "-o", output_path,
            "--no-playlist",
            "--no-mtime",
            "--quiet",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"✓ Downloaded: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Download failed: {e.stderr[-300:]}")
            raise

    def download_batch(
        self,
        videos: List[Dict],
        max_downloads: int = 10,
    ) -> List[str]:
        """Download multiple videos."""
        paths = []
        for i, video in enumerate(videos[:max_downloads]):
            try:
                path = self.download(video["id"])
                paths.append(path)
                logger.info(f"  [{i+1}/{min(len(videos), max_downloads)}] {video['title'][:50]}")
            except Exception as e:
                logger.error(f"  Failed: {video['title'][:50]} - {e}")

        return paths

    # ============================================================
    # Local Library Management
    # ============================================================
    @property
    def library(self) -> List[Dict]:
        """Get all videos in local library."""
        if self._library_cache is not None:
            return self._library_cache

        videos = []
        for ext in ["*.mp4", "*.mkv", "*.webm", "*.mov"]:
            for f in self.library_dir.glob(ext):
                videos.append({
                    "id": f.stem,
                    "path": str(f),
                    "size_mb": f.stat().st_size / (1024 * 1024),
                })

        self._library_cache = videos
        return videos

    def get_random_video(self) -> Optional[str]:
        """Get a random video from the library."""
        library = self.library
        if not library:
            logger.warning("Mukbang library is empty. Run search_and_download() first.")
            return None

        video = random.choice(library)
        logger.debug(f"Random mukbang video: {video['id']}")
        return video["path"]

    def get_library_size(self) -> Dict:
        """Get library statistics."""
        library = self.library
        total_size = sum(v.get("size_mb", 0) for v in library)
        return {
            "video_count": len(library),
            "total_size_mb": round(total_size, 1),
            "directory": str(self.library_dir),
        }

    # ============================================================
    # One-shot: Search + Download + Build Library
    # ============================================================
    def build_library(
        self,
        target_count: int = 20,
        queries: Optional[List[str]] = None,
    ) -> Dict:
        """
        Build a complete mukbang video library.

        Searches with multiple queries and downloads diverse videos.

        Args:
            target_count: Number of videos to download
            queries: Custom search queries

        Returns:
            Library stats dict
        """
        logger.info(f"Building mukbang library (target: {target_count} videos)...")

        # Search
        videos = self.search_multiple(queries, results_per_query=5)
        logger.info(f"Search results: {len(videos)} videos")

        # Filter out already downloaded
        existing_ids = {v["id"] for v in self.library}
        new_videos = [v for v in videos if v["id"] not in existing_ids]
        logger.info(f"New videos to download: {len(new_videos)}")

        if not new_videos:
            logger.info("Library already up to date")
            return self.get_library_size()

        # Download
        to_download = new_videos[:target_count]
        self.download_batch(to_download)

        # Reset cache
        self._library_cache = None

        return self.get_library_size()

    def refresh_library(self, keep_count: int = 30):
        """
        Refresh library: remove old videos, keep only the newest.
        """
        library = self.library
        if len(library) <= keep_count:
            return

        # Sort by file modification time (oldest first)
        library.sort(key=lambda v: Path(v["path"]).stat().st_mtime)
        to_remove = library[:-keep_count]

        for video in to_remove:
            Path(video["path"]).unlink(missing_ok=True)
            logger.debug(f"  Removed: {video['id']}")

        self._library_cache = None
        logger.info(f"Library refreshed: {len(to_remove)} removed, ~{keep_count} kept")


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for mukbang video management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch and manage mukbang/cooking background videos"
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="YouTube API key"
    )
    parser.add_argument(
        "--search", type=str, default=None,
        help="Search query"
    )
    parser.add_argument(
        "--download", type=str, default=None,
        help="Download a specific video ID"
    )
    parser.add_argument(
        "--build", action="store_true",
        help="Build complete library"
    )
    parser.add_argument(
        "--target", type=int, default=20,
        help="Target videos for library"
    )
    parser.add_argument(
        "--library-dir", type=str, default="data/mukbang_library",
        help="Library directory"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show library statistics"
    )
    parser.add_argument(
        "--random", action="store_true",
        help="Get a random video from library"
    )

    args = parser.parse_args()

    # Get API key from args or env
    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        parser.error("YouTube API key required (--api-key or YOUTUBE_API_KEY env)")

    import os
    fetcher = MukbangFetcher(
        youtube_api_key=api_key,
        library_dir=args.library_dir,
    )

    if args.stats:
        stats = fetcher.get_library_size()
        print(f"\nMukbang Library:")
        print(f"  Videos: {stats['video_count']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Directory: {stats['directory']}")

    elif args.search:
        results = fetcher.search(args.search)
        print(f"\nSearch results for '{args.search}':")
        for i, v in enumerate(results):
            print(f"  [{i+1}] {v['title'][:70]}")
            print(f"      Channel: {v['channel']} | ID: {v['id']}")

    elif args.download:
        path = fetcher.download(args.download)
        print(f"✓ Downloaded: {path}")

    elif args.build:
        stats = fetcher.build_library(target_count=args.target)
        print(f"\n✓ Library built: {stats['video_count']} videos, {stats['total_size_mb']} MB")

    elif args.random:
        video = fetcher.get_random_video()
        if video:
            print(f"Random video: {video}")
        else:
            print("Library is empty. Run --build first.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
