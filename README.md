<<<<<<< HEAD
# Youtube_miniproject
=======
# 🎧 YouTube Audiobook Pipeline

> Hệ thống tự động hóa sản xuất video audiobook cho YouTube — từ khâu tạo nội dung đến publish.

## 🏗️ Kiến Trúc

```
┌──────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (Celery/CLI)                │
└──────────────────────────────────────────────────────────┘
        │           │           │           │           │
   Module 1     Module 2    Module 3    Module 4    Module 5
   Ingestion    Preprocess  TTS Engine  Assembly    Publish
   (AI Story)   (Clean)     (VieNeu)    (FFmpeg)    (YouTube)
```

## 🚀 Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/sanng1112/Youtube_miniproject.git
cd Youtube_miniproject
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Install VieNeu-TTS (local TTS engine)
git clone https://github.com/pnnbao97/VieNeu-TTS.git /tmp/vieneu
cd /tmp/vieneu && pip install -e . && cd -

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run pipeline
python -m orchestrator.run --story-genre ngon_tinh_hien_dai --publish
```

## 📁 Cấu Trúc Dự Án

```
youtube_audiobook_pipeline/
├── config/                  # Cấu hình hệ thống
│   └── settings.yaml
├── module_1_ingestion/      # Tạo/tải nội dung text
│   └── story_generator.py   # AI viết truyện
├── module_2_preprocessing/  # Làm sạch text
│   └── text_processor.py    # Chuẩn hóa cho TTS
├── module_3_tts/            # Text-to-Speech
│   ├── tts_engine.py        # VieNeu-TTS wrapper
│   └── batch_processor.py   # Xử lý hàng loạt
├── module_4_assembly/       # Ghép video
│   ├── video_composer.py    # FFmpeg 3-panel layout
│   └── thumbnail_gen.py     # Tạo thumbnail
├── module_5_publishing/     # Upload YouTube
│   ├── youtube_uploader.py  # API upload
│   └── seo_generator.py     # Metadata SEO
├── orchestrator/            # Điều phối chính
│   └── run.py               # Main CLI entry
├── docker/                  # Docker setup
├── data/                    # Input/Output data
└── tests/                   # Unit tests
```

## 🎯 Tính Năng Chính

- ✅ **AI tạo truyện hư cấu 100%** — không vi phạm bản quyền
- ✅ **TTS tiếng Việt local** — VieNeu-TTS với giọng nữ Bắc tự nhiên
- ✅ **Voice cloning** — Clone giọng Ngọc Huyền với 3-5s audio mẫu
- ✅ **3-Panel Video Layout** — Title | Mukbang | Channel Info
- ✅ **Tự động upload YouTube** — API v3 + OAuth 2.0
- ✅ **Pipeline tự động hoàn toàn** — Text → Audio → Video → YouTube

## ⚠️ Yêu Cầu

- Python 3.11+
- FFmpeg (cho xử lý video)
- VieNeu-TTS (cho TTS engine - cài đặt riêng)
- YouTube Data API v3 (cho upload)
- OpenAI/Claude API key (cho tạo truyện)

## 📄 License

MIT License — Xem file [LICENSE](LICENSE)
>>>>>>> a2ad162 (Step 1: Initialize project structure)
