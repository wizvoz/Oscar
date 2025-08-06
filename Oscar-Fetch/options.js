// Saves options to chrome.storage
function saveOptions() {
  const serverAddress = document.getElementById('serverAddress').value;
  chrome.storage.sync.set({
    serverAddress: serverAddress
  }, () => {
    // Update status to let user know options were saved.
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(() => {
      status.textContent = '';
    }, 1500);
  });
}

// Restores input box state using the preferences stored in chrome.storage.
function restoreOptions() {
  chrome.storage.sync.get({
    serverAddress: 'http://127.0.0.1:5000' // Default value
  }, (items) => {
    document.getElementById('serverAddress').value = items.serverAddress;
  });
}

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('saveButton').addEventListener('click', saveOptions);