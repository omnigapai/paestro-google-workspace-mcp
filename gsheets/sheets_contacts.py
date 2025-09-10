"""
Google Sheets Contact Management System
Provides bidirectional sync between Paestro and Google Sheets
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from core.server import server

logger = logging.getLogger(__name__)

class SheetsContactManager:
    """Manages contacts in Google Sheets for each coach"""
    
    # Column definitions for the contact sheet
    COLUMNS = [
        'ID',           # Unique identifier
        'Name',         # Full name
        'Email',        # Email address
        'Phone',        # Phone number
        'Organization', # Company/Team
        'Role',         # Role (Student, Parent, Coach, etc.)
        'Notes',        # Additional notes
        'Tags',         # Comma-separated tags
        'Created',      # Creation timestamp
        'Updated',      # Last update timestamp
        'Source'        # Where contact came from (Dashboard, Manual, Import)
    ]
    
    def __init__(self, credentials: Credentials):
        """Initialize with Google credentials"""
        self.service = build('sheets', 'v4', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)
    
    def find_or_create_sheet(self, coach_id: str, sheet_name: str = None) -> str:
        """
        Find existing contact sheet or create a new one
        
        Args:
            coach_id: Coach identifier
            sheet_name: Optional custom sheet name
            
        Returns:
            Spreadsheet ID
        """
        try:
            # Default sheet name if not provided
            if not sheet_name:
                sheet_name = f"Paestro Contacts - Coach {coach_id}"
            
            # Search for existing sheet
            query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                # Sheet exists, return its ID
                spreadsheet_id = files[0]['id']
                logger.info(f"Found existing sheet: {spreadsheet_id}")
                return spreadsheet_id
            
            # Create new sheet
            spreadsheet = {
                'properties': {
                    'title': sheet_name
                },
                'sheets': [{
                    'properties': {
                        'title': 'Contacts',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': len(self.COLUMNS)
                        }
                    }
                }]
            }
            
            sheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = sheet.get('spreadsheetId')
            
            # Add headers
            header_values = [self.COLUMNS]
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Contacts!A1:K1',
                valueInputOption='RAW',
                body={'values': header_values}
            ).execute()
            
            # Format headers (bold, background color)
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.5,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True,
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                }
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Created new sheet: {spreadsheet_id}")
            return spreadsheet_id
            
        except HttpError as error:
            logger.error(f"Error finding/creating sheet: {error}")
            raise
    
    def get_all_contacts(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Get all contacts from the sheet
        
        Args:
            spreadsheet_id: Google Sheets ID
            
        Returns:
            List of contact dictionaries
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Contacts!A:K'
            ).execute()
            
            values = result.get('values', [])
            
            if len(values) <= 1:
                # No data rows, only headers or empty
                return []
            
            headers = values[0]
            contacts = []
            
            for row_index, row in enumerate(values[1:], start=2):
                # Pad row to match header length
                while len(row) < len(headers):
                    row.append('')
                
                contact = {
                    'row': row_index,  # Track row number for updates
                    'id': row[0] if len(row) > 0 else '',
                    'name': row[1] if len(row) > 1 else '',
                    'email': row[2] if len(row) > 2 else '',
                    'phone': row[3] if len(row) > 3 else '',
                    'organization': row[4] if len(row) > 4 else '',
                    'role': row[5] if len(row) > 5 else '',
                    'notes': row[6] if len(row) > 6 else '',
                    'tags': row[7].split(',') if len(row) > 7 and row[7] else [],
                    'createdAt': row[8] if len(row) > 8 else '',
                    'updatedAt': row[9] if len(row) > 9 else '',
                    'source': row[10] if len(row) > 10 else ''
                }
                
                # Only include contacts with at least a name or phone
                if contact['name'] or contact['phone']:
                    contacts.append(contact)
            
            return contacts
            
        except HttpError as error:
            logger.error(f"Error getting contacts: {error}")
            if error.resp.status == 404:
                return []
            raise
    
    def add_contact(self, spreadsheet_id: str, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new contact to the sheet
        
        Args:
            spreadsheet_id: Google Sheets ID
            contact: Contact data
            
        Returns:
            Created contact with ID
        """
        try:
            # Generate unique ID if not provided
            if 'id' not in contact or not contact['id']:
                contact['id'] = str(uuid.uuid4())[:8]
            
            # Set timestamps
            now = datetime.now().isoformat()
            contact['createdAt'] = now
            contact['updatedAt'] = now
            contact['source'] = contact.get('source', 'Dashboard')
            
            # Prepare row data
            row = [
                contact.get('id', ''),
                contact.get('name', ''),
                contact.get('email', ''),
                contact.get('phone', ''),
                contact.get('organization', ''),
                contact.get('role', ''),
                contact.get('notes', ''),
                ','.join(contact.get('tags', [])) if isinstance(contact.get('tags'), list) else contact.get('tags', ''),
                contact.get('createdAt', ''),
                contact.get('updatedAt', ''),
                contact.get('source', '')
            ]
            
            # Append to sheet
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range='Contacts!A:K',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()
            
            logger.info(f"Added contact: {contact['id']}")
            return contact
            
        except HttpError as error:
            logger.error(f"Error adding contact: {error}")
            raise
    
    def update_contact(self, spreadsheet_id: str, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing contact
        
        Args:
            spreadsheet_id: Google Sheets ID
            contact_id: Contact ID to update
            updates: Fields to update
            
        Returns:
            Updated contact
        """
        try:
            # Get all contacts to find the one to update
            contacts = self.get_all_contacts(spreadsheet_id)
            
            target_contact = None
            target_row = None
            
            for contact in contacts:
                if contact['id'] == contact_id:
                    target_contact = contact
                    target_row = contact['row']
                    break
            
            if not target_contact:
                raise ValueError(f"Contact {contact_id} not found")
            
            # Merge updates
            target_contact.update(updates)
            target_contact['updatedAt'] = datetime.now().isoformat()
            
            # Prepare updated row
            row = [
                target_contact.get('id', ''),
                target_contact.get('name', ''),
                target_contact.get('email', ''),
                target_contact.get('phone', ''),
                target_contact.get('organization', ''),
                target_contact.get('role', ''),
                target_contact.get('notes', ''),
                ','.join(target_contact.get('tags', [])) if isinstance(target_contact.get('tags'), list) else target_contact.get('tags', ''),
                target_contact.get('createdAt', ''),
                target_contact.get('updatedAt', ''),
                target_contact.get('source', '')
            ]
            
            # Update the specific row
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'Contacts!A{target_row}:K{target_row}',
                valueInputOption='RAW',
                body={'values': [row]}
            ).execute()
            
            logger.info(f"Updated contact: {contact_id}")
            return target_contact
            
        except HttpError as error:
            logger.error(f"Error updating contact: {error}")
            raise
    
    def delete_contact(self, spreadsheet_id: str, contact_id: str) -> bool:
        """
        Delete a contact (actually clears the row)
        
        Args:
            spreadsheet_id: Google Sheets ID
            contact_id: Contact ID to delete
            
        Returns:
            True if deleted
        """
        try:
            # Get all contacts to find the one to delete
            contacts = self.get_all_contacts(spreadsheet_id)
            
            target_row = None
            for contact in contacts:
                if contact['id'] == contact_id:
                    target_row = contact['row']
                    break
            
            if not target_row:
                raise ValueError(f"Contact {contact_id} not found")
            
            # Clear the row (we don't actually delete to preserve row numbers)
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f'Contacts!A{target_row}:K{target_row}'
            ).execute()
            
            logger.info(f"Deleted contact: {contact_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Error deleting contact: {error}")
            raise
    
    def sync_from_dashboard(self, spreadsheet_id: str, dashboard_contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync contacts from dashboard to Google Sheets
        
        Args:
            spreadsheet_id: Google Sheets ID
            dashboard_contacts: Contacts from dashboard
            
        Returns:
            Sync statistics
        """
        try:
            sheet_contacts = self.get_all_contacts(spreadsheet_id)
            sheet_contacts_by_id = {c['id']: c for c in sheet_contacts}
            
            added = 0
            updated = 0
            
            for contact in dashboard_contacts:
                contact_id = contact.get('id')
                
                if not contact_id:
                    # New contact without ID
                    self.add_contact(spreadsheet_id, contact)
                    added += 1
                elif contact_id in sheet_contacts_by_id:
                    # Existing contact - update if changed
                    sheet_contact = sheet_contacts_by_id[contact_id]
                    if self._has_changes(sheet_contact, contact):
                        self.update_contact(spreadsheet_id, contact_id, contact)
                        updated += 1
                else:
                    # Contact exists in dashboard but not in sheet
                    self.add_contact(spreadsheet_id, contact)
                    added += 1
            
            return {
                'added': added,
                'updated': updated,
                'total_sheet': len(sheet_contacts) + added,
                'total_dashboard': len(dashboard_contacts)
            }
            
        except HttpError as error:
            logger.error(f"Error syncing from dashboard: {error}")
            raise
    
    def _has_changes(self, sheet_contact: Dict[str, Any], dashboard_contact: Dict[str, Any]) -> bool:
        """Check if dashboard contact has changes compared to sheet contact"""
        fields_to_check = ['name', 'email', 'phone', 'organization', 'role', 'notes']
        
        for field in fields_to_check:
            if sheet_contact.get(field, '') != dashboard_contact.get(field, ''):
                return True
        
        return False


# HTTP Route handlers for the Google Workspace MCP server

@server.custom_route("/sheets-contacts/list", ["POST"])
async def sheets_contacts_list(request):
    """Get all contacts from coach's Google Sheet"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        contacts = manager.get_all_contacts(spreadsheet_id)
        
        return {
            'success': True,
            'contacts': contacts,
            'total': len(contacts),
            'spreadsheet_id': spreadsheet_id
        }
        
    except Exception as e:
        logger.error(f"Error getting sheets contacts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.custom_route("/sheets-contacts/add", ["POST"])
async def sheets_contacts_add(request):
    """Add a new contact to coach's Google Sheet"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    contact_data = data.get('contact_data', {})
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        contact = manager.add_contact(spreadsheet_id, contact_data)
        
        return {
            'success': True,
            'contact': contact,
            'message': f"Contact '{contact.get('name', 'Unknown')}' added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding sheets contact: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.custom_route("/sheets-contacts/update", ["POST"])
async def sheets_contacts_update(request):
    """Update a contact in coach's Google Sheet"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    contact_id = data.get('contact_id')
    updates = data.get('updates', {})
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        contact = manager.update_contact(spreadsheet_id, contact_id, updates)
        
        return {
            'success': True,
            'contact': contact,
            'message': 'Contact updated successfully'
        }
        
    except Exception as e:
        logger.error(f"Error updating sheets contact: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.custom_route("/sheets-contacts/delete", ["POST"])
async def sheets_contacts_delete(request):
    """Delete a contact from coach's Google Sheet"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    contact_id = data.get('contact_id')
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        success = manager.delete_contact(spreadsheet_id, contact_id)
        
        return {
            'success': success,
            'message': 'Contact deleted successfully'
        }
        
    except Exception as e:
        logger.error(f"Error deleting sheets contact: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.custom_route("/sheets-contacts/init", ["POST"])
async def sheets_contacts_init(request):
    """Initialize Google Sheet for coach's contacts"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    sheet_name = data.get('sheet_name')
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id, sheet_name)
        
        # Add some example contacts for testing
        example_contacts = [
            {
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'phone': '(555) 123-4567',
                'role': 'Parent',
                'organization': 'Team Eagles',
                'notes': 'Parent of Tommy Smith'
            },
            {
                'name': 'Sarah Johnson',
                'email': 'sarah.j@example.com', 
                'phone': '(555) 987-6543',
                'role': 'Student',
                'organization': 'Team Eagles',
                'notes': 'Pitcher, #12'
            }
        ]
        
        for contact in example_contacts:
            manager.add_contact(spreadsheet_id, contact)
        
        return {
            'success': True,
            'spreadsheet_id': spreadsheet_id,
            'message': 'Google Sheets contact database initialized successfully',
            'sheet_url': f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'
        }
        
    except Exception as e:
        logger.error(f"Error initializing sheets contacts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.custom_route("/sheets-contacts/sync", ["POST"])
async def sheets_contacts_sync(request):
    """Sync contacts between dashboard and Google Sheets"""
    import json
    data = json.loads(request.body) if request.body else {}
    coach_id = data.get('coach_id')
    dashboard_contacts = data.get('dashboard_contacts')
    session = data.get('session')
    from auth.oauth21_session_store import OAuth21SessionStore
    
    try:
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return {
                'success': False,
                'error': 'No session ID provided',
                'requiresAuth': True
            }
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            return {
                'success': False,
                'error': 'No Google account connected',
                'requiresAuth': True
            }
        
        if dashboard_contacts is None:
            dashboard_contacts = []
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        
        # Bidirectional sync
        # 1. Get contacts from sheet
        sheet_contacts = manager.get_all_contacts(spreadsheet_id)
        
        # 2. Sync dashboard contacts to sheet
        sync_stats = manager.sync_from_dashboard(spreadsheet_id, dashboard_contacts)
        
        # 3. Return merged contact list
        all_contacts = manager.get_all_contacts(spreadsheet_id)
        
        return {
            'success': True,
            'contacts': all_contacts,
            'sync_stats': sync_stats,
            'message': f"Synced {sync_stats['added']} new, {sync_stats['updated']} updated contacts"
        }
        
    except Exception as e:
        logger.error(f"Error syncing sheets contacts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Additional REST-style endpoints for coach-specific routes

@server.custom_route("/coach/{coach_id}/sheets-contacts", ["GET", "POST", "OPTIONS"])
async def coach_sheets_contacts(request):
    """GET: List all contacts, POST: Add new contact for specific coach"""
    import json
    from fastapi.responses import JSONResponse
    from auth.oauth21_session_store import OAuth21SessionStore
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return JSONResponse(content={}, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, session-id"
        })
    
    try:
        # Extract coach_id from path
        coach_id = request.path_params.get('coach_id')
        if not coach_id:
            return JSONResponse(
                content={'success': False, 'error': 'Coach ID required'},
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No session ID provided',
                    'requiresAuth': True
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        
        # Debug logging
        logger.info(f"Attempting to retrieve credentials for session ID: {session_id}")
        logger.info(f"Coach ID: {coach_id}")
        
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            # Log available sessions for debugging
            logger.warning(f"No credentials found for session ID: {session_id}")
            logger.info(f"Available MCP sessions: {list(store._mcp_session_mapping.keys())}")
            
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No Google account connected',
                    'requiresAuth': True,
                    'debug': {
                        'session_id': session_id,
                        'available_sessions': list(store._mcp_session_mapping.keys()) if hasattr(store, '_mcp_session_mapping') else []
                    }
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        
        if request.method == "GET":
            # List all contacts
            contacts = manager.get_all_contacts(spreadsheet_id)
            return JSONResponse(
                content={
                    'success': True,
                    'contacts': contacts,
                    'total': len(contacts),
                    'spreadsheet_id': spreadsheet_id
                },
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        elif request.method == "POST":
            # Add new contact
            body = await request.body()
            data = json.loads(body) if body else {}
            contact_data = data.get('contact_data', data)  # Support both formats
            
            contact = manager.add_contact(spreadsheet_id, contact_data)
            return JSONResponse(
                content={
                    'success': True,
                    'contact': contact,
                    'message': f"Contact '{contact.get('name', 'Unknown')}' added successfully"
                },
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
    except Exception as e:
        logger.error(f"Error in coach sheets contacts endpoint: {e}")
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


@server.custom_route("/coach/{coach_id}/sheets-contacts/{contact_id}", ["PUT", "DELETE", "OPTIONS"])
async def coach_sheets_contact_detail(request):
    """PUT: Update contact, DELETE: Delete contact for specific coach"""
    import json
    from fastapi.responses import JSONResponse
    from auth.oauth21_session_store import OAuth21SessionStore
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return JSONResponse(content={}, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, session-id"
        })
    
    try:
        # Extract path parameters
        coach_id = request.path_params.get('coach_id')
        contact_id = request.path_params.get('contact_id')
        
        if not coach_id or not contact_id:
            return JSONResponse(
                content={'success': False, 'error': 'Coach ID and Contact ID required'},
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No session ID provided',
                    'requiresAuth': True
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        
        # Debug logging
        logger.info(f"Attempting to retrieve credentials for session ID: {session_id}")
        logger.info(f"Coach ID: {coach_id}")
        
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            # Log available sessions for debugging
            logger.warning(f"No credentials found for session ID: {session_id}")
            logger.info(f"Available MCP sessions: {list(store._mcp_session_mapping.keys())}")
            
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No Google account connected',
                    'requiresAuth': True,
                    'debug': {
                        'session_id': session_id,
                        'available_sessions': list(store._mcp_session_mapping.keys()) if hasattr(store, '_mcp_session_mapping') else []
                    }
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id)
        
        if request.method == "PUT":
            # Update contact
            body = await request.body()
            data = json.loads(body) if body else {}
            updates = data.get('updates', data)  # Support both formats
            
            contact = manager.update_contact(spreadsheet_id, contact_id, updates)
            return JSONResponse(
                content={
                    'success': True,
                    'contact': contact,
                    'message': 'Contact updated successfully'
                },
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        elif request.method == "DELETE":
            # Delete contact
            success = manager.delete_contact(spreadsheet_id, contact_id)
            return JSONResponse(
                content={
                    'success': success,
                    'message': 'Contact deleted successfully'
                },
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
    except Exception as e:
        logger.error(f"Error in coach sheets contact detail endpoint: {e}")
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


@server.custom_route("/coach/{coach_id}/init-sheets-contacts", ["POST", "OPTIONS"])
async def coach_init_sheets_contacts(request):
    """Initialize Google Sheet for coach's contacts"""
    import json
    from fastapi.responses import JSONResponse
    from auth.oauth21_session_store import OAuth21SessionStore
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return JSONResponse(content={}, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, session-id"
        })
    
    try:
        # Extract coach_id from path
        coach_id = request.path_params.get('coach_id')
        if not coach_id:
            return JSONResponse(
                content={'success': False, 'error': 'Coach ID required'},
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get session ID from headers
        session_id = request.headers.get('session-id')
        if not session_id:
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No session ID provided',
                    'requiresAuth': True
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get credentials from session store
        store = OAuth21SessionStore()
        
        # Debug logging
        logger.info(f"Attempting to retrieve credentials for session ID: {session_id}")
        logger.info(f"Coach ID: {coach_id}")
        
        credentials = store.get_credentials_by_mcp_session(session_id)
        if not credentials:
            # Log available sessions for debugging
            logger.warning(f"No credentials found for session ID: {session_id}")
            logger.info(f"Available MCP sessions: {list(store._mcp_session_mapping.keys())}")
            
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'No Google account connected',
                    'requiresAuth': True,
                    'debug': {
                        'session_id': session_id,
                        'available_sessions': list(store._mcp_session_mapping.keys()) if hasattr(store, '_mcp_session_mapping') else []
                    }
                },
                status_code=401,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get optional sheet name from request body
        body = await request.body()
        data = json.loads(body) if body else {}
        sheet_name = data.get('sheet_name')
        
        manager = SheetsContactManager(credentials)
        spreadsheet_id = manager.find_or_create_sheet(coach_id, sheet_name)
        
        # Add some example contacts for testing
        example_contacts = [
            {
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'phone': '(555) 123-4567',
                'role': 'Parent',
                'organization': 'Team Eagles',
                'notes': 'Parent of Tommy Smith'
            },
            {
                'name': 'Sarah Johnson',
                'email': 'sarah.j@example.com', 
                'phone': '(555) 987-6543',
                'role': 'Student',
                'organization': 'Team Eagles',
                'notes': 'Pitcher, #12'
            }
        ]
        
        for contact in example_contacts:
            manager.add_contact(spreadsheet_id, contact)
        
        return JSONResponse(
            content={
                'success': True,
                'spreadsheet_id': spreadsheet_id,
                'message': 'Google Sheets contact database initialized successfully',
                'sheet_url': f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )
        
    except Exception as e:
        logger.error(f"Error initializing coach sheets contacts: {e}")
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


# Register all HTTP routes
logger.info("Google Sheets contact management HTTP routes initialized (including REST-style coach endpoints)")