"""Script to verify Telegram channels exist and are accessible.
Kiểm tra các kênh Telegram có tồn tại và hoạt động không.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError
from src.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION_STRING,
    env_channels
)
import argparse
from datetime import datetime, timedelta


async def verify_channels(channels: list[str], check_activity: bool = True):
    """
    Verify that channels exist and optionally check activity.
    
    Args:
        channels: List of channel usernames
        check_activity: If True, check if channel has recent posts
    """
    # Create client from session string
    from telethon.sessions import StringSession
    
    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )
    
    try:
        # Connect
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session not authorized!")
            print("Please run: python scripts/create_session.py")
            return
            
        print(f"\n✓ Connected to Telegram")
        print(f"Checking {len(channels)} channels...\n")
        print("="*80)
        
        valid_channels = []
        invalid_channels = []
        inactive_channels = []
        
        for i, channel_username in enumerate(channels, 1):
            channel_username = channel_username.strip()
            if not channel_username:
                continue
                
            try:
                # Get channel entity
                entity = await client.get_entity(channel_username)
                
                # Get basic info
                title = getattr(entity, 'title', 'N/A')
                member_count = getattr(entity, 'participants_count', None)
                
                # Check activity if requested
                last_post = None
                post_count_7days = 0
                is_active = True
                
                if check_activity:
                    try:
                        # Get last 20 messages
                        messages = await client.get_messages(entity, limit=20)
                        
                        if messages:
                            last_post = messages[0].date
                            
                            # Count posts in last 7 days
                            seven_days_ago = datetime.now() - timedelta(days=7)
                            post_count_7days = sum(
                                1 for msg in messages 
                                if msg.date and msg.date > seven_days_ago
                            )
                            
                            # Consider inactive if no posts in last 7 days
                            if post_count_7days == 0:
                                is_active = False
                    except Exception as e:
                        print(f"⚠️  {i}. @{channel_username} - Cannot check activity: {e}")
                
                # Print result
                status = "✓" if is_active else "⚠️ "
                print(f"{status} {i}. @{channel_username}")
                print(f"     Title: {title}")
                if member_count is not None:
                    print(f"     Members: {member_count:,}")
                if last_post:
                    print(f"     Last post: {last_post.strftime('%Y-%m-%d %H:%M')}")
                    print(f"     Posts (7 days): {post_count_7days}")
                
                if is_active:
                    valid_channels.append(channel_username)
                else:
                    inactive_channels.append(channel_username)
                    print(f"     ⚠️  INACTIVE (no posts in 7 days)")
                
                print()
                
            except (UsernameInvalidError, UsernameNotOccupiedError):
                print(f"❌ {i}. @{channel_username} - NOT FOUND (invalid username)")
                invalid_channels.append(channel_username)
                print()
            except ChannelPrivateError:
                print(f"❌ {i}. @{channel_username} - PRIVATE (cannot access)")
                invalid_channels.append(channel_username)
                print()
            except Exception as e:
                print(f"❌ {i}. @{channel_username} - ERROR: {e}")
                invalid_channels.append(channel_username)
                print()
            
            # Rate limiting
            await asyncio.sleep(1)
        
        # Summary
        print("="*80)
        print("\n📊 SUMMARY")
        print("="*80)
        print(f"✓ Valid & Active: {len(valid_channels)}")
        print(f"⚠️  Inactive: {len(inactive_channels)}")
        print(f"❌ Invalid/Private: {len(invalid_channels)}")
        print(f"Total checked: {len(channels)}")
        
        # Show invalid channels
        if invalid_channels:
            print("\n❌ INVALID/PRIVATE CHANNELS (remove from .env):")
            for ch in invalid_channels:
                print(f"   - {ch}")
        
        # Show inactive channels
        if inactive_channels:
            print("\n⚠️  INACTIVE CHANNELS (no posts in 7 days):")
            for ch in inactive_channels:
                print(f"   - {ch}")
        
        # Generate updated .env line
        if valid_channels:
            print("\n✅ RECOMMENDED TELEGRAM_CHANNELS for .env:")
            print("="*80)
            # Group by 5 channels per line for readability
            grouped = [valid_channels[i:i+5] for i in range(0, len(valid_channels), 5)]
            env_value = "TELEGRAM_CHANNELS=" + ";\\\n".join(
                ";".join(group) for group in grouped
            )
            print(env_value)
            
    finally:
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Verify Telegram channels")
    parser.add_argument('--no-activity-check', action='store_true',
                       help='Skip activity check (faster)')
    parser.add_argument('--channels', type=str,
                       help='Comma-separated list of channels to check (default: from .env)')
    args = parser.parse_args()
    
    print("="*80)
    print("TELEGRAM CHANNEL VERIFICATION")
    print("="*80)
    
    # Get channels to check
    if args.channels:
        channels = [ch.strip() for ch in args.channels.split(',')]
    else:
        channels = env_channels()
    
    if not channels:
        print("❌ No channels to check!")
        print("Add channels to .env TELEGRAM_CHANNELS or use --channels flag")
        return
    
    # Run verification
    asyncio.run(verify_channels(
        channels,
        check_activity=not args.no_activity_check
    ))
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Remove invalid/private channels from .env")
    print("2. Consider removing inactive channels")
    print("3. Update TELEGRAM_CHANNELS in .env with recommended list")
    print("4. Run: scripts\\fetch_telegram.cmd --full")
    print("="*80)


if __name__ == "__main__":
    main()
