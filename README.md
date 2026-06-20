# PdfBot — Production-Grade Local RAG System

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-6.4-646CFF?style=flat&logo=vite&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF4B4B?style=flat)
![HuggingFace](https://img.shields.io/badge/HuggingFace-all--mpnet--base--v2-FFD21E?style=flat&logo=huggingface&logoColor=black)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2-FF6B35?style=flat)


> A locally-hosted, full-stack Retrieval-Augmented Generation (RAG) system. Implements multi-query expansion, hybrid sparse-dense retrieval, Reciprocal Rank Fusion, parent-child chunking, cross-encoder reranking, and stateful conversational memory — all running entirely on-device with no external API dependencies.

---

## System Overview

PdfBot is a document-grounded QA system built on a FastAPI backend and a Vite/React frontend. The retrieval pipeline goes well beyond naive top-k similarity search — it combines sparse BM25 and dense vector retrieval across LLM-expanded query variants, fuses results using rank-based scoring, reconstructs parent-level context, and applies a neural cross-encoder reranker before passing context to the LLM.

All inference and embedding runs locally via Ollama and HuggingFace `sentence-transformers`. No data leaves the machine.

---

## Retrieval Pipeline

```
Raw User Query
      │
      ▼
┌─────────────────────┐
│   Query Rewriting   │  ← LLM resolves coreferences and follow-up references
│   (generateQuery)   │    using sliding conversation window
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Multi-Query        │  ← LLM generates MULTI_QUERY_COUNT=3 query variants
│  Expansion          │    to increase recall across diverse phrasings
└────────┬────────────┘
         │
    ┌────┴──── per query variant ────────────────┐
    ▼                                            ▼
┌─────────────┐                        ┌─────────────────┐
│ Dense Search│                        │  BM25 Sparse    │  Dense and BM25 search
│  ChromaDB   │                        │  Search         │  find their top 10 results
│  (child     │                        │  (child chunks) │  then combine them
│   chunks)   │                        │                 │
└──────┬──────┘                        └──────┬──────────┘
       └──────────────┬────────────────────────┘
                      ▼
             ┌─────────────────┐
             │  Reciprocal     │  ← rank-position fusion immune
             │  Rank Fusion    │    to scale differences between BM25 logits
             │  (RRF)          │    and cosine distances
             └────────┬────────┘
                      ▼
             ┌─────────────────┐
             │  Parent Chunk   │  ← Child chunks (400 tokens) map back to
             │  Reconstruction │    parent chunks (1500 tokens) via parent_hash
             └────────┬────────┘
                      ▼
             ┌─────────────────┐
             │  Cross-Encoder  │  ← ms-marco-MiniLM-L-6-v2 scores each
             │  Reranking      │    (query, document) pair and keep top 5 
             │  TOP_K_RERANK=5 │    deeply relevant results
             └────────┬────────┘
                      ▼
             ┌─────────────────┐
             │  LLM Generation │  ← llama3.2 via Ollama grounded answer
             │  + Citations    │    with source + page metadata injected
             └────────┬────────┘
                      ▼
             Answer + Source Pages
```

---

## Key Design Decisions

### Parent-Child Chunking
Documents are indexed at two granularities. **Child chunks** (400 tokens, 80 overlap) are used for retrieval — smaller chunks give higher-precision embedding matches. **Parent chunks** (1500 tokens, 200 overlap) are reconstructed post-retrieval and passed to the LLM — larger context windows reduce answer truncation and improve coherence.

### Reciprocal Rank Fusion
BM25 logit scores and cosine distances are not numerically comparable. Rather than normalizing and weighting raw scores (fragile, domain-dependent), PdfBot uses RRF with K=60. Each document's fused score is computed as the sum of `1 / (K + rank)` across all ranked lists. This is order-preserving, scale-invariant, and proven to outperform linear score combination in TREC benchmarks.

### Multi-Query Expansion
A single query may miss relevant passages due to vocabulary mismatch. The LLM generates 3 alternative phrasings of the original query. Dense and BM25 searches run independently for each variant, producing up to 6 ranked lists that are then fused via RRF — significantly improving recall without retraining.

### Cross-Encoder Reranking
Bi-encoder retrieval (FAISS/ChromaDB) is fast but approximate. After RRF, a cross-encoder (`ms-marco-MiniLM-L-6-v2`) scores each (query, document) pair jointly, capturing fine-grained relevance signals that bi-encoders miss. Documents scoring below the hard floor logit of -15.0 are discarded before LLM context assembly.

---

## Tech Stack

### Backend
| Component | Implementation |
|---|---|
| API Server | FastAPI + Uvicorn (async, background tasks) |
| LLM Inference | Ollama — `llama3.2:latest` |
| Vector Store | ChromaDB — `sentence-transformers/all-mpnet-base-v2` |
| Sparse Retrieval | BM25 via `rank-bm25`|
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| PDF Parsing | LangChain `PyPDF`|
| Chunking | Parent-child chunking strategy (`chunk.py`) |
### Frontend
| Component | Implementation |
|---|---|
| Framework | React 18 |
| API Layer | FastAPI  |
| Markdown | React markdown|


---

## Project Structure

```
PdfBot/
├── api.py               # FastAPI application — endpoints, background indexing, RAG orchestration
├── main.py              # LLM answer generation, prompt assembly, citation extraction
├── retrival.py          # Hybrid retrieval: multi-query, dense+BM25, RRF, parent reconstruction
├── embedding.py         # ChromaDB vector store creation and loading
├── bm25.py              # BM25 index creation, persistence, and search
├── chunk.py             # Parent-child document chunking with metadata linkage
├── rank.py              # Cross-encoder reranking with hard-floor filtering
├── generateQuery.py     # LLM query rewriting and multi-query expansion
├── memory.py            # Sliding-window conversation state management
├── py_pdf.py            # PDF text extraction and whitespace/artefact cleaning
├── config.py            # All tuneable hyperparameters in one place
├── .gitignore
│
└── frontend/
    ├── vite.config.js   # Dev proxy: /api/* → http://127.0.0.1:8000
    ├── package.json
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── styles.css
        ├── components/
        │   ├── ChatPanel.jsx        # Conversation thread, input handling
        │   ├── ChatMessage.jsx      # Message rendering with markdown support
        │   ├── DocumentSidebar.jsx  # Upload, status polling, document listing
        │   ├── Header.jsx
        │   ├── Sources.jsx          # Source citation chip rendering
        │   ├── Toast.jsx            # Error / info notifications
        │   └── UploadPanel.jsx      # File selection, validation, upload trigger
        ├── config/api.js            # BASE_URL configuration
        ├── hooks/useTheme.js        # Dark/light theme state hook
        ├── services/ragApi.js       # Axios wrappers for all API endpoints
        └── utils/format.js         # String and markdown formatting helpers
```

---

## Installation

### Requirements

- Python 3.10+
- Node.js 18+ / npm
- [Ollama](https://ollama.com/download) installed and running
- Git

---

### 1. Clone

```bash
git clone https://github.com/Naseef301/PdfBot.git
cd PdfBot
```

### 2. Backend

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Pull LLM

```bash
ollama pull llama3.2
```

### 4. Frontend

```bash
cd frontend && npm install
```

---

## Running

Requires **two concurrent terminals**.

```bash
# Terminal 1 — Backend
python -m uvicorn api:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Verify backend: `curl http://127.0.0.1:8000/api/health` → `{"status": "ok"}`

Open: `http://localhost:5173`

---

## Troubleshooting

**Port 8000 already in use:**
```powershell
netstat -ano | findstr ":8000"
taskkill /PID <PID> /F
```

**Frontend proxy error (`ECONNREFUSED 127.0.0.1:8000`):**  
Backend must be running before frontend requests are made. Confirm health endpoint responds.

**PowerShell execution policy:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

**`LF will be replaced by CRLF` warnings:**  
Normal Git behaviour on Windows. No action needed.

---

## Known Limitations

- **Single-document active context** — uploading a new PDF replaces the existing vector store and BM25 index
- **No streaming** — LLM response is returned in full after generation completes
- **In-memory session state** — conversation history is lost on server restart
- **English-optimised** — BM25 tokenisation and NLTK stopwords are tuned for English
- **Single-user** — global document state; concurrent users would interfere

---

## Roadmap

- [ ] Streaming token output via SSE
- [ ] Persistent session store (Redis / SQLite)
- [ ] Multi-document simultaneous indexing and cross-document retrieval
- [ ] DOCX / TXT / web page ingestion
- [ ] Confidence score display per source citation
- [ ] Docker Compose deployment
- [ ] Groq API backend as a drop-in Ollama replacement for cloud option

---

## Author

Built by [Naseef301](https://github.com/Naseef301)
