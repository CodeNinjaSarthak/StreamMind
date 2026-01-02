import { auth } from './auth';
import { youtubePoller } from './youtubePoller';
import { websocket } from './websocket';
import { quota } from './quota';

chrome.runtime.onInstalled.addListener(() => {
  console.log('AI Live Doubt Manager extension installed');
});

// Initialize services
auth.init();
youtubePoller.init();
websocket.init();
quota.init();

