"""Module: cleaning
Các hàm làm sạch văn bản: chuẩn hóa khoảng trắng, tách link, bỏ ký tự không cần thiết.
"""
from __future__ import annotations
import re
from typing import List, Tuple

URL_REGEX = re.compile(r"https?://\S+")
WHITESPACE_REGEX = re.compile(r"\s+")
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")  # vùng emoji mở rộng


def extract_links(text: str) -> Tuple[str, List[str]]:
    links = URL_REGEX.findall(text)
    without_links = URL_REGEX.sub("", text)
    return without_links.strip(), links


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_REGEX.sub(" ", text).strip()


def remove_emojis(text: str) -> str:
    return EMOJI_REGEX.sub("", text)


def clean_text(raw: str) -> Tuple[str, List[str]]:
    """Chuỗi xử lý chính.
    Steps:
      1. Tách link
      2. Bỏ emoji
      3. Chuẩn hóa khoảng trắng
    Trả về: (text_sạch, list_link)
    """
    tmp, links = extract_links(raw)
    tmp = remove_emojis(tmp)
    tmp = normalize_whitespace(tmp)
    return tmp, links

if __name__ == "__main__":
    sample = "Hello   world!!!  https://example.com 😀😀"
    cleaned, links = clean_text(sample)
    print(cleaned, links)
