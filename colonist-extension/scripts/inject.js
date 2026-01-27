// Content script - injects the interceptor into the page context
// This runs in an isolated world, so we need to inject a script tag

const script = document.createElement('script');
script.src = chrome.runtime.getURL('scripts/interceptor.js');
script.onload = function() {
  this.remove();
};
(document.head || document.documentElement).appendChild(script);

// Listen for messages from the injected script
window.addEventListener('colonist-game-data', (event) => {
  const gameData = event.detail;
  console.log('[Colonist Tracker] Game data received:', gameData);

  // Send to background script for processing/storage
  chrome.runtime.sendMessage({
    type: 'GAME_DATA',
    payload: gameData
  });
});

console.log('[Colonist Tracker] Content script loaded');
