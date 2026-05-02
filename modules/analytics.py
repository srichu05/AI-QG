"""
analytics.py
============
Compute and retrieve analytics for the dashboard.
"""

import logging
import json
from typing import Any
from collections import Counter

from modules.utils import timed

logger = logging.getLogger(__name__)


@timed
def compute_analytics(
    doc_id: str,
    questions: list[dict[str, Any]],
    processing_time: float,
) -> dict:
    """
    Compute analytics for a processed document and save to Supabase.

    Parameters
    ----------
    doc_id : str
        Document ID.
    questions : list[dict]
        All generated questions.
    processing_time : float
        Total pipeline processing time in seconds.

    Returns
    -------
    dict
        Analytics summary.
    """
    from modules.supabase_client import SupabaseManager

    type_dist = Counter(q.get("question_type", "unknown") for q in questions)
    diff_dist = Counter(q.get("difficulty", "medium") for q in questions)
    tax_dist = Counter(q.get("bloom_taxonomy", "remember") for q in questions)

    analytics_data = {
        "total_questions": len(questions),
        "type_distribution": json.dumps(dict(type_dist)),
        "difficulty_distribution": json.dumps(dict(diff_dist)),
        "taxonomy_distribution": json.dumps(dict(tax_dist)),
        "processing_time_seconds": round(processing_time, 2),
    }

    db = SupabaseManager()
    db.save_analytics(doc_id, analytics_data)

    logger.info(
        "Analytics for doc %s: %d questions, types=%s, time=%.1fs",
        doc_id, len(questions), dict(type_dist), processing_time,
    )
    return analytics_data


def get_dashboard_data() -> dict[str, Any]:
    """
    Aggregate analytics across all documents for the dashboard.

    Returns
    -------
    dict
        Dashboard data with totals, distributions, and recent documents.
    """
    from modules.supabase_client import SupabaseManager

    db = SupabaseManager()
    all_analytics = db.get_all_analytics()
    all_documents = db.list_documents()

    total_questions = 0
    total_processing_time = 0.0
    agg_types: Counter = Counter()
    agg_difficulty: Counter = Counter()
    agg_taxonomy: Counter = Counter()

    for entry in all_analytics:
        total_questions += entry.get("total_questions", 0)
        total_processing_time += entry.get("processing_time_seconds", 0)

        for field, counter in [
            ("type_distribution", agg_types),
            ("difficulty_distribution", agg_difficulty),
            ("taxonomy_distribution", agg_taxonomy),
        ]:
            raw = entry.get(field, "{}")
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    data = {}
            else:
                data = raw or {}
            counter.update(data)

    return {
        "total_uploads": len(all_documents),
        "total_questions": total_questions,
        "avg_processing_time": round(
            total_processing_time / max(len(all_analytics), 1), 1
        ),
        "type_distribution": dict(agg_types),
        "difficulty_distribution": dict(agg_difficulty),
        "taxonomy_distribution": dict(agg_taxonomy),
        "recent_documents": all_documents[:10],
    }


def get_document_analytics(doc_id: str) -> dict[str, Any]:
    """Get analytics for a specific document."""
    from modules.supabase_client import SupabaseManager

    db = SupabaseManager()
    all_analytics = db.get_all_analytics()

    for entry in all_analytics:
        if entry.get("document_id") == doc_id:
            # Parse JSON fields
            for field in ("type_distribution", "difficulty_distribution", "taxonomy_distribution"):
                raw = entry.get(field, "{}")
                if isinstance(raw, str):
                    try:
                        entry[field] = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        entry[field] = {}
            return entry

    return {
        "total_questions": 0,
        "type_distribution": {},
        "difficulty_distribution": {},
        "taxonomy_distribution": {},
        "processing_time_seconds": 0,
    }
