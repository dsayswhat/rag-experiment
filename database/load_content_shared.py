#!/usr/bin/env python3
"""
Load extracted content into PostgreSQL using core configuration.

This is a simplified version of load_content.py that uses the shared config system.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

from tqdm import tqdm
from psycopg2.extras import execute_values

# Add the parent directory to the path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    get_config, get_db_connection, get_embeddings_batch_sync, 
    get_embedding_sync, average_embeddings
)


def classify_content(title: str, content: str, config) -> Tuple[List[str], List[str]]:
    """
    Classify content based on title and content analysis using configurable types
    Returns (content_types, tags)
    """
    title_lower = title.lower()
    content_lower = content.lower()
    
    content_types = []
    tags = []
    
    # Generic content type classification based on common patterns
    # Users can customize this by environment variables or configuration
    
    # Map common keywords to generic types
    type_keywords = {
        'reference': ['reference', 'definition', 'glossary', 'index'],
        'procedure': ['procedure', 'rule', 'mechanic', 'process', 'step'],
        'concept': ['concept', 'theory', 'principle', 'explanation'],
        'example': ['example', 'sample', 'demo', 'case study'],
    }
    
    # Check configured content types for keyword matches
    for content_type in config.content_types:
        keywords = type_keywords.get(content_type, [content_type.lower()])
        if any(keyword in title_lower for keyword in keywords):
            content_types.append(content_type)
    
    # If no configured types match, try to infer from available types
    if not content_types and config.content_types:
        # Default to first configured type as fallback
        content_types.append(config.content_types[0])
    
    # Extract general tags
    common_tag_keywords = {
        'technical': ['api', 'code', 'programming', 'technical'],
        'process': ['workflow', 'process', 'procedure'],
        'guide': ['guide', 'tutorial', 'how-to', 'instructions'],
    }
    
    for tag, keywords in common_tag_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            tags.append(tag)
    
    return content_types, tags


def chunk_text(text: str, max_chunk_size: int = 32000) -> List[str]:
    """Split large text into chunks at sentence boundaries"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (simple approach)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def process_section_file(file_path: Path, config) -> Optional[Dict]:
    """Process a single section file and return section data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return None
        
        # Extract title (first line starting with #)
        lines = content.split('\n')
        title = "Unknown Section"
        for line in lines:
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                break
        
        # Extract section ID from filename
        section_id = file_path.stem.replace(f"{file_path.parts[-1].split('_')[0]}_section_", "")
        
        # Determine source book from filename/path
        source_book = "unknown"
        if "players_book" in str(file_path):
            source_book = "players_book"
        elif "campaign_book" in str(file_path):
            source_book = "campaign_book"
        elif "monster_book" in str(file_path):
            source_book = "monster_book"
        
        # Classify content
        content_types, tags = classify_content(title, content, config)
        
        # Generate embedding
        if len(content) > config.max_chunk_size:
            # Chunk large content and average embeddings
            chunks = chunk_text(content, config.max_chunk_size)
            embeddings = get_embeddings_batch_sync(chunks)
            embedding = average_embeddings(embeddings)
        else:
            embedding = get_embedding_sync(content)
        
        return {
            'id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'embedding': embedding,
            'source_type': config.default_source_type,
            'source_book': source_book,
            'section_id': section_id,
            'content_type': content_types,
            'tags': tags,
            'page_range': 'extracted',  # Could be enhanced to extract from metadata
            'character_count': len(content),
            'word_count': len(content.split()),
            'file_path': str(file_path)
        }
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None


def load_sections_batch(sections: List[Dict], connection):
    """Load sections into database in batch"""
    cursor = connection.cursor()
    
    # Prepare data for batch insert
    values = []
    for section in sections:
        values.append((
            section['id'],
            section['title'],
            section['content'],
            section['embedding'],
            section['source_type'],
            section['source_book'],
            section['section_id'],
            section['content_type'],
            section['tags'],
            section['page_range'],
            section['character_count'],
            section['word_count'],
            section['file_path']
        ))
    
    # Batch insert
    execute_values(
        cursor,
        """
        INSERT INTO content_sections 
        (id, title, content, embedding, source_type, source_book, section_id, 
         content_type, tags, page_range, character_count, word_count, file_path)
        VALUES %s
        """,
        values,
        template=None,
        page_size=100
    )
    
    connection.commit()
    cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Load content into PostgreSQL")
    parser.add_argument("--sections-dir", type=Path, required=True,
                        help="Directory containing extracted section files")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Batch size for processing (default from config)")
    parser.add_argument("--source-type", default=None,
                        help="Source type for content (default from config)")
    
    args = parser.parse_args()
    
    # Get configuration
    config = get_config()
    batch_size = args.batch_size or config.default_batch_size
    source_type = args.source_type or config.default_source_type
    
    # Find all section files
    section_files = list(args.sections_dir.glob("*_section_*.md"))
    if not section_files:
        print(f"No section files found in {args.sections_dir}")
        return
    
    print(f"Found {len(section_files)} section files")
    print(f"Processing in batches of {batch_size}")
    
    # Process files in batches
    with get_db_connection() as conn:
        batch = []
        
        for file_path in tqdm(section_files, desc="Processing sections"):
            section_data = process_section_file(file_path, config)
            if section_data:
                section_data['source_type'] = source_type
                batch.append(section_data)
                
                if len(batch) >= batch_size:
                    load_sections_batch(batch, conn)
                    batch = []
        
        # Process remaining batch
        if batch:
            load_sections_batch(batch, conn)
    
    print(f"Successfully loaded {len(section_files)} sections")


if __name__ == "__main__":
    main()