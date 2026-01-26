"""
PDF extraction module using PyMuPDF (fitz) to extract text from PDFs.

This module handles:
- Extracting raw text from PDFs
- Handling multi-column layouts
- Preserving document structure
- Extracting metadata (title, abstract, sections)
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional
import re


class PDFExtractor:
    """Extractor for PDF text and metadata."""
    
    def __init__(self, output_dir: str = "data/extracted_text"):
        """
        Initialize the PDF extractor.
        
        Args:
            output_dir: Directory to store extracted text files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text and metadata from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
                - text: Full extracted text
                - title: Document title (if found)
                - abstract: Abstract section (if found)
                - sections: List of section headers and content
                - metadata: PDF metadata
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        
        # Extract metadata
        metadata = doc.metadata
        
        # Get number of pages before closing
        num_pages = len(doc)
        
        # Extract full text
        full_text = ""
        pages_text = []
        
        for page_num in range(num_pages):
            page = doc[page_num]
            page_text = page.get_text()
            pages_text.append(page_text)
            full_text += page_text + "\n\n"
        
        doc.close()
        
        # Try to extract title (usually in first few lines or metadata)
        title = self._extract_title(full_text, metadata)
        
        # Try to extract abstract
        abstract = self._extract_abstract(full_text)
        
        # Extract sections
        sections = self._extract_sections(full_text)
        
        result = {
            'text': full_text,
            'title': title,
            'abstract': abstract,
            'sections': sections,
            'metadata': metadata,
            'num_pages': num_pages,
            'pages': pages_text
        }
        
        # Save extracted text to file
        output_file = self.output_dir / f"{pdf_path.stem}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        return result
    
    def _extract_title(self, text: str, metadata: Dict) -> Optional[str]:
        """
        Extract title from text or metadata.
        
        Args:
            text: Full text of the document
            metadata: PDF metadata dictionary
            
        Returns:
            Title string or None
        """
        # First, try metadata
        if metadata.get('title') and metadata['title'].strip():
            return metadata['title'].strip()
        
        # Try to find title in first few lines
        lines = text.split('\n')[:20]  # Check first 20 lines
        for line in lines:
            line = line.strip()
            # Title is usually short, capitalized, and not empty
            if line and len(line) < 200 and len(line.split()) > 3:
                # Check if it looks like a title (has capital letters, not all caps)
                if line[0].isupper() and not line.isupper():
                    return line
        
        return None
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """
        Extract abstract section from text.
        
        Args:
            text: Full text of the document
            
        Returns:
            Abstract string or None
        """
        # Look for abstract section
        abstract_patterns = [
            r'(?i)abstract\s*\n\s*(.+?)(?=\n\s*(?:1\.|introduction|keywords|index terms))',
            r'(?i)abstract\s*\n\s*(.+?)(?=\n\s*\n)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up abstract
                abstract = re.sub(r'\s+', ' ', abstract)
                if len(abstract) > 50:  # Reasonable abstract length
                    return abstract
        
        return None
    
    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Extract section headers and their content.
        
        Args:
            text: Full text of the document
            
        Returns:
            List of dictionaries with 'header' and 'content' keys
        """
        sections = []
        
        # Pattern to match section headers (numbered or unnumbered)
        # Examples: "1. Introduction", "2. Related Work", "Introduction", etc.
        section_pattern = r'(?m)^(?:\d+\.?\s*)?([A-Z][A-Za-z\s]+?)(?:\n|$)'
        
        matches = list(re.finditer(section_pattern, text))
        
        for i, match in enumerate(matches):
            header = match.group(1).strip()
            start_pos = match.end()
            
            # Find end position (start of next section or end of text)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            content = text[start_pos:end_pos].strip()
            
            # Skip very short sections (likely false positives)
            if len(content) > 100:
                sections.append({
                    'header': header,
                    'content': content
                })
        
        return sections
    
    def extract_batch(self, pdf_paths: List[str]) -> List[Dict]:
        """
        Extract text from multiple PDFs.
        
        Args:
            pdf_paths: List of paths to PDF files
            
        Returns:
            List of extraction result dictionaries
        """
        results = []
        for pdf_path in pdf_paths:
            try:
                result = self.extract_text(pdf_path)
                result['pdf_path'] = pdf_path
                results.append(result)
                print(f"Extracted: {Path(pdf_path).name}")
            except Exception as e:
                print(f"Error extracting {pdf_path}: {e}")
                results.append({
                    'pdf_path': pdf_path,
                    'error': str(e)
                })
        
        return results


def main():
    """Main function for testing extraction."""
    import json
    
    # Load metadata to get PDF paths
    metadata_file = Path("data/papers_metadata.json")
    if not metadata_file.exists():
        print("No papers metadata found. Run paper_scraper.py first.")
        return
    
    with open(metadata_file, 'r') as f:
        papers = json.load(f)
    
    extractor = PDFExtractor()
    
    print(f"Extracting text from {len(papers)} papers...")
    pdf_paths = [paper['pdf_path'] for paper in papers if 'pdf_path' in paper]
    
    results = extractor.extract_batch(pdf_paths)
    
    # Save extraction results
    results_file = Path("data/extraction_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nExtraction complete. Results saved to {results_file}")


if __name__ == "__main__":
    main()

