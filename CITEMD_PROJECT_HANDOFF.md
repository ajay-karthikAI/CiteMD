# CiteMD Project Handoff

Generated: 2026-06-10  
Workspace: `/Users/ajayk/Desktop/untitled folder`

This document is a migration summary for a new account/session. It captures what CiteMD is, what has been built, how it runs, what decisions were made, what is currently bloated, and what should happen next.

## One-Line Summary

CiteMD is a local-first biomedical research assistant and Chrome extension that acts like a "PubMed Copilot": it searches PubMed, retrieves abstracts, ranks evidence, generates cited scientific answers, and displays supporting papers with confidence scores.

## Original Goal

Build an AI application called **CiteMD**.

Core concept:

- User asks a biomedical research question.
- App searches PubMed using Entrez.
- App retrieves up to 100 abstracts.
- App stores/retrieves documents using embeddings and FAISS.
- App uses a biomedical transformer ranker for relevance scoring.
- App uses an LLM to generate a cited final answer.
- App displays supporting papers, citations, confidence scores, and evaluation metrics.

Example query:

```text
What are the latest treatments for pancreatic cancer?
```

Requested stack:

- Python
- PyTorch
- Hugging Face Transformers
- Sentence Transformers
- FAISS
- Streamlit
- LangChain
- OpenAI API
- PubMed Entrez / Biopython
- Chrome extension frontend

## Current Product Shape

CiteMD currently has two usable surfaces:

1. **Streamlit app**
   - Runs locally.
   - Provides a search box, generated answer, citations, confidence, conflicts, and evaluation-like evidence display.

2. **Chrome/Edge extension**
   - Injects a CiteMD panel into PubMed and Google Scholar pages.
   - Calls a local FastAPI backend.
   - Uses the current page as optional context.
   - Extension itself is tiny, about 48 KB.

The extension should be treated as a thin client. The backend, Python virtualenv, and ML models should not be packaged with the extension.

## Current Architecture

```mermaid
flowchart LR
    A[Chrome Extension or Streamlit UI] --> B[FastAPI / CiteMDAssistant]
    B --> C[PubMed Entrez Client]
    C --> D[Top PubMed Abstracts]
    D --> E[Sentence Transformer Embeddings]
    E --> F[FAISS Vector Store]
    F --> G[PubMedBERT Relevance Ranker]
    G --> H[OpenAI / LangChain Generation]
    G --> I[Evidence Conflict Detector]
    H --> J[Cited Answer]
    I --> J
    J --> K[Supporting Papers + Confidence]
```

## Main Directories

```text
backend/       FastAPI API, PubMed client, retrieval, ranking, generation, RAG orchestration
frontend/      Streamlit app
extension/     Chrome/Edge extension files
models/        Model helper code plus local fine-tuned PubMedBERT checkpoints
training/      Weak-label data generation and PubMedBERT fine-tuning scripts
evaluation/    Retrieval and generation evaluation scripts
data/          Weak-label dataset and local artifacts
tests/         Unit tests
config/        YAML configuration
notebooks/     Placeholder for experiments
```

## Important Files

```text
README.md
requirements.txt
pyproject.toml
Dockerfile
config/config.yaml

backend/api.py
backend/config.py
backend/schemas.py
backend/services/pubmed.py
backend/services/retrieval.py
backend/services/ranking.py
backend/services/generation.py
backend/services/rag.py
backend/services/conflict.py

frontend/app.py

extension/manifest.json
extension/background.js
extension/content.js
extension/styles.css
extension/popup.html
extension/popup.js
extension/popup.css
extension/README.md

training/weak_labels.py
training/train_ranker.py
training/dataset.py

evaluation/evaluate_retrieval.py
evaluation/evaluate_generation.py
evaluation/metrics.py

tests/test_api.py
tests/test_conflict.py
tests/test_metrics.py
tests/test_ranking.py
tests/test_retrieval.py
```

## Configuration

Current config file:

```text
config/config.yaml
```

Current settings:

```yaml
pubmed:
  email: citemd@example.com
  api_key:
  retmax: 100

models:
  embedding_model: pritamdeka/S-PubMedBert-MS-MARCO
  ranker_base_model: microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract
  ranker_model_path: models/pubmedbert-ranker-v2
  openai_model: gpt-4o-mini

rag:
  vector_store_dir: data/vector_store
  top_k_retrieval: 20
  top_k_context: 8

logging:
  level: INFO
```

Environment variables are loaded from `.env`. Do not paste secrets into handoffs or commits.

Expected variables:

```text
OPENAI_API_KEY=...
PUBMED_EMAIL=...
PUBMED_API_KEY=...       # optional but useful
```

## Backend API

Main file:

```text
backend/api.py
```

Endpoints:

```text
GET  /health
POST /api/answer
```

Request body for `/api/answer`:

```json
{
  "query": "What are the latest treatments for pancreatic cancer?",
  "pubmed_limit": 100,
  "top_k": 20,
  "page_context": []
}
```

`page_context` supports supplemental browser context:

```json
[
  {
    "source": "Google Scholar",
    "title": "Google Scholar results for pancreatic cancer treatment",
    "url": "https://scholar.google.com/...",
    "text": "Visible result titles, snippets, metadata, and links"
  }
]
```

Important runtime note:

- `backend/api.py` has a `main()` that runs on port `8000`.
- The extension and docs currently use `uvicorn` on port `8001`.
- Port `8000` was previously occupied by another local app, so CiteMD was moved to `8001`.

Recommended local API command:

```bash
.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

## Streamlit App

Main file:

```text
frontend/app.py
```

Run:

```bash
.venv/bin/streamlit run frontend/app.py --server.headless true --server.port 8501 --server.fileWatcherType none
```

Open:

```text
http://localhost:8501
```

## Chrome Extension

Directory:

```text
extension/
```

The actual extension is about 48 KB. The project is large because of `.venv/` and `models/`, not because of the extension.

Install locally:

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer Mode.
3. Click "Load unpacked".
4. Select only the `extension/` directory.
5. Start the local API on port `8001`.
6. Open PubMed or Google Scholar.
7. Click the CiteMD button.

Supported pages:

```text
https://pubmed.ncbi.nlm.nih.gov/*
https://scholar.google.com/*
```

Important extension behavior:

- `extension/background.js` default API URL is `http://localhost:8001`.
- It normalizes stale `http://localhost:8501` settings to `http://localhost:8001`.
- It sends `query`, `pubmed_limit`, `top_k`, and `page_context` to the backend.
- It does not call OpenAI directly.
- API keys should never be placed in the extension.

Google Scholar behavior:

- The extension reads only visible result titles, snippets, metadata, and links from the current page.
- The backend still retrieves PubMed literature.
- Do not implement backend scraping of Google Scholar for a public product; prefer official APIs and source partnerships.

## Current UI/Design State

The extension popup/panel was redesigned to look like a sleek dark-mode AI research tool.

Design direction:

- Dark charcoal background, not pure black.
- Emerald green accent.
- DM Sans for body text.
- DM Mono for labels, PMIDs, and confidence.
- Confidence shown as a percentage, not a decimal.
- Supporting papers styled as cards.
- PMID citations styled as inline code badges.
- Category labels like **Surgery**, **Chemotherapy**, **Targeted Therapies**, **Immunotherapy**, and **Radiotherapy** should render prominently.

Relevant files:

```text
extension/styles.css
extension/popup.css
extension/content.js
extension/popup.html
```

User preference:

- Avoid overly harsh black/green neon.
- Keep it polished, precise, and professional.
- "Perplexity meets Linear" was the desired feel.
- Answers should be scientific and straightforward, not layperson-simple and not rambly.
- Use bold category titles in generated answers.

## Generation Behavior

Main file:

```text
backend/services/generation.py
```

Current answer style aims to:

- Be concise.
- Use scientific language.
- Group key developments by bold category labels.
- Include inline citations such as `[PMID:27644909]`.
- Summarize uncertainty.
- Mention conflicting evidence when detected.

The LLM is configured in `config/config.yaml` as:

```yaml
openai_model: gpt-4o-mini
```

If `OPENAI_API_KEY` is missing, CiteMD should still return an extractive evidence summary rather than failing completely.

## Retrieval

Main file:

```text
backend/services/retrieval.py
```

Current retrieval stack:

- Sentence Transformers for embeddings.
- FAISS for vector similarity.
- Deterministic local embedding fallback if the embedding model is unavailable.

Configured embedding model:

```text
pritamdeka/S-PubMedBert-MS-MARCO
```

## Ranking

Main files:

```text
backend/services/ranking.py
models/ranker.py
training/train_ranker.py
training/dataset.py
```

Base ranker:

```text
microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract
```

Current configured fine-tuned ranker:

```text
models/pubmedbert-ranker-v2
```

The ranker takes:

```text
(question, paper abstract) -> relevance score
```

Fallback:

- If no fine-tuned model is available or loading fails, the system uses lexical relevance scoring rather than an untrained neural classifier.

Training now includes:

```text
--save-total-limit 1
```

This was added to prevent future Hugging Face training runs from saving many huge checkpoints.

## Weak Supervision Training

Weak-label generation:

```bash
python -m training.weak_labels \
  --query "pancreatic cancer treatment" \
  --output data/weak_ranker_dataset.jsonl \
  --positives 50 \
  --negatives 50
```

Training:

```bash
python -m training.train_ranker \
  --train-file data/weak_ranker_dataset.jsonl \
  --output-dir models/pubmedbert-ranker-v2 \
  --epochs 2 \
  --batch-size 8
```

Weak supervision rule:

- Top returned PubMed papers are positive examples.
- Random unrelated papers are negative examples.

Important caution:

- The current local model should be treated as a functional starter checkpoint, not a validated biomedical benchmark model.

## Evaluation

Main files:

```text
evaluation/metrics.py
evaluation/evaluate_retrieval.py
evaluation/evaluate_generation.py
```

Retrieval metrics:

- Recall@5
- Recall@10
- MRR

Ranking metrics:

- Accuracy
- Precision
- Recall
- F1

Generated-answer metrics:

- RAGAS-style evaluation
- Faithfulness
- Context precision
- Answer relevance

Current test command:

```bash
.venv/bin/python -m pytest
```

Last verified result on 2026-06-10:

```text
8 passed in 0.20s
```

Passing tests:

```text
tests/test_api.py
tests/test_conflict.py
tests/test_metrics.py
tests/test_ranking.py
tests/test_retrieval.py
```

## Evidence Conflict Detector

Main file:

```text
backend/services/conflict.py
```

Goal:

- Detect when retrieved papers contain conflicting conclusions.
- Show a message like "Conflicting evidence detected."
- Summarize both sides simply.

This is intentionally simple for now. It should be improved before public launch.

## Disk Usage / Bloat Context

The project looked huge because local ML artifacts were saved in the workspace.

Current approximate sizes:

```text
extension/   48 KB
backend/     160 KB
frontend/    28 KB
data/        148 KB
training/    40 KB
evaluation/  32 KB
tests/       68 KB
models/      5.7 GB
.venv/       1.4 GB
```

The Chrome extension itself is tiny. The large folders are:

```text
models/
.venv/
```

Largest model directories:

```text
models/pubmedbert-ranker-v2                  ~4.1 GB
models/pubmedbert-ranker                     ~1.6 GB
models/pubmedbert-ranker-v2/checkpoint-20    ~1.2 GB
models/pubmedbert-ranker-v2/checkpoint-40    ~1.2 GB
models/pubmedbert-ranker-v2/checkpoint-60    ~1.2 GB
models/pubmedbert-ranker/checkpoint-6        ~1.2 GB
```

Why this happened:

- Hugging Face Trainer saved full model checkpoints every epoch.
- Each checkpoint includes model weights and optimizer state.
- PubMedBERT is large.
- `.venv/` includes PyTorch, Transformers, FAISS, and scientific Python libraries.

Safe cleanup candidates, assuming the final v2 model should be kept:

```text
models/pubmedbert-ranker
models/pubmedbert-ranker-v2/checkpoint-20
models/pubmedbert-ranker-v2/checkpoint-40
models/pubmedbert-ranker-v2/checkpoint-60
```

Keep:

```text
models/pubmedbert-ranker-v2/model.safetensors
models/pubmedbert-ranker-v2/config.json
models/pubmedbert-ranker-v2/tokenizer files
```

Do not delete anything automatically without confirming first.

## Known Issues / Caveats

1. **CORS is open in development**
   - `backend/api.py` currently uses `allow_origins=["*"]`.
   - For production, restrict this to the Chrome extension ID and official domains.

2. **API port mismatch**
   - `backend/api.py` `main()` uses port `8000`.
   - Extension docs/config use `8001`.
   - Standardize this before release.

3. **The local model is not validated**
   - Current PubMedBERT ranker was weak-supervised.
   - It is useful for demos but not enough for official biomedical claims.

4. **Confidence scores are not clinical certainty**
   - They are relevance/confidence heuristics from retrieval/ranking/generation.
   - Do not artificially force scores to 85%+.
   - Calibrate confidence using evaluation data instead.

5. **Google Scholar support is page-context only**
   - It reads visible results from the browser page.
   - Avoid backend scraping for an official product.

6. **Mayo Clinic is not yet fully implemented as a source adapter**
   - User asked about adding Mayo Clinic.
   - Recommended approach: build a source adapter only if permitted by source terms/API, otherwise treat selected page text as browser page context.

7. **Not a medical device**
   - CiteMD should be positioned as a literature research assistant.
   - It should not diagnose, prescribe, or replace clinical judgment.

8. **No hosted deployment yet**
   - Currently local-first.
   - A professional app should host the backend and keep extension users away from local setup.

## User's Recent Questions And Decisions

The user asked why required ML libraries were not installed. The project now includes them in `requirements.txt`:

```text
torch
transformers
sentence-transformers
faiss-cpu
biopython
accelerate
```

The user asked how to set the OpenAI key:

- Use `.env`.
- Set `OPENAI_API_KEY`.
- Keep key server-side only.

The user had a "Connection error" from Streamlit:

- Restart Streamlit with the command above.

The user had CORS issues from the extension:

- The extension was hitting `http://localhost:8501/api/answer`, which is Streamlit, not FastAPI.
- The extension was updated to use `http://localhost:8001`.
- Background/popup code normalizes stale `8501` API settings to `8001`.

The user asked why confidence scores were low:

- The display was changed from decimal to percent.
- Scores should not be cosmetically inflated.
- Proper improvement requires better training/evaluation/calibration.

The user asked how this is a copilot / PubMed extension:

- It is an unpacked Chrome/Edge extension that injects a CiteMD panel into PubMed and Google Scholar pages.
- For official distribution, publish only the extension to Chrome Web Store and host the backend separately.

The user asked for a professional UI:

- Extension UI was redesigned with a dark, precise AI startup look.
- Key visual files are `extension/styles.css` and `extension/popup.css`.

The user asked for test prompts:

- Useful prompts include treatment updates, mechanism questions, evidence comparisons, guideline-like summaries, contradictions, and page-specific analysis.

The user asked about Google Scholar:

- Added Google Scholar content-script support.
- The extension sends visible Scholar page context to the backend.

The user asked why the project was 8 GB:

- Cause: model checkpoints and `.venv`.
- Actual extension is 48 KB.

## Professional / Official App Roadmap

Recommended next steps:

1. **Separate extension from backend**
   - Package only `extension/` for Chrome Web Store.
   - Keep backend/model on a hosted server.

2. **Clean disk artifacts**
   - Remove old/intermediate model checkpoints after confirming final v2 model is enough.
   - Keep source code lightweight.

3. **Deploy backend**
   - Dockerize FastAPI API.
   - Deploy to Render, Fly.io, Railway, AWS, GCP, or Azure.
   - Add HTTPS.

4. **Secure backend**
   - Restrict CORS.
   - Add rate limiting.
   - Add API auth.
   - Store OpenAI key in backend environment only.

5. **Improve source adapters**
   - PubMed is primary.
   - Add Mayo Clinic carefully only if source terms permit it.
   - Avoid unofficial backend scraping of Google Scholar.

6. **Improve citation faithfulness**
   - Every factual claim should map to one or more citations.
   - Remove unsupported claims.
   - Add citation validation tests.

7. **Calibrate confidence**
   - Use benchmark queries.
   - Report confidence as an evidence-quality signal, not an aesthetic score.

8. **Build a real evaluation set**
   - Create 30-100 biomedical benchmark questions.
   - Add gold relevant PMIDs.
   - Track retrieval, ranking, and generated-answer metrics.

9. **Add compliance docs**
   - Privacy policy.
   - Terms of use.
   - Medical disclaimer.
   - Data retention policy.

10. **Prepare Chrome Web Store release**
    - Manifest V3.
    - Minimal permissions.
    - Extension icon set.
    - Screenshots.
    - Support email.
    - Reviewer instructions.

## Recommended Production Architecture

```text
Chrome Extension
  - Lightweight UI
  - Content script for PubMed/Scholar pages
  - No API keys
  - No ML models

Hosted FastAPI Backend
  - /api/answer
  - PubMed retrieval
  - Source adapters
  - Ranking
  - Generation
  - Logging
  - Rate limiting
  - Auth

Model Layer
  - Hosted PubMedBERT ranker, or smaller/reranker API
  - Embedding model
  - Vector index/cache

Data Layer
  - Query/result cache
  - Evaluation datasets
  - Logs/analytics with privacy controls
```

## Commands To Remember

Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run FastAPI for extension:

```bash
.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

Run Streamlit:

```bash
.venv/bin/streamlit run frontend/app.py --server.headless true --server.port 8501 --server.fileWatcherType none
```

Run tests:

```bash
.venv/bin/python -m pytest
```

Train weak-supervised ranker:

```bash
python -m training.weak_labels \
  --query "pancreatic cancer treatment" \
  --output data/weak_ranker_dataset.jsonl \
  --positives 50 \
  --negatives 50

python -m training.train_ranker \
  --train-file data/weak_ranker_dataset.jsonl \
  --output-dir models/pubmedbert-ranker-v2 \
  --epochs 2 \
  --batch-size 8
```

## Good Test Prompts

Use these to test the app:

```text
What are the latest treatments for pancreatic cancer?
Compare FOLFIRINOX and gemcitabine plus nab-paclitaxel in pancreatic cancer.
What does PubMed say about immunotherapy in pancreatic cancer?
Are KRAS inhibitors effective in pancreatic cancer?
What are recent advances in targeted therapies for pancreatic cancer?
What is the evidence for stereotactic body radiotherapy in pancreatic cancer?
Summarize conflicting evidence on aspirin for primary prevention.
What are the latest treatments for triple-negative breast cancer?
What are emerging therapies for Alzheimer's disease?
What does the literature say about GLP-1 receptor agonists and cardiovascular outcomes?
```

Expected answer style:

- Direct scientific summary.
- Bold key development categories.
- Inline citations.
- Supporting papers listed below.
- Confidence shown as percent.
- Conflict warning when applicable.

## Current Verification Status

Last local verification:

```text
2026-06-10
.venv/bin/python -m pytest
8 passed in 0.20s
```

No browser re-test was performed while generating this handoff. The most important manual check for the new account is:

1. Start FastAPI on port `8001`.
2. Reload unpacked extension in Chrome.
3. Open PubMed.
4. Ask a query.
5. Confirm citations, confidence percent, and supporting papers render correctly.

## Final Mental Model For The New Account

CiteMD is not "a 2 GB Chrome extension." It is:

- A 48 KB Chrome extension.
- A local Python AI backend.
- A large optional local biomedical ranker.
- A prototype that already works locally but needs deployment, security, evaluation, cleanup, and compliance work before it can be called official.

The next best engineering move is to separate the extension from the backend completely, clean the checkpoint bloat, deploy the FastAPI backend, and make the extension point to that hosted API.
