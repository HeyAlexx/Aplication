@echo off
cd /d "%~dp0"
python tools\anime_sync_pipeline.py --config config\anime-sync.json --apply --watch --interval 300
pause
