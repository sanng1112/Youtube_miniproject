# YouTube Audiobook Pipeline - Makefile
# ======================================

.PHONY: help install run generate tts assemble upload pipeline clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	pip install -r requirements.txt
	@echo "VieNeu-TTS must be installed separately:"
	@echo "  git clone https://github.com/pnnbao97/VieNeu-TTS.git"
	@echo "  cd VieNeu-TTS && pip install -e ."

run:  ## Run full pipeline (generate → TTS → video)
	python -m orchestrator.run --full

generate:  ## Generate a story
	python -m orchestrator.run --generate --genre ngon_tinh_hien_dai

batch:  ## Generate 5 stories in batch
	python -m orchestrator.run --batch 5

tts:  ## TTS from existing story (usage: make tts STORY=data/stories/xxx.json)
	python -m orchestrator.run --tts --story $(STORY)

assemble:  ## Assemble video from audio (usage: make assemble ID=abc123)
	python -m orchestrator.run --assemble --story-id $(ID)

upload:  ## Upload to YouTube (usage: make upload ID=abc123)
	python -m orchestrator.run --upload --story-id $(ID) --privacy private

pipeline:  ## Full pipeline + YouTube upload
	python -m orchestrator.run --full --publish

list:  ## List all generated stories
	python -m orchestrator.run --list-stories

library:  ## Build mukbang video library
	python -m orchestrator.run --build-library --library-count 20

clean:  ## Clean generated files
	rm -rf data/audio/* data/video/* data/thumbnails/*
	@echo "Cleaned generated files (stories preserved)"

clean-all:  ## Clean everything including stories
	rm -rf data/audio/* data/video/* data/thumbnails/* data/stories/*
	@echo "Cleaned all data"

docker-build:  ## Build Docker image
	docker compose -f docker/docker-compose.yml build

docker-run:  ## Run pipeline in Docker
	docker compose -f docker/docker-compose.yml run pipeline python -m orchestrator.run --full

test:  ## Run tests
	python -m pytest tests/ -v

lint:  ## Lint code
	python -m flake8 module_* orchestrator/ --max-line-length=100
