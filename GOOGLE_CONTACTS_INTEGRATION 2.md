# Google Contacts Integration for Google Workspace MCP

## ✅ Integration Complete

The Google Contacts module has been successfully added to the Google Workspace MCP. This integration provides full access to Google People API for managing contacts.

## 📦 Module Structure

```
google-workspace-mcp/
├── gcontacts/
│   ├── __init__.py          # Python package marker
│   └── contacts_tools.py    # Google People API tools
```

## 🛠️ Available Tools

The following MCP tools are now available:

1. **list_google_contacts** - List all contacts with pagination support
2. **search_google_contacts** - Search contacts by query string
3. **get_google_contact** - Get detailed information about a specific contact
4. **create_google_contact** - Create a new contact
5. **update_google_contact** - Update an existing contact
6. **delete_google_contact** - Delete a contact
7. **batch_get_google_contacts** - Get multiple contacts in one request

## 🚀 Starting the Server

### With All Tools (Including Contacts)
```bash
cd /Users/jarettwesley/Desktop/paestro-project/backend/google-workspace-mcp
source .venv/bin/activate
python main.py --transport streamable-http
```

### With Only Contacts Tool
```bash
cd /Users/jarettwesley/Desktop/paestro-project/backend/google-workspace-mcp
source .venv/bin/activate
python main.py --tools contacts --transport streamable-http
```

### With Specific Tools Including Contacts
```bash
python main.py --tools gmail calendar contacts --transport streamable-http
```

## 🔐 OAuth Scopes

The contacts module requires the following Google OAuth scopes:
- `https://www.googleapis.com/auth/contacts` - Full access to contacts
- `https://www.googleapis.com/auth/contacts.readonly` - Read-only access
- `https://www.googleapis.com/auth/contacts.other.readonly` - Read other contacts
- `https://www.googleapis.com/auth/directory.readonly` - Directory access

These scopes are automatically requested when a user authenticates with Google.

## 📡 API Endpoints

Once the server is running on port 3003, the Orchestrator MCP will route these patterns to the Google Workspace MCP:

- `/coach/**/google-contacts` → Google Contacts operations
- `/coach/**/google-oauth-status` → OAuth status checks

## 🧪 Testing the Integration

### 1. Start Google Workspace MCP
```bash
cd backend/google-workspace-mcp
source .venv/bin/activate
python main.py --transport streamable-http
```

### 2. Check Server Status
The server should show:
```
🛠️  Loading 11 tool modules:
   📧 Gmail - Google Gmail API integration
   📁 Drive - Google Drive API integration
   📅 Calendar - Google Calendar API integration
   📄 Docs - Google Docs API integration
   📊 Sheets - Google Sheets API integration
   💬 Chat - Google Chat API integration
   📝 Forms - Google Forms API integration
   🖼️ Slides - Google Slides API integration
   ✓ Tasks - Google Tasks API integration
   🔍 Search - Google Search API integration
   👥 Contacts - Google Contacts API integration  ← NEW!
```

### 3. Frontend Will Automatically Use It
The frontend's `googleContactsService.ts` will:
1. Try to fetch from `/coach/{coachId}/google-contacts`
2. If Google Workspace MCP has contacts, it returns real data
3. If not available, falls back to mock data

## 📋 Tool Usage Examples

### List Contacts
```python
await list_google_contacts(
    service,
    user_google_email="user@example.com",
    page_size=50
)
```

### Search Contacts
```python
await search_google_contacts(
    service,
    user_google_email="user@example.com",
    query="John Smith",
    page_size=30
)
```

### Create Contact
```python
await create_google_contact(
    service,
    user_google_email="user@example.com",
    given_name="John",
    family_name="Doe",
    email="john.doe@example.com",
    phone="+1-555-123-4567",
    organization="Acme Corp",
    title="Software Engineer"
)
```

## ✅ Integration Status

- **Module Created**: ✅ Complete
- **Tools Implemented**: ✅ 7 tools available
- **OAuth Scopes Added**: ✅ People API scopes configured
- **Server Integration**: ✅ Registered in main.py
- **Testing**: ✅ Module imports successfully
- **Documentation**: ✅ This file

## 🎯 Next Steps

1. **Deploy Google Workspace MCP** with the new contacts module
2. **Test OAuth Flow** to ensure contacts permissions are granted
3. **Update Frontend** to remove mock data fallback once confirmed working
4. **Monitor Usage** to ensure API quotas are sufficient

## 🔧 Troubleshooting

### Module Not Loading
- Ensure `gcontacts/__init__.py` exists
- Check Python path includes the workspace directory
- Verify virtual environment is activated

### OAuth Errors
- User needs to re-authenticate to grant contacts permissions
- Check Google Cloud Console for People API enablement
- Verify OAuth consent screen includes contacts scope

### API Errors
- Enable People API in Google Cloud Console
- Check API quotas and limits
- Verify service account has proper permissions