"""
Inter-Service Client for Google Workspace MCP
Enables direct communication with Main MCP for enterprise-scale operations
"""

import os
import json
import uuid
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

class InterServiceClient:
    """Client for making direct calls to other MCPs without going through Orchestrator"""
    
    # Service URLs (from environment or defaults)
    SERVICE_URLS = {
        'main-platform': os.getenv('MAIN_PLATFORM_URL', 'https://paestro-mcp-modular-production.up.railway.app'),
        'orchestrator': os.getenv('ORCHESTRATOR_URL', 'https://paestro-orchestrator-mcp-production.up.railway.app'),
        'textbee': os.getenv('TEXTBEE_URL', 'https://paestro-textbee-server-production.up.railway.app')
    }
    
    def __init__(self, service_name: str = 'google-workspace'):
        self.service_name = service_name
        self.service_key = os.getenv('GOOGLE_WORKSPACE_SERVICE_KEY', 'gw-secret-key-default')
        self.session = None
        
        # Setup token cache directory
        self.cache_dir = Path('/tmp/google-workspace-mcp-cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.token_cache_file = self.cache_dir / 'oauth_tokens.json'
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def call_service(
        self, 
        target_service: str, 
        endpoint: str, 
        method: str = 'POST', 
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make a direct call to another MCP service
        
        Args:
            target_service: Name of the target service (e.g., 'main-platform')
            endpoint: The endpoint path (e.g., '/internal/store-oauth-tokens')
            method: HTTP method (GET, POST, etc.)
            data: Request body data
            timeout: Request timeout in seconds
            
        Returns:
            Response data from the target service
        """
        if target_service not in self.SERVICE_URLS:
            raise ValueError(f"Unknown target service: {target_service}")
            
        url = f"{self.SERVICE_URLS[target_service]}{endpoint}"
        request_id = str(uuid.uuid4())
        
        headers = {
            'Content-Type': 'application/json',
            'x-service-name': self.service_name,
            'x-service-key': self.service_key,
            'x-request-id': request_id
        }
        
        logger.info(f"[{request_id}] Inter-service call: {self.service_name} -> {target_service}{endpoint}")
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method != 'GET' else None,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = await response.json()
                
                if response.status >= 400:
                    logger.error(f"[{request_id}] Service call failed: {response.status} - {result}")
                    raise Exception(f"Service call failed: {result.get('error', 'Unknown error')}")
                    
                logger.info(f"[{request_id}] Service call successful")
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"[{request_id}] Service call timeout after {timeout}s")
            raise Exception(f"Service call to {target_service} timed out")
        except Exception as e:
            logger.error(f"[{request_id}] Service call error: {str(e)}")
            raise
            
    async def store_oauth_tokens(
        self, 
        tokens: Dict[str, Any], 
        coach_id: str, 
        coach_email: str
    ) -> Dict[str, Any]:
        """
        Store OAuth tokens directly in Main MCP's Supabase
        AND cache them locally for reuse
        
        Args:
            tokens: OAuth token data from Google
            coach_id: Coach UUID
            coach_email: Coach email address
            
        Returns:
            Storage confirmation from Main MCP
        """
        logger.info(f"Storing OAuth tokens for coach {coach_id[:8]}... directly to Main MCP")
        
        # Store to Supabase via Main MCP
        result = await self.call_service(
            target_service='main-platform',
            endpoint='/internal/store-oauth-tokens',
            method='POST',
            data={
                'tokens': tokens,
                'coachId': coach_id,
                'coachEmail': coach_email
            }
        )
        
        # Cache tokens locally for this coach
        if result.get('success'):
            await self._cache_tokens(coach_id, coach_email, tokens)
            logger.info(f"Cached OAuth tokens locally for coach {coach_id[:8]}...")
        
        return result
        
    async def _cache_tokens(self, coach_id: str, coach_email: str, tokens: Dict[str, Any]):
        """
        Cache tokens locally in a JSON file
        
        Args:
            coach_id: Coach UUID
            coach_email: Coach email address
            tokens: OAuth token data
        """
        try:
            # Load existing cache
            cache = {}
            if self.token_cache_file.exists():
                with open(self.token_cache_file, 'r') as f:
                    cache = json.load(f)
            
            # Update cache with new tokens
            cache[coach_id] = {
                'email': coach_email,
                'tokens': tokens,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            # Save updated cache
            with open(self.token_cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to cache tokens: {e}")
    
    async def get_oauth_tokens(self, coach_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth tokens from local cache or Supabase
        
        Args:
            coach_id: Coach UUID
            
        Returns:
            OAuth tokens if found, None otherwise
        """
        # First check local cache
        try:
            if self.token_cache_file.exists():
                with open(self.token_cache_file, 'r') as f:
                    cache = json.load(f)
                    if coach_id in cache:
                        logger.info(f"Found cached OAuth tokens for coach {coach_id[:8]}...")
                        return cache[coach_id]['tokens']
        except Exception as e:
            logger.error(f"Error reading token cache: {e}")
        
        # If not in cache, fetch from Supabase via Main MCP
        logger.info(f"No cached tokens, fetching from Supabase for coach {coach_id[:8]}...")
        try:
            result = await self.call_service(
                target_service='main-platform',
                endpoint=f'/internal/get-oauth-tokens/{coach_id}',
                method='GET'
            )
            
            if result.get('success') and result.get('tokens'):
                # Cache the retrieved tokens
                await self._cache_tokens(
                    coach_id, 
                    result.get('email', ''),
                    result['tokens']
                )
                return result['tokens']
                
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth tokens from Supabase: {e}")
        
        return None
    
    async def get_coach_context(self, coach_id: str) -> Dict[str, Any]:
        """
        Get coach context directly from Main MCP
        
        Args:
            coach_id: Coach UUID
            
        Returns:
            Coach context data
        """
        return await self.call_service(
            target_service='main-platform',
            endpoint=f'/internal/get-coach-context/{coach_id}',
            method='GET'
        )
        
    async def send_oauth_confirmation_sms(
        self, 
        phone_number: str, 
        coach_name: str
    ) -> Dict[str, Any]:
        """
        Send OAuth confirmation SMS via TextBee MCP
        
        Args:
            phone_number: Coach phone number
            coach_name: Coach name for personalization
            
        Returns:
            SMS send confirmation
        """
        return await self.call_service(
            target_service='textbee',
            endpoint='/internal/send-oauth-confirmation',
            method='POST',
            data={
                'phone_number': phone_number,
                'coach_name': coach_name,
                'message': f"Hi {coach_name}! Your Google Workspace is now connected to Paestro. You can access your calendar and contacts from your dashboard."
            }
        )


# Singleton instance for reuse
_inter_service_client = None

def get_inter_service_client() -> InterServiceClient:
    """Get or create the singleton inter-service client"""
    global _inter_service_client
    if _inter_service_client is None:
        _inter_service_client = InterServiceClient()
    return _inter_service_client


# Example usage in OAuth handler
async def handle_oauth_with_direct_storage(code: str, coach_id: str, coach_email: str):
    """
    Example of how to use inter-service communication in OAuth flow
    """
    # Step 1: Exchange code for tokens with Google
    tokens = await exchange_code_for_tokens(code)  # Your existing function
    
    # Step 2: Store tokens directly in Main MCP (bypassing Orchestrator)
    async with InterServiceClient() as client:
        storage_result = await client.store_oauth_tokens(
            tokens=tokens,
            coach_id=coach_id,
            coach_email=coach_email
        )
        
        # Optional Step 3: Send confirmation SMS
        if storage_result.get('success'):
            # Get coach details for SMS
            coach_context = await client.get_coach_context(coach_id)
            if coach_phone := coach_context.get('phone'):
                await client.send_oauth_confirmation_sms(
                    phone_number=coach_phone,
                    coach_name=coach_context.get('name', 'Coach')
                )
    
    return {
        'success': True,
        'tokens': tokens,
        'storage': storage_result
    }