# Colonist Game Tracker

Chrome extension that captures game data from colonist.io (Catan) for analysis.

## Features

- Captures board layout (hex resources, numbers, ports)
- Records player information
- Tracks game outcomes
- Stores data locally in browser
- Exports to Google Sheets

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the `colonist-extension` folder
5. The extension is now installed!

## Google Sheets Setup (Optional)

1. Go to [Google Apps Script](https://script.google.com/)
2. Create a new project
3. Copy contents of `scripts/google-apps-script.js` into the editor
4. Create a Google Sheet and copy its ID from the URL
5. Update `SPREADSHEET_ID` in the Apps Script
6. Deploy as Web App (Execute as: Me, Access: Anyone)
7. Copy the deployment URL
8. Update `GOOGLE_SHEETS_WEBHOOK_URL` in `scripts/background.js`
9. Reload the extension

## Data Captured

### Board Data (`tileHexStates`)
- Hex index/position
- Resource type (brick, wood, ore, wheat, sheep, desert)
- Number token (2-12)
- Robber location

### Port Data (`portEdgeStates`)
- Port locations
- Port types (3:1 or 2:1 specific resource)

### Player Data
- Usernames
- Colors
- Bot status

### Game Settings
- Map type
- Game mode
- Victory points to win
- Game speed

## Viewing Captured Data

Open the browser console on colonist.io to see logged data:
- `[Colonist Tracker]` - Interceptor messages
- `[Colonist Tracker BG]` - Background script messages

To export all stored games, run in console:
```javascript
chrome.runtime.sendMessage({type: 'EXPORT_GAMES'}, (response) => {
  console.log(response.games);
});
```

## Files

```
colonist-extension/
├── manifest.json           # Extension configuration
├── scripts/
│   ├── inject.js          # Content script (injection)
│   ├── interceptor.js     # WebSocket interception
│   ├── background.js      # Data processing & storage
│   └── google-apps-script.js  # Google Sheets webhook code
└── README.md
```

## Development

The extension works by:
1. Injecting a script before page load (`document_start`)
2. Patching `WebSocket.prototype` to intercept connections
3. Decoding MessagePack-encoded messages
4. Capturing `BuildGame` events with full board data
5. Storing locally and optionally sending to Google Sheets
