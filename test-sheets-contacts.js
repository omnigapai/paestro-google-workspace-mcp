#!/usr/bin/env node

/**
 * Test script for Google Sheets Contacts API endpoints
 * Tests the bidirectional sync functionality for coach contact management
 */

const GOOGLE_WORKSPACE_URL = 'https://paestro-google-workspace-mcp-production.up.railway.app';
const SESSION_ID = 'test-session-' + Date.now();
const COACH_ID = 'test-coach-' + Math.random().toString(36).substring(7);

async function testEndpoint(name, url, method, body = null) {
  console.log(`\n🧪 Testing ${name}...`);
  console.log(`   URL: ${url}`);
  console.log(`   Method: ${method}`);
  if (body) console.log(`   Body:`, JSON.stringify(body, null, 2));
  
  try {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'session-id': SESSION_ID
      }
    };
    
    if (body) {
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    const responseText = await response.text();
    
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      try {
        const data = JSON.parse(responseText);
        console.log(`   ✅ Success:`, JSON.stringify(data, null, 2));
        return data;
      } catch (e) {
        console.log(`   ✅ Response:`, responseText);
        return responseText;
      }
    } else {
      console.log(`   ❌ Error:`, responseText);
      return null;
    }
  } catch (error) {
    console.log(`   ❌ Network Error:`, error.message);
    return null;
  }
}

async function runTests() {
  console.log('=====================================');
  console.log('Google Sheets Contacts API Test Suite');
  console.log('=====================================');
  console.log(`Server: ${GOOGLE_WORKSPACE_URL}`);
  console.log(`Session ID: ${SESSION_ID}`);
  console.log(`Coach ID: ${COACH_ID}`);
  
  // Test 1: Health Check
  const healthUrl = `${GOOGLE_WORKSPACE_URL}/health`;
  const health = await testEndpoint('Health Check', healthUrl, 'GET');
  
  if (!health || health.status !== 'healthy') {
    console.log('\n❌ Server is not healthy. Aborting tests.');
    return;
  }
  
  // Test 2: Initialize Sheet for Coach
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const initResult = await testEndpoint(
    'Initialize Contact Sheet',
    `${GOOGLE_WORKSPACE_URL}/sheets-contacts/init`,
    'POST',
    {
      coachId: COACH_ID,
      sheetName: `Paestro Contacts - Test ${COACH_ID}`
    }
  );
  
  if (!initResult) {
    console.log('\n⚠️  Could not initialize sheet. Routes may not be deployed yet.');
  }
  
  const spreadsheetId = initResult?.spreadsheetId;
  
  // Test 3: Add Contact
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const contact1 = {
    coachId: COACH_ID,
    spreadsheetId: spreadsheetId || 'test-sheet-id',
    contact: {
      name: 'John Doe',
      email: 'john.doe@example.com',
      phone: '555-0100',
      role: 'Parent',
      notes: 'Parent of player Jimmy'
    }
  };
  
  const addResult = await testEndpoint(
    'Add Contact',
    `${GOOGLE_WORKSPACE_URL}/sheets-contacts/add`,
    'POST',
    contact1
  );
  
  // Test 4: List Contacts
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const listResult = await testEndpoint(
    'List Contacts',
    `${GOOGLE_WORKSPACE_URL}/sheets-contacts/list`,
    'POST',
    {
      coachId: COACH_ID,
      spreadsheetId: spreadsheetId || 'test-sheet-id'
    }
  );
  
  // Test 5: Update Contact
  if (addResult?.contactId) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    const updateResult = await testEndpoint(
      'Update Contact',
      `${GOOGLE_WORKSPACE_URL}/sheets-contacts/update`,
      'POST',
      {
        coachId: COACH_ID,
        spreadsheetId: spreadsheetId || 'test-sheet-id',
        contactId: addResult.contactId,
        updates: {
          phone: '555-0200',
          notes: 'Updated phone number'
        }
      }
    );
  }
  
  // Test 6: Sync from Frontend
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const syncData = {
    coachId: COACH_ID,
    spreadsheetId: spreadsheetId || 'test-sheet-id',
    contacts: [
      {
        name: 'Jane Smith',
        email: 'jane@example.com',
        phone: '555-0300',
        role: 'Assistant Coach'
      },
      {
        name: 'Bob Johnson',
        email: 'bob@example.com',
        phone: '555-0400',
        role: 'Parent'
      }
    ]
  };
  
  const syncResult = await testEndpoint(
    'Sync Contacts from Frontend',
    `${GOOGLE_WORKSPACE_URL}/sheets-contacts/sync`,
    'POST',
    syncData
  );
  
  // Test 7: Delete Contact
  if (addResult?.contactId) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    const deleteResult = await testEndpoint(
      'Delete Contact',
      `${GOOGLE_WORKSPACE_URL}/sheets-contacts/delete`,
      'POST',
      {
        coachId: COACH_ID,
        spreadsheetId: spreadsheetId || 'test-sheet-id',
        contactId: addResult.contactId
      }
    );
  }
  
  // Summary
  console.log('\n=====================================');
  console.log('Test Summary');
  console.log('=====================================');
  
  if (spreadsheetId) {
    console.log('✅ Google Sheets contact management is operational!');
    console.log(`📊 Spreadsheet created: ${spreadsheetId}`);
    console.log(`🔗 View at: https://docs.google.com/spreadsheets/d/${spreadsheetId}`);
  } else {
    console.log('⚠️  Routes may not be fully deployed yet.');
    console.log('   Wait for deployment to complete and try again.');
  }
}

// Run tests
runTests().catch(console.error);