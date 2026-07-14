Markdown

# 🧠 Multimodal PDF RAG System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![LangChain](https://img.shields.io/badge/LangChain-0.3-orange?style=for-the-badge)
![CLIP](https://img.shields.io/badge/CLIP-ViT--B/32-purple?style=for-the-badge)
![FAISS](https://img.shields.io/badge/FAISS-Vector--DB-red?style=for-the-badge)

**An intelligent PDF question-answering system that understands both text and images using multimodal AI**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [Guardrails](#-guardrails)
- [Semantic Cache](#-semantic-cache)
- [How It Works](#-how-it-works)
- [Screenshots](#-screenshots)

---

## 🌟 Overview

The **Multimodal PDF RAG System** is a full-stack AI application that lets you upload PDF documents and ask questions about them in natural language. Unlike traditional RAG systems that only process text, this system **understands both text and images** (charts, diagrams, figures) embedded in your PDFs.

Built with **OpenAI CLIP** for multimodal embeddings, **FAISS** for vector similarity search, **LangChain** for the RAG pipeline, and **Groq** for ultra-fast LLM inference.

---

## ✨ Features

### 🤖 AI Capabilities
- **Multimodal Understanding** — Processes both text and images from PDFs
- **Vision Analysis** — Analyzes charts, graphs, diagrams, and figures
- **Context-Aware Answers** — Answers grounded strictly in document content
- **Query Enrichment** — Auto-converts vague queries to precise questions

### 🛡️ Guardrails System
- **Input Guardrails** — Blocks prompt injection, harmful content, jailbreak attempts
- **Output Guardrails** — Detects hallucinations, scrubs PII, filters toxic content
- **Rate Limiting** — Sliding window rate limiter per IP and per PDF
- **PII Detection** — Detects emails, phone numbers, SSNs, API keys

### ⚡ Semantic Cache
- **Exact Match Cache** — SHA-256 hash-based instant lookup
- **Semantic Cache** — CLIP cosine similarity fuzzy matching (≥0.97 threshold)
- **PDF-Scoped Cache** — Isolated cache namespace per document
- **LRU Eviction** — Automatic eviction with TTL expiration
- **Cache Persistence** — Survives within session

### 💻 Frontend
- **Drag & Drop Upload** — Easy PDF upload with progress tracking
- **Per-PDF Chat** — Isolated chat history for each document
- **Real-time Guardrail Feedback** — Visual blocked query cards with violations
- **Cache Indicators** — Shows exact/semantic cache hits with similarity scores
- **Test Suite** — Built-in UI for testing guardrails and cache
- **Dark Theme** — Modern dark UI with smooth animations

### 🔧 Backend
- **RESTful API** — FastAPI with automatic Swagger documentation
- **Persistent Storage** — PDFs survive server restarts via pickle serialization
- **Request Timing** — Every response includes latency headers
- **Structured Logging** — Detailed logs for debugging and monitoring

---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────────────┐
│ USER QUERY │
└─────────────────────────┬───────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ INPUT GUARDRAILS │
│ Prompt Injection │ Harmful Content │ PII │ Query Enrichment │
└─────────────────────────┬───────────────────────────────────────┘
│ (safe query)
▼
┌─────────────────────────────────────────────────────────────────┐
│ SEMANTIC CACHE │
│ Exact Match (SHA-256) │ Semantic Match (CLIP) │
└──────────┬──────────────────────────────────┬───────────────────┘
│ HIT │ MISS
│ ▼
│ ┌──────────────────────────────────┐
│ │ RAG PIPELINE │
│ │ │
│ │ PDF → Text Chunks + Images │
│ │ ↓ │
│ │ CLIP Embeddings │
│ │ ↓ │
│ │ FAISS Vector Search │
│ │ ↓ │
│ │ Context Assembly │
│ │ ↓ │
│ │ Groq LLM (Llama 4 Scout) │
│ └──────────────┬───────────────────┘
│ │
▼ ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT GUARDRAILS │
│ Hallucination Detection │ PII Scrubbing │ Toxicity Filter │
└─────────────────────────┬───────────────────────────────────────┘
│
▼
FINAL ANSWER

text


---

## 🛠️ Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | 0.115 | REST API framework |
| **Python** | 3.11 | Core language |
| **LangChain** | 0.3 | RAG pipeline orchestration |
| **CLIP (ViT-B/32)** | - | Multimodal embeddings |
| **FAISS** | 1.8 | Vector similarity search |
| **Groq** | - | LLM inference (Llama 4 Scout) |
| **PyMuPDF** | 1.24 | PDF text & image extraction |
| **Transformers** | 4.44 | HuggingFace model loading |
| **PyTorch** | 2.4 | Deep learning backend |
| **Uvicorn** | 0.30 | ASGI server |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **React** | 18 | UI framework |
| **Vite** | 5 | Build tool |
| **Tailwind CSS** | 3 | Styling |
| **Axios** | 1.7 | HTTP client |
| **React Dropzone** | 14 | File upload |
| **React Markdown** | 9 | Markdown rendering |
| **Lucide React** | 0.44 | Icons |

---

## 📁 Project Structure
multimodal-rag/
│
├── backend/ # FastAPI backend
│ ├── main.py # App entry point & all routes
│ ├── rag_engine.py # Core RAG pipeline
│ ├── requirements.txt # Python dependencies
│ ├── build.sh # Build script
│ ├── .env # Environment variables
│ │
│ ├── guardrails/ # Safety layer
│ │ ├── init.py
│ │ ├── input_guard.py # Input validation & enrichment
│ │ ├── output_guard.py # Output validation & PII scrub
│ │ └── rate_limiter.py # Sliding window rate limiter
│ │
│ ├── cache/ # Caching layer
│ │ ├── init.py
│ │ ├── semantic_cache.py # Two-level semantic cache
│ │ └── cache_manager.py # Cache orchestrator
│ │
│ ├── models/ # Pydantic schemas
│ │ └── schemas.py
│ │
│ └── storage/ # Persistent PDF store
│ └── pdf_store.pkl # Auto-generated
│
├── frontend/ # React frontend
│ ├── src/
│ │ ├── App.jsx # Root component
│ │ ├── main.jsx # Entry point
│ │ ├── index.css # Global styles
│ │ │
│ │ ├── api/
│ │ │ └── client.js # Axios API client
│ │ │
│ │ └── components/
│ │ ├── PDFUploader.jsx # Drag & drop uploader
│ │ ├── PDFList.jsx # Sidebar PDF list
│ │ ├── ChatInterface.jsx # Main chat UI
│ │ ├── MessageBubble.jsx # Message renderer
│ │ ├── CacheIndicator.jsx # Cache hit badge
│ │ └── TestPanel.jsx # Guardrail & cache tester
│ │
│ ├── package.json
│ ├── vite.config.js
│ ├── tailwind.config.js
│ └── vercel.json
│
├── docker-compose.yml
└── .gitignore

text


---

## 🚀 Getting Started

### Prerequisites
Python 3.11+
Node.js 20+
Groq API Key (free at console.groq.com)
text


### 1. Clone Repository

```bash
git clone https://github.com/PeyalaAnandanaidu/multimodal-rag.git
cd multimodal-rag
2. Backend Setup
Bash

cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
3. Environment Variables
Create backend/.env:

env

GROQ_API_KEY=your_groq_api_key_here
ALLOWED_ORIGINS=http://localhost:5173
Get your free Groq API key at console.groq.com

4. Run Backend
Bash

cd backend
uvicorn main:app --reload --port 8000
Backend starts at: http://localhost:8000
API Docs at: http://localhost:8000/docs

5. Frontend Setup
Bash

cd frontend

# Install dependencies
npm install
6. Frontend Environment
Create frontend/.env:

env

VITE_API_URL=http://localhost:8000
7. Run Frontend
Bash

cd frontend
npm run dev
Frontend starts at: http://localhost:5173

📡 API Reference
PDF Management
Method	Endpoint	Description
POST	/api/pdfs/upload	Upload and process a PDF
GET	/api/pdfs	List all uploaded PDFs
GET	/api/pdfs/{pdf_id}	Get PDF metadata
DELETE	/api/pdfs/{pdf_id}	Delete a PDF
Query
Method	Endpoint	Description
POST	/api/pdfs/{pdf_id}/query	Ask a question about a PDF
Cache
Method	Endpoint	Description
GET	/api/cache/stats	Global cache statistics
GET	/api/cache/stats/{pdf_id}	Per-PDF cache stats
DELETE	/api/cache	Clear all cache
DELETE	/api/cache/{pdf_id}	Clear PDF cache
System
Method	Endpoint	Description
GET	/health	Health check + system stats
Example Request
Bash

# Upload PDF
curl -X POST http://localhost:8000/api/pdfs/upload \
  -F "file=@document.pdf"

# Query PDF
curl -X POST http://localhost:8000/api/pdfs/{pdf_id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
Example Response
JSON

{
  "pdf_id": "abc-123",
  "query": "What is this document about?",
  "answer": "This document covers...",
  "sources": [
    {"page": 1, "type": "text", "preview": "..."},
    {"page": 1, "type": "image", "image_id": "page_0_img_0"}
  ],
  "from_cache": false,
  "warnings": [],
  "latency_ms": 2145.32
}
🛡️ Guardrails
Input Guardrails
Validates every query before processing:

Check	Description	Action
Length	Min 2, Max 2000 chars	Block
Prompt Injection	12 regex patterns	Block
Harmful Content	Dangerous keywords	Block
Off-Topic	Non-document queries	Block
PII Detection	Email, phone, SSN, etc.	Warn
Query Enrichment	Noun phrases → questions	Auto-fix
Query Enrichment Examples
text

"his projects"    →  "List all the projects mentioned in the document..."
"skills"          →  "What are the technical skills and technologies..."
"email"           →  "What is the email address mentioned in the document?"
"education"       →  "What is the educational background mentioned..."
Output Guardrails
Validates every LLM response before returning:

Check	Description	Action
Empty Response	Blank LLM output	Replace with fallback
Length	Max 8000 chars	Truncate gracefully
Hallucination	Out-of-context phrases	Add disclaimer
PII Scrubbing	Removes PII from output	Redact
Toxic Content	Harmful output	Block
Rate Limiting
Sliding window rate limiter:

text

Global:    60 requests/minute per IP
           300 requests/hour per IP
Per-PDF:   20 requests/minute per PDF
Uploads:   5 uploads/minute per IP
           50 uploads/day per IP
⚡ Semantic Cache
Two-level cache system for fast repeated queries:

Level 1: Exact Match
text

Query  →  SHA-256 hash  →  instant lookup
"What is this document about?"
    └→  hash: abc123...  →  cached answer ✅
Level 2: Semantic Match
text

Query  →  CLIP embedding  →  cosine similarity  →  cached answer
"What does this document cover?"
    └→  embedding [0.02, -0.05, ...]
        └→  similarity: 0.98 ≥ 0.97 threshold  →  cached ✅
Cache Configuration
Python

similarity_threshold = 0.97    # Minimum cosine similarity
ttl_seconds          = 3600    # 1 hour TTL
exact_ttl            = 7200    # 2 hour exact match TTL
max_entries          = 500     # LRU eviction limit
Cache Response
JSON

{
  "from_cache": true,
  "cache_similarity": 0.9823,
  "latency_ms": 67.32
}
🔍 How It Works
PDF Processing Pipeline
text

1. Upload PDF
      ↓
2. Extract text per page (PyMuPDF)
      ↓
3. Extract images per page (PyMuPDF)
      ↓
4. Split text into chunks (500 chars, 100 overlap)
      ↓
5. Generate CLIP embeddings for text chunks
      ↓
6. Generate CLIP embeddings for images
      ↓
7. Store in FAISS vector index
      ↓
8. Persist to disk (pickle)
Query Processing Pipeline
text

1. Receive query
      ↓
2. Rate limit check
      ↓
3. Input guardrails (validate + enrich)
      ↓
4. Cache lookup (exact → semantic)
      ↓  (cache miss)
5. Embed query with CLIP
      ↓
6. FAISS similarity search (k=6)
      ↓
7. Deduplicate retrieved docs
      ↓
8. Build multimodal prompt
   [System] + [Text Context] + [Images] + [Question]
      ↓
9. Groq LLM inference (Llama 4 Scout)
      ↓
10. Output guardrails
      ↓
11. Store in cache
      ↓
12. Return response
Multimodal Prompt Structure
text

[SYSTEM]
You are a precise document analyst AI...

[HUMAN]
=== DOCUMENT TEXT CONTEXT ===
[Page 1]
...extracted text...

=== DOCUMENT IMAGES (1 total) ===
[Image from Page 1, ID: page_0_img_0]
<base64 image>

=== USER QUESTION ===
What does the chart show?

Now answer using ONLY the document context...
🧪 Testing
The app includes a built-in Test Suite accessible from the UI (🧪 button in header).

Guardrail Tests
Test	Query	Expected
Prompt Injection	Ignore previous instructions...	🔴 Blocked
Harmful Content	how to make a bomb...	🔴 Blocked
Jailbreak	You are now DAN mode...	🔴 Blocked
Empty Query	(empty)	🔴 Blocked
Query Enrichment	his projects	✅ Pass + Enriched
PII Warning	email test@test.com	✅ Pass + Warning
Valid Query	What is this about?	✅ Pass
Cache Tests
Test	Expected
First query	Cache MISS (~2000ms)
Same query again	Exact Cache HIT (<100ms)
Similar query	Semantic Cache HIT (<200ms)
Different topic	Cache MISS (~2000ms)
🔑 Environment Variables
Backend
Variable	Required	Description
GROQ_API_KEY	✅ Yes	Groq API key
ALLOWED_ORIGINS	✅ Yes	CORS origins (comma-separated)
KMP_DUPLICATE_LIB_OK	Windows only	Fix OpenMP conflict
OMP_NUM_THREADS	Windows only	Limit OpenMP threads
Frontend
Variable	Required	Description
VITE_API_URL	✅ Yes	Backend API URL
📄 License
MIT License — see LICENSE file for details.

🙏 Acknowledgements
OpenAI CLIP — Multimodal embeddings
LangChain — RAG framework
Groq — Ultra-fast LLM inference
FAISS — Vector similarity search
PyMuPDF — PDF processing
FastAPI — API framework
