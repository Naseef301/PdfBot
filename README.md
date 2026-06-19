# 🤖 PdfBot — Local RAG PDF Chatbot

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-6.4-646CFF?style=flat&logo=vite&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Embeddings-FFD21E?style=flat&logo=huggingface&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-Integrated-1C3C3C?style=flat)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat)

> A fully local AI-powered PDF chatbot. Upload any PDF — ask anything. Every answer is grounded in your document. No cloud. No API fees. Your data never leaves your machine.

---

## 📌 What Is This?

**PdfBot** is a full-stack **Retrieval-Augmented Generation (RAG)** chatbot built from scratch with a FastAPI backend and a Vite + React frontend. It lets you have intelligent conversations with your PDF documents — entirely on your local machine.

It implements advanced retrieval techniques beyond basic RAG:
- **Hybrid retrieval** combining dense embeddings and BM25 keyword search
- **Cross-encoder reranking** for precision document scoring
- **LLM-based query rewriting** to handle follow-up questions
- **Conversational memory** for multi-turn context-aware dialogue
- **Background indexing** so the UI stays responsive during processing

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 PDF Upload | Upload any PDF — validated, size-limited (30 MB), background indexed |
| 🔍 Hybrid Retrieval | Dense semantic search + BM25 keyword search combined |
| 🎯 Cross-Encoder Reranking | Neural reranker scores every (query, doc) pair for precision |
| 🔄 Query Rewriting | LLM resolves follow-ups and vague references automatically |
| 🧠 Conversational Memory | Multi-turn dialogue with automatic context carry-over |
| ⚡ Background Indexing | Document processing runs async — UI stays responsive |
| 📎 Source Citations | Every answer shows the source document and page |
| 🔒 Fully Local | No OpenAI, no external APIs — all on your machine |
| 🌙 Dark / Light Mode | Theme toggle built into the UI |
| 🏥 Health Endpoint | `/api/health` for easy status checks |

---

## 🏗️ Architecture

```
User Question
      │
      ▼
┌──────────────────┐
│  Query Rewriting  │  ← LLM resolves follow-ups & ambiguous references
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│        Hybrid Retrieval               │
│  ┌─────────────┐  ┌───────────────┐  │
│  │ Dense Vector│  │  BM25 Keyword │  │  ← Semantic + keyword search
│  │ (embeddings)│  │    Search     │  │
│  └──────┬──────┘  └──────┬────────┘  │
│         └────────┬────────┘          │
└──────────────────┼───────────────────┘
                   ▼
         ┌─────────────────┐
         │  Cross-Encoder  │  ← Neural reranker scores every (query, doc) pair
         │   Reranking     │
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │  Conversation   │  ← Injects chat history for context-aware answers
         │     Memory      │
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │  LLM Answer     │  ← Generates grounded answer with cited sources
         │  Generation     │
         └────────┬────────┘
                  ▼
        Answer + Sources [page 1][page 4]
```

---

## 🛠️ Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Server | FastAPI + Uvicorn |
| PDF Parsing | LangChain + PyPDF |
| Embeddings | HuggingFace Sentence Transformers |
| Keyword Search | BM25 (rank-bm25) |
| Reranker | Cross-Encoder (sentence-transformers) |
| Query Rewriting | LLM-based (`generateQuery.py`) |
| Memory | Custom conversation state (`memory.py`) |
| Chunking | Custom chunking strategy (`chunk.py`) |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 18 |
| Build Tool | Vite 6.4 |
| Proxy | Vite dev proxy → FastAPI |
| Styling | CSS with dark/light theme |

---

## 📁 Project Structure

```
PdfBot/
│
├── api.py               # FastAPI app — all endpoints & RAG pipeline
├── main.py              # Core answer generation logic
├── embedding.py         # Embedding model & vector store management
├── bm25.py              # BM25 keyword search index
├── chunk.py             # PDF chunking strategy
├── retrival.py          # Hybrid retrieval pipeline
├── rank.py              # Cross-encoder reranking
├── generateQuery.py     # LLM query rewriting & expansion
├── memory.py            # Conversation state management
├── py_pdf.py            # PDF loading & text cleaning
├── config.py            # Central configuration settings
├── .gitignore
│
└── frontend/
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── styles.css
        ├── components/
        │   ├── ChatPanel.jsx        # Main chat interface
        │   ├── ChatMessage.jsx      # Individual message rendering
        │   ├── DocumentSidebar.jsx  # PDF upload & document list
        │   ├── Header.jsx           # Top navigation bar
        │   ├── Sources.jsx          # Source citation display
        │   ├── Toast.jsx            # Notifications
        │   └── UploadPanel.jsx      # PDF upload logic
        ├── config/
        │   └── api.js               # API base URL config
        ├── hooks/
        │   └── useTheme.js          # Dark/light mode hook
        ├── services/
        │   └── ragApi.js            # API calls to FastAPI backend
        └── utils/
            └── format.js            # Text formatting helpers
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Git

---

### 1. Clone the Repository

```bash
git clone https://github.com/Naseef301/PdfBot.git
cd PdfBot
```

---

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate — Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Activate — macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Frontend Setup

```bash
cd frontend
npm install
```

---

## 🚀 Running the Project

You need **two terminals** running at the same time.

**Terminal 1 — FastAPI Backend:**
```bash
cd PdfBot
.\.venv\Scripts\Activate.ps1        # Windows
python -m uvicorn api:app --reload --port 8000
```

Backend runs at: `http://127.0.0.1:8000`

**Terminal 2 — React Frontend:**
```bash
cd PdfBot/frontend
npm run dev
```

Frontend runs at: `http://localhost:5173`

Open your browser at **http://localhost:5173**

---

## 💡 How to Use

1. **Upload** — Click "Upload PDF" in the sidebar and select your PDF
2. **Wait** — The status changes to "ready" when indexing is complete
3. **Ask** — Type your question in the chat box and press Enter
4. **Read** — Answer appears with source citations showing which page the info came from
5. **Follow up** — Ask follow-up questions; the bot remembers the conversation context

### Example Questions
```
What is this document about?
Summarize the key points
What does section 3 say?
Can you explain that in simpler terms?    ← follow-up remembered automatically
```

---

## 🔧 Configuration

Key settings are in `config.py`:

```python
CHUNK_SIZE = 512          # Token size per chunk
CHUNK_OVERLAP = 64        # Overlap between chunks
TOP_K_DENSE = 10          # Dense retrieval results
TOP_K_BM25 = 10           # BM25 keyword results
TOP_K_RERANK = 5          # Final docs after reranking
MEMORY_WINDOW = 4         # Conversation turns to remember
# MAX_FILE_SIZE = 30 MB   # Upload size limit (set in api.py)
```

---

## 🐛 Troubleshooting

### Backend shuts down immediately / port 8000 in use

```powershell
# Find what is using port 8000
netstat -ano | findstr ":8000"

# Kill the process (replace PID with the number you see)
taskkill /PID <PID> /F
```

Then restart the backend.

### Frontend shows `ECONNREFUSED` or proxy error

The backend must be running **before** or **at the same time** as the frontend. Both servers must be active in separate terminals. Check that `http://127.0.0.1:8000/api/health` returns `{"status":"ok"}` in your browser.

### `LF will be replaced by CRLF` warnings on Windows

These are normal Git warnings on Windows. They do not affect how the project runs and can be safely ignored.

### PowerShell execution policy error

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Run this once per terminal session before activating the virtual environment.

---

## 🔮 Future Improvements

- [ ] Streaming responses (word-by-word answer display)
- [ ] Support for DOCX and TXT files
- [ ] Multi-document comparison and cross-document search
- [ ] Document management (list, rename, delete individual docs)
- [ ] Export chat history
- [ ] Persistent vector store across sessions
- [ ] Deploy with Docker

---

## 🙌 Author

Built by [Naseef301](https://github.com/Naseef301)

---

## 📄 License

This project is licensed under the MIT License.
