#!/usr/bin/env python3
"""
Test script to verify session mapping in Google Workspace MCP
"""

import requests
import json
import base64

# Test data
ORCHESTRATOR_URL = "https://paestro-orchestrator-mcp-production.up.railway.app"
SESSION_ID = "mfdcly13-jie2drcyyc"  # Your current session ID
COACH_ID = "1ce17ea6-2d4d-4f95-b984-060081e92550"

# Test endpoint
test_url = f"{ORCHESTRATOR_URL}/coach/{COACH_ID}/init-sheets-contacts"

# Headers including session-id
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "secure-orchestrator-key-2024",
    "session-id": SESSION_ID
}

# Body
body = {
    "sheetName": "Test Contacts Sheet"
}

print(f"Testing endpoint: {test_url}")
print(f"Session ID: {SESSION_ID}")
print(f"Headers: {json.dumps(headers, indent=2)}")
print(f"Body: {json.dumps(body, indent=2)}")

try:
    response = requests.post(test_url, headers=headers, json=body)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"\nError: {e}")