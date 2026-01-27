// Interceptor script - runs in page context
// Patches WebSocket to capture game data

(function() {
  'use strict';

  console.log('[Colonist Tracker] Interceptor initializing...');

  // MessagePack decoder (minimal implementation for our needs)
  // We'll load the full library dynamically
  let msgpackDecode = null;

  // Load msgpack library
  async function loadMsgpack() {
    try {
      const module = await import('https://cdn.jsdelivr.net/npm/@msgpack/msgpack@2.8.0/+esm');
      msgpackDecode = module.decode;
      console.log('[Colonist Tracker] MessagePack loaded successfully');
    } catch (e) {
      console.error('[Colonist Tracker] Failed to load MessagePack:', e);
    }
  }

  // Current game state
  let currentGame = {
    gameId: null,
    startTime: null,
    players: [],
    board: null,
    settings: null,
    events: []
  };

  // Game update types we care about
  const GameUpdate = {
    FirstGameState: 0,
    BuildGame: 8,
    GameStateUpdated: 10,
    GameEndState: 25,
    GivePlayerResourcesFromTile: 11
  };

  // Extract hex data from tileHexStates
  function extractBoardData(mapState) {
    if (!mapState) return null;

    const hexes = [];
    const ports = [];
    const corners = [];
    const edges = [];

    // Extract hex tiles
    if (mapState.tileHexStates) {
      for (const [index, hex] of Object.entries(mapState.tileHexStates)) {
        hexes.push({
          index: parseInt(index),
          resource: hex.terrain ?? hex.resource ?? hex.type,
          number: hex.diceNumber ?? hex.number ?? hex.value,
          hasRobber: hex.hasRobber ?? false,
          ...hex
        });
      }
    }

    // Extract ports
    if (mapState.portEdgeStates) {
      for (const [index, port] of Object.entries(mapState.portEdgeStates)) {
        ports.push({
          index: parseInt(index),
          ...port
        });
      }
    }

    // Extract corners (settlements/cities)
    if (mapState.tileCornerStates) {
      for (const [index, corner] of Object.entries(mapState.tileCornerStates)) {
        if (corner.building || corner.owner) {
          corners.push({
            index: parseInt(index),
            ...corner
          });
        }
      }
    }

    // Extract edges (roads)
    if (mapState.tileEdgeStates) {
      for (const [index, edge] of Object.entries(mapState.tileEdgeStates)) {
        if (edge.road || edge.owner) {
          edges.push({
            index: parseInt(index),
            ...edge
          });
        }
      }
    }

    return { hexes, ports, corners, edges };
  }

  // Process incoming game messages
  function processGameMessage(data) {
    if (!data || typeof data !== 'object') return;

    // Handle different message types
    const messageType = data.type ?? data.t;
    const payload = data.payload ?? data.p ?? data.data ?? data.d;

    // Log all game updates for debugging
    // console.log('[Colonist Tracker] Message:', messageType, data);

    // BuildGame - contains full board setup
    if (messageType === GameUpdate.BuildGame || data.type === 'BuildGame') {
      console.log('[Colonist Tracker] BuildGame received!', payload || data);

      const gameData = payload || data;

      currentGame.gameId = gameData.gameSettings?.id || currentGame.gameId;
      currentGame.settings = gameData.gameSettings;
      currentGame.players = gameData.playerUserStates || [];
      currentGame.startTime = new Date().toISOString();

      if (gameData.gameState?.mapState) {
        currentGame.board = extractBoardData(gameData.gameState.mapState);
      }

      // Also store raw gameState for reference
      currentGame.gameState = gameData.gameState;
      currentGame.playOrder = gameData.playOrder;
      currentGame.playerColor = gameData.playerColor;

      // Dispatch event to content script
      dispatchGameData('BUILD_GAME', currentGame);
    }

    // FirstGameState - initial connection
    if (messageType === GameUpdate.FirstGameState) {
      console.log('[Colonist Tracker] FirstGameState received');
      currentGame.gameId = payload?.gameSettingId || payload?.databaseGameId;
    }

    // GameStateUpdated - ongoing updates
    if (messageType === GameUpdate.GameStateUpdated) {
      // Track state updates if needed
      currentGame.events.push({
        type: 'state_update',
        timestamp: new Date().toISOString(),
        data: payload
      });
    }

    // GameEndState - game finished
    if (messageType === GameUpdate.GameEndState) {
      console.log('[Colonist Tracker] Game ended!', payload);
      currentGame.endTime = new Date().toISOString();
      currentGame.outcome = payload;

      dispatchGameData('GAME_END', currentGame);
    }

    // Resource production
    if (messageType === GameUpdate.GivePlayerResourcesFromTile) {
      currentGame.events.push({
        type: 'resource_production',
        timestamp: new Date().toISOString(),
        data: payload
      });
    }
  }

  // Dispatch game data to content script
  function dispatchGameData(eventType, data) {
    window.dispatchEvent(new CustomEvent('colonist-game-data', {
      detail: {
        eventType,
        data: JSON.parse(JSON.stringify(data)), // Deep clone
        timestamp: new Date().toISOString()
      }
    }));
  }

  // Patch WebSocket
  const OriginalWebSocket = window.WebSocket;

  window.WebSocket = function(...args) {
    console.log('[Colonist Tracker] WebSocket created:', args[0]);

    const ws = new OriginalWebSocket(...args);

    ws.addEventListener('message', async (event) => {
      try {
        let decoded;

        if (event.data instanceof Blob) {
          const buffer = await event.data.arrayBuffer();
          if (msgpackDecode) {
            decoded = msgpackDecode(new Uint8Array(buffer));
          }
        } else if (event.data instanceof ArrayBuffer) {
          if (msgpackDecode) {
            decoded = msgpackDecode(new Uint8Array(event.data));
          }
        } else if (typeof event.data === 'string') {
          try {
            decoded = JSON.parse(event.data);
          } catch (e) {
            // Not JSON
          }
        }

        if (decoded) {
          processGameMessage(decoded);
        }
      } catch (e) {
        // Silently ignore decode errors
      }
    });

    return ws;
  };

  // Copy prototype and static properties
  window.WebSocket.prototype = OriginalWebSocket.prototype;
  window.WebSocket.CONNECTING = OriginalWebSocket.CONNECTING;
  window.WebSocket.OPEN = OriginalWebSocket.OPEN;
  window.WebSocket.CLOSING = OriginalWebSocket.CLOSING;
  window.WebSocket.CLOSED = OriginalWebSocket.CLOSED;

  // Initialize
  loadMsgpack();

  console.log('[Colonist Tracker] Interceptor ready!');
})();
