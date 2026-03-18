console.log('StreamMind content script loaded');

// Inject overlay into YouTube page
function injectOverlay(): void {
  const overlay = document.createElement('div');
  overlay.id = 'streammind-overlay';
  overlay.style.cssText = 'position: fixed; top: 0; right: 0; z-index: 10000;';
  document.body.appendChild(overlay);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectOverlay);
} else {
  injectOverlay();
}

