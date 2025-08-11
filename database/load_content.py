#!/usr/bin/env python3
"""
Load extracted Dolmenwood content into PostgreSQL with vector embeddings.

This script:
1. Reads extracted markdown sections and their metadata
2. Classifies content types based on section titles/content
3. Generates OpenAI embeddings for content (batched for performance)
4. Loads everything into PostgreSQL with pgvector (batched transactions)

Features:
- Batched processing for better performance (default: 20 sections per batch)
- Smart text chunking for large sections (preserves sentence boundaries)
- Automatic fallback to individual processing on batch failures
- Environment variable support for database URL and OpenAI API key
- Progress tracking with tqdm
- Configurable chunk size for memory and token limit management

Usage:
    # Use environment variables (recommended)
    python database/load_content.py --sections-dir output/
    
    # Or specify database URL directly
    python database/load_content.py --sections-dir output/ --db-url postgresql://user:pass@localhost/dolmenwood_content
    
    # Adjust batch size for performance tuning
    python database/load_content.py --sections-dir output/ --batch-size 10
    
    # Adjust chunk size for large sections (76K char rumours section will be chunked)
    python database/load_content.py --sections-dir output/ --max-chunk-size 16000
    
    # Disable batching (use individual processing)
    python database/load_content.py --sections-dir output/ --no-batching
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

import psycopg2
from psycopg2.extras import execute_values
import openai
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

class ContentLoader:
    def __init__(self, db_url: str, openai_api_key: Optional[str] = None, max_chunk_size: int = 32000):
        """Initialize with database connection and OpenAI client."""
        self.conn = psycopg2.connect(db_url)
        self.openai_client = openai.OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        self.max_chunk_size = max_chunk_size
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        
    def classify_content_type(self, title: str, content: str) -> List[str]:
        """Classify content based on title and content analysis."""
        title_lower = title.lower()
        content_lower = content.lower()
        types = []
        
        # Spell detection
        if ('spell' in title_lower or 'rank' in title_lower or 
            'arcane' in title_lower or 'holy' in title_lower or
            'glamour' in title_lower or 'rune' in title_lower):
            types.append('spell')
            if 'arcane' in title_lower:
                types.append('arcane')
            if 'holy' in title_lower:
                types.append('holy')
                
        # Location detection
        if any(word in title_lower for word in ['gazetteer', 'castle', 'fort', 'town', 'village', 'settlement', 'dungeon']):
            types.append('location')
            
        # Character race/ancestry detection
        if title_lower in ['breggle', 'elf', 'grimalkin', 'human', 'mossling', 'woodgrue']:
            types.append('ancestry')
            
        # Character class detection  
        if title_lower in ['bard', 'cleric', 'enchanter', 'fighter', 'friar', 'hunter', 'knight', 'magician', 'thief']:
            types.append('class')
            
        # Equipment and gear
        if any(word in title_lower for word in ['gear', 'weapon', 'armour', 'armor', 'equipment', 'horse', 'vehicle']):
            types.append('equipment')
            
        # Food, drink, and services
        if any(word in title_lower for word in ['food', 'beverage', 'lodging', 'service', 'pipeleaf', 'fungi', 'herb']):
            types.append('services')
            
        # Rules and mechanics
        if any(word in title_lower for word in ['rule', 'procedure', 'combat', 'movement', 'encumbrance', 'travel', 'camping']):
            types.append('rule')
            
        # Lore and setting
        if any(word in title_lower for word in ['folk', 'faction', 'noble', 'religion', 'calendar', 'language']):
            types.append('lore')
            
        # Examples and guides
        if 'example' in title_lower:
            types.append('example')
            
        # Default to general if no specific type found
        if not types:
            types.append('general')
            
        return types
        
    def generate_tags(self, title: str, content: str, content_types: List[str]) -> List[str]:
        """Generate relevant tags for content organization."""
        tags = []
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Add content types as tags
        tags.extend(content_types)
        
        # Magic-related tags
        if any(word in content_lower for word in ['magic', 'spell', 'enchant', 'charm']):
            tags.append('magic')
            
        # Combat-related tags
        if any(word in content_lower for word in ['combat', 'attack', 'weapon', 'fight', 'battle']):
            tags.append('combat')
            
        # Social interaction tags
        if any(word in content_lower for word in ['noble', 'lord', 'duke', 'baron', 'faction']):
            tags.append('social')
            
        # Nature/wilderness tags
        if any(word in content_lower for word in ['forest', 'wood', 'wild', 'travel', 'camp']):
            tags.append('wilderness')
            
        # Religion tags
        if any(word in content_lower for word in ['church', 'saint', 'prayer', 'holy', 'god']):
            tags.append('religion')
            
        return list(set(tags))  # Remove duplicates
        
    def smart_chunk_text(self, text: str, max_chars: int = None) -> List[str]:
        """Split text into chunks that preserve sentence boundaries."""
        if max_chars is None:
            max_chars = self.max_chunk_size
            
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # Get chunk with max size
            chunk_end = min(current_pos + max_chars, len(text))
            chunk = text[current_pos:chunk_end]
            
            # If this isn't the last chunk, try to break at sentence boundary
            if chunk_end < len(text):
                # Look for sentence endings within the last 20% of the chunk
                search_start = max(0, len(chunk) - int(max_chars * 0.2))
                
                # Find the last sentence ending
                for ending in ['. ', '.\n', '.\t']:
                    last_sentence = chunk.rfind(ending, search_start)
                    if last_sentence != -1:
                        chunk = chunk[:last_sentence + 1]
                        break
                else:
                    # No sentence boundary found, look for paragraph break
                    last_paragraph = chunk.rfind('\n\n', search_start)
                    if last_paragraph != -1:
                        chunk = chunk[:last_paragraph + 2]
                    # Otherwise keep the chunk as-is (hard break)
            
            chunks.append(chunk)
            current_pos += len(chunk)
        
        return chunks

    def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text content with smart chunking."""
        max_single_chunk = self.max_chunk_size
        
        # For small text, process normally
        if len(text) <= max_single_chunk:
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"Error generating embedding: {e}")
                return [0.0] * 1536
        
        # For large text, use chunking and averaging
        print(f"  📄 Large content ({len(text)} chars) - using chunking")
        chunks = self.smart_chunk_text(text)
        
        embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=chunk
                )
                embeddings.append(response.data[0].embedding)
                print(f"    ✓ Chunk {i+1}/{len(chunks)} processed")
            except Exception as e:
                print(f"    ✗ Error with chunk {i+1}: {e}")
                embeddings.append([0.0] * 1536)  # Fallback
        
        # Average the embeddings
        if embeddings:
            avg_embedding = [sum(dim)/len(embeddings) for dim in zip(*embeddings)]
            print(f"  ✓ Averaged {len(embeddings)} chunk embeddings")
            return avg_embedding
        else:
            return [0.0] * 1536
            
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts at once with smart chunking."""
        if not texts:
            return []
        
        # Check if any texts need chunking
        large_texts = [i for i, text in enumerate(texts) if len(text) > self.max_chunk_size]
        
        if large_texts:
            print(f"  📄 Batch contains {len(large_texts)} large texts - processing individually")
            # Fall back to individual processing for large texts
            return [self.generate_embedding(text) for text in texts]
        
        # All texts are small enough for batch processing
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Batch embedding failed ({len(texts)} texts): {e}")
            print("Falling back to individual embedding generation...")
            # Fallback to individual calls (which will handle chunking if needed)
            return [self.generate_embedding(text) for text in texts]
            
    def parse_section_file(self, file_path: Path) -> Dict:
        """Parse a section markdown file and extract metadata."""
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Extract title (first line should be # Title)
        title = lines[0].replace('# ', '').strip() if lines else file_path.stem
        
        # Extract metadata from header
        metadata = {}
        content_start = 0
        
        for i, line in enumerate(lines[1:10], 1):  # Check first few lines for metadata
            if line.startswith('**Pages:**'):
                metadata['page_range'] = line.replace('**Pages:**', '').strip()
            elif line.startswith('**Characters:**'):
                try:
                    metadata['character_count'] = int(line.replace('**Characters:**', '').strip().replace(',', ''))
                except ValueError:
                    pass
            elif line.startswith('**Words:**'):
                try:
                    metadata['word_count'] = int(line.replace('**Words:**', '').strip().replace(',', ''))
                except ValueError:
                    pass
            elif line.startswith('**Section ID:**'):
                metadata['section_id'] = line.replace('**Section ID:**', '').strip()
            elif line == '---':
                content_start = i + 1
                break
                
        # Extract main content (after metadata section)
        main_content = '\n'.join(lines[content_start:]) if content_start > 0 else content
        
        return {
            'title': title,
            'content': main_content,
            'file_path': str(file_path),
            **metadata
        }
        
    def load_sections_from_directory(self, sections_dir: Path, source_book: str) -> List[Dict]:
        """Load all section files from a directory."""
        sections = []
        
        # Look for section files
        section_files = list(sections_dir.glob(f"{source_book}_section_*.md"))
        
        print(f"Found {len(section_files)} section files for {source_book}")
        
        for file_path in section_files:
            try:
                section_data = self.parse_section_file(file_path)
                section_data['source_book'] = source_book
                sections.append(section_data)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                
        return sections
        
    def insert_section(self, section: Dict, source_type: str = 'dolmenwood_official'):
        """Insert a single section into the database."""
        # Classify content and generate tags
        content_types = self.classify_content_type(section['title'], section['content'])
        tags = self.generate_tags(section['title'], section['content'], content_types)
        
        # Generate embedding
        embedding_text = f"{section['title']}\n\n{section['content']}"
        embedding = self.generate_embedding(embedding_text)
        
        # Prepare data for insertion
        insert_data = {
            'id': str(uuid.uuid4()),
            'title': section['title'],
            'content': section['content'],
            'embedding': embedding,
            'source_type': source_type,
            'source_book': section.get('source_book'),
            'section_id': section.get('section_id'),
            'content_type': content_types,
            'tags': tags,
            'page_range': section.get('page_range'),
            'character_count': section.get('character_count'),
            'word_count': section.get('word_count'),
            'file_path': section.get('file_path')
        }
        
        # Insert into database
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO content_sections (
                    id, title, content, embedding, source_type, source_book, 
                    section_id, content_type, tags, page_range, character_count, 
                    word_count, file_path
                ) VALUES (
                    %(id)s, %(title)s, %(content)s, %(embedding)s, %(source_type)s, 
                    %(source_book)s, %(section_id)s, %(content_type)s, %(tags)s, 
                    %(page_range)s, %(character_count)s, %(word_count)s, %(file_path)s
                )
            """, insert_data)
            self.conn.commit()
        except Exception as e:
            print(f"Error inserting section '{section['title']}': {e}")
            self.conn.rollback()
        finally:
            cursor.close()
            
    def insert_batch(self, sections_data: List[Dict]):
        """Insert multiple sections in a single transaction."""
        if not sections_data:
            return
            
        cursor = self.conn.cursor()
        try:
            # Prepare data tuples for batch insert
            values = []
            for data in sections_data:
                values.append((
                    data['id'], data['title'], data['content'], data['embedding'],
                    data['source_type'], data['source_book'], data['section_id'],
                    data['content_type'], data['tags'], data['page_range'],
                    data['character_count'], data['word_count'], data['file_path']
                ))
            
            execute_values(
                cursor,
                """
                INSERT INTO content_sections (
                    id, title, content, embedding, source_type, source_book, 
                    section_id, content_type, tags, page_range, character_count, 
                    word_count, file_path
                ) VALUES %s
                """,
                values,
                template=None,
                page_size=100
            )
            self.conn.commit()
            print(f"✓ Inserted batch of {len(sections_data)} sections")
            
        except Exception as e:
            print(f"✗ Error inserting batch of {len(sections_data)} sections: {e}")
            self.conn.rollback()
            # Fallback to individual inserts
            print("Falling back to individual section processing...")
            for section_data in sections_data:
                try:
                    cursor.execute("""
                        INSERT INTO content_sections (
                            id, title, content, embedding, source_type, source_book, 
                            section_id, content_type, tags, page_range, character_count, 
                            word_count, file_path
                        ) VALUES (
                            %(id)s, %(title)s, %(content)s, %(embedding)s, %(source_type)s, 
                            %(source_book)s, %(section_id)s, %(content_type)s, %(tags)s, 
                            %(page_range)s, %(character_count)s, %(word_count)s, %(file_path)s
                        )
                    """, section_data)
                    self.conn.commit()
                    print(f"  ✓ Inserted: {section_data['title']}")
                except Exception as section_error:
                    print(f"  ✗ Failed to insert '{section_data['title']}': {section_error}")
                    self.conn.rollback()
        finally:
            cursor.close()
            
    def process_batch(self, batch: List[Dict], source_type: str):
        """Process a batch of sections: generate embeddings and insert to DB."""
        if not batch:
            return
            
        print(f"Processing batch of {len(batch)} sections...")
        
        # Prepare texts for batch embedding
        texts = [f"{section['title']}\n\n{section['content']}" for section in batch]
        
        # Generate all embeddings at once
        print(f"  Generating embeddings for {len(texts)} sections...")
        embeddings = self.generate_embeddings_batch(texts)
        
        # Prepare data for batch database insert
        sections_data = []
        for section, embedding in zip(batch, embeddings):
            sections_data.append({
                'id': str(uuid.uuid4()),
                'title': section['title'],
                'content': section['content'],
                'embedding': embedding,
                'source_type': source_type,
                'source_book': section.get('source_book'),
                'section_id': section.get('section_id'),
                'content_type': section['content_types'],
                'tags': section['tags'],
                'page_range': section.get('page_range'),
                'character_count': section.get('character_count'),
                'word_count': section.get('word_count'),
                'file_path': section.get('file_path')
            })
        
        # Insert entire batch
        self.insert_batch(sections_data)
            
    def load_all_sections(self, sections_dir: Path, source_type: str = 'dolmenwood_official'):
        """Load all sections from extracted content."""
        # Detect available books
        md_files = list(sections_dir.glob("*_section_*.md"))
        books = set()
        
        for file in md_files:
            # Extract book name from filename pattern: {book}_section_{section}.md
            book_match = re.match(r'(.+)_section_', file.name)
            if book_match:
                books.add(book_match.group(1))
                
        print(f"Found books: {sorted(books)}")
        
        total_sections = 0
        for book in sorted(books):
            print(f"\nLoading {book}...")
            sections = self.load_sections_from_directory(sections_dir, book)
            
            for section in tqdm(sections, desc=f"Processing {book}"):
                self.insert_section(section, source_type)
                total_sections += 1
                
        print(f"\nLoaded {total_sections} sections total")
        
        # Print summary
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_book, COUNT(*) FROM content_sections GROUP BY source_book ORDER BY source_book")
        results = cursor.fetchall()
        cursor.close()
        
        print("\nDatabase summary:")
        for book, count in results:
            print(f"  {book}: {count} sections")
            
    def load_all_sections_batched(self, sections_dir: Path, source_type: str = 'dolmenwood_official', batch_size: int = 20):
        """Load all sections from extracted content using batched processing."""
        # Detect available books
        md_files = list(sections_dir.glob("*_section_*.md"))
        books = set()
        
        for file in md_files:
            # Extract book name from filename pattern: {book}_section_{section}.md
            book_match = re.match(r'(.+)_section_', file.name)
            if book_match:
                books.add(book_match.group(1))
                
        print(f"Found books: {sorted(books)}")
        print(f"Using batch size: {batch_size}")
        
        total_sections = 0
        for book in sorted(books):
            print(f"\nLoading {book}...")
            sections = self.load_sections_from_directory(sections_dir, book)
            
            # Process content classification for all sections first
            for section in sections:
                content_types = self.classify_content_type(section['title'], section['content'])
                tags = self.generate_tags(section['title'], section['content'], content_types)
                section['content_types'] = content_types
                section['tags'] = tags
            
            # Process in batches
            batch = []
            with tqdm(total=len(sections), desc=f"Processing {book}") as pbar:
                for section in sections:
                    batch.append(section)
                    
                    if len(batch) >= batch_size:
                        self.process_batch(batch, source_type)
                        total_sections += len(batch)
                        pbar.update(len(batch))
                        batch.clear()
                
                # Process remaining sections
                if batch:
                    self.process_batch(batch, source_type)
                    total_sections += len(batch)
                    pbar.update(len(batch))
                    
        print(f"\nLoaded {total_sections} sections total using batched processing")
        
        # Print summary
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_book, COUNT(*) FROM content_sections GROUP BY source_book ORDER BY source_book")
        results = cursor.fetchall()
        cursor.close()
        
        print("\nDatabase summary:")
        for book, count in results:
            print(f"  {book}: {count} sections")

def main():
    parser = argparse.ArgumentParser(description='Load Dolmenwood content into PostgreSQL with vector embeddings')
    parser.add_argument('--sections-dir', type=Path, default='output', 
                       help='Directory containing extracted section files')
    parser.add_argument('--db-url',
                       help='PostgreSQL connection URL (or set DATABASE_URL env var)')
    parser.add_argument('--source-type', default='dolmenwood_official',
                       choices=['dolmenwood_official', 'homebrew', 'campaign_notes'],
                       help='Type of content being loaded')
    parser.add_argument('--openai-api-key', 
                       help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of sections to process in each batch (default: 20)')
    parser.add_argument('--use-batching', action='store_true', default=True,
                       help='Use batched processing for better performance (default: True)')
    parser.add_argument('--no-batching', action='store_true',
                       help='Disable batched processing (use individual processing)')
    parser.add_argument('--max-chunk-size', type=int, default=32000,
                       help='Maximum characters per chunk for large sections (default: 32000)')
    
    args = parser.parse_args()
    
    # Use DATABASE_URL from environment if --db-url not provided
    db_url = args.db_url or os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: Database URL required. Provide --db-url argument or set DATABASE_URL environment variable")
        sys.exit(1)
    
    if not args.sections_dir.exists():
        print(f"Error: Sections directory {args.sections_dir} does not exist")
        sys.exit(1)
        
    # Determine processing method
    use_batching = args.use_batching and not args.no_batching
    
    try:
        with ContentLoader(db_url, args.openai_api_key, args.max_chunk_size) as loader:
            if use_batching:
                print(f"Using batched processing (batch size: {args.batch_size})")
                loader.load_all_sections_batched(args.sections_dir, args.source_type, args.batch_size)
            else:
                print("Using individual processing")
                loader.load_all_sections(args.sections_dir, args.source_type)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()