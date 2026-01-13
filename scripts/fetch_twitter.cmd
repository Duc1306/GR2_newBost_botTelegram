@echo off
REM Fetch tweets from configured Twitter sources
echo Starting Twitter ingestion...
python -m src.ingestion.twitter_worker %*
