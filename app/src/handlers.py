"""Endpoint handlers. Pure business logic — knows nothing about FastAPI or AWS specifics."""
import io
import json
import re
import uuid
from typing import Optional


PROMPT_TEMPLATE = """You are a study assistant. Answer the student's question using ONLY the
context retrieved from their uploaded lecture notes. Cite the source by chunk
number where possible. If the context does not contain the answer, say so
plainly. Do not invent information.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def _extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from PDF or .txt upload."""
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return "(pypdf not installed — install requirements.txt)"
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    # Default: assume UTF-8 text
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def handle_upload(
    user_id: str,
    filename: str,
    data: bytes,
    storage,
    userstore,
    vector_store,
) -> dict:
    """Store the file, extract text, ingest into vector store, record in userstore."""
    doc_id = str(uuid.uuid4())
    key = f"{user_id}/{doc_id}/{filename}"
    location = storage.put(key, data)
    text = _extract_text(filename, data)
    if text.strip():
        vector_store.ingest(doc_id=doc_id, text=text, metadata={"user_id": user_id, "filename": filename})
    userstore.add_doc(
        user_id=user_id,
        doc_id=doc_id,
        metadata={"filename": filename, "size": len(data), "location": location, "chars": len(text)},
    )
    return {
        "doc_id": doc_id,
        "filename": filename,
        "size": len(data),
        "chars_extracted": len(text),
        "location": location,
    }


def handle_query(
    user_id: str,
    question: str,
    ai_client,
    userstore,
    vector_store,
    vector_backend: str,
    bedrock_kb_id: str,
) -> dict:
    """RAG flow: retrieve user's relevant chunks → call AI with context → log + return."""
    if vector_backend == "bedrock_kb":
        # Production path: let Bedrock do retrieve + generate in one call
        result = ai_client.retrieve_and_generate(query=question, kb_id=bedrock_kb_id)
        answer = result["answer"]
        citations = result["citations"]
    else:
        # Local path: do our own retrieve then prompt
        chunks = vector_store.search(question, top_k=5, filter={"user_id": user_id})
        if not chunks:
            answer = "No relevant content found in your uploaded documents. Upload some first."
            citations = []
        else:
            context = "\n\n".join(f"[chunk {i+1}] {c['text']}" for i, c in enumerate(chunks))
            prompt = PROMPT_TEMPLATE.format(context=context, question=question)
            answer = ai_client.invoke(prompt, max_tokens=512)
            citations = [
                {"chunk": i + 1, "doc_id": c["doc_id"], "score": c["score"], "text": c["text"][:200]}
                for i, c in enumerate(chunks)
            ]

    userstore.log_query(user_id=user_id, query=question, answer=answer)
    return {"question": question, "answer": answer, "citations": citations}


def handle_list_docs(user_id: str, userstore) -> dict:
    return {"user_id": user_id, "docs": userstore.list_docs(user_id)}


def handle_delete_doc(user_id: str, doc_id: str, userstore, storage, vector_store=None) -> dict:
    """Remove the doc from userstore + storage; clear local vector chunks if supported."""
    docs = userstore.list_docs(user_id)
    doc = next((d for d in docs if d.get("doc_id") == doc_id), None)
    if not doc:
        raise KeyError(f"Document {doc_id} not found for user {user_id}")
    filename = doc.get("filename", "")
    if filename:
        try:
            storage.delete(f"{user_id}/{doc_id}/{filename}")
        except Exception:
            pass  # storage cleanup is best-effort; userstore is source of truth
    if vector_store and hasattr(vector_store, "delete_doc"):
        vector_store.delete_doc(doc_id=doc_id, filter={"user_id": user_id})
    userstore.delete_doc(user_id, doc_id)
    return {"deleted": True, "doc_id": doc_id, "filename": filename}


def handle_recent_queries(user_id: str, userstore, limit: int = 10) -> dict:
    return {"user_id": user_id, "queries": userstore.recent_queries(user_id, limit=limit)}


# ---------------------------------------------------------------------------
# Summarize + Quiz — student-facing study features (Criterion I customization)
# ---------------------------------------------------------------------------

MAX_DOC_CHARS = 8000  # cap context to control Bedrock token cost

SUMMARIZE_PROMPT = """You are a study assistant. Read the lecture notes below and identify the 5 most testable concepts a student should master for an exam. For each concept, write a 1-sentence explanation suitable for a flashcard.

Return ONLY a valid JSON array of exactly 5 objects, no preamble, no markdown:
[{{"concept": "<short name>", "explanation": "<one sentence>"}}, ...]

LECTURE NOTES:
{text}

JSON:"""


QUIZ_PROMPT = """You are an exam writer. Read the lecture notes below and write {n} multiple-choice questions a teacher could give as a quiz. Each question must have exactly 4 options labelled by index (0..3), exactly one correct answer, and a 1-sentence explanation of why the correct answer is right.

Return ONLY a valid JSON array, no preamble, no markdown:
[{{"question": "<q>", "options": ["A", "B", "C", "D"], "answer_index": 0, "explanation": "<why>"}}, ...]

LECTURE NOTES:
{text}

JSON:"""


def _load_doc_text(user_id: str, doc_id: str, userstore, storage) -> tuple[str, str]:
    """Returns (filename, text). Raises KeyError if doc not found."""
    docs = userstore.list_docs(user_id)
    doc = next((d for d in docs if d.get("doc_id") == doc_id), None)
    if not doc:
        raise KeyError(f"Document {doc_id} not found for user {user_id}")
    filename = doc.get("filename", "unknown")
    key = f"{user_id}/{doc_id}/{filename}"
    raw = storage.get(key)
    return filename, _extract_text(filename, raw)[:MAX_DOC_CHARS]


def _parse_json_array(text: str) -> Optional[list]:
    """Tolerant JSON extractor — handles ```json fences and stray prose around the array."""
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "")
    match = re.search(r"\[\s*[\{\[].*[\}\]]\s*\]", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        return None


def _mock_concepts(text: str) -> list:
    """Fallback for local stub: pick first 5 non-trivial sentences."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 30 < len(s.strip()) < 240]
    out = []
    for i, s in enumerate(sentences[:5]):
        first_clause = s.split(",")[0].strip()[:80]
        out.append({"concept": first_clause or f"Key idea {i+1}", "explanation": s})
    while len(out) < 5:
        out.append({"concept": f"Topic {len(out)+1}", "explanation": "(local stub — set AI_BACKEND=bedrock for real concepts)"})
    return out


def _mock_quiz(text: str, n: int) -> list:
    """Fallback for local stub: synthesize trivially-wrong distractors for demo purposes."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 30 < len(s.strip()) < 240]
    out = []
    for i, s in enumerate(sentences[:n]):
        keyword = re.findall(r"\b[A-Z][a-z]{3,}\b", s)
        correct = keyword[0] if keyword else s.split()[0]
        out.append({
            "question": f"Which best describes: '{s[:120]}…'?",
            "options": [correct, "Random distractor A", "Random distractor B", "None of the above"],
            "answer_index": 0,
            "explanation": "(local stub — questions are placeholder. Set AI_BACKEND=bedrock for real quiz.)",
        })
    while len(out) < n:
        out.append({
            "question": f"Placeholder question {len(out)+1}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer_index": 0,
            "explanation": "(local stub)",
        })
    return out


def handle_summarize(user_id: str, doc_id: str, ai_client, userstore, storage) -> dict:
    filename, text = _load_doc_text(user_id, doc_id, userstore, storage)
    prompt = SUMMARIZE_PROMPT.format(text=text)
    raw = ai_client.invoke(prompt, max_tokens=800, temperature=0.3)
    concepts = _parse_json_array(raw) or _mock_concepts(text)
    return {"doc_id": doc_id, "filename": filename, "concepts": concepts[:5]}


def handle_quiz(user_id: str, doc_id: str, ai_client, userstore, storage, n: int = 10) -> dict:
    n = max(1, min(n, 20))
    filename, text = _load_doc_text(user_id, doc_id, userstore, storage)
    prompt = QUIZ_PROMPT.format(n=n, text=text)
    raw = ai_client.invoke(prompt, max_tokens=2000, temperature=0.4)
    questions = _parse_json_array(raw) or _mock_quiz(text, n)
    # Normalize: clamp answer_index, trim to 4 options
    norm = []
    for q in questions[:n]:
        if not isinstance(q, dict):
            continue
        opts = (q.get("options") or [])[:4]
        while len(opts) < 4:
            opts.append("—")
        idx = q.get("answer_index", 0)
        try:
            idx = max(0, min(int(idx), 3))
        except (TypeError, ValueError):
            idx = 0
        norm.append({
            "question": str(q.get("question", "")),
            "options": [str(o) for o in opts],
            "answer_index": idx,
            "explanation": str(q.get("explanation", "")),
        })
    return {"doc_id": doc_id, "filename": filename, "questions": norm}
