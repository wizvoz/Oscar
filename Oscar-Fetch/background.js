// background.js (v1.6 - Uses saved settings from Options Page)
// This script reads the server address from storage and uses it to
// open or update the GUI tab.

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'oscarFetch') {
    
    // Step 1: Get the saved server address from storage.
    chrome.storage.sync.get({
      serverAddress: 'http://127.0.0.1:5000' // Provide a default value
    }, (items) => {
      const serverAddress = items.serverAddress;
      
      // Step 2: Use the retrieved address to build the target URLs.
      const videoUrl = request.url;
      const encodedVideoUrl = encodeURIComponent(videoUrl);
      const downloadUrl = `${serverAddress}/?url=${encodedVideoUrl}`;
      const guiUrlPattern = `${serverAddress}/*`;

      // Step 3: Check if the GUI tab is already open and take action.
      // This logic is now nested inside the storage callback.
      chrome.tabs.query({ url: guiUrlPattern }, (foundTabs) => {
        if (foundTabs.length > 0) {
          // If a tab is found, update it with the new download URL and activate it.
          const tabId = foundTabs[0].id;
          console.log(`[DEBUG] Oscar-Fetch: GUI tab found (ID: ${tabId}). Updating and focusing.`);
          
          chrome.tabs.update(tabId, { url: downloadUrl, active: true });
          chrome.windows.update(foundTabs[0].windowId, { focused: true });
          
        } else {
          // If no tab is found, create a new one.
          console.log('[DEBUG] Oscar-Fetch: No GUI tab found. Creating a new one.');
          chrome.tabs.create({ url: downloadUrl });
        }
      });
    });
  }
});