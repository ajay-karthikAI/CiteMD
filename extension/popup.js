const DEFAULT_API_URL = "http://localhost:8001";

const input = document.getElementById("apiUrl");
const status = document.getElementById("status");

function normalizeApiUrl(apiUrl) {
  const cleanUrl = (apiUrl || DEFAULT_API_URL).trim().replace(/\/$/, "");
  return cleanUrl.replace(/^http:\/\/(localhost|127\.0\.0\.1):8501$/i, "http://localhost:8001");
}

chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL }, ({ apiUrl }) => {
  const normalizedApiUrl = normalizeApiUrl(apiUrl);
  input.value = normalizedApiUrl;
  if (normalizedApiUrl !== apiUrl) {
    chrome.storage.sync.set({ apiUrl: normalizedApiUrl });
    status.textContent = "Updated API port to 8001.";
  }
});

document.getElementById("save").addEventListener("click", () => {
  const apiUrl = normalizeApiUrl(input.value);
  input.value = apiUrl;
  chrome.storage.sync.set({ apiUrl }, () => {
    status.textContent = "Saved.";
  });
});
