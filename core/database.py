"""
Core database utilities for content management
"""

import psycopg2
import psycopg2.extras
import uuid
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from .config import get_config


class ContentSection:
    """Represents a content section from the database"""
    
    def __init__(self, row: Tuple):
        self.id = row[0]
        self.title = row[1]
        self.content = row[2]
        self.source_type = row[3]
        self.source_book = row[4]
        self.section_id = row[5]
        self.content_type = row[6] or []
        self.tags = row[7] or []
        self.page_range = row[8]
        self.character_count = row[9]
        self.word_count = row[10]
        self.file_path = row[11] if len(row) > 11 else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "source_type": self.source_type,
            "source_book": self.source_book,
            "section_id": self.section_id,
            "content_type": self.content_type,
            "tags": self.tags,
            "page_range": self.page_range,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "file_path": self.file_path
        }


@contextmanager
def get_db_connection():
    """Get a database connection with automatic cleanup"""
    config = get_config()
    conn = None
    try:
        conn = psycopg2.connect(config.database_url)
        yield conn
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor(connection=None):
    """Get a database cursor with automatic cleanup"""
    if connection:
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()


def execute_query(
    sql: str, 
    params: Optional[List] = None,
    fetch_all: bool = True
) -> List[Tuple]:
    """Execute a database query and return results"""
    with get_db_connection() as conn:
        with get_db_cursor(conn) as cursor:
            cursor.execute(sql, params or [])
            if fetch_all:
                return cursor.fetchall()
            else:
                return cursor.fetchone()


def semantic_search_query(
    query_embedding: List[float],
    content_types: Optional[List[str]] = None,
    source_books: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    limit: int = 5
) -> List[ContentSection]:
    """
    Perform semantic search on content_sections table
    
    Args:
        query_embedding: Vector embedding for the search query
        content_types: Filter by content types (spell, location, rule, etc.)
        source_books: Filter by source books (players_book, campaign_book, etc.)
        source_types: Filter by source types (dolmenwood_official, homebrew, etc.)
        limit: Maximum number of results to return
    
    Returns:
        List of ContentSection objects ordered by relevance
    """
    # Build SQL query with filters
    sql_parts = [
        "SELECT id, title, content, source_type, source_book, section_id,",
        "       content_type, tags, page_range, character_count, word_count, file_path",
        "FROM content_sections",
        "WHERE 1=1"
    ]
    
    params = []
    
    # Add content type filter
    if content_types:
        sql_parts.append("AND content_type && %s")
        params.append(content_types)
    
    # Add source book filter
    if source_books:
        sql_parts.append("AND source_book = ANY(%s)")
        params.append(source_books)
    
    # Add source type filter
    if source_types:
        sql_parts.append("AND source_type = ANY(%s)")
        params.append(source_types)
    
    # Add vector similarity ordering
    sql_parts.extend([
        "ORDER BY embedding <-> %s::vector",
        f"LIMIT {limit}"
    ])
    
    params.append(query_embedding)
    
    sql = " ".join(sql_parts)
    
    # Execute query
    rows = execute_query(sql, params)
    return [ContentSection(row) for row in rows]


def get_content_by_section_id(section_id: str, source_book: Optional[str] = None) -> Optional[ContentSection]:
    """Get content by section ID (useful for hex lookups)"""
    sql = "SELECT id, title, content, source_type, source_book, section_id, content_type, tags, page_range, character_count, word_count, file_path FROM content_sections WHERE section_id = %s"
    params = [section_id]
    
    if source_book:
        sql += " AND source_book = %s"
        params.append(source_book)
    
    rows = execute_query(sql, params)
    if rows:
        return ContentSection(rows[0])
    return None


def get_multiple_sections(section_ids: List[str], source_book: Optional[str] = None) -> List[ContentSection]:
    """Get multiple content sections by section IDs"""
    if not section_ids:
        return []
    
    sql = "SELECT id, title, content, source_type, source_book, section_id, content_type, tags, page_range, character_count, word_count, file_path FROM content_sections WHERE section_id = ANY(%s)"
    params = [section_ids]
    
    if source_book:
        sql += " AND source_book = %s"
        params.append(source_book)
    
    rows = execute_query(sql, params)
    return [ContentSection(row) for row in rows]


def get_content_by_id(content_id: str) -> Optional[ContentSection]:
    """Get content by UUID ID"""
    sql = "SELECT id, title, content, source_type, source_book, section_id, content_type, tags, page_range, character_count, word_count, file_path FROM content_sections WHERE id = %s"
    rows = execute_query(sql, [content_id])
    if rows:
        return ContentSection(rows[0])
    return None


def get_content_by_title(title: str, exact_match: bool = True) -> List[ContentSection]:
    """Get content by title (exact match or partial match)"""
    if exact_match:
        sql = "SELECT id, title, content, source_type, source_book, section_id, content_type, tags, page_range, character_count, word_count, file_path FROM content_sections WHERE title = %s"
        params = [title]
    else:
        sql = "SELECT id, title, content, source_type, source_book, section_id, content_type, tags, page_range, character_count, word_count, file_path FROM content_sections WHERE title ILIKE %s ORDER BY title"
        params = [f"%{title}%"]
    
    rows = execute_query(sql, params)
    return [ContentSection(row) for row in rows]


def search_content_titles(query: str, limit: int = 10) -> List[ContentSection]:
    """Search for content by title (partial match, returns limited results)"""
    sql = """
        SELECT id, title, content, source_type, source_book, section_id, content_type, tags, 
               page_range, character_count, word_count, file_path 
        FROM content_sections 
        WHERE title ILIKE %s 
        ORDER BY 
            CASE WHEN title ILIKE %s THEN 1 ELSE 2 END,  -- Exact matches first
            LENGTH(title),  -- Shorter titles first
            title
        LIMIT %s
    """
    search_term = f"%{query}%"
    exact_term = query
    rows = execute_query(sql, [search_term, exact_term, limit])
    return [ContentSection(row) for row in rows]


def update_content_section(
    content_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    content_type: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source_book: Optional[str] = None,
    section_id: Optional[str] = None,
    page_range: Optional[str] = None,
    generate_embedding: bool = False
) -> bool:
    """
    Update an existing content section
    
    Args:
        content_id: UUID of the content section to update
        title: New title (optional)
        content: New content (optional)
        content_type: New content types array (optional)
        tags: New tags array (optional)
        source_book: New source book (optional)
        section_id: New section ID (optional)
        page_range: New page range (optional)
        generate_embedding: Whether to generate new embedding (requires content update)
    
    Returns:
        True if update was successful, False if content not found
    """
    # Build update fields dynamically
    update_fields = []
    params = []
    
    if title is not None:
        update_fields.append("title = %s")
        params.append(title)
    
    if content is not None:
        update_fields.append("content = %s")
        update_fields.append("character_count = %s")
        update_fields.append("word_count = %s")
        params.extend([content, len(content), len(content.split())])
    
    if content_type is not None:
        update_fields.append("content_type = %s")
        params.append(content_type)
    
    if tags is not None:
        update_fields.append("tags = %s")
        params.append(tags)
    
    if source_book is not None:
        update_fields.append("source_book = %s")
        params.append(source_book)
    
    if section_id is not None:
        update_fields.append("section_id = %s")
        params.append(section_id)
    
    if page_range is not None:
        update_fields.append("page_range = %s")
        params.append(page_range)
    
    if generate_embedding and content is not None:
        # Note: This would require importing openai_utils, which would create a circular import
        # For now, we'll handle embedding generation in the MCP server
        pass
    
    if not update_fields:
        return False  # Nothing to update
    
    # Add the ID parameter for WHERE clause
    params.append(content_id)
    
    sql = f"""
        UPDATE content_sections 
        SET {', '.join(update_fields)}
        WHERE id = %s
    """
    
    with get_db_connection() as conn:
        with get_db_cursor(conn) as cursor:
            cursor.execute(sql, params)
            rows_affected = cursor.rowcount
            conn.commit()
            return rows_affected > 0


def delete_content_section(content_id: str) -> bool:
    """
    Delete a content section by ID
    
    Args:
        content_id: UUID of the content section to delete
    
    Returns:
        True if deletion was successful, False if content not found
    """
    sql = "DELETE FROM content_sections WHERE id = %s"
    
    with get_db_connection() as conn:
        with get_db_cursor(conn) as cursor:
            cursor.execute(sql, [content_id])
            rows_affected = cursor.rowcount
            conn.commit()
            return rows_affected > 0


def create_content_section(
    title: str,
    content: str,
    content_type: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source_book: Optional[str] = None,
    section_id: Optional[str] = None,
    page_range: Optional[str] = None,
    source_type: str = "campaign_notes",
    embedding: Optional[List[float]] = None
) -> Optional[str]:
    """
    Create a new content section
    
    Args:
        title: Title of the content section (required)
        content: Content text (required)
        content_type: Content types array (optional, defaults to empty list)
        tags: Tags array (optional, defaults to empty list)
        source_book: Source book identifier (optional)
        section_id: Section identifier (optional)
        page_range: Page range (optional)
        source_type: Source type (defaults to "campaign_notes")
        embedding: Vector embedding (optional, should be generated separately)
    
    Returns:
        UUID of the created content section, or None if creation failed
    """
    # Generate UUID for the new section
    section_uuid = str(uuid.uuid4())
    
    # Calculate content stats
    character_count = len(content)
    word_count = len(content.split())
    
    # Default empty arrays if not provided
    if content_type is None:
        content_type = []
    if tags is None:
        tags = []
    
    sql = """
        INSERT INTO content_sections (
            id, title, content, source_type, source_book, section_id,
            content_type, tags, page_range, character_count, word_count, embedding
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    params = [
        section_uuid, title, content, source_type, source_book, section_id,
        content_type, tags, page_range, character_count, word_count, embedding
    ]
    
    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return section_uuid
    except Exception as e:
        print(f"Error creating content section: {e}")
        return None


def get_content_stats() -> Dict[str, Any]:
    """Get statistics about the content database"""
    stats = {}
    
    # Total sections
    result = execute_query("SELECT COUNT(*) FROM content_sections", fetch_all=False)
    stats['total_sections'] = result[0] if result else 0
    
    # Sections by source book
    rows = execute_query("""
        SELECT source_book, COUNT(*) 
        FROM content_sections 
        GROUP BY source_book 
        ORDER BY source_book
    """)
    stats['by_source_book'] = dict(rows)
    
    # Content types
    rows = execute_query("""
        SELECT unnest(content_type) as type, COUNT(*) 
        FROM content_sections 
        WHERE content_type IS NOT NULL
        GROUP BY type 
        ORDER BY count DESC
    """)
    stats['by_content_type'] = dict(rows)
    
    return stats