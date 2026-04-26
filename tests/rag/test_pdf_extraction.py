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
from rag_system.pipeline.data_pipeline.pdf_extractor import PDFExtractor
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
    
    text = """Abstract

This is a test abstract that should be extracted. It contains multiple sentences.
The abstract should be long enough to pass the length check, which requires it to be over 50 characters in length. This is additional padding text.

1. Introduction
"""
    
    abstract = extractor._extract_abstract(text)
    assert abstract is not None
    assert len(abstract) > 50


def test_extract_sections():
    """Test section extraction."""
    extractor = PDFExtractor()
    
    text = """1. Introduction
This is the introduction content. It needs to be more than 100 characters long to not be skipped. This is some extra padding text to make sure the introduction content is long enough to pass the 100 character threshold check in the PDFExtractor.

2. Related Work
This is related work content. It also needs to be more than 100 characters long. Adding some filler text here to ensure that it passes the length check. The length check requires section content to be greater than 100 characters.

3. Methodology
This is methodology content. This final section must also be over 100 characters. So I will keep writing sentences until the length is sufficient for the extractor to pick it up and return it in the list of sections.
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

