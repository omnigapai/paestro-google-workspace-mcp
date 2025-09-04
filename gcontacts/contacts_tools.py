"""
Google Contacts (People API) MCP Tools

This module provides MCP tools for interacting with the Google People API.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Literal, Any

from auth.service_decorator import require_google_service
from core.utils import handle_http_errors
from core.server import server

logger = logging.getLogger(__name__)

CONTACTS_BATCH_SIZE = 50
CONTACTS_REQUEST_DELAY = 0.1


@server.tool()
@handle_http_errors("list_google_contacts", is_read_only=True, service_type="contacts")
@require_google_service("people", "v1")
async def list_google_contacts(
    service,
    user_google_email: str,
    page_size: int = 50,
    page_token: Optional[str] = None,
    person_fields: str = "names,emailAddresses,phoneNumbers,organizations,addresses,photos"
) -> str:
    """
    List contacts from Google Contacts using the People API.
    
    Args:
        user_google_email: The user's Google email address. Required.
        page_size: Number of contacts to return (max 1000). Defaults to 50.
        page_token: Token for next page of results.
        person_fields: Comma-separated list of person fields to include.
    
    Returns:
        str: LLM-friendly formatted list of contacts with their details.
    """
    logger.info(f"[list_google_contacts] Email: '{user_google_email}', PageSize: {page_size}")
    
    try:
        # Build request parameters
        request_params = {
            'pageSize': min(page_size, 1000),
            'personFields': person_fields,
            'sources': ['READ_SOURCE_TYPE_CONTACT']
        }
        
        if page_token:
            request_params['pageToken'] = page_token
        
        # List connections (contacts)
        response = await asyncio.to_thread(
            service.people().connections().list(
                resourceName='people/me',
                **request_params
            ).execute
        )
        
        contacts = response.get('connections', [])
        total_items = response.get('totalItems', 0)
        next_page_token = response.get('nextPageToken')
        
        # Format output for LLM
        output = [f"Found {len(contacts)} contacts (Total: {total_items})"]
        if next_page_token:
            output.append(f"Next page token: {next_page_token}")
        output.append("")
        
        for i, person in enumerate(contacts, 1):
            contact_info = [f"{i}. Contact:"]
            
            # Extract names
            names = person.get('names', [])
            if names:
                primary_name = names[0]
                display_name = primary_name.get('displayName', 'Unknown')
                contact_info.append(f"   Name: {display_name}")
                if primary_name.get('givenName'):
                    contact_info.append(f"   First: {primary_name['givenName']}")
                if primary_name.get('familyName'):
                    contact_info.append(f"   Last: {primary_name['familyName']}")
            
            # Extract email addresses
            emails = person.get('emailAddresses', [])
            if emails:
                contact_info.append("   Emails:")
                for email in emails:
                    email_type = email.get('type', 'other')
                    contact_info.append(f"     - {email.get('value')} ({email_type})")
            
            # Extract phone numbers
            phones = person.get('phoneNumbers', [])
            if phones:
                contact_info.append("   Phones:")
                for phone in phones:
                    phone_type = phone.get('type', 'other')
                    contact_info.append(f"     - {phone.get('value')} ({phone_type})")
            
            # Extract organizations
            orgs = person.get('organizations', [])
            if orgs:
                contact_info.append("   Organizations:")
                for org in orgs:
                    if org.get('name'):
                        org_str = f"     - {org['name']}"
                        if org.get('title'):
                            org_str += f" ({org['title']})"
                        contact_info.append(org_str)
            
            # Resource name for reference
            contact_info.append(f"   Resource: {person.get('resourceName')}")
            
            output.extend(contact_info)
            output.append("")
        
        logger.info(f"[list_google_contacts] Successfully retrieved {len(contacts)} contacts")
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        return f"Failed to list contacts: {str(e)}"


@server.tool()
@handle_http_errors("search_google_contacts", is_read_only=True, service_type="contacts")
@require_google_service("people", "v1")
async def search_google_contacts(
    service,
    user_google_email: str,
    query: str,
    page_size: int = 30
) -> str:
    """
    Search for contacts in Google Contacts.
    
    Args:
        user_google_email: The user's Google email address. Required.
        query: Search query string.
        page_size: Number of results to return (max 100). Defaults to 30.
    
    Returns:
        str: LLM-friendly formatted search results.
    """
    logger.info(f"[search_google_contacts] Email: '{user_google_email}', Query: '{query}'")
    
    try:
        request_params = {
            'query': query,
            'pageSize': min(page_size, 100),
            'readMask': 'names,emailAddresses,phoneNumbers,organizations',
            'sources': ['READ_SOURCE_TYPE_CONTACT']
        }
        
        # Search for contacts
        response = await asyncio.to_thread(
            service.people().searchContacts(**request_params).execute
        )
        
        results = response.get('results', [])
        
        # Format output for LLM
        output = [f"Search results for '{query}': Found {len(results)} contacts"]
        output.append("")
        
        for i, result in enumerate(results, 1):
            person = result.get('person', {})
            contact_info = [f"{i}. Contact:"]
            
            # Extract names
            names = person.get('names', [])
            if names:
                display_name = names[0].get('displayName', 'Unknown')
                contact_info.append(f"   Name: {display_name}")
            
            # Extract emails
            emails = person.get('emailAddresses', [])
            if emails:
                contact_info.append(f"   Email: {emails[0].get('value')}")
            
            # Extract phones
            phones = person.get('phoneNumbers', [])
            if phones:
                contact_info.append(f"   Phone: {phones[0].get('value')}")
            
            # Extract organization
            orgs = person.get('organizations', [])
            if orgs:
                org = orgs[0]
                if org.get('name'):
                    org_str = f"   Organization: {org['name']}"
                    if org.get('title'):
                        org_str += f" - {org['title']}"
                    contact_info.append(org_str)
            
            output.extend(contact_info)
            output.append("")
        
        logger.info(f"[search_google_contacts] Found {len(results)} matching contacts")
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        return f"Failed to search contacts: {str(e)}"


@server.tool()
@handle_http_errors("get_google_contact", is_read_only=True, service_type="contacts")
@require_google_service("people", "v1")
async def get_google_contact(
    service,
    user_google_email: str,
    resource_name: str,
    person_fields: str = "names,emailAddresses,phoneNumbers,organizations,addresses,biographies,birthdays,nicknames,urls,photos"
) -> str:
    """
    Get detailed information about a specific contact.
    
    Args:
        user_google_email: The user's Google email address. Required.
        resource_name: Resource name of the contact (e.g., 'people/c1234567890').
        person_fields: Comma-separated list of fields to include.
    
    Returns:
        str: LLM-friendly formatted contact details.
    """
    logger.info(f"[get_google_contact] Email: '{user_google_email}', Resource: '{resource_name}'")
    
    try:
        # Get contact details
        person = await asyncio.to_thread(
            service.people().get(
                resourceName=resource_name,
                personFields=person_fields
            ).execute
        )
        
        # Format output for LLM
        output = ["Contact Details:"]
        output.append(f"Resource: {person.get('resourceName')}")
        output.append("")
        
        # Names
        names = person.get('names', [])
        if names:
            name = names[0]
            output.append("Name Information:")
            if name.get('displayName'):
                output.append(f"  Display: {name['displayName']}")
            if name.get('givenName'):
                output.append(f"  First: {name['givenName']}")
            if name.get('familyName'):
                output.append(f"  Last: {name['familyName']}")
            if name.get('middleName'):
                output.append(f"  Middle: {name['middleName']}")
            output.append("")
        
        # Email addresses
        emails = person.get('emailAddresses', [])
        if emails:
            output.append("Email Addresses:")
            for email in emails:
                primary = " (primary)" if email.get('metadata', {}).get('primary') else ""
                output.append(f"  - {email.get('value')} ({email.get('type', 'other')}){primary}")
            output.append("")
        
        # Phone numbers
        phones = person.get('phoneNumbers', [])
        if phones:
            output.append("Phone Numbers:")
            for phone in phones:
                output.append(f"  - {phone.get('value')} ({phone.get('type', 'other')})")
            output.append("")
        
        # Organizations
        orgs = person.get('organizations', [])
        if orgs:
            output.append("Organizations:")
            for org in orgs:
                org_lines = []
                if org.get('name'):
                    org_lines.append(f"  Company: {org['name']}")
                if org.get('title'):
                    org_lines.append(f"  Title: {org['title']}")
                if org.get('department'):
                    org_lines.append(f"  Department: {org['department']}")
                output.extend(org_lines)
            output.append("")
        
        # Addresses
        addresses = person.get('addresses', [])
        if addresses:
            output.append("Addresses:")
            for addr in addresses:
                if addr.get('formattedValue'):
                    output.append(f"  - {addr['formattedValue']} ({addr.get('type', 'other')})")
            output.append("")
        
        # Birthdays
        birthdays = person.get('birthdays', [])
        if birthdays:
            output.append("Birthdays:")
            for bday in birthdays:
                date = bday.get('date', {})
                if date:
                    output.append(f"  - {date.get('month')}/{date.get('day')}/{date.get('year', 'Unknown year')}")
            output.append("")
        
        # Biographies
        bios = person.get('biographies', [])
        if bios:
            output.append("Notes:")
            for bio in bios:
                if bio.get('value'):
                    output.append(f"  {bio['value']}")
            output.append("")
        
        # URLs
        urls = person.get('urls', [])
        if urls:
            output.append("URLs:")
            for url in urls:
                output.append(f"  - {url.get('value')} ({url.get('type', 'other')})")
            output.append("")
        
        logger.info(f"[get_google_contact] Successfully retrieved contact details")
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Error getting contact: {e}")
        return f"Failed to get contact: {str(e)}"


@server.tool()
@handle_http_errors("create_google_contact", is_read_only=False, service_type="contacts")
@require_google_service("people", "v1")
async def create_google_contact(
    service,
    user_google_email: str,
    given_name: str,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    organization: Optional[str] = None,
    title: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Create a new contact in Google Contacts.
    
    Args:
        user_google_email: The user's Google email address. Required.
        given_name: First name of the contact.
        family_name: Last name of the contact.
        email: Email address.
        phone: Phone number.
        organization: Organization name.
        title: Job title.
        notes: Notes about the contact.
    
    Returns:
        str: Success message with resource name of created contact.
    """
    logger.info(f"[create_google_contact] Email: '{user_google_email}', Creating: {given_name} {family_name or ''}")
    
    try:
        # Build contact data
        contact_data = {
            'names': [{
                'givenName': given_name
            }]
        }
        
        if family_name:
            contact_data['names'][0]['familyName'] = family_name
        
        if email:
            contact_data['emailAddresses'] = [{
                'value': email,
                'type': 'work'
            }]
        
        if phone:
            contact_data['phoneNumbers'] = [{
                'value': phone,
                'type': 'work'
            }]
        
        if organization or title:
            org_data = {}
            if organization:
                org_data['name'] = organization
            if title:
                org_data['title'] = title
            contact_data['organizations'] = [org_data]
        
        if notes:
            contact_data['biographies'] = [{
                'value': notes,
                'contentType': 'TEXT_PLAIN'
            }]
        
        # Create the contact
        result = await asyncio.to_thread(
            service.people().createContact(body=contact_data).execute
        )
        
        resource_name = result.get('resourceName')
        logger.info(f"[create_google_contact] Successfully created contact: {resource_name}")
        
        return f"""Contact created successfully!
Resource Name: {resource_name}
Name: {given_name} {family_name or ''}
Email: {email or 'Not provided'}
Phone: {phone or 'Not provided'}
Organization: {organization or 'Not provided'}
Title: {title or 'Not provided'}"""
        
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        return f"Failed to create contact: {str(e)}"


@server.tool()
@handle_http_errors("update_google_contact", is_read_only=False, service_type="contacts")
@require_google_service("people", "v1")
async def update_google_contact(
    service,
    user_google_email: str,
    resource_name: str,
    etag: str,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    organization: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Update an existing contact in Google Contacts.
    
    Args:
        user_google_email: The user's Google email address. Required.
        resource_name: Resource name of the contact to update.
        etag: Current etag of the contact.
        given_name: Updated first name.
        family_name: Updated last name.
        email: Updated email address.
        phone: Updated phone number.
        organization: Updated organization.
        title: Updated job title.
    
    Returns:
        str: Success message with updated contact information.
    """
    logger.info(f"[update_google_contact] Email: '{user_google_email}', Resource: '{resource_name}'")
    
    try:
        # Build update data
        update_data = {
            'resourceName': resource_name,
            'etag': etag
        }
        
        update_fields = []
        
        if given_name is not None or family_name is not None:
            name_data = {}
            if given_name:
                name_data['givenName'] = given_name
            if family_name:
                name_data['familyName'] = family_name
            update_data['names'] = [name_data]
            update_fields.append('names')
        
        if email is not None:
            update_data['emailAddresses'] = [{
                'value': email,
                'type': 'work'
            }]
            update_fields.append('emailAddresses')
        
        if phone is not None:
            update_data['phoneNumbers'] = [{
                'value': phone,
                'type': 'work'
            }]
            update_fields.append('phoneNumbers')
        
        if organization is not None or title is not None:
            org_data = {}
            if organization:
                org_data['name'] = organization
            if title:
                org_data['title'] = title
            update_data['organizations'] = [org_data]
            update_fields.append('organizations')
        
        # Update the contact
        result = await asyncio.to_thread(
            service.people().updateContact(
                resourceName=resource_name,
                updatePersonFields=','.join(update_fields),
                body=update_data
            ).execute
        )
        
        logger.info(f"[update_google_contact] Successfully updated contact")
        
        return f"""Contact updated successfully!
Resource Name: {result.get('resourceName')}
Updated fields: {', '.join(update_fields)}"""
        
    except Exception as e:
        logger.error(f"Error updating contact: {e}")
        return f"Failed to update contact: {str(e)}"


@server.tool()
@handle_http_errors("delete_google_contact", is_read_only=False, service_type="contacts")
@require_google_service("people", "v1")
async def delete_google_contact(
    service,
    user_google_email: str,
    resource_name: str
) -> str:
    """
    Delete a contact from Google Contacts.
    
    Args:
        user_google_email: The user's Google email address. Required.
        resource_name: Resource name of the contact to delete.
    
    Returns:
        str: Success message confirming deletion.
    """
    logger.info(f"[delete_google_contact] Email: '{user_google_email}', Resource: '{resource_name}'")
    
    try:
        # Delete the contact
        await asyncio.to_thread(
            service.people().deleteContact(resourceName=resource_name).execute
        )
        
        logger.info(f"[delete_google_contact] Successfully deleted contact")
        return f"Contact '{resource_name}' has been successfully deleted."
        
    except Exception as e:
        logger.error(f"Error deleting contact: {e}")
        return f"Failed to delete contact: {str(e)}"


@server.tool()
@handle_http_errors("batch_get_google_contacts", is_read_only=True, service_type="contacts")
@require_google_service("people", "v1")
async def batch_get_google_contacts(
    service,
    user_google_email: str,
    resource_names: str,
    person_fields: str = "names,emailAddresses,phoneNumbers,organizations"
) -> str:
    """
    Get multiple contacts in a single batch request.
    
    Args:
        user_google_email: The user's Google email address. Required.
        resource_names: Comma-separated list of resource names to fetch (max 50).
        person_fields: Comma-separated list of fields to include.
    
    Returns:
        str: LLM-friendly formatted list of requested contacts.
    """
    logger.info(f"[batch_get_google_contacts] Email: '{user_google_email}'")
    
    try:
        # Parse resource names
        names_list = [name.strip() for name in resource_names.split(',')][:50]
        
        # Batch get contacts
        response = await asyncio.to_thread(
            service.people().getBatchGet(
                resourceNames=names_list,
                personFields=person_fields
            ).execute
        )
        
        # Format output for LLM
        output = [f"Batch retrieved {len(response.get('responses', []))} contacts:"]
        output.append("")
        
        for i, resp in enumerate(response.get('responses', []), 1):
            if 'person' in resp:
                person = resp['person']
                contact_info = [f"{i}. Contact:"]
                
                # Extract basic info
                names = person.get('names', [])
                if names:
                    contact_info.append(f"   Name: {names[0].get('displayName', 'Unknown')}")
                
                emails = person.get('emailAddresses', [])
                if emails:
                    contact_info.append(f"   Email: {emails[0].get('value')}")
                
                phones = person.get('phoneNumbers', [])
                if phones:
                    contact_info.append(f"   Phone: {phones[0].get('value')}")
                
                orgs = person.get('organizations', [])
                if orgs:
                    org = orgs[0]
                    if org.get('name'):
                        org_str = f"   Organization: {org['name']}"
                        if org.get('title'):
                            org_str += f" - {org['title']}"
                        contact_info.append(org_str)
                
                contact_info.append(f"   Resource: {person.get('resourceName')}")
                output.extend(contact_info)
                output.append("")
        
        logger.info(f"[batch_get_google_contacts] Successfully retrieved {len(response.get('responses', []))} contacts")
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Error batch getting contacts: {e}")
        return f"Failed to batch get contacts: {str(e)}"