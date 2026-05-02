"""
supabase_client.py
==================
Supabase integration layer for database operations and file storage.
Provides a singleton SupabaseManager for all DB and storage interactions.
"""

import logging
import json
from typing import Any
from pathlib import Path

from config import SupabaseConfig
from modules.utils import timed, generate_uuid

logger = logging.getLogger(__name__)

# Singleton instance
_instance = None


class SupabaseManager:
    """
    Singleton manager for all Supabase operations.

    Handles documents, questions, analytics, exports, and file storage.
    Falls back to local JSON storage if Supabase is not configured.
    """

    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client = None
        self._local_mode = False

        if SupabaseConfig.validate():
            try:
                from supabase import create_client
                self._client = create_client(SupabaseConfig.URL, SupabaseConfig.KEY)
                logger.info("Supabase client initialized")
            except Exception as exc:
                logger.warning("Supabase init failed (%s) — using local storage", exc)
                self._local_mode = True
        else:
            logger.warning("Supabase not configured — using local JSON storage")
            self._local_mode = True

        # Local storage fallback
        if self._local_mode:
            from config import OUTPUT_DIR
            self._local_dir = OUTPUT_DIR / "local_db"
            self._local_dir.mkdir(parents=True, exist_ok=True)
            self._local_data = self._load_local()

    # ------------------------------------------------------------------
    # Local JSON fallback
    # ------------------------------------------------------------------

    def _load_local(self) -> dict:
        path = self._local_dir / "data.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"documents": [], "questions": [], "analytics": [], "exports": []}

    def _save_local(self):
        path = self._local_dir / "data.json"
        path.write_text(json.dumps(self._local_data, default=str, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def save_document(self, doc_id: str, filename: str, file_type: str,
                      file_size: int, raw_text: str, processed_text: str = "") -> dict:
        record = {
            "id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "raw_text": raw_text[:50000],  # Limit text size
            "processed_text": processed_text[:10000],
            "status": "processing",
        }
        if self._local_mode:
            self._local_data["documents"].append(record)
            self._save_local()
            return record

        try:
            result = self._client.table("documents").insert(record).execute()
            return result.data[0] if result.data else record
        except Exception as exc:
            logger.error("Failed to save document: %s", exc)
            return record

    def get_document(self, doc_id: str) -> dict | None:
        if self._local_mode:
            for doc in self._local_data["documents"]:
                if doc["id"] == doc_id:
                    return doc
            return None
        try:
            result = self._client.table("documents").select("*").eq("id", doc_id).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("Failed to get document: %s", exc)
            return None

    def list_documents(self) -> list[dict]:
        if self._local_mode:
            return [
                {k: v for k, v in d.items() if k not in ("raw_text", "processed_text")}
                for d in self._local_data["documents"]
            ]
        try:
            result = (self._client.table("documents")
                      .select("id, filename, file_type, file_size, status, upload_timestamp, created_at")
                      .order("created_at", desc=True)
                      .execute())
            return result.data or []
        except Exception as exc:
            logger.error("Failed to list documents: %s", exc)
            return []

    def update_document_status(self, doc_id: str, status: str, error_msg: str = None):
        if self._local_mode:
            for doc in self._local_data["documents"]:
                if doc["id"] == doc_id:
                    doc["status"] = status
                    if error_msg:
                        doc["error_message"] = error_msg
            self._save_local()
            return
        try:
            update = {"status": status}
            if error_msg:
                update["error_message"] = error_msg
            self._client.table("documents").update(update).eq("id", doc_id).execute()
        except Exception as exc:
            logger.error("Failed to update document status: %s", exc)

    # ------------------------------------------------------------------
    # Question operations
    # ------------------------------------------------------------------

    def save_questions(self, doc_id: str, questions: list[dict]):
        records = []
        for q in questions:
            record = {
                "id": generate_uuid(),
                "document_id": doc_id,
                "question_text": q.get("question", ""),
                "answer": q.get("answer", ""),
                "question_type": q.get("question_type", "short_answer"),
                "difficulty": q.get("difficulty", "medium"),
                "bloom_taxonomy": q.get("bloom_taxonomy", "remember"),
                "source_sentence": q.get("source_sentence", ""),
                "distractors": json.dumps(q.get("distractors", [])),
                "options": json.dumps(q.get("options", [])),
                "correct_index": q.get("correct_index"),
                "metadata": json.dumps(q.get("metadata", {})),
                "is_edited": False,
            }
            records.append(record)

        if self._local_mode:
            self._local_data["questions"].extend(records)
            self._save_local()
            return records

        try:
            # Batch insert in chunks of 50
            for i in range(0, len(records), 50):
                chunk = records[i:i + 50]
                self._client.table("generated_questions").insert(chunk).execute()
            logger.info("Saved %d questions for doc %s", len(records), doc_id)
        except Exception as exc:
            logger.error("Failed to save questions: %s", exc)
        return records

    def get_questions(self, doc_id: str, filters: dict | None = None) -> list[dict]:
        if self._local_mode:
            results = [q for q in self._local_data["questions"] if q["document_id"] == doc_id]
            if filters:
                if filters.get("question_type"):
                    results = [q for q in results if q["question_type"] == filters["question_type"]]
                if filters.get("difficulty"):
                    results = [q for q in results if q["difficulty"] == filters["difficulty"]]
                if filters.get("bloom_taxonomy"):
                    results = [q for q in results if q["bloom_taxonomy"] == filters["bloom_taxonomy"]]
                if filters.get("search"):
                    search = filters["search"].lower()
                    results = [q for q in results if search in q["question_text"].lower()]
            # Parse JSON fields
            for q in results:
                for field in ("distractors", "options", "metadata"):
                    if isinstance(q.get(field), str):
                        try:
                            q[field] = json.loads(q[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
            return results

        try:
            query = self._client.table("generated_questions").select("*").eq("document_id", doc_id)
            if filters:
                if filters.get("question_type"):
                    query = query.eq("question_type", filters["question_type"])
                if filters.get("difficulty"):
                    query = query.eq("difficulty", filters["difficulty"])
                if filters.get("bloom_taxonomy"):
                    query = query.eq("bloom_taxonomy", filters["bloom_taxonomy"])
            result = query.order("created_at").execute()
            questions = result.data or []
            if filters and filters.get("search"):
                search = filters["search"].lower()
                questions = [q for q in questions if search in q.get("question_text", "").lower()]
            return questions
        except Exception as exc:
            logger.error("Failed to get questions: %s", exc)
            return []

    def update_question(self, question_id: str, data: dict) -> dict:
        update = {}
        if "question_text" in data:
            update["question_text"] = data["question_text"]
            update["is_edited"] = True
            update["edited_text"] = data["question_text"]
        if "answer" in data:
            update["answer"] = data["answer"]
        if "difficulty" in data:
            update["difficulty"] = data["difficulty"]
        if "bloom_taxonomy" in data:
            update["bloom_taxonomy"] = data["bloom_taxonomy"]

        if self._local_mode:
            for q in self._local_data["questions"]:
                if q["id"] == question_id:
                    q.update(update)
                    self._save_local()
                    return q
            return {}

        try:
            result = (self._client.table("generated_questions")
                      .update(update).eq("id", question_id).execute())
            return result.data[0] if result.data else {}
        except Exception as exc:
            logger.error("Failed to update question: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Analytics operations
    # ------------------------------------------------------------------

    def save_analytics(self, doc_id: str, analytics_data: dict):
        record = {
            "id": generate_uuid(),
            "document_id": doc_id,
            **analytics_data,
        }
        if self._local_mode:
            self._local_data["analytics"].append(record)
            self._save_local()
            return record
        try:
            result = self._client.table("analytics").insert(record).execute()
            return result.data[0] if result.data else record
        except Exception as exc:
            logger.error("Failed to save analytics: %s", exc)
            return record

    def get_all_analytics(self) -> list[dict]:
        if self._local_mode:
            return self._local_data.get("analytics", [])
        try:
            result = self._client.table("analytics").select("*").order("created_at", desc=True).execute()
            return result.data or []
        except Exception as exc:
            logger.error("Failed to get analytics: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Export operations
    # ------------------------------------------------------------------

    def save_export(self, doc_id: str, export_type: str, file_path: str):
        record = {
            "id": generate_uuid(),
            "document_id": doc_id,
            "export_type": export_type,
            "file_path": file_path,
        }
        if self._local_mode:
            self._local_data["exports"].append(record)
            self._save_local()
            return record
        try:
            result = self._client.table("exports").insert(record).execute()
            return result.data[0] if result.data else record
        except Exception as exc:
            logger.error("Failed to save export: %s", exc)
            return record

    # ------------------------------------------------------------------
    # Storage operations
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str, storage_path: str):
        if self._local_mode:
            logger.info("Local mode — skipping storage upload for %s", storage_path)
            return
        try:
            with open(local_path, "rb") as f:
                self._client.storage.from_(SupabaseConfig.STORAGE_BUCKET).upload(
                    storage_path, f.read()
                )
            logger.info("Uploaded %s to Supabase Storage", storage_path)
        except Exception as exc:
            logger.warning("Storage upload failed: %s", exc)
