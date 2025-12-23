#!/usr/bin/env python3
"""
Bybit V5 API Documentation Change Monitor

This script monitors the Bybit V5 API documentation for changes by crawling
the documentation site and tracking each page's content with hash-based detection.
"""

import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, Set, Tuple


class BybitDocMonitor:
    def __init__(self, storage_file: str = "bybit_docs_state.json"):
        """
        Initialize the Bybit documentation monitor.
        
        Args:
            storage_file: Path to JSON file storing previous state
        """
        self.base_url = "https://bybit-exchange.github.io/docs/v5/intro"
        self.docs_domain = "bybit-exchange.github.io"
        self.storage_file = storage_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_page_hash(self, content: str) -> str:
        """Generate SHA-256 hash of page content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def fetch_page(self, url: str) -> Tuple[str, str, str]:
        """
        Fetch a page and return its content, hash, and title.
        
        Returns:
            Tuple of (content, hash, title)
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else url.split('/')[-1]
            
            # Remove non-content elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Remove navigation menus
            for nav_class in ['navbar', 'menu', 'sidebar', 'toc']:
                for element in soup.find_all(class_=lambda x: x and nav_class in x.lower()):
                    element.decompose()
            
            # Get main content
            main_content = soup.find('main') or soup.find('article') or soup
            content = main_content.get_text(separator='\n', strip=True)
            content_hash = self.get_page_hash(content)
            
            return content, content_hash, title
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return "", "", ""
    
    def discover_pages(self, max_pages: int = 200) -> Set[str]:
        """
        Discover documentation pages by crawling from the base URL.
        
        Args:
            max_pages: Maximum number of pages to discover
            
        Returns:
            Set of discovered URLs
        """
        visited = set()
        to_visit = {self.base_url}
        discovered = set()
        
        print(f"Discovering Bybit V5 API documentation from {self.base_url}...")
        
        while to_visit and len(discovered) < max_pages:
            url = to_visit.pop()
            
            if url in visited:
                continue
                
            visited.add(url)
            
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Add current page to discovered
                discovered.add(url)
                
                # Extract page title for display
                title_elem = soup.find('h1')
                title = title_elem.get_text(strip=True) if title_elem else url.split('/')[-1]
                print(f"Discovered ({len(discovered)}/{max_pages}): {title}")
                
                # Find all documentation links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    
                    # Parse URL
                    parsed = urlparse(absolute_url)
                    
                    # Only follow links within the v5 docs
                    if (parsed.netloc == self.docs_domain and 
                        '/docs/v5/' in parsed.path and
                        absolute_url not in visited and
                        len(discovered) < max_pages):
                        # Remove fragments and query params
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        to_visit.add(clean_url)
                
                time.sleep(0.5)  # Be polite to the server
                
            except Exception as e:
                print(f"Error discovering from {url}: {e}")
        
        print(f"\nDiscovered {len(discovered)} pages")
        return discovered
    
    def load_previous_state(self) -> Dict:
        """Load previous state from storage file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading previous state: {e}")
        return {}
    
    def save_state(self, state: Dict):
        """Save current state to storage file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"\nState saved to {self.storage_file}")
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def check_for_changes(self, save_content: bool = False) -> Dict:
        """
        Check all documentation pages for changes.
        
        Args:
            save_content: Whether to save full content (for detailed diffs)
            
        Returns:
            Dictionary with change information
        """
        print("=" * 70)
        print("Bybit V5 API Documentation Change Monitor")
        print("=" * 70)
        
        # Discover pages
        pages = self.discover_pages()
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_pages = previous_state.get('pages', {})
        previous_timestamp = previous_state.get('timestamp', 'Never')
        
        print(f"\nPrevious check: {previous_timestamp}")
        print(f"Checking {len(pages)} pages for changes...\n")
        
        # Current state
        current_state = {
            'timestamp': datetime.now().isoformat(),
            'pages': {}
        }
        
        # Track changes
        changes = {
            'new_pages': [],
            'modified_pages': [],
            'deleted_pages': [],
            'unchanged_pages': []
        }
        
        # Check each page
        for i, url in enumerate(sorted(pages), 1):
            # Create a short display name
            display_name = url.replace('https://bybit-exchange.github.io/docs/v5/', '')
            print(f"[{i}/{len(pages)}] Checking {display_name}...", end=' ')
            
            content, content_hash, title = self.fetch_page(url)
            
            if not content_hash:
                print("FAILED")
                continue
            
            # Store in current state
            page_data = {
                'hash': content_hash,
                'title': title,
                'last_checked': datetime.now().isoformat()
            }
            
            if save_content:
                page_data['content'] = content
            
            current_state['pages'][url] = page_data
            
            # Compare with previous state
            if url not in previous_pages:
                print("NEW")
                changes['new_pages'].append({
                    'url': url,
                    'title': title
                })
            elif previous_pages[url].get('hash') != content_hash:
                print("MODIFIED")
                changes['modified_pages'].append({
                    'url': url,
                    'title': title,
                    'old_hash': previous_pages[url].get('hash'),
                    'new_hash': content_hash
                })
            else:
                print("UNCHANGED")
                changes['unchanged_pages'].append(url)
            
            time.sleep(0.3)  # Rate limiting
        
        # Check for deleted pages
        for url in previous_pages:
            if url not in current_state['pages']:
                changes['deleted_pages'].append({
                    'url': url,
                    'title': previous_pages[url].get('title', 'Unknown')
                })
        
        # Save current state
        self.save_state(current_state)
        
        return changes
    
    def print_summary(self, changes: Dict):
        """Print a summary of changes."""
        print("\n" + "=" * 70)
        print("CHANGE SUMMARY")
        print("=" * 70)
        
        if changes['new_pages']:
            print(f"\n📄 NEW PAGES ({len(changes['new_pages'])}):")
            for page in changes['new_pages']:
                print(f"  + {page['title']}")
                print(f"    {page['url']}")
        
        if changes['modified_pages']:
            print(f"\n✏️  MODIFIED PAGES ({len(changes['modified_pages'])}):")
            for page in changes['modified_pages']:
                print(f"  ~ {page['title']}")
                print(f"    {page['url']}")
                print(f"    Old hash: {page['old_hash'][:16]}...")
                print(f"    New hash: {page['new_hash'][:16]}...")
        
        if changes['deleted_pages']:
            print(f"\n🗑️  DELETED PAGES ({len(changes['deleted_pages'])}):")
            for page in changes['deleted_pages']:
                print(f"  - {page['title']}")
                print(f"    {page['url']}")
        
        print(f"\n✓ UNCHANGED PAGES: {len(changes['unchanged_pages'])}")
        
        total_changes = (len(changes['new_pages']) + 
                        len(changes['modified_pages']) + 
                        len(changes['deleted_pages']))
        
        if total_changes == 0:
            print("\n✅ No changes detected!")
        else:
            print(f"\n⚠️  Total changes: {total_changes}")
        
        print(f"\nView full documentation at: https://bybit-exchange.github.io/docs/v5/")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor Bybit V5 API documentation for changes'
    )
    parser.add_argument(
        '--storage-file',
        default='bybit_docs_state.json',
        help='Path to state storage file (default: bybit_docs_state.json)'
    )
    parser.add_argument(
        '--save-content',
        action='store_true',
        help='Save full page content for detailed diffs (increases storage)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=200,
        help='Maximum number of pages to discover (default: 200)'
    )
    
    args = parser.parse_args()
    
    monitor = BybitDocMonitor(storage_file=args.storage_file)
    
    # Temporarily set max_pages if provided
    if args.max_pages != 200:
        original_discover = monitor.discover_pages
        monitor.discover_pages = lambda: original_discover(max_pages=args.max_pages)
    
    changes = monitor.check_for_changes(save_content=args.save_content)
    monitor.print_summary(changes)


if __name__ == "__main__":
    main()
