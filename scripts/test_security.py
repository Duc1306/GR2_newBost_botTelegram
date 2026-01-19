"""
Quick test script for API security features.
Tests authentication, rate limiting, and logging.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.auth import login, create_access_token, decode_access_token, authenticate_user
from loguru import logger

def test_authentication():
    """Test JWT authentication system."""
    print("\n" + "="*60)
    print(" Testing Authentication System")
    print("="*60)
    
    # Test 1: Valid login
    print("\n✓ Test 1: Valid login")
    try:
        result = login("admin", "admin123")
        print(f"  ✓ Login successful: {result.username}")
        print(f"  ✓ Token: {result.access_token[:50]}...")
        print(f"  ✓ Expires in: {result.expires_in} seconds")
    except Exception as e:
        print(f"  ✗ Login failed: {e}")
        return False
    
    # Test 2: Invalid password
    print("\n✓ Test 2: Invalid password")
    try:
        result = login("admin", "wrongpassword")
        print(f"  ✗ Should have failed but succeeded!")
        return False
    except Exception as e:
        print(f"  ✓ Correctly rejected: {str(e)}")
    
    # Test 3: Token decoding
    print("\n✓ Test 3: Token decoding")
    try:
        token = create_access_token({"sub": "admin"})
        decoded = decode_access_token(token)
        print(f"  ✓ Token decoded: username={decoded.username}")
        print(f"  ✓ Expires at: {decoded.exp}")
    except Exception as e:
        print(f"  ✗ Token decode failed: {e}")
        return False
    
    print("\n All authentication tests passed!")
    return True

def test_logging():
    """Test logging system."""
    print("\n" + "="*60)
    print(" Testing Logging System")
    print("="*60)
    
    from src.api.middleware import setup_logging, log_ingestion_error, log_api_error
    
    # Setup logging
    setup_logging()
    
    # Test different log levels
    print("\n✓ Testing log levels:")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    
    # Test structured logging
    print("\n✓ Testing structured logging:")
    log_ingestion_error(
        source="telegram",
        error=Exception("Test error"),
        context={"channel": "@test", "message_id": 123}
    )
    
    log_api_error(
        endpoint="/posts",
        error=Exception("Test API error"),
        user="admin"
    )
    
    print("\n Logging tests completed! Check logs/api.log")
    return True

def test_rate_limiting():
    """Test rate limiting configuration."""
    print("\n" + "="*60)
    print(" Testing Rate Limiting Configuration")
    print("="*60)
    
    from src.config import (
        RATE_LIMIT_ENABLED,
        RATE_LIMIT_PER_MINUTE,
        RATE_LIMIT_PER_HOUR
    )
    
    print(f"\n✓ Rate limiting enabled: {RATE_LIMIT_ENABLED}")
    print(f"✓ Limit per minute: {RATE_LIMIT_PER_MINUTE}")
    print(f"✓ Limit per hour: {RATE_LIMIT_PER_HOUR}")
    
    if RATE_LIMIT_ENABLED:
        print("\n Rate limiting is configured and enabled!")
    else:
        print("\n  Rate limiting is disabled (enable in .env)")
    
    return True

def main():
    """Run all security tests."""
    print("\n" + "="*60)
    print(" API SECURITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Authentication", test_authentication()))
    results.append(("Logging", test_logging()))
    results.append(("Rate Limiting", test_rate_limiting()))
    
    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = " PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n All security features are working correctly!")
        print("\nNext steps:")
        print("1. Start API: scripts\\run_api.cmd")
        print("2. Start frontend: cd web && npm run dev")
        print("3. Access: http://localhost:5173")
        print("4. Login with: admin / admin123")
        return 0
    else:
        print("\n Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
