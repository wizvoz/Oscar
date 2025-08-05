// background.js
// This script runs in the background and handles requests from content.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'oscarFetch') {
    fetch('http://127.0.0.1:5000/start-download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url: request.url })
    })
    .then(response => response.json())
    .then(data => {
      console.log('Download request sent to server:', data);
    })
    .catch(error => {
      console.error('Error sending download request:', error);
    });
  }
});
