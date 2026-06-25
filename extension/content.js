const PANEL_ID = "citemd-pubmed-panel";
const BUTTON_ID = "citemd-pubmed-button";

function getArticleTitle() {
  const heading = document.querySelector("h1.heading-title");
  if (heading) {
    return heading.textContent.replace(/\s+/g, " ").trim();
  }
  if (isGoogleScholar()) {
    const firstResult = document.querySelector(".gs_rt");
    if (firstResult) {
      return firstResult.textContent.replace(/\s+/g, " ").trim();
    }
  }
  return document.title.replace(/\s+-\s+Google Scholar\s*$/i, "").trim();
}

function getSearchQuery() {
  const term = document.querySelector("#id_term");
  if (term && term.value) {
    return term.value.trim();
  }
  const scholarInput = document.querySelector("#gs_hdr_tsi, input[name='q']");
  if (scholarInput && scholarInput.value) {
    return scholarInput.value.trim();
  }
  const query = new URLSearchParams(window.location.search).get("term");
  if (query) {
    return query.trim();
  }
  const scholarQuery = new URLSearchParams(window.location.search).get("q");
  return scholarQuery ? scholarQuery.trim() : "";
}

function getAbstractText() {
  const abstract = document.querySelector(".abstract-content");
  return abstract ? abstract.textContent.replace(/\s+/g, " ").trim() : "";
}

function defaultQuestion() {
  const title = getArticleTitle();
  const searchQuery = getSearchQuery();
  if (isGoogleScholar() && searchQuery) {
    return `Summarize the biomedical evidence for: ${searchQuery}`;
  }
  if (title) {
    return `What does current PubMed literature say about: ${title}`;
  }
  if (searchQuery) {
    return searchQuery;
  }
  return "What are the latest treatments for pancreatic cancer?";
}

function buildPanel() {
  if (document.getElementById(PANEL_ID)) {
    return;
  }

  const panel = document.createElement("aside");
  panel.id = PANEL_ID;
  panel.innerHTML = `
    <div class="citemd-header">
      <div>
        <div class="citemd-title">CiteMD</div>
        <div class="citemd-subtitle">PubMed + Scholar Copilot</div>
      </div>
      <button class="citemd-icon-button" data-citemd-close aria-label="Close CiteMD">x</button>
    </div>
    <textarea class="citemd-query" rows="5"></textarea>
    <div class="citemd-controls">
      <button class="citemd-primary" data-citemd-run>Ask CiteMD</button>
      <button class="citemd-secondary" data-citemd-page>Use Page</button>
    </div>
    <div class="citemd-status"></div>
    <div class="citemd-result"></div>
  `;
  document.body.appendChild(panel);

  const textarea = panel.querySelector(".citemd-query");
  textarea.value = defaultQuestion();

  panel.querySelector("[data-citemd-close]").addEventListener("click", () => {
    panel.classList.remove("is-open");
  });
  panel.querySelector("[data-citemd-page]").addEventListener("click", () => {
    const title = getArticleTitle();
    const abstract = getAbstractText();
    const searchQuery = getSearchQuery();
    if (isGoogleScholar()) {
      textarea.value = searchQuery
        ? `Analyze these Google Scholar results and compare them with PubMed literature: ${searchQuery}`
        : `Analyze this Google Scholar page and compare it with PubMed literature: ${title}`;
      return;
    }
    textarea.value = title && abstract
      ? `Analyze this PubMed article and compare it with related literature: ${title}`
      : defaultQuestion();
  });
  panel.querySelector("[data-citemd-run]").addEventListener("click", () => {
    runCiteMD(textarea.value);
  });
}

function buildButton() {
  if (document.getElementById(BUTTON_ID)) {
    return;
  }

  const button = document.createElement("button");
  button.id = BUTTON_ID;
  button.textContent = "CiteMD";
  button.addEventListener("click", () => {
    buildPanel();
    document.getElementById(PANEL_ID).classList.toggle("is-open");
  });
  document.body.appendChild(button);
}

function setStatus(message) {
  const status = document.querySelector(`#${PANEL_ID} .citemd-status`);
  if (status) {
    status.textContent = message;
  }
}

function renderResponse(response) {
  const target = document.querySelector(`#${PANEL_ID} .citemd-result`);
  if (!target) {
    return;
  }

  const citations = (response.citations || []).slice(0, 8).map((citation) => `
    <li>
      <a href="${citation.url}" target="_blank" rel="noreferrer">${escapeHtml(citationLabel(citation))}</a>
      <span>${escapeHtml(citation.title)}</span>
      <strong>${formatPercent(citation.score)}</strong>
    </li>
  `).join("");

  const conflict = response.conflict && response.conflict.conflicting
    ? `<div class="citemd-conflict">${escapeHtml(response.conflict.summary)}</div>`
    : "";

  target.innerHTML = `
    <div class="citemd-confidence">Confidence ${formatPercent(response.confidence)}</div>
    ${conflict}
    <div class="citemd-answer">${markdownLite(response.answer || "", response.citations || [])}</div>
    <h3>Supporting papers</h3>
    <ol class="citemd-citations">${citations}</ol>
  `;
}

function runCiteMD(query) {
  const cleanQuery = query.trim();
  if (!cleanQuery) {
    setStatus("Ask a biomedical question first.");
    return;
  }

  setStatus("Searching PubMed and ranking evidence...");
  chrome.runtime.sendMessage(
    {
      type: "CITEMD_ANSWER",
          query: cleanQuery,
          pubmedLimit: 100,
          topK: 20,
          pageContext: getPageContexts()
    },
    (response) => {
      if (!response || !response.ok) {
        setStatus(response && response.error ? response.error : "CiteMD request failed.");
        return;
      }
      setStatus("");
      renderResponse(response.data);
    }
  );
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function citationLabel(citation) {
  if ((citation.source || "PubMed") === "PubMed") {
    return `PMID:${citation.pmid}`;
  }
  return `${citation.source}:${citation.pmid}`;
}

function isGoogleScholar() {
  return window.location.hostname === "scholar.google.com";
}

function getPageContexts() {
  if (isGoogleScholar()) {
    const context = getGoogleScholarContext();
    return context ? [context] : [];
  }
  const title = getArticleTitle();
  const abstract = getAbstractText();
  if (title && abstract) {
    return [{
      source: "PubMed Page",
      title,
      url: window.location.href,
      text: abstract
    }];
  }
  return [];
}

function getGoogleScholarContext() {
  const query = getSearchQuery();
  const results = Array.from(document.querySelectorAll(".gs_r.gs_or.gs_scl")).slice(0, 8);
  const snippets = results.map((result, index) => {
    const titleEl = result.querySelector(".gs_rt");
    const linkEl = titleEl ? titleEl.querySelector("a") : null;
    const metaEl = result.querySelector(".gs_a");
    const snippetEl = result.querySelector(".gs_rs");
    const title = titleEl ? titleEl.textContent.replace(/\s+/g, " ").trim() : `Result ${index + 1}`;
    const url = linkEl ? linkEl.href : "";
    const meta = metaEl ? metaEl.textContent.replace(/\s+/g, " ").trim() : "";
    const snippet = snippetEl ? snippetEl.textContent.replace(/\s+/g, " ").trim() : "";
    return `${index + 1}. ${title}\n${meta}\n${snippet}\n${url}`.trim();
  }).filter(Boolean);

  if (!snippets.length) {
    return null;
  }

  return {
    source: "Google Scholar",
    title: query ? `Google Scholar results for ${query}` : "Google Scholar visible results",
    url: window.location.href,
    text: snippets.join("\n\n")
  };
}

function markdownLite(value, citations) {
  let safe = escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[PMID:(\d+)\]/g, '<a href="https://pubmed.ncbi.nlm.nih.gov/$1/" target="_blank" rel="noreferrer">[PMID:$1]</a>');
  citations.forEach((citation) => {
    const label = citationLabel(citation);
    if (label.startsWith("PMID:")) {
      return;
    }
    const escapedLabel = escapeHtml(label).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const replacement = `<a href="${escapeHtml(citation.url)}" target="_blank" rel="noreferrer">[${escapeHtml(label)}]</a>`;
    safe = safe.replace(new RegExp(`\\[${escapedLabel}\\]`, "g"), replacement);
  });
  const lines = safe.split(/\n+/);
  const html = [];
  let inList = false;

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }
    if (trimmed.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${trimmed.slice(2)}</li>`);
      return;
    }
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
    html.push(`<p>${trimmed}</p>`);
  });

  if (inList) {
    html.push("</ul>");
  }

  return html.join("");
}

buildButton();
buildPanel();
