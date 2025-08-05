// content.js
// This script runs on the YouTube page and injects the download button.

(function() {
  function createButton() {
    // Check if the button already exists to prevent duplicates
    if (document.getElementById('oscar-fetch-button')) {
      return;
    }

    // Create the button element
    const button = document.createElement('button');
    button.id = 'oscar-fetch-button';
    button.textContent = 'Oscar Fetch';
    button.style.cssText = `
      background-color: #4A90E2;
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px 12px;
      margin-left: 10px;
      cursor: pointer;
      font-weight: bold;
    `;

    // Add an event listener to the button
    button.addEventListener('click', () => {
      const url = window.location.href;
      // Clean the URL before sending to the server
      const cleanedUrl = url.split('&')[0].split('?')[0];

      // Send a message to the background script to handle the fetch request
      chrome.runtime.sendMessage({
        action: 'oscarFetch',
        url: cleanedUrl
      });
    });

    // Find the right place to inject the button
    const container = document.querySelector('ytd-watch-metadata #actions');
    if (container) {
      container.appendChild(button);
    }
  }

  // Use a MutationObserver to ensure the button is added even when navigating within YouTube
  const observer = new MutationObserver(createButton);
  const config = { childList: true, subtree: true };
  observer.observe(document.body, config);

  // Initial call to create the button
  createButton();
})();