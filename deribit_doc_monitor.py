#!/usr/bin/env python3
"""
Deribit API Documentation Change Monitor

This script scrapes the Deribit API documentation website and tracks changes
by storing page hashes and optionally full content for comparison.
"""

import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, Set, List, Tuple


class DeribitDocMonitor:
    def __init__(self, storage_file: str = "deribit_docs_state.json"):
        """
        Initialize the documentation monitor.
        
        Args:
            storage_file: Path to JSON file storing previous state
        """
        self.base_url = "https://docs.deribit.com/"
        self.storage_file = storage_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_page_hash(self, content: str) -> str:
        """Generate SHA-256 hash of page content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def fetch_page(self, section_id: str) -> Tuple[str, str]:
        """
        Fetch a specific section's content and return its content and hash.
        
        Returns:
            Tuple of (content, hash)
        """
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the section by ID
            section = soup.find(id=section_id)
            
            if not section:
                print(f"Section {section_id} not found")
                return "", ""
            
            # Get all content until the next major heading
            content_parts = []
            for sibling in section.find_all_next():
                # Stop at the next h1 or h2
                if sibling.name in ['h1', 'h2'] and sibling.get('id') != section_id:
                    break
                
                # Get text from this element
                if sibling.name not in ['script', 'style', 'nav', 'footer', 'header']:
                    text = sibling.get_text(separator=' ', strip=True)
                    if text:
                        content_parts.append(text)
            
            content = '\n'.join(content_parts)
            content_hash = self.get_page_hash(content)
            
            return content, content_hash
        except Exception as e:
            print(f"Error fetching section {section_id}: {e}")
            return "", ""
    
    def discover_pages(self, max_pages: int = 200) -> Dict[str, str]:
        """
        Discover documentation sections from the single-page docs.
        
        Since Deribit docs is a single-page app, we extract major sections
        as separate trackable items.
        
        Returns:
            Dict of section_id -> section_title
        """
        print(f"Fetching documentation from {self.base_url}...")
        
        sections = {}
        
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all major headings (h1, h2) which represent different sections
            for heading in soup.find_all(['h1', 'h2']):
                # Get the id attribute for the section
                section_id = heading.get('id')
                if section_id:
                    section_title = heading.get_text(strip=True)
                    sections[section_id] = section_title
                    print(f"Found section: {section_title} (#{section_id})")
            
            print(f"\nDiscovered {len(sections)} documentation sections")
            
        except Exception as e:
            print(f"Error fetching documentation: {e}")
        
        return sections
    
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
        Check all documentation sections for changes.
        
        Args:
            save_content: Whether to save full content (for detailed diffs)
            
        Returns:
            Dictionary with change information
        """
        print("=" * 70)
        print("Deribit API Documentation Change Monitor")
        print("=" * 70)
        
        # Discover sections
        sections = self.discover_pages()
        print(f"\nDiscovered {len(sections)} sections")
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_sections = previous_state.get('sections', {})
        previous_timestamp = previous_state.get('timestamp', 'Never')
        
        print(f"Previous check: {previous_timestamp}")
        print(f"Checking {len(sections)} sections for changes...\n")
        
        # Current state
        current_state = {
            'timestamp': datetime.now().isoformat(),
            'sections': {}
        }
        
        # Track changes
        changes = {
            'new_sections': [],
            'modified_sections': [],
            'deleted_sections': [],
            'unchanged_sections': []
        }
        
        # Check each section
        for i, (section_id, section_title) in enumerate(sorted(sections.items()), 1):
            print(f"[{i}/{len(sections)}] Checking {section_title}...", end=' ')
            
            content, content_hash = self.fetch_page(section_id)
            
            if not content_hash:
                print("FAILED")
                continue
            
            # Store in current state
            section_data = {
                'title': section_title,
                'hash': content_hash,
                'last_checked': datetime.now().isoformat()
            }
            
            if save_content:
                section_data['content'] = content
            
            current_state['sections'][section_id] = section_data
            
            # Compare with previous state
            if section_id not in previous_sections:
                print("NEW")
                changes['new_sections'].append({
                    'id': section_id,
                    'title': section_title
                })
            elif previous_sections[section_id].get('hash') != content_hash:
                print("MODIFIED")
                changes['modified_sections'].append({
                    'id': section_id,
                    'title': section_title,
                    'old_hash': previous_sections[section_id].get('hash'),
                    'new_hash': content_hash
                })
            else:
                print("UNCHANGED")
                changes['unchanged_sections'].append(section_id)
            
            time.sleep(0.3)  # Rate limiting
        
        # Check for deleted sections
        for section_id in previous_sections:
            if section_id not in current_state['sections']:
                changes['deleted_sections'].append({
                    'id': section_id,
                    'title': previous_sections[section_id].get('title', 'Unknown')
                })
        
        # Save current state
        self.save_state(current_state)
        
        return changes
    
    def print_summary(self, changes: Dict):
        """Print a summary of changes."""
        print("\n" + "=" * 70)
        print("CHANGE SUMMARY")
        print("=" * 70)
        
        if changes['new_sections']:
            print(f"\n📄 NEW SECTIONS ({len(changes['new_sections'])}):")
            for section in changes['new_sections']:
                print(f"  + {section['title']} (#{section['id']})")
        
        if changes['modified_sections']:
            print(f"\n✏️  MODIFIED SECTIONS ({len(changes['modified_sections'])}):")
            for section in changes['modified_sections']:
                print(f"  ~ {section['title']} (#{section['id']})")
                print(f"    Old hash: {section['old_hash'][:16]}...")
                print(f"    New hash: {section['new_hash'][:16]}...")
        
        if changes['deleted_sections']:
            print(f"\n🗑️  DELETED SECTIONS ({len(changes['deleted_sections'])}):")
            for section in changes['deleted_sections']:
                print(f"  - {section['title']} (#{section['id']})")
        
        print(f"\n✓ UNCHANGED SECTIONS: {len(changes['unchanged_sections'])}")
        
        total_changes = (len(changes['new_sections']) + 
                        len(changes['modified_sections']) + 
                        len(changes['deleted_sections']))
        
        if total_changes == 0:
            print("\n✅ No changes detected!")
        else:
            print(f"\n⚠️  Total changes: {total_changes}")
        
        print(f"\nView full documentation at: {self.base_url}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor Deribit API documentation for changes'
    )
    parser.add_argument(
        '--storage-file',
        default='deribit_docs_state.json',
        help='Path to state storage file (default: deribit_docs_state.json)'
    )
    parser.add_argument(
        '--save-content',
        action='store_true',
        help='Save full section content for detailed diffs (increases storage)'
    )
    
    args = parser.parse_args()
    
    monitor = DeribitDocMonitor(storage_file=args.storage_file)
    changes = monitor.check_for_changes(save_content=args.save_content)
    monitor.print_summary(changes)


if __name__ == "__main__":
    main()
