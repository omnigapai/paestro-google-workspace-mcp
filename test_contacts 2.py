#!/usr/bin/env python3
"""
Test script to verify Google Contacts module is loaded correctly
"""

import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add current directory to path
sys.path.append('.')

# Try importing the module
try:
    import gcontacts.contacts_tools as contacts
    print("✅ Google Contacts module imported successfully!")
    
    # List all tools in the module
    tools = [
        'list_google_contacts',
        'search_google_contacts', 
        'get_google_contact',
        'create_google_contact',
        'update_google_contact',
        'delete_google_contact',
        'batch_get_google_contacts'
    ]
    
    for tool in tools:
        if hasattr(contacts, tool):
            print(f"  ✅ {tool} - Found")
        else:
            print(f"  ❌ {tool} - Missing")
    
    print("\n👥 Google Contacts module is ready to use!")
    print("\nTo start the server with contacts support:")
    print("  python main.py --transport streamable-http")
    print("  or")
    print("  python main.py --tools contacts")
    
except ImportError as e:
    print(f"❌ Failed to import contacts module: {e}")
    sys.exit(1)