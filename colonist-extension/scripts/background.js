// Background service worker
// Handles data processing and Google Sheets integration

// Configuration - UPDATE THIS with your Google Apps Script URL
const GOOGLE_SHEETS_WEBHOOK_URL = 'YOUR_GOOGLE_APPS_SCRIPT_URL_HERE';

// Store games locally as backup
let recentGames = [];

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GAME_DATA') {
    handleGameData(message.payload);
  }
  return true;
});

// Process and store game data
async function handleGameData(payload) {
  const { eventType, data, timestamp } = payload;

  console.log('[Colonist Tracker BG] Received:', eventType);

  if (eventType === 'BUILD_GAME') {
    // Game started - store initial data
    const gameRecord = formatGameRecord(data);
    recentGames.push(gameRecord);

    // Store locally
    await storeLocally(gameRecord);

    console.log('[Colonist Tracker BG] Game started:', gameRecord.gameId);
  }

  if (eventType === 'GAME_END') {
    // Game ended - update record and send to sheets
    const gameRecord = formatGameRecord(data);

    // Update local storage
    await storeLocally(gameRecord);

    // Send to Google Sheets
    await sendToGoogleSheets(gameRecord);

    console.log('[Colonist Tracker BG] Game ended:', gameRecord.gameId);
  }
}

// Format game data into a clean record
function formatGameRecord(data) {
  const record = {
    gameId: data.gameId || 'unknown',
    startTime: data.startTime,
    endTime: data.endTime || null,

    // Settings
    mapType: data.settings?.mapSetting ?? 0,
    gameMode: data.settings?.modeSetting ?? 0,
    victoryPoints: data.settings?.victoryPointsToWin ?? 10,
    gameSpeed: data.settings?.gameSpeed ?? 1,

    // Players
    players: (data.players || []).map(p => ({
      oderId: p.oderId,
      username: p.username,
      color: p.selectedColor,
      isBot: p.isBot || false
    })),

    // Your player color
    playerColor: data.playerColor,
    playOrder: data.playOrder,

    // Board
    hexes: data.board?.hexes || [],
    ports: data.board?.ports || [],

    // Outcome (if game ended)
    outcome: data.outcome || null,

    // Raw data for debugging
    _raw: {
      settings: data.settings,
      gameState: data.gameState
    }
  };

  return record;
}

// Store in chrome.storage.local
async function storeLocally(gameRecord) {
  try {
    const result = await chrome.storage.local.get('games');
    const games = result.games || [];

    // Update existing or add new
    const existingIndex = games.findIndex(g => g.gameId === gameRecord.gameId);
    if (existingIndex >= 0) {
      games[existingIndex] = gameRecord;
    } else {
      games.push(gameRecord);
    }

    // Keep only last 100 games
    if (games.length > 100) {
      games.shift();
    }

    await chrome.storage.local.set({ games });
    console.log('[Colonist Tracker BG] Stored locally, total games:', games.length);
  } catch (e) {
    console.error('[Colonist Tracker BG] Storage error:', e);
  }
}

// Send to Google Sheets via Apps Script webhook
async function sendToGoogleSheets(gameRecord) {
  if (GOOGLE_SHEETS_WEBHOOK_URL === 'YOUR_GOOGLE_APPS_SCRIPT_URL_HERE') {
    console.log('[Colonist Tracker BG] Google Sheets URL not configured, skipping...');
    return;
  }

  try {
    const response = await fetch(GOOGLE_SHEETS_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(gameRecord)
    });

    if (response.ok) {
      console.log('[Colonist Tracker BG] Sent to Google Sheets successfully');
    } else {
      console.error('[Colonist Tracker BG] Google Sheets error:', response.status);
    }
  } catch (e) {
    console.error('[Colonist Tracker BG] Failed to send to Google Sheets:', e);
  }
}

// Export games as JSON (for manual download)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'EXPORT_GAMES') {
    chrome.storage.local.get('games', (result) => {
      sendResponse({ games: result.games || [] });
    });
    return true; // Keep channel open for async response
  }
});

console.log('[Colonist Tracker BG] Background service worker started');
