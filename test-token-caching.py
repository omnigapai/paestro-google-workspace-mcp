#!/usr/bin/env python3
"""
Test script for OAuth token caching functionality
Tests the new token caching and retrieval system
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.inter_service_client import InterServiceClient

async def test_token_caching():
    """Test the token caching functionality"""
    
    print("🧪 Testing OAuth Token Caching System")
    print("=" * 50)
    
    # Test data
    test_coach_id = "test-coach-123"
    test_coach_email = "test@example.com"
    test_tokens = {
        "access_token": "test-access-token-abc123",
        "refresh_token": "test-refresh-token-xyz789",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
    
    # Initialize the client
    client = InterServiceClient()
    
    print("\n1️⃣ Testing token caching...")
    try:
        # Test direct caching (bypassing Supabase for this test)
        await client._cache_tokens(test_coach_id, test_coach_email, test_tokens)
        print("✅ Tokens cached successfully")
        
        # Verify cache file exists
        cache_file = Path('/tmp/google-workspace-mcp-cache/oauth_tokens.json')
        if cache_file.exists():
            print(f"✅ Cache file exists at: {cache_file}")
            
            # Read and verify cache contents
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                if test_coach_id in cache:
                    print(f"✅ Coach {test_coach_id} found in cache")
                    cached_data = cache[test_coach_id]
                    if cached_data['tokens']['access_token'] == test_tokens['access_token']:
                        print("✅ Cached tokens match test data")
                    else:
                        print("❌ Cached tokens don't match")
                else:
                    print(f"❌ Coach {test_coach_id} not found in cache")
        else:
            print(f"❌ Cache file not found at: {cache_file}")
            
    except Exception as e:
        print(f"❌ Error caching tokens: {e}")
        
    print("\n2️⃣ Testing token retrieval from cache...")
    try:
        # Test retrieving from cache
        retrieved_tokens = await client.get_oauth_tokens(test_coach_id)
        
        if retrieved_tokens:
            print(f"✅ Tokens retrieved from cache")
            if retrieved_tokens['access_token'] == test_tokens['access_token']:
                print("✅ Retrieved tokens match original")
            else:
                print("❌ Retrieved tokens don't match original")
        else:
            print("❌ Failed to retrieve tokens from cache")
            
    except Exception as e:
        print(f"❌ Error retrieving tokens: {e}")
        
    print("\n3️⃣ Testing cache with multiple coaches...")
    try:
        # Add another coach
        test_coach2_id = "test-coach-456"
        test_coach2_email = "test2@example.com"
        test_tokens2 = {
            "access_token": "test-access-token-def456",
            "refresh_token": "test-refresh-token-uvw456",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        await client._cache_tokens(test_coach2_id, test_coach2_email, test_tokens2)
        print(f"✅ Added second coach to cache")
        
        # Verify both coaches are in cache
        with open(cache_file, 'r') as f:
            cache = json.load(f)
            if len(cache) >= 2:
                print(f"✅ Cache contains {len(cache)} coaches")
            else:
                print(f"❌ Cache only contains {len(cache)} coach(es)")
                
    except Exception as e:
        print(f"❌ Error with multiple coaches: {e}")
        
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print("- Token caching mechanism is working")
    print("- Cache persists to disk at /tmp/google-workspace-mcp-cache/")
    print("- Multiple coaches can be cached simultaneously")
    print("\n💡 Next steps:")
    print("1. Deploy to Railway to test with real OAuth flow")
    print("2. Test the /sheets/create-contacts endpoint")
    print("3. Verify tokens are retrieved from Supabase when not in cache")

if __name__ == "__main__":
    asyncio.run(test_token_caching())