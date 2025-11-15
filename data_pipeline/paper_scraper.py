"""
Paper scraper for downloading RL papers from arxiv.org and conference sites.

This module handles:
- Scraping papers from arxiv.org using arxiv API
- Downloading PDFs
- Storing metadata (title, authors, arxiv ID, date)
"""

import os
import json
import requests
import arxiv
from typing import List, Dict, Optional
from pathlib import Path
import time
import random


class PaperScraper:
    """Scraper for downloading RL papers from various sources."""
    
    def __init__(self, papers_dir: str = "data/papers", metadata_file: str = "data/papers_metadata.json"):
        """
        Initialize the paper scraper.
        
        Args:
            papers_dir: Directory to store downloaded PDFs
            metadata_file: Path to JSON file storing paper metadata
        """
        self.papers_dir = Path(papers_dir)
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = Path(metadata_file)
        self.metadata = self._load_metadata()
        # client instance for the arxiv API with rate limiting
        # Arxiv recommends max 1 request per 3 seconds
        self.arxiv_client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,  # 3 second delay between requests
            num_retries=5  # Retry up to 5 times
        )
    
    def _load_metadata(self) -> List[Dict]:
        """Load existing metadata if available."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_metadata(self):
        """Save metadata to JSON file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def scrape_arxiv(self, 
                     query: str = "reinforcement learning",
                     max_results: int = 30,
                     sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
                     sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending) -> List[Dict]:
        """
        Scrape papers from arxiv.org using the arxiv API.
        
        Args:
            query: Search query (default: "reinforcement learning")
            max_results: Maximum number of papers to download
            sort_by: How to sort results
            sort_order: Sort order (ascending/descending)
            
        Returns:
            List of paper metadata dictionaries
        """
        print(f"Searching arxiv.org for: {query}")
        print(f"Max results: {max_results}")
        
        # create search object
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        downloaded = []

        # 2. Use the client to get the results from the search
        try:
            results = self.arxiv_client.results(search)
        except Exception as e:
            print(f"Error querying arxiv API: {e}")
            return []

        for paper in results:
            try:
                # Check if already downloaded
                               # paper.entry_id is the full URL, paper.get_short_id() is just '1312.5602v1'
                arxiv_id = paper.get_short_id()
                if any(p['arxiv_id'].startswith(arxiv_id) for p in self.metadata):
                    print(f"Skipping {arxiv_id} - already downloaded")
                    continue
                
                # Download PDF
                pdf_path = self._download_pdf(paper, arxiv_id)
                if pdf_path:
                    # Store metadata
                    paper_metadata = {
                        'arxiv_id': arxiv_id,
                        'title': paper.title,
                        'authors': [str(author) for author in paper.authors],
                        'published': paper.published.isoformat() if paper.published else None,
                        'summary': paper.summary,
                        'pdf_path': str(pdf_path),
                        'source': 'arxiv',
                        'url': paper.entry_id
                    }
                    self.metadata.append(paper_metadata)
                    downloaded.append(paper_metadata)
                    print(f"Downloaded: {paper.title[:60]}...")
                    
                    # Be polite to arxiv servers
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error processing paper {paper.entry_id}: {e}")
                continue
        
        # Save metadata
        self._save_metadata()
        print(f"\nDownloaded {len(downloaded)} new papers from arxiv")
        return downloaded
    
    def _fetch_paper_with_retry(self, arxiv_id: str, max_retries: int = 5) -> Optional[arxiv.Result]:
        """
        Fetch a single paper from arxiv with retry logic and exponential backoff.
        
        Args:
            arxiv_id: Arxiv ID (without version)
            max_retries: Maximum number of retry attempts
            
        Returns:
            arxiv.Result object or None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                search = arxiv.Search(id_list=[arxiv_id])
                results = list(self.arxiv_client.results(search))
                
                if results:
                    return results[0]
                else:
                    print(f"  Paper {arxiv_id} not found in arxiv")
                    return None
                    
            except arxiv.HTTPError as e:
                # HTTPError may have status_code as attribute or in args
                status_code = getattr(e, 'status_code', None)
                if status_code is None and hasattr(e, 'args') and len(e.args) >= 3:
                    status_code = e.args[2]  # status_code is typically the 3rd argument
                
                # Extract status code from error message if needed
                if status_code is None:
                    error_str = str(e)
                    if '429' in error_str:
                        status_code = 429
                    elif '503' in error_str:
                        status_code = 503
                
                if status_code == 429:  # Too Many Requests
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                    print(f"  Rate limited (429). Waiting {wait_time:.1f} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                elif status_code == 503:  # Service Unavailable
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"  Service unavailable (503). Waiting {wait_time:.1f} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    print(f"  HTTP error {status_code or 'unknown'} for paper {arxiv_id}: {e}")
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(wait_time)
                    else:
                        return None
                        
            except Exception as e:
                print(f"  Error fetching paper {arxiv_id}: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    return None
        
        return None
    
    def _download_pdf(self, paper: arxiv.Result, arxiv_id: str) -> Optional[Path]:
        """
        Download PDF for a given arxiv paper.
        
        Args:
            paper: arxiv.Result object
            arxiv_id: Arxiv ID for the paper
            
        Returns:
            Path to downloaded PDF, or None if download failed
        """
        try:
            # Try to get PDF URL from paper object
            pdf_url = None
            
            # Method 1: Use _get_pdf_url() method if available (most reliable)
            if hasattr(paper, '_get_pdf_url'):
                try:
                    pdf_url = paper._get_pdf_url()
                except Exception:
                    pass
            
            # Method 2: Extract from links attribute (contains PDF link)
            if not pdf_url and hasattr(paper, 'links') and paper.links:
                for link in paper.links:
                    # Links can be Link objects or strings
                    link_str = str(link) if not isinstance(link, str) else link
                    if '/pdf/' in link_str and 'arxiv.org' in link_str:
                        pdf_url = link_str
                        break
                    # Also check if it's a Link object with href
                    if hasattr(link, 'href'):
                        if '/pdf/' in link.href:
                            pdf_url = link.href
                            break
            
            # Method 3: Check pdf_url attribute (usually None but check anyway)
            if not pdf_url and hasattr(paper, 'pdf_url'):
                pdf_url = paper.pdf_url
            
            # Method 4: Construct from entry_id if still no URL
            if not pdf_url and hasattr(paper, 'entry_id') and paper.entry_id:
                entry_id = paper.entry_id
                # Entry ID format: http://arxiv.org/abs/1707.06347v2
                # PDF URL format: https://arxiv.org/pdf/1707.06347v2.pdf
                if '/abs/' in entry_id:
                    # Replace http with https and /abs/ with /pdf/, add .pdf
                    pdf_url = entry_id.replace('http://', 'https://').replace('/abs/', '/pdf/') + '.pdf'
                elif 'arxiv.org' in entry_id:
                    # Extract the ID part and construct PDF URL
                    parts = entry_id.split('/')
                    if len(parts) >= 2:
                        paper_id = parts[-1]  # Get the ID part
                        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
            
            # Method 5: Construct from short_id as last resort
            if not pdf_url:
                short_id = paper.get_short_id() if hasattr(paper, 'get_short_id') else arxiv_id
                pdf_url = f"https://arxiv.org/pdf/{short_id}.pdf"
            
            if not pdf_url:
                print(f"  Could not determine PDF URL for {arxiv_id}")
                return None

            print(f"  Downloading from: {pdf_url}")
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Use the simple arxiv_id (e.g., 1312.5602v1) for the filename
            pdf_filename = f"{arxiv_id.replace('/', '_')}.pdf"
            pdf_path = self.papers_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return pdf_path
        except requests.exceptions.RequestException as e:
            print(f"  Error downloading PDF for {arxiv_id}: {e}")
            return None
        except Exception as e:
            print(f"  Unexpected error downloading PDF for {arxiv_id}: {e}")
            return None
    
    def get_foundational_rl_papers(self) -> List[Dict]:
        """
        Get a curated list of foundational RL papers.
        This method uses specific arxiv IDs for well-known RL papers.
        
        Returns:
            List of paper metadata dictionaries
        """
        # Curated list of foundational RL papers (arxiv IDs)
        # Using version less IDs for simplicity
        foundational_papers = [
            "1707.06347",  # PPO: Proximal Policy Optimization Algorithms
            "1602.01783",  # A3C: Asynchronous Methods for Deep Reinforcement Learning
            "1801.01290",  # Soft Actor-Critic
            "1706.03762",  # Attention Is All You Need (Transformer)
            "1703.03864",  # Evolution Strategies as a Scalable Alternative
            "1801.01290",  # Soft Actor-Critic
            "1906.10667",  # AlphaStar: Grandmaster level in StarCraft II
            "1911.08265",  # Mastering Atari, Go, Chess and Shogi
            "2009.01325",  # MuZero: Mastering Go, chess, shogi and Atari

        ]
        foundational_papers_extanded = [
            #"1312.5602",  # DQN: Playing Atari with Deep Reinforcement Learning
            #"1509.06461",  # DQN Nature paper
            "1707.06347",  # PPO: Proximal Policy Optimization Algorithms
            #"1506.02438",  # DDPG: Continuous control with deep reinforcement learning
            "1602.01783",  # A3C: Asynchronous Methods for Deep Reinforcement Learning
            "1801.01290",  # Soft Actor-Critic
            "1706.03762",  # Attention Is All You Need (Transformer)
            "1810.06339",  # IMPALA: Scalable Distributed Deep-RL
            "1906.00953",  # MuZero
            #"1910.06591",  # Dreamer: Learning Latent Dynamics
            "2006.05990",  # Decision Transformer
            "2106.01345",  # Decision Transformer: Reinforcement Learning via Sequence Modeling
            "1707.01495",  # Rainbow: Combining Improvements in Deep RL
            "1803.00933",  # Distributional RL
            #"1901.10912",  # R2D2: Recurrent Experience Replay
            #"2003.13350",  # Agent57: Outperforming the Atari Human Benchmark
            "1502.05477",  # Trust Region Policy Optimization
            "1604.06778",  # Asynchronous Advantage Actor-Critic
            "1802.01561",  # Hindsight Experience Replay
            "1907.02057",  # Prioritized Experience Replay
            "1703.03864",  # Evolution Strategies as a Scalable Alternative
            "1801.01290",  # Soft Actor-Critic
            "1906.10667",  # AlphaStar: Grandmaster level in StarCraft II
            "1911.08265",  # Mastering Atari, Go, Chess and Shogi
            "2009.01325",  # MuZero: Mastering Go, chess, shogi and Atari
        ]
        
        downloaded = []
        # Check existing metadata to avoid re-downloading
        existing_ids = set()
        for p in self.metadata:
            existing_ids.add(p['arxiv_id'].split('v')[0]) # Get base ID

        ids_to_fetch = []
        for base_id in foundational_papers:
            if base_id not in existing_ids:
                ids_to_fetch.append(base_id)
            else:
                print(f"Skipping {base_id} - already downloaded")

        if not ids_to_fetch:
            print("\nAll foundational papers are already downloaded.")
            return []

        print(f"Fetching {len(ids_to_fetch)} foundational papers...")
        print("Note: Fetching papers one at a time to respect arxiv rate limits...")
        
        # Fetch papers one at a time to avoid rate limiting
        for i, base_id in enumerate(ids_to_fetch, 1):
            try:
                print(f"\n[{i}/{len(ids_to_fetch)}] Fetching paper {base_id}...")
                
                # Fetch single paper with retry logic
                paper = self._fetch_paper_with_retry(base_id)
                
                if not paper:
                    print(f"  Failed to fetch paper {base_id} after retries")
                    continue
                
                arxiv_id = paper.get_short_id()  # e.g., 1312.5602v1
                
                # Download PDF
                pdf_path = self._download_pdf(paper, arxiv_id)
                if pdf_path:
                    paper_metadata = {
                        'arxiv_id': arxiv_id,
                        'title': paper.title,
                        'authors': [str(author) for author in paper.authors],
                        'published': paper.published.isoformat() if paper.published else None,
                        'summary': paper.summary,
                        'pdf_path': str(pdf_path),
                        'source': 'arxiv',
                        'url': paper.entry_id
                    }
                    self.metadata.append(paper_metadata)
                    downloaded.append(paper_metadata)
                    # Save metadata incrementally to preserve progress
                    self._save_metadata()
                    print(f"  ✓ Downloaded: {paper.title[:60]}...")
                else:
                    print(f"  ✗ Failed to download PDF for {arxiv_id}")
                
                # Be polite to arxiv servers - wait between papers
                if i < len(ids_to_fetch):  # Don't wait after last paper
                    wait_time = 3.0 + random.uniform(0, 2)  # 3-5 seconds
                    print(f"  Waiting {wait_time:.1f} seconds before next request...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                print(f"  ✗ Error processing paper {base_id}: {e}")
                # Wait even on error to avoid hammering the server
                if i < len(ids_to_fetch):
                    time.sleep(3.0)
                continue
        
        # Final save (already saved incrementally, but ensure it's saved)
        self._save_metadata()
        print(f"\n✓ Successfully downloaded {len(downloaded)} foundational RL papers")
        if len(downloaded) < len(ids_to_fetch):
            print(f"  Note: {len(ids_to_fetch) - len(downloaded)} papers could not be downloaded")
        return downloaded


def main():
    """Main function to run the scraper."""
    scraper = PaperScraper()
    
    # First, get foundational papers
    print("=" * 60)
    print("Downloading Foundational RL Papers")
    print("=" * 60)
    foundational = scraper.get_foundational_rl_papers()
    
    # Then, search for additional recent papers
    print("\n" + "=" * 60)
    print("Searching for Additional Recent RL Papers")
    print("=" * 60)
    recent = scraper.scrape_arxiv(
        query="reinforcement learning AND (deep learning OR neural networks)",
        max_results=10
    )
    
    print(f"\nTotal papers in database: {len(scraper.metadata)}")


if __name__ == "__main__":
    main()