"""
Module 5: YouTube Publisher
===========================
Tự động upload video lên YouTube với đầy đủ metadata SEO.
Hỗ trợ: upload, lập lịch, thumbnail, playlist.

Yêu cầu:
1. Google Cloud Project với YouTube Data API v3 đã bật
2. OAuth 2.0 Client ID (Desktop application)
3. File client_secrets.json trong thư mục config/

Usage:
    from module_5_publishing import YouTubePublisher

    pub = YouTubePublisher(client_secrets_file="config/client_secrets.json")
    pub.upload_video(
        video_file="output/chapter_01.mp4",
        metadata={
            "title": "AUDIO | TÊN TRUYỆN | Channel #audio",
            "description": "...",
            "tags": ["truyen audio", "audio"],
        }
    )
"""

import json
import os
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False
    logger.warning(
        "Google API packages not installed. Run: "
        "pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )


class YouTubePublisher:
    """
    Upload videos to YouTube with full metadata control.

    Features:
    - OAuth 2.0 authentication with token persistence
    - Resumable uploads with progress tracking
    - Custom thumbnail upload
    - Playlist insertion
    - Scheduled publishing
    - Bulk upload
    """

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    CATEGORY_ENTERTAINMENT = "24"
    CATEGORY_MUSIC = "10"
    CATEGORY_PEOPLE = "22"

    def __init__(
        self,
        client_secrets_file: str = "config/client_secrets.json",
        token_file: str = "config/token.pickle",
        api_key: Optional[str] = None,
    ):
        """
        Initialize YouTube publisher.

        Args:
            client_secrets_file: OAuth 2.0 client secrets JSON
            token_file: Path to save/load OAuth token
            api_key: YouTube Data API v3 key (for read-only operations)
        """
        if not HAS_GOOGLE_API:
            raise ImportError(
                "Google API packages required. "
                "pip install google-api-python-client google-auth-oauthlib"
            )

        self.client_secrets_file = Path(client_secrets_file)
        self.token_file = Path(token_file)
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")

        self.youtube = None
        self._authenticated = False

    # ============================================================
    # Authentication
    # ============================================================
    def authenticate(self, force: bool = False):
        """
        Authenticate with YouTube OAuth 2.0.

        On first run, opens a browser for authorization.
        Token is saved for subsequent runs.

        Args:
            force: Force re-authentication even if token exists
        """
        credentials = None

        # Load saved token
        if not force and self.token_file.exists():
            with open(self.token_file, "rb") as token:
                credentials = pickle.load(token)
            logger.debug("Loaded saved OAuth token")

        # Refresh or create new credentials
        if not credentials or not credentials.valid:
            if (
                credentials
                and credentials.expired
                and credentials.refresh_token
            ):
                logger.info("Refreshing expired OAuth token...")
                credentials.refresh(Request())
            else:
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"Client secrets not found: {self.client_secrets_file}\n"
                        "Download from Google Cloud Console → APIs & Services → Credentials"
                    )

                logger.info("Starting OAuth flow. A browser window will open...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file), self.SCOPES
                )
                credentials = flow.run_local_server(
                    port=0,
                    prompt="consent",
                )

            # Save token for next time
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "wb") as token:
                pickle.dump(credentials, token)
            logger.info(f"OAuth token saved to {self.token_file}")

        self.youtube = build(
            self.API_SERVICE_NAME,
            self.API_VERSION,
            credentials=credentials,
        )
        self._authenticated = True
        logger.info("✓ YouTube authentication successful")

    # ============================================================
    # Upload
    # ============================================================
    def upload_video(
        self,
        video_file: str,
        metadata: Dict,
        privacy: str = "private",
    ) -> Dict:
        """
        Upload a video to YouTube.

        Args:
            video_file: Path to video file (MP4)
            metadata: Video metadata dict with keys:
                - title (str, required, max 100 chars)
                - description (str, max 5000 chars)
                - tags (list of str, max 20)
                - categoryId (str, default "24" = Entertainment)
                - thumbnail (str, path to thumbnail image)
                - publishAt (str, ISO 8601 datetime for scheduled publish)
                - playlist_id (str, add to playlist after upload)
                - made_for_kids (bool, default False)
            privacy: "private", "unlisted", or "public"

        Returns:
            Dict with video_id and url
        """
        if not self._authenticated:
            self.authenticate()

        video_path = Path(video_file)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_file}")

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"Uploading: {video_path.name} ({file_size_mb:.1f} MB)")

        # Build request body
        body = {
            "snippet": {
                "title": metadata.get("title", video_path.stem)[:100],
                "description": metadata.get("description", "")[:5000],
                "tags": metadata.get("tags", [])[:20],
                "categoryId": metadata.get(
                    "categoryId", self.CATEGORY_ENTERTAINMENT
                ),
                "defaultLanguage": "vi",
                "defaultAudioLanguage": "vi",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": metadata.get("made_for_kids", False),
            },
        }

        # Handle scheduled publishing
        publish_at = metadata.get("publishAt")
        if publish_at:
            body["status"]["publishAt"] = publish_at
            body["status"]["privacyStatus"] = "private"
            logger.info(f"  Scheduled for: {publish_at}")

        # Upload with progress tracking
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/*",
            resumable=True,
            chunksize=5 * 1024 * 1024,  # 5MB chunks
        )

        request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        last_progress = -1
        start_time = time.time()

        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                # Only log every 10% to reduce noise
                if progress - last_progress >= 10:
                    elapsed = time.time() - start_time
                    speed = file_size_mb / (elapsed / 60) if elapsed > 0 else 0
                    logger.info(f"  Upload: {progress}% ({speed:.1f} MB/min)")
                    last_progress = progress

        video_id = response["id"]
        elapsed = time.time() - start_time
        logger.info(
            f"✓ Upload complete: https://youtube.com/watch?v={video_id} "
            f"({elapsed:.0f}s)"
        )

        # Upload thumbnail if provided
        thumbnail_path = metadata.get("thumbnail")
        if thumbnail_path and Path(thumbnail_path).exists():
            self.set_thumbnail(video_id, thumbnail_path)

        # Add to playlist if specified
        playlist_id = metadata.get("playlist_id")
        if playlist_id:
            self.add_to_playlist(video_id, playlist_id)

        return {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "upload_time_seconds": round(elapsed, 1),
        }

    # ============================================================
    # Thumbnail
    # ============================================================
    def set_thumbnail(self, video_id: str, thumbnail_path: str):
        """Set custom thumbnail for a video."""
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(
                    thumbnail_path, mimetype="image/jpeg"
                ),
            ).execute()
            logger.info(f"  ✓ Thumbnail set: {Path(thumbnail_path).name}")
        except HttpError as e:
            logger.error(f"  ✗ Thumbnail failed: {e}")

    # ============================================================
    # Playlist
    # ============================================================
    def add_to_playlist(self, video_id: str, playlist_id: str):
        """Add video to a playlist."""
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            ).execute()
            logger.info(f"  ✓ Added to playlist: {playlist_id}")
        except HttpError as e:
            logger.error(f"  ✗ Playlist add failed: {e}")

    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy: str = "public",
    ) -> str:
        """Create a new playlist and return its ID."""
        response = (
            self.youtube.playlists()
            .insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                    },
                    "status": {"privacyStatus": privacy},
                },
            )
            .execute()
        )
        playlist_id = response["id"]
        logger.info(f"✓ Playlist created: {title} (ID: {playlist_id})")
        return playlist_id

    # ============================================================
    # Bulk Upload
    # ============================================================
    def bulk_upload(
        self,
        video_metadata_file: str,
        privacy: str = "private",
        delay_seconds: int = 60,
    ) -> List[Dict]:
        """
        Upload multiple videos from a metadata JSON file.

        Args:
            video_metadata_file: JSON file with list of video metadata
            privacy: Default privacy setting
            delay_seconds: Delay between uploads (respect rate limits)

        Returns:
            List of upload results
        """
        with open(video_metadata_file, "r", encoding="utf-8") as f:
            videos_meta = json.load(f)

        if isinstance(videos_meta, dict):
            videos_meta = videos_meta.get("videos", [])

        results = []
        for i, meta in enumerate(videos_meta):
            video_file = meta.get("file", "")
            if not Path(video_file).exists():
                logger.warning(f"Video not found: {video_file}, skipping")
                continue

            logger.info(f"\n[{i+1}/{len(videos_meta)}] {Path(video_file).name}")

            try:
                result = self.upload_video(
                    video_file=video_file,
                    metadata=meta,
                    privacy=privacy,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"  ✗ Upload failed: {e}")
                continue

            # Respect rate limits
            if i < len(videos_meta) - 1:
                time.sleep(delay_seconds)

        logger.info(
            f"\nBulk upload complete: {len(results)}/{len(videos_meta)} videos"
        )
        return results

    def upload_story_videos(
        self,
        output_dir: str,
        story_id: str,
        privacy: str = "private",
    ) -> List[Dict]:
        """
        Upload all chapter videos from a story output directory.

        Args:
            output_dir: Directory with video_metadata.json
            story_id: Story ID
            privacy: Privacy setting

        Returns:
            List of upload results
        """
        metadata_file = Path(output_dir) / story_id / "video_metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Video metadata not found: {metadata_file}")

        return self.bulk_upload(str(metadata_file), privacy)


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    """CLI for YouTube publishing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload audiobook videos to YouTube"
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Single video file to upload"
    )
    parser.add_argument(
        "--title", type=str, default=None,
        help="Video title"
    )
    parser.add_argument(
        "--description", type=str, default=None,
        help="Video description"
    )
    parser.add_argument(
        "--tags", type=str, default="truyen audio,audio,truyen hay",
        help="Comma-separated tags"
    )
    parser.add_argument(
        "--thumbnail", type=str, default=None,
        help="Thumbnail image path"
    )
    parser.add_argument(
        "--privacy", type=str, default="private",
        choices=["private", "unlisted", "public"],
        help="Privacy setting"
    )
    parser.add_argument(
        "--bulk", type=str, default=None,
        help="Bulk upload from video_metadata.json"
    )
    parser.add_argument(
        "--secrets", type=str, default="config/client_secrets.json",
        help="OAuth client secrets file"
    )
    parser.add_argument(
        "--schedule", type=str, default=None,
        help="ISO 8601 publish time (e.g., 2026-06-01T12:00:00Z)"
    )

    args = parser.parse_args()

    publisher = YouTubePublisher(client_secrets_file=args.secrets)

    if args.bulk:
        publisher.bulk_upload(args.bulk, args.privacy)

    elif args.video:
        if not args.title:
            parser.error("--title is required for single upload")

        metadata = {
            "title": args.title,
            "description": args.description or "",
            "tags": [t.strip() for t in args.tags.split(",")],
            "thumbnail": args.thumbnail,
        }
        if args.schedule:
            metadata["publishAt"] = args.schedule

        result = publisher.upload_video(
            args.video, metadata, args.privacy
        )
        print(f"\n✓ Video uploaded: {result['url']}")

    else:
        parser.error("Provide --video or --bulk")


if __name__ == "__main__":
    main()
