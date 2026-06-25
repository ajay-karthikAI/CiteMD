const DEFAULT_API_URL = "http://localhost:8001";

function normalizeApiUrl(apiUrl) {
  const cleanUrl = (apiUrl || DEFAULT_API_URL).trim().replace(/\/$/, "");
  return cleanUrl.replace(/^http:\/\/(localhost|127\.0\.0\.1):8501$/i, "http://localhost:8001");
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "CITEMD_ANSWER") {
    return false;
  }

  chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL }, async ({ apiUrl }) => {
    const normalizedApiUrl = normalizeApiUrl(apiUrl);
    if (normalizedApiUrl !== apiUrl) {
      chrome.storage.sync.set({ apiUrl: normalizedApiUrl });
    }
    try {
      const response = await fetch(`${normalizedApiUrl}/api/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: message.query,
          pubmed_limit: message.pubmedLimit || 100,
          top_k: message.topK || 20,
          page_context: message.pageContext || []
        })
      });

      const payload = await response.json();
      if (!response.ok) {
        sendResponse({ ok: false, error: payload.detail || "CiteMD API request failed." });
        return;
      }
      sendResponse({ ok: true, data: payload });
    } catch (error) {
      sendResponse({
        ok: false,
        error: "Could not reach CiteMD API. Start it with: .venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8001"
      });
    }
  });

  return true;
});
