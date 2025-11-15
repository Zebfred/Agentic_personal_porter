"""
Unit tests for PDF extraction module.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from pathlib import Path
from data_pipeline.pdf_extractor import PDFExtractor
import tempfile
import os


def test_pdf_extractor_initialization():
    """Test PDFExtractor initialization."""
    extractor = PDFExtractor()
    assert extractor.output_dir.exists()


def test_extract_text_nonexistent_file():
    """Test extraction with non-existent file raises error."""
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract_text("nonexistent.pdf")


def test_extract_title_from_metadata():
    """Test title extraction from PDF metadata."""
    extractor = PDFExtractor()
    
    # Mock metadata
    metadata = {'title': 'Test Paper Title'}
    text = "Some content here."
    
    title = extractor._extract_title(text, metadata)
    assert title == 'Test Paper Title'


def test_extract_abstract_pattern():
    """Test abstract extraction using regex patterns."""
    extractor = PDFExtractor()
    
    text = """
    Abstract
    
    This is a test abstract that should be extracted. It contains multiple sentences.
    The abstract should be long enough to pass the length check.
    """
    
    abstract = extractor._extract_abstract(text)
    assert abstract is not None
    assert len(abstract) > 50


def test_extract_sections():
    """Test section extraction."""
    extractor = PDFExtractor()
    
    text = """
    1. Introduction
    This is the introduction content.
    
    2. Related Work
    This is related work content.
    
    3. Methodology
    This is methodology content.
    """
    
    sections = extractor._extract_sections(text)
    assert len(sections) > 0
    assert any('Introduction' in s['header'] for s in sections)


def test_extract_batch():
    """Test batch extraction."""
    extractor = PDFExtractor()
    
    # Test with empty list
    results = extractor.extract_batch([])
    assert results == []
    
    # Test with non-existent files (should handle gracefully)
    results = extractor.extract_batch(["nonexistent1.pdf", "nonexistent2.pdf"])
    assert len(results) == 2
    assert all('error' in r for r in results)

