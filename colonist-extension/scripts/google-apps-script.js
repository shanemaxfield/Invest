/**
 * Google Apps Script - Colonist Game Tracker Webhook
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to https://script.google.com/
 * 2. Create a new project
 * 3. Paste this entire code
 * 4. Click "Deploy" > "New deployment"
 * 5. Select type: "Web app"
 * 6. Execute as: "Me"
 * 7. Who has access: "Anyone"
 * 8. Click "Deploy" and copy the URL
 * 9. Paste the URL in background.js GOOGLE_SHEETS_WEBHOOK_URL
 *
 * SHEET SETUP:
 * 1. Create a new Google Sheet
 * 2. Copy the Sheet ID from the URL (between /d/ and /edit)
 * 3. Paste it below in SPREADSHEET_ID
 * 4. Create two sheets named "Games" and "Hexes"
 */

// UPDATE THIS with your Google Sheet ID
const SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE';

// Handle POST requests from the extension
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    // Log to Games sheet
    logGame(data);

    // Log hexes to separate sheet
    logHexes(data);

    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Log game summary to Games sheet
function logGame(data) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = ss.getSheetByName('Games');

  // Create sheet with headers if it doesn't exist
  if (!sheet) {
    sheet = ss.insertSheet('Games');
    sheet.appendRow([
      'Game ID',
      'Start Time',
      'End Time',
      'Map Type',
      'Game Mode',
      'Victory Points',
      'Player 1',
      'Player 2',
      'Player 3',
      'Player 4',
      'Your Color',
      'Winner',
      'Play Order',
      'Hex Count'
    ]);
  }

  // Extract player names
  const playerNames = (data.players || []).map(p => p.username || 'Unknown');
  while (playerNames.length < 4) playerNames.push('');

  // Determine winner from outcome
  let winner = '';
  if (data.outcome) {
    // Adjust based on actual outcome structure
    winner = data.outcome.winner || data.outcome.winnerName || '';
  }

  // Append row
  sheet.appendRow([
    data.gameId,
    data.startTime,
    data.endTime || '',
    data.mapType,
    data.gameMode,
    data.victoryPoints,
    playerNames[0],
    playerNames[1],
    playerNames[2],
    playerNames[3],
    data.playerColor,
    winner,
    JSON.stringify(data.playOrder),
    (data.hexes || []).length
  ]);
}

// Log hex data to Hexes sheet
function logHexes(data) {
  if (!data.hexes || data.hexes.length === 0) return;

  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = ss.getSheetByName('Hexes');

  // Create sheet with headers if it doesn't exist
  if (!sheet) {
    sheet = ss.insertSheet('Hexes');
    sheet.appendRow([
      'Game ID',
      'Hex Index',
      'Resource',
      'Number',
      'Has Robber',
      'Raw Data'
    ]);
  }

  // Append each hex as a row
  const rows = data.hexes.map(hex => [
    data.gameId,
    hex.index,
    hex.resource || hex.terrain || '',
    hex.number || hex.diceNumber || '',
    hex.hasRobber || false,
    JSON.stringify(hex)
  ]);

  if (rows.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  }
}

// Test function - run this to verify setup
function testSetup() {
  const testData = {
    gameId: 'test123',
    startTime: new Date().toISOString(),
    endTime: new Date().toISOString(),
    mapType: 0,
    gameMode: 0,
    victoryPoints: 10,
    players: [
      { username: 'Player1', color: 1 },
      { username: 'Player2', color: 2 }
    ],
    playerColor: 1,
    playOrder: [1, 2],
    hexes: [
      { index: 0, resource: 'brick', number: 8 },
      { index: 1, resource: 'wood', number: 6 }
    ]
  };

  logGame(testData);
  logHexes(testData);

  Logger.log('Test data logged successfully!');
}
