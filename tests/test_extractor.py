"""
test_extractor.py — Tests for document text extraction.
"""
import os
import tempfile
import pytest


def _create_temp_file(content: str, suffix: str) -> str:
    """Create a temporary file with given content and suffix."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


class TestTxtExtraction:
    def test_extract_basic_txt(self):
        from modules.extractor import extract_text
        text = "Photosynthesis is the process by which plants convert sunlight into energy."
        path = _create_temp_file(text, ".txt")
        try:
            result = extract_text(path)
            assert "Photosynthesis" in result
            assert "plants" in result
        finally:
            os.unlink(path)

    def test_extract_empty_txt(self):
        from modules.extractor import extract_text
        path = _create_temp_file("", ".txt")
        try:
            result = extract_text(path)
            assert result == ""
        finally:
            os.unlink(path)

    def test_extract_whitespace_normalization(self):
        from modules.extractor import extract_text
        text = "Hello   world.\n\n\n\n\nMultiple   blanks."
        path = _create_temp_file(text, ".txt")
        try:
            result = extract_text(path)
            assert "   " not in result  # Multiple spaces collapsed
        finally:
            os.unlink(path)


class TestUnsupportedFile:
    def test_unsupported_extension(self):
        from modules.extractor import extract_text
        path = _create_temp_file("data", ".xyz")
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                extract_text(path)
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        from modules.extractor import extract_text
        with pytest.raises(FileNotFoundError):
            extract_text("/nonexistent/file.pdf")
