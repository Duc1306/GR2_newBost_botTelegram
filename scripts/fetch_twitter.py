#!/usr/bin/env python3
"""Wrapper script to run Twitter ingestion worker."""
import sys
from src.ingestion.twitter_worker import main

if __name__ == "__main__":
    main()
