"""
Simple diagnostic script to test arxiv API endpoints and check paper data structure.
"""

import arxiv
import json
from typing import Dict, Any


def inspect_paper(paper: arxiv.Result) -> Dict[str, Any]:
    """Inspect a paper object and extract all available attributes."""
    inspection = {
        'title': paper.title,
        'authors': [str(a) for a in paper.authors],
        'published': str(paper.published) if paper.published else None,
        'summary': paper.summary[:200] + "..." if len(paper.summary) > 200 else paper.summary,
        'entry_id': paper.entry_id,
        'get_short_id': paper.get_short_id(),
    }
    
    # Check for PDF URL in various possible attributes
    pdf_url_attrs = ['pdf_url', 'pdf_urls', 'link', 'links', 'pdf_link']
    for attr in pdf_url_attrs:
        if hasattr(paper, attr):
            value = getattr(paper, attr)
            inspection[attr] = value
    
    # Check all attributes
    inspection['all_attributes'] = [attr for attr in dir(paper) if not attr.startswith('_')]
    
    # Check if there are any link-related attributes
    inspection['link_attributes'] = [attr for attr in dir(paper) if 'link' in attr.lower() or 'url' in attr.lower() or 'pdf' in attr.lower()]
    
    return inspection


def test_single_paper(arxiv_id: str):
    """Test fetching a single paper and inspect its structure."""
    print(f"\n{'='*60}")
    print(f"Testing paper: {arxiv_id}")
    print('='*60)
    
    try:
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=3
        )
        
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        
        if not results:
            print(f"❌ No results found for {arxiv_id}")
            return None
        
        paper = results[0]
        print(f"✓ Successfully fetched paper")
        print(f"\nTitle: {paper.title}")
        print(f"Short ID: {paper.get_short_id()}")
        print(f"Entry ID: {paper.entry_id}")
        
        # Inspect the paper object
        inspection = inspect_paper(paper)
        
        print(f"\n📋 Available attributes with 'link', 'url', or 'pdf' in name:")
        for attr in inspection['link_attributes']:
            try:
                value = getattr(paper, attr)
                print(f"  - {attr}: {value}")
            except Exception as e:
                print(f"  - {attr}: <error accessing: {e}>")
        
        print(f"\n🔍 PDF URL check:")
        if hasattr(paper, 'pdf_url'):
            pdf_url = paper.pdf_url
            print(f"  paper.pdf_url = {pdf_url}")
            if pdf_url:
                print(f"  ✓ PDF URL found!")
            else:
                print(f"  ✗ PDF URL is None or empty")
        else:
            print(f"  ✗ 'pdf_url' attribute does not exist")
        
        # Try alternative methods to get PDF URL
        print(f"\n🔍 Alternative PDF URL methods:")
        
        # Method 1: Construct from entry_id
        if paper.entry_id:
            # Arxiv PDFs are typically at: https://arxiv.org/pdf/{id}.pdf
            # Entry ID format: http://arxiv.org/abs/1707.06347v2
            entry_id = paper.entry_id
            if 'abs' in entry_id:
                pdf_url_constructed = entry_id.replace('/abs/', '/pdf/') + '.pdf'
                print(f"  Constructed from entry_id: {pdf_url_constructed}")
            elif 'abs' not in entry_id and 'pdf' not in entry_id:
                # Try to extract ID and construct
                short_id = paper.get_short_id()
                pdf_url_constructed = f"https://arxiv.org/pdf/{short_id}.pdf"
                print(f"  Constructed from short_id: {pdf_url_constructed}")
        
        # Method 2: Check links attribute if it exists
        if hasattr(paper, 'links'):
            print(f"  paper.links = {paper.links}")
        
        # Method 3: Check if there's a _raw attribute with more data
        if hasattr(paper, '_raw'):
            print(f"  paper._raw exists (raw data available)")
        
        # Print full inspection as JSON for debugging
        print(f"\n📄 Full inspection (JSON):")
        print(json.dumps(inspection, indent=2, default=str))
        
        return paper
        
    except arxiv.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        error_str = str(e)
        if '429' in error_str:
            print("  → Rate limited (429). Wait and try again.")
        elif '503' in error_str:
            print("  → Service unavailable (503). Wait and try again.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_papers(arxiv_ids: list):
    """Test multiple papers."""
    print(f"\n{'='*60}")
    print(f"Testing {len(arxiv_ids)} papers")
    print('='*60)
    
    results = []
    for arxiv_id in arxiv_ids:
        paper = test_single_paper(arxiv_id)
        results.append((arxiv_id, paper is not None))
        import time
        time.sleep(3)  # Be polite
    
    print(f"\n{'='*60}")
    print("Summary:")
    print('='*60)
    for arxiv_id, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {arxiv_id}")


if __name__ == "__main__":
    # Test the papers that are failing
    test_ids = [
        "1707.06347",  # PPO
        "1602.01783",  # A3C
        "1801.01290",  # Soft Actor-Critic
    ]
    
    print("Arxiv API Endpoint Diagnostic Tool")
    print("=" * 60)
    
    # Test single paper first
    test_single_paper(test_ids[0])
    
    # Uncomment to test all papers
    # test_multiple_papers(test_ids)

