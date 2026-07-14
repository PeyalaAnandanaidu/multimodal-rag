# 🚀 Multimodal PDF RAG System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react">
  <img src="https://img.shields.io/badge/LangChain-RAG-orange?style=for-the-badge">
  <img src="https://img.shields.io/badge/FAISS-Vector_DB-red?style=for-the-badge">
  <img src="https://img.shields.io/badge/CLIP-Multimodal-purple?style=for-the-badge">
</p>

<p align="center">
A production-ready <b>Multimodal Retrieval-Augmented Generation (RAG)</b> system that answers questions from PDFs using both <b>text and images</b>.
</p>

---

## ✨ Highlights

- 📄 Upload one or multiple PDFs
- 🖼️ Understands text, charts, diagrams, tables, and figures
- 🧠 CLIP embeddings for multimodal retrieval
- ⚡ FAISS vector search
- 🤖 LangChain-powered RAG pipeline
- 🚀 Groq (Llama) inference
- 🛡️ Input & Output Guardrails
- ⚡ Exact + Semantic Cache
- 📊 Swagger API documentation
- 💬 Modern React chat interface

---

# Architecture

```text
                User
                  │
                  ▼
          React Frontend
                  │
                  ▼
          FastAPI REST API
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
 Input Guardrails      Semantic Cache
      │                       │
      └───────────┬───────────┘
                  ▼
          Multimodal RAG Engine
                  │
     PDF → Text + Images
                  │
         CLIP Embeddings
                  │
             FAISS Search
                  │
        Context Construction
                  │
          Groq Llama Model
                  │
       Output Guardrails
                  │
                  ▼
             Final Answer
```

---

# Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11 |
| AI | LangChain, OpenAI CLIP |
| Vector DB | FAISS |
| LLM | Groq Llama |
| PDF Parsing | PyMuPDF |
| Deep Learning | PyTorch |
| Frontend | React + Vite |
| Styling | Tailwind CSS |

---

# Features

## AI
- Multimodal document understanding
- Vision-aware retrieval
- Context-grounded answers
- Automatic query enrichment

## Guardrails
- Prompt injection protection
- Harmful content filtering
- PII detection
- Hallucination detection
- Rate limiting

## Semantic Cache
- SHA256 exact cache
- CLIP similarity cache
- LRU eviction
- TTL expiration
- Per-document cache isolation

---

# Project Structure

```text
backend/
frontend/
guardrails/
cache/
storage/
docker-compose.yml
README.md
```

---

# Quick Start

## Backend

```bash
git clone https://github.com/<username>/multimodal-rag.git
cd multimodal-rag/backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload
```

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# Environment Variables

Backend

```env
GROQ_API_KEY=YOUR_KEY
ALLOWED_ORIGINS=http://localhost:5173
```

Frontend

```env
VITE_API_URL=http://localhost:8000
```

---

# REST API

| Method | Endpoint |
|---------|----------|
| POST | /api/pdfs/upload |
| GET | /api/pdfs |
| POST | /api/pdfs/{pdf_id}/query |
| GET | /api/cache/stats |
| GET | /health |

Swagger:

```
http://localhost:8000/docs
```

---

# Example Response

```json
{
  "answer":"...",
  "sources":[...],
  "from_cache":false,
  "latency_ms":1543
}
```

---

# Roadmap

- Docker deployment
- Qdrant support
- Hybrid search
- OCR pipeline
- Authentication
- Streaming responses
- Evaluation dashboard

---

# License

MIT License

---

# Acknowledgements

- OpenAI CLIP
- LangChain
- FAISS
- Groq
- FastAPI
- PyMuPDF
