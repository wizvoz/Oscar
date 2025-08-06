document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT SELECTORS ---
    const downloadButton = document.getElementById('downloadButton');
    const cleanupButton = document.getElementById('cleanupButton');
    const videoUrlInput = document.getElementById('videoUrl');
    const copyPathButton = document.getElementById('copyPathButton');
    const downloadsPathInput = document.getElementById('downloadsPath');
    const logPanel = document.getElementById('logPanel');
    const logOutput = document.getElementById('logOutput');

    // --- INITIALIZATION ---
    function initializePage() {
        try {
            // Read data embedded in the page by the server
            const configData = window.APP_CONFIG;
            const historyData = window.APP_HISTORY;

            const guiVersion = document.body.dataset.guiVersion || 'N/A';
            const guiDate = document.body.dataset.guiDate || '';
            document.getElementById('versionDisplay').textContent = `Backend: v${configData.version} | GUI: v${guiVersion} (${guiDate})`;
            downloadsPathInput.value = configData.download_dir;
            document.getElementById('historyPathDisplay').textContent = `(Saving to: ${configData.download_dir})`;
            
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = '';
            if (historyData.length === 0) {
                historyList.innerHTML = '<li class="text-gray-500">No downloads yet.</li>';
            } else {
                historyData.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'p-4 bg-white rounded-lg shadow-sm border';
                    listItem.innerHTML = `
                        <p class="text-xs text-gray-500">${new Date(item.timestamp).toLocaleString()}</p>
                        <p class="font-medium truncate mt-1" title="${item.filename}">${item.filename}</p>
                        <a href="${item.url}" target="_blank" class="text-[#4A90E2] text-sm hover:underline">Source URL</a>
                    `;
                    historyList.appendChild(listItem);
                });
            }
        } catch (error) {
            console.error("Failed to initialize page from embedded data:", error);
            alert("A critical error occurred while loading page data.");
        }
    }

    // --- CORE FUNCTIONS ---
    const startDownload = () => {
        const videoUrl = videoUrlInput.value.trim();
        if (!videoUrl) { alert("Please enter a video URL."); return; }
        if (downloadButton.disabled) return;
        
        logPanel.style.display = 'block';
        logOutput.textContent = `[INFO] Connecting to server for: ${videoUrl}\n`;
        downloadButton.disabled = true;
        downloadButton.textContent = 'Download in Progress...';
        downloadButton.classList.add('bg-gray-400');

        const encodedUrl = encodeURIComponent(videoUrl);
        const eventSource = new EventSource(`/start-download-stream?url=${encodedUrl}`);

        eventSource.onmessage = (event) => {
            const message = event.data;
            logOutput.textContent += `${message}\n`;
            logOutput.scrollTop = logOutput.scrollHeight;
            
            if (message.includes('---DOWNLOAD_COMPLETE---')) {
                eventSource.close();
                downloadButton.disabled = false;
                downloadButton.textContent = 'Download Video';
                downloadButton.classList.remove('bg-gray-400');
                
                // --- THIS IS THE FIX FOR THE LOOP ---
                // Redirect to the root URL without parameters to prevent auto-restart.
                window.location.href = '/';
            }
        };

        eventSource.onerror = () => {
            logOutput.textContent += `[FATAL] Connection to server lost.\n`;
            eventSource.close();
            downloadButton.disabled = false;
            downloadButton.textContent = 'Download Video';
            downloadButton.classList.remove('bg-gray-400');
        };
    };

    // --- EVENT LISTENERS ---
    downloadButton.addEventListener('click', startDownload);
    
    cleanupButton.addEventListener('click', async () => {
         if (!confirm('This will delete all incomplete (.part) files. Are you sure?')) return;
         const response = await fetch('/cleanup_partials', { method: 'POST' });
         const result = await response.json();
         alert(`Cleanup complete! ${result.deleted_count} file(s) were removed.`);
    });

    copyPathButton.addEventListener('click', () => {
        const path = downloadsPathInput.value;
        if (!path) return;
        navigator.clipboard.writeText(path).then(() => {
            const originalContent = copyPathButton.innerHTML;
            copyPathButton.innerHTML = `<span>Copied!</span>`;
            copyPathButton.disabled = true;
            setTimeout(() => {
                copyPathButton.innerHTML = originalContent;
                copyPathButton.disabled = false;
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy path to clipboard:', err);
        });
    });

    // --- INITIAL EXECUTION ---
    initializePage();
    
    if (videoUrlInput.value) {
        console.log('[INFO] URL found on page load, triggering automatic download.');
        startDownload();
    }
});