@echo off
REM Check Twitter API rate limit status
echo Checking Twitter API rate limits...
python scripts\check_twitter_rate_limit.py
pause
