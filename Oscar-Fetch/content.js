// content.js (v1.3 - Added URL cleaning to prevent playlist downloads)
// This script runs on the YouTube page and injects the download button.

(function() {
  function createButton() {
    if (document.getElementById('oscar-fetch-button')) {
      return; // Button already exists
    }

    const button = document.createElement('button');
    button.id = 'oscar-fetch-button';
    button.textContent = 'Oscar Fetch';
    button.style.cssText = `
      background-color: #4A90E2; color: white; border: none;
      border-radius: 4px; padding: 8px 12px; margin-left: 10px;
      cursor: pointer; font-weight: bold; z-index: 9999;
    `;

    button.addEventListener('click', () => {
      console.log('Oscar-Fetch: Button clicked.');
      try {
        const currentUrl = new URL(window.location.href);
        const videoId = currentUrl.searchParams.get('v');

        if (videoId) {
          const cleanUrl = `https://www.youtube.com/watch?v=${videoId}`;
          console.log(`Oscar-Fetch: Sending cleaned URL to background: ${cleanUrl}`);
          
          chrome.runtime.sendMessage({ action: 'oscarFetch', url: cleanUrl });

          // Give the user some visual feedback
          button.textContent = 'Sent!';
          button.style.backgroundColor = '#28a745';
          setTimeout(() => {
              button.textContent = 'Oscar Fetch';
              button.style.backgroundColor = '#4A90E2';
          }, 3000);
        } else {
          throw new Error('Could not find a video ID ("v" parameter) in the URL.');
        }
      } catch (error) {
          console.error('Oscar-Fetch: Error processing URL.', error);
          alert(`Oscar-Fetch Error: Could not process the video URL.\n\n${error.message}`);
      }
    });

    const container = document.querySelector('ytd-watch-metadata #actions');
    if (container) {
      container.appendChild(button);
    }
  }

  const observer = new MutationObserver(() => {
    setTimeout(createButton, 500);
  });
  
  observer.observe(document.body, { childList: true, subtree: true });

  setTimeout(createButton, 2000); 
})();