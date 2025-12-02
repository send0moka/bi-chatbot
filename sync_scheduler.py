"""
Sync Scheduler for Auto-Sync Knowledge Base
Run this script via cron/task scheduler for automated syncing
"""

import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import sys

KNOWLEDGE_BASE_DIR = "knowledge_base"
SYNC_CONFIG_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "sync_config.json")
CURRENT_KB_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "current_knowledge.json")
SYNC_LOG_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "sync_log.txt")

def log_message(message):
    """Log sync activities"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(log_entry.strip())
    
    with open(SYNC_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def load_sync_config():
    """Load sync configuration"""
    if os.path.exists(SYNC_CONFIG_FILE):
        with open(SYNC_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def fetch_content(url):
    """Fetch content from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        log_message(f"ERROR fetching {url}: {str(e)}")
        return None

def update_knowledge_base(url_contents):
    """Update knowledge base with fetched content"""
    try:
        # Load current KB
        if os.path.exists(CURRENT_KB_FILE):
            with open(CURRENT_KB_FILE, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
        else:
            kb_data = {"sections": [], "version": "1.0.0"}
        
        # Add synced content as new sections
        for url, content in url_contents.items():
            if content:
                # Create section for synced content
                section = {
                    "title": f"Auto-Synced from {url}",
                    "content": content[:5000],  # Limit content size
                    "synced_at": datetime.now().isoformat(),
                    "source_url": url,
                    "auto_synced": True
                }
                
                # Check if section already exists and update
                existing_idx = None
                for idx, sec in enumerate(kb_data["sections"]):
                    if sec.get("source_url") == url and sec.get("auto_synced"):
                        existing_idx = idx
                        break
                
                if existing_idx is not None:
                    kb_data["sections"][existing_idx] = section
                    log_message(f"Updated existing section from {url}")
                else:
                    kb_data["sections"].append(section)
                    log_message(f"Added new section from {url}")
        
        # Save updated KB
        kb_data["last_updated"] = datetime.now().isoformat()
        
        with open(CURRENT_KB_FILE, 'w', encoding='utf-8') as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
        
        log_message(f"Knowledge base updated successfully")
        return True
        
    except Exception as e:
        log_message(f"ERROR updating KB: {str(e)}")
        return False

def main():
    """Main sync function"""
    log_message("=" * 60)
    log_message("Starting scheduled sync")
    
    # Check if KB directory exists
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        log_message("ERROR: knowledge_base directory not found")
        sys.exit(1)
    
    # Load config
    config = load_sync_config()
    
    if not config:
        log_message("ERROR: sync_config.json not found")
        sys.exit(1)
    
    if not config.get("enabled"):
        log_message("Auto-sync is disabled. Skipping.")
        sys.exit(0)
    
    urls = config.get("urls", [])
    if not urls:
        log_message("No URLs configured for sync")
        sys.exit(0)
    
    log_message(f"Syncing {len(urls)} URL(s)")
    
    # Fetch content from all URLs
    url_contents = {}
    for url in urls:
        log_message(f"Fetching: {url}")
        content = fetch_content(url)
        if content:
            url_contents[url] = content
            log_message(f"SUCCESS: Fetched {len(content)} characters")
        else:
            log_message(f"FAILED: Could not fetch content")
    
    # Update knowledge base
    if url_contents:
        success = update_knowledge_base(url_contents)
        if success:
            # Update last sync time in config
            config["last_sync"] = datetime.now().isoformat()
            with open(SYNC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            log_message("Sync completed successfully")
        else:
            log_message("Sync completed with errors")
            sys.exit(1)
    else:
        log_message("No content fetched. Sync aborted.")
        sys.exit(1)
    
    log_message("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_message(f"FATAL ERROR: {str(e)}")
        sys.exit(1)
