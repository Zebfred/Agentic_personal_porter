"""
Paul's version of the paper scraper.
Paper scraper for downloading RL papers from arxiv.org and conference sites.

This module handles:
- Scraping papers from arxiv.org using arxiv API
- Downloading PDFs
- Storing metadata (title, authors, arxiv ID, date)
"""

import os
import json
import requests
import arxiv # Make sure this library is installed: pip install arxiv
from typing import List, Dict, Optional
from pathlib import Path
import time


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
        # Create a client instance for the arxiv API
        self.arxiv_client = arxiv.Client()
    
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
        
        # 1. Create the Search object (this doesn't make a request)
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
            # The 'paper' object from client.results() WILL have a valid pdf_url
            pdf_url = paper.pdf_url
            if not pdf_url:
                print(f"No PDF URL found for {arxiv_id}, skipping.")
                return None

            print(f"Downloading from: {pdf_url}")
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Use the simple arxiv_id (e.g., 1312.5602v1) for the filename
            pdf_filename = f"{arxiv_id.replace('/', '_')}.pdf"
            pdf_path = self.papers_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return pdf_path
        except Exception as e:
            print(f"Error downloading PDF for {arxiv_id} from {pdf_url}: {e}")
            return None
    
    def get_foundational_rl_papers(self) -> List[Dict]:
        """
        Get a curated list of foundational RL papers.
        This method uses specific arxiv IDs for well-known RL papers.
        
        Returns:
            List of paper metadata dictionaries
        """
        # Curated list of foundational RL papers (arxiv IDs)
        # Using version-less IDs for simplicity
        foundational_ids = [
            "1312.5602",  # DQN: Playing Atari with Deep Reinforcement Learning
            "1707.06347",  # PPO: Proximal Policy Optimization Algorithms
            "1506.02438",  # DDPG: Continuous control with deep reinforcement learning
            "1602.01783",  # A3C: Asynchronous Methods for Deep Reinforcement Learning
            "1801.01290",  # Soft Actor-Critic
            "1706.03762",  # Attention Is All You Need (Transformer)
            # ... (add more from the original list if desired)
        ]
        
        downloaded = []
        
        # Check existing metadata to avoid re-downloading
        existing_ids = set()
        for p in self.metadata:
            existing_ids.add(p['arxiv_id'].split('v')[0]) # Get base ID

        ids_to_fetch = []
        for base_id in foundational_ids:
            if base_id not in existing_ids:
                ids_to_fetch.append(base_id)
            else:
                print(f"Skipping {base_id} - already downloaded")

        if not ids_to_fetch:
            print("\nAll foundational papers are already downloaded.")
            return []

        print(f"Fetching {len(ids_to_fetch)} foundational papers...")
        try:
            # Fetch papers from arxiv in a batch
            search = arxiv.Search(id_list=ids_to_fetch)
            results = self.arxiv_client.results(search)
        except Exception as e:
            print(f"Error querying foundational papers: {e}")
            return []

        for paper in results:
            try:
                arxiv_id = paper.get_short_id() # e.g., 1312.5602v1
                
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
                    print(f"Downloaded: {paper.title[:60]}...")
                    time.sleep(1) # Be polite
                else:
                    print(f"Paper {arxiv_id} not found on arxiv (this shouldn't happen in batch)")
                    
            except Exception as e:
                print(f"Error downloading paper {arxiv_id}: {e}")
                continue
        
        self._save_metadata()
        print(f"\nDownloaded {len(downloaded)} foundational RL papers")
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