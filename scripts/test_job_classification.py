"""Test topic classification on job posts."""
from src.processing.topic_classifier import classify_post_topics

# Sample job post text
text = """Frontend or Fullstack Company: Make Location: Anywhere Level: Middle #full_time Make is seeking a frontend developer with React experience"""

topics = classify_post_topics(text, lang='en')
print(f"Text: {text}")
print(f"Classified topics: {topics}")
