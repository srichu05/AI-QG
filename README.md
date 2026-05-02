# AI-QG: AI Question Generator for Educational Content

An intelligent, production-style full-stack web application that accepts educational documents (PDF / DOCX / TXT), processes them using NLP pipelines, and automatically generates a structured question bank.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey?logo=flask)
![spaCy](https://img.shields.io/badge/spaCy-3.8-green?logo=spacy)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **4 Question Types**: Fill-in-the-blank, WH, Short-answer, MCQs
- **Intelligent Distractors**: WordNet + semantic similarity + concept neighbors
- **Difficulty Labeling**: Easy / Medium / Hard (multi-factor scoring)
- **Bloom's Taxonomy**: Remember / Understand / Apply classification
- **Semantic Deduplication**: Removes near-duplicate questions using sentence-transformers
- **Real-time Processing**: Background pipeline with live progress updates
- **Cloud Storage**: Supabase PostgreSQL + Storage (with local JSON fallback)
- **Export**: Professional PDF question bank + CSV
- **Analytics Dashboard**: Chart.js visualizations
- **Inline Editing**: Edit generated questions directly in the browser

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| NLP | spaCy (en_core_web_md), NLTK, scikit-learn |
| Semantic | sentence-transformers (all-MiniLM-L6-v2) |
| LLM API | Hugging Face Inference API (T5 models) |
| Database | Supabase PostgreSQL (or local JSON fallback) |
| Export | ReportLab (PDF), pandas (CSV) |

---

## Quick Start

### 1. Clone & Setup

```bash
cd AI-QG
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Download NLP Models

```bash
python -m spacy download en_core_web_md
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('omw-1.4')"
```

### 3. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` with your credentials:
- `SUPABASE_URL` and `SUPABASE_KEY` (optional — app falls back to local JSON)
- `HF_API_TOKEN` (optional — app falls back to rule-based question generation)

### 4. Run

```bash
python app.py
```

Visit **http://localhost:5000**

---

## Database Setup (Optional)

If using Supabase, run `database/schema.sql` in your Supabase SQL Editor.

Create a storage bucket named `documents` in Supabase Storage.

---

## Project Structure

```
AI-QG/
├── app.py                    # Flask routes (thin)
├── config.py                 # Configuration
├── requirements.txt
├── .env.example
├── database/schema.sql       # Supabase schema
├── modules/                  # Service modules
│   ├── extractor.py          # PDF/DOCX/TXT extraction
│   ├── preprocess.py         # NLP preprocessing
│   ├── keyword_extract.py    # TF-IDF keyword extraction
│   ├── sentence_ranker.py    # Sentence importance ranking
│   ├── hf_generator.py       # HF API question generation
│   ├── blank_generator.py    # Fill-in-the-blank
│   ├── mcq_generator.py      # MCQ assembly
│   ├── distractor_engine.py  # Distractor generation
│   ├── difficulty_classifier.py
│   ├── taxonomy_classifier.py
│   ├── semantic_filter.py    # Deduplication
│   ├── supabase_client.py    # DB + Storage
│   ├── exporter.py           # PDF/CSV export
│   ├── analytics.py          # Dashboard analytics
│   └── utils.py              # Shared utilities
├── templates/                # Jinja2 templates
├── static/                   # CSS, JS, exports
└── tests/                    # pytest suite
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Landing page |
| GET/POST | `/upload` | Upload page + handler |
| GET | `/process/<doc_id>` | Processing status page |
| GET | `/results/<doc_id>` | Question bank results |
| GET | `/dashboard` | Analytics dashboard |
| GET | `/export/<doc_id>` | Export page |
| GET | `/api/status/<doc_id>` | Processing status JSON |
| GET | `/api/questions/<doc_id>` | Questions with filters |
| PUT | `/api/questions/<q_id>` | Update a question |
| GET | `/api/analytics` | Dashboard data |
| POST | `/api/export/<doc_id>` | Generate export |
| GET | `/api/download/<filename>` | Download export file |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT
