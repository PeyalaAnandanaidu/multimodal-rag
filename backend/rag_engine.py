# ============================================================
# Fix Windows OpenMP conflict — MUST be first
# ============================================================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"]       = "1"

import fitz
import io
import base64
import uuid
import pickle
from pathlib import Path
from typing import Optional
from datetime import datetime

from langchain_core.documents import Document
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model


# ============================================================
# Global CLIP Model
# ============================================================
print("Loading CLIP model...")
clip_model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model.eval()
print("CLIP model loaded.")


# ============================================================
# PDF Store (in-memory)
# ============================================================
pdf_store: dict[str, dict] = {}


# ============================================================
# Persistence Configuration
# ============================================================
STORAGE_DIR    = Path("./storage")
PDF_STORE_PATH = STORAGE_DIR / "pdf_store.pkl"
STORAGE_DIR.mkdir(exist_ok=True)


def load_pdf_store():
    """Load pdf_store from disk on startup."""
    global pdf_store
    if PDF_STORE_PATH.exists():
        try:
            with open(PDF_STORE_PATH, "rb") as f:
                pdf_store = pickle.load(f)
            print(f"✅ Loaded {len(pdf_store)} PDF(s) from disk")
        except Exception as e:
            print(f"⚠️  Failed to load PDF store: {e}")
            pdf_store = {}
    else:
        print("ℹ️  No existing PDF store found, starting fresh")


def save_pdf_store():
    """Persist pdf_store to disk."""
    try:
        with open(PDF_STORE_PATH, "wb") as f:
            pickle.dump(pdf_store, f)
        print(f"💾 Saved {len(pdf_store)} PDF(s) to disk")
    except Exception as e:
        print(f"⚠️  Failed to save PDF store: {e}")


# Auto-load on module import
load_pdf_store()


# ============================================================
# Embedding Functions
# ============================================================
def embed_image(pil_image: Image.Image) -> np.ndarray:
    inputs = clip_processor(images=pil_image, return_tensors="pt")
    with torch.no_grad():
        features = clip_model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().numpy()


def embed_text(text: str) -> np.ndarray:
    inputs = clip_processor(
        text=text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=77
    )
    with torch.no_grad():
        features = clip_model.get_text_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().numpy()


# ============================================================
# Process PDF
# ============================================================
def process_pdf(pdf_bytes: bytes, filename: str) -> dict:
    pdf_id = str(uuid.uuid4())
    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")

    all_docs         = []
    all_embeddings   = []
    image_data_store = {}
    page_count       = len(doc)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )

    for page_num, page in enumerate(doc):

        # ── Text ─────────────────────────────────────────
        text = page.get_text()
        if text.strip():
            temp_doc = Document(
                page_content=text,
                metadata={"page": page_num, "type": "text"}
            )
            for chunk in splitter.split_documents([temp_doc]):
                all_docs.append(chunk)
                all_embeddings.append(embed_text(chunk.page_content))

        # ── Images ───────────────────────────────────────
        for img_index, img in enumerate(page.get_images(full=True)):
            try:
                xref        = img[0]
                base_image  = doc.extract_image(xref)
                image_bytes = base_image["image"]
                pil_image   = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                image_id    = f"page_{page_num}_img_{img_index}"

                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                image_data_store[image_id] = base64.b64encode(
                    buffered.getvalue()
                ).decode()

                image_doc = Document(
                    page_content=f"[Image:{image_id}]",
                    metadata={
                        "page":     page_num,
                        "type":     "image",
                        "image_id": image_id
                    }
                )
                all_docs.append(image_doc)
                all_embeddings.append(embed_image(pil_image))

            except Exception as e:
                print(f"Image error page {page_num}: {e}")

    doc.close()

    if not all_docs:
        raise ValueError("No content extracted from PDF.")

    # ── Build FAISS vector store ──────────────────────────
    embeddings_array = np.array(all_embeddings)
    vector_store     = FAISS.from_embeddings(
        text_embeddings=[
            (d.page_content, emb)
            for d, emb in zip(all_docs, embeddings_array)
        ],
        embedding  = None,
        metadatas  = [d.metadata for d in all_docs]
    )

    # ── Store in memory ───────────────────────────────────
    pdf_store[pdf_id] = {
        "filename":         filename,
        "vector_store":     vector_store,
        "image_data_store": image_data_store,
        "page_count":       page_count,
        "doc_count":        len(all_docs),
        "created_at":       datetime.now().isoformat()
    }

    # ── Persist to disk ───────────────────────────────────
    save_pdf_store()

    print(f"✅ PDF '{filename}' → {pdf_id} | Pages:{page_count} Docs:{len(all_docs)}")
    return {
        "pdf_id":      pdf_id,
        "filename":    filename,
        "page_count":  page_count,
        "doc_count":   len(all_docs),
        "image_count": len(image_data_store)
    }


# ============================================================
# Retrieve — with deduplication
# ============================================================
def retrieve_multimodal(pdf_id: str, query: str, k: int = 6) -> list:
    if pdf_id not in pdf_store:
        raise ValueError(f"PDF '{pdf_id}' not found.")

    vector_store    = pdf_store[pdf_id]["vector_store"]
    query_embedding = embed_text(query)
    results         = vector_store.similarity_search_by_vector(query_embedding, k=k)

    # ── Deduplicate by content ────────────────────────────
    seen   = set()
    unique = []
    for doc in results:
        key = (
            doc.metadata.get("type"),
            doc.metadata.get("image_id", ""),
            doc.page_content[:200]
        )
        if key not in seen:
            seen.add(key)
            unique.append(doc)

    return unique


# ============================================================
# Build Multimodal Message  (context-first structure)
# ============================================================
def create_multimodal_message(
    query:            str,
    retrieved_docs:   list,
    image_data_store: dict
) -> list:
    """Returns [SystemMessage, HumanMessage] with context BEFORE question."""

    text_docs  = [d for d in retrieved_docs if d.metadata.get("type") == "text"]
    image_docs = [d for d in retrieved_docs if d.metadata.get("type") == "image"]

    # ── System Message ────────────────────────────────────
    system_msg = SystemMessage(content="""You are a precise document analyst AI.

STRICT RULES:
1. Answer ONLY using the provided document context below.
2. NEVER say "ask your question" or "go ahead" — the question is already provided.
3. If information is not in the context, say: "This information is not available in the document."
4. Always be specific — quote or reference exact content from the document.
5. If a chart/image is provided, describe what you see in detail.
6. Never make up information not present in the context.""")

    # ── Human Message content ─────────────────────────────
    content = []

    # ── Step 1: Provide ALL context FIRST ─────────────────
    if text_docs:
        text_sections = []
        for doc in text_docs:
            page_num = doc.metadata.get("page", 0) + 1
            text_sections.append(
                f"[Page {page_num}]\n{doc.page_content.strip()}"
            )
        full_text = "\n\n---\n\n".join(text_sections)
        content.append({
            "type": "text",
            "text": f"=== DOCUMENT TEXT CONTEXT ===\n\n{full_text}\n\n=== END OF TEXT CONTEXT ==="
        })

    if image_docs:
        content.append({
            "type": "text",
            "text": f"=== DOCUMENT IMAGES ({len(image_docs)} total) ==="
        })
        for doc in image_docs:
            image_id = doc.metadata.get("image_id", "")
            page_num = doc.metadata.get("page", 0) + 1

            if not image_id or image_id not in image_data_store:
                continue

            image_b64 = image_data_store[image_id]
            if not image_b64 or len(image_b64) < 100:
                continue

            content.append({
                "type": "text",
                "text": f"[Image from Page {page_num}, ID: {image_id}]"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url":    f"data:image/png;base64,{image_b64}",
                    "detail": "high"
                }
            })
        content.append({
            "type": "text",
            "text": "=== END OF IMAGES ==="
        })

    # ── Step 2: Ask the question AFTER context ─────────────
    content.append({
        "type": "text",
        "text": (
            f"\n=== USER QUESTION ===\n"
            f"{query}\n"
            f"=== END OF QUESTION ===\n\n"
            f"Now answer the question above using ONLY the document context provided. "
            f"Be specific, accurate, and reference page numbers where relevant."
        )
    })

    human_msg = HumanMessage(content=content)
    return [system_msg, human_msg]


# ============================================================
# Full RAG Pipeline
# ============================================================
def run_rag_pipeline(pdf_id: str, query: str) -> dict:
    if pdf_id not in pdf_store:
        return {"error": f"PDF '{pdf_id}' not found.", "answer": None}

    image_data_store = pdf_store[pdf_id]["image_data_store"]
    retrieved_docs   = retrieve_multimodal(pdf_id, query, k=6)

    if not retrieved_docs:
        return {
            "answer":  "No relevant content found for your question.",
            "sources": []
        }

    messages = create_multimodal_message(query, retrieved_docs, image_data_store)

    llm = init_chat_model(
        model          = "meta-llama/llama-4-scout-17b-16e-instruct",
        model_provider = "groq",
        temperature    = 0
    )

    try:
        response = llm.invoke(messages)
        answer   = response.content

        # ── Build deduplicated sources ────────────────────
        seen_sources = set()
        sources      = []
        for doc in retrieved_docs:
            page     = doc.metadata.get("page", 0) + 1
            doc_type = doc.metadata.get("type")
            src_key  = (page, doc_type, doc.metadata.get("image_id", ""))

            if src_key in seen_sources:
                continue
            seen_sources.add(src_key)

            source = {"page": page, "type": doc_type}
            if doc_type == "image":
                source["image_id"] = doc.metadata.get("image_id")
            else:
                source["preview"] = doc.page_content[:120].strip()
            sources.append(source)

        return {"answer": answer, "sources": sources}

    except Exception as e:
        return {"error": str(e), "answer": None}


# ============================================================
# PDF Management
# ============================================================
def list_pdfs() -> list:
    return [
        {
            "pdf_id":      pid,
            "filename":    d["filename"],
            "page_count":  d["page_count"],
            "doc_count":   d["doc_count"],
            "image_count": len(d["image_data_store"]),
            "created_at":  d["created_at"]
        }
        for pid, d in pdf_store.items()
    ]


def delete_pdf(pdf_id: str) -> bool:
    if pdf_id in pdf_store:
        del pdf_store[pdf_id]
        save_pdf_store()  # ← Persist after delete
        return True
    return False


def get_pdf_info(pdf_id: str) -> Optional[dict]:
    if pdf_id not in pdf_store:
        return None
    d = pdf_store[pdf_id]
    return {
        "pdf_id":      pdf_id,
        "filename":    d["filename"],
        "page_count":  d["page_count"],
        "doc_count":   d["doc_count"],
        "image_count": len(d["image_data_store"]),
        "created_at":  d["created_at"]
    }