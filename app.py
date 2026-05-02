"""
app.py
======
Thin Flask application entry-point.
All business logic is delegated to service modules in ``modules/``.
"""

import os
import json
import time
import logging
import threading
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    abort,
)
from werkzeug.utils import secure_filename

from config import (
    FlaskConfig,
    UPLOAD_DIR,
    OUTPUT_DIR,
    EXPORT_DIR,
    ALLOWED_EXTENSIONS,
    allowed_file,
)
from modules.utils import setup_logger, generate_uuid, get_file_extension, safe_filename

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = FlaskConfig.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = FlaskConfig.MAX_CONTENT_LENGTH

logger = setup_logger("app")

# In-memory processing status tracker  {doc_id: {stage, progress, error}}
_processing_status: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_pipeline(doc_id: str, filepath: str, filename: str, file_type: str) -> None:
    """
    Run the full NLP → question-generation pipeline in a background thread.
    Updates ``_processing_status`` as it progresses.
    """
    # Late imports to keep app.py thin and avoid circular imports
    from modules.extractor import extract_text
    from modules.preprocess import preprocess_text
    from modules.keyword_extract import extract_keywords, extract_concepts
    from modules.sentence_ranker import rank_sentences
    from modules.hf_generator import HuggingFaceGenerator
    from modules.blank_generator import generate_fill_blanks
    from modules.distractor_engine import generate_distractors
    from modules.mcq_generator import generate_mcqs
    from modules.difficulty_classifier import classify_difficulty
    from modules.taxonomy_classifier import classify_bloom
    from modules.semantic_filter import filter_duplicates
    from modules.supabase_client import SupabaseManager
    from modules.analytics import compute_analytics

    status = _processing_status[doc_id]
    start_time = time.time()

    try:
        # --- Stage 1: Extract ---
        status.update(stage="Extracting text", progress=5)
        raw_text = extract_text(filepath)
        if not raw_text or len(raw_text.strip()) < 50:
            raise ValueError("Extracted text is too short or empty.")
        logger.info("Doc %s: extracted %d chars", doc_id, len(raw_text))

        # --- Stage 2: Preprocess ---
        status.update(stage="Analyzing content", progress=15)
        processed = preprocess_text(raw_text)
        sentences = processed["sentences"]
        logger.info("Doc %s: %d sentences extracted", doc_id, len(sentences))

        # --- Stage 3: Keywords ---
        status.update(stage="Extracting keywords", progress=25)
        keywords = extract_keywords(processed)
        concepts = extract_concepts(processed)
        logger.info("Doc %s: %d keywords, %d concepts", doc_id, len(keywords), len(concepts))

        # --- Stage 4: Sentence ranking ---
        status.update(stage="Ranking sentences", progress=35)
        ranked = rank_sentences(sentences, keywords)
        logger.info("Doc %s: ranked %d sentences", doc_id, len(ranked))

        # --- Stage 5: Question generation ---
        status.update(stage="Generating questions", progress=45)
        all_questions: list[dict] = []

        # 5a. Hugging Face WH / short-answer questions
        hf_gen = HuggingFaceGenerator()
        hf_questions = hf_gen.generate_from_ranked_sentences(ranked, concepts)
        all_questions.extend(hf_questions)
        logger.info("Doc %s: %d HF questions", doc_id, len(hf_questions))

        # 5b. Fill-in-the-blank
        status.update(stage="Creating fill-in-the-blanks", progress=55)
        keyword_strings = [kw[0] if isinstance(kw, tuple) else kw for kw in keywords]
        blanks = generate_fill_blanks(ranked, keyword_strings)
        all_questions.extend(blanks)
        logger.info("Doc %s: %d blank questions", doc_id, len(blanks))

        # 5c. MCQs with distractors
        status.update(stage="Building MCQs", progress=65)
        mcqs = generate_mcqs(all_questions, keyword_strings, concepts)
        all_questions.extend(mcqs)
        logger.info("Doc %s: %d MCQs", doc_id, len(mcqs))

        # --- Stage 6: Classify ---
        status.update(stage="Classifying difficulty", progress=75)
        for q in all_questions:
            q["difficulty"] = classify_difficulty(
                q.get("question", ""),
                q.get("answer", ""),
                q.get("source_sentence", ""),
            )
            q["bloom_taxonomy"] = classify_bloom(
                q.get("question", ""),
                q.get("answer", ""),
            )

        # --- Stage 7: Semantic deduplication ---
        status.update(stage="Removing duplicates", progress=85)
        all_questions = filter_duplicates(all_questions)
        logger.info("Doc %s: %d questions after dedup", doc_id, len(all_questions))

        # --- Stage 8: Save to Supabase ---
        status.update(stage="Saving results", progress=90)
        db = SupabaseManager()

        # Save document record
        doc_record = db.save_document(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=os.path.getsize(filepath),
            raw_text=raw_text,
            processed_text=json.dumps(processed.get("lemmas", [])[:500]),
        )

        # Upload file to Supabase Storage
        try:
            db.upload_file(filepath, f"{doc_id}/{filename}")
        except Exception as storage_err:
            logger.warning("Storage upload failed: %s", storage_err)

        # Save questions
        db.save_questions(doc_id, all_questions)

        # Compute and save analytics
        elapsed = time.time() - start_time
        compute_analytics(doc_id, all_questions, elapsed)

        # Update document status
        db.update_document_status(doc_id, "completed")

        status.update(stage="Complete", progress=100, error=None)
        logger.info("Doc %s: pipeline completed in %.1fs — %d questions",
                     doc_id, elapsed, len(all_questions))

    except Exception as exc:
        logger.exception("Pipeline failed for doc %s", doc_id)
        status.update(stage="Failed", progress=0, error=str(exc))
        try:
            from modules.supabase_client import SupabaseManager
            db = SupabaseManager()
            db.update_document_status(doc_id, "failed", str(exc))
        except Exception:
            pass


# ============================= ROUTES ======================================

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/upload", methods=["GET"])
def upload_page():
    """File upload page."""
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload, save to disk, and start pipeline."""
    if "file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("upload_page"))

    file = request.files["file"]
    if file.filename == "" or file.filename is None:
        flash("No file selected.", "danger")
        return redirect(url_for("upload_page"))

    if not allowed_file(file.filename):
        flash("Unsupported file type. Please upload PDF, DOCX, or TXT.", "danger")
        return redirect(url_for("upload_page"))

    # Save file
    doc_id = generate_uuid()
    original_name = secure_filename(file.filename)
    ext = get_file_extension(original_name)
    saved_name = f"{doc_id}.{ext}"
    save_path = UPLOAD_DIR / saved_name
    file.save(str(save_path))

    logger.info("Uploaded %s as %s (%s)", original_name, saved_name, ext)

    # Init status and start background pipeline
    _processing_status[doc_id] = {"stage": "Queued", "progress": 0, "error": None}

    thread = threading.Thread(
        target=_run_pipeline,
        args=(doc_id, str(save_path), original_name, ext),
        daemon=True,
    )
    thread.start()

    return redirect(url_for("processing_page", doc_id=doc_id))


@app.route("/process/<doc_id>")
def processing_page(doc_id: str):
    """Processing status page with live progress updates."""
    if doc_id not in _processing_status:
        flash("Document not found.", "warning")
        return redirect(url_for("upload_page"))
    return render_template("processing.html", doc_id=doc_id)


@app.route("/results/<doc_id>")
def results_page(doc_id: str):
    """Question bank results page."""
    return render_template("results.html", doc_id=doc_id)


@app.route("/dashboard")
def dashboard():
    """Analytics dashboard page."""
    return render_template("dashboard.html")


@app.route("/export/<doc_id>")
def export_page(doc_id: str):
    """Export page for a document."""
    return render_template("export.html", doc_id=doc_id)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/status/<doc_id>")
def api_status(doc_id: str):
    """Return current processing status for a document."""
    status = _processing_status.get(doc_id)
    if status is None:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(status)


@app.route("/api/questions/<doc_id>")
def api_questions(doc_id: str):
    """Return generated questions with optional filters."""
    from modules.supabase_client import SupabaseManager
    db = SupabaseManager()

    filters = {
        "question_type": request.args.get("type"),
        "difficulty": request.args.get("difficulty"),
        "bloom_taxonomy": request.args.get("bloom"),
        "search": request.args.get("search"),
    }
    # Remove None filters
    filters = {k: v for k, v in filters.items() if v}

    try:
        questions = db.get_questions(doc_id, filters)
        return jsonify({"questions": questions, "total": len(questions)})
    except Exception as exc:
        logger.error("Failed to fetch questions: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/questions/<question_id>", methods=["PUT"])
def api_update_question(question_id: str):
    """Update an edited question."""
    from modules.supabase_client import SupabaseManager
    db = SupabaseManager()

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        updated = db.update_question(question_id, data)
        return jsonify({"success": True, "question": updated})
    except Exception as exc:
        logger.error("Failed to update question: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/analytics")
def api_analytics():
    """Return aggregated analytics for the dashboard."""
    from modules.analytics import get_dashboard_data
    try:
        data = get_dashboard_data()
        return jsonify(data)
    except Exception as exc:
        logger.error("Failed to fetch analytics: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/analytics/<doc_id>")
def api_document_analytics(doc_id: str):
    """Return analytics for a specific document."""
    from modules.analytics import get_document_analytics
    try:
        data = get_document_analytics(doc_id)
        return jsonify(data)
    except Exception as exc:
        logger.error("Failed to fetch document analytics: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/export/<doc_id>", methods=["POST"])
def api_export(doc_id: str):
    """Generate an export file (PDF or CSV)."""
    from modules.exporter import export_questions
    from modules.supabase_client import SupabaseManager

    data = request.get_json() or {}
    export_type = data.get("format", "pdf").lower()

    if export_type not in ("pdf", "csv"):
        return jsonify({"error": "Invalid format. Use 'pdf' or 'csv'."}), 400

    try:
        db = SupabaseManager()
        questions = db.get_questions(doc_id)
        doc_info = db.get_document(doc_id)

        filepath = export_questions(
            questions=questions,
            document_info=doc_info,
            export_type=export_type,
            doc_id=doc_id,
        )

        # Save export record
        db.save_export(doc_id, export_type, str(filepath))

        return jsonify({
            "success": True,
            "download_url": url_for("api_download", filename=Path(filepath).name),
        })
    except Exception as exc:
        logger.error("Export failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/download/<filename>")
def api_download(filename: str):
    """Download an exported file."""
    filepath = EXPORT_DIR / safe_filename(filename)
    if not filepath.exists():
        abort(404)
    return send_file(str(filepath), as_attachment=True)


@app.route("/api/documents")
def api_documents():
    """List all processed documents."""
    from modules.supabase_client import SupabaseManager
    try:
        db = SupabaseManager()
        docs = db.list_documents()
        return jsonify({"documents": docs})
    except Exception as exc:
        logger.error("Failed to list documents: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("base.html", error="Page not found"), 404


@app.errorhandler(413)
def too_large(e):
    flash("File too large. Maximum size is 16 MB.", "danger")
    return redirect(url_for("upload_page"))


@app.errorhandler(500)
def server_error(e):
    logger.exception("Internal server error")
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("base.html", error="Something went wrong"), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host=FlaskConfig.HOST,
        port=FlaskConfig.PORT,
        debug=FlaskConfig.DEBUG,
    )
