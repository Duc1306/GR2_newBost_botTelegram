"""Script tạo session string cho Telethon.
Chạy một lần để đăng nhập (nhập SĐT + OTP), sau đó copy session string vào .env
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telethon import TelegramClient
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH

async def main():
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Thiếu TELEGRAM_API_ID hoặc TELEGRAM_API_HASH trong .env")
        print("   Vào https://my.telegram.org/apps để lấy.")
        return
    
    print("🔐 Đăng nhập Telegram để tạo session string...")
    print(f"   API ID: {TELEGRAM_API_ID}")
    
    client = TelegramClient(StringSession(), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("📱 Nhập số điện thoại (bắt đầu bằng +84...): ")
        await client.send_code_request(phone)
        code = input("🔢 Nhập mã OTP từ Telegram: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            print(f"❌ Lỗi đăng nhập: {e}")
            password = input("🔒 Nếu có 2FA, nhập password: ")
            await client.sign_in(password=password)
    
    session_string = client.session.save()
    print("\n✅ Đăng nhập thành công!")
    print("📋 Session string (copy vào .env dòng TELEGRAM_SESSION_STRING):\n")
    print(session_string)
    print("\n💡 Lưu ý: Giữ session string bí mật, không commit vào git.")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
