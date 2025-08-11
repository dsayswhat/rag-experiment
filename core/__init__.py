"""
Shared utilities for Dolmenwood project
"""

from .config import Config, get_config, reset_config
from .database import ContentSection, get_db_connection, get_db_cursor, semantic_search_query, get_content_by_section_id, get_multiple_sections, get_content_stats, get_content_by_id, get_content_by_title, search_content_titles, update_content_section, delete_content_section, create_content_section
from .openai_utils import get_openai_client, get_embedding_async, get_embedding_sync, get_embeddings_batch_sync, average_embeddings

__all__ = [
    # Config
    'Config', 'get_config', 'reset_config',
    # Database
    'ContentSection', 'get_db_connection', 'get_db_cursor', 'semantic_search_query', 
    'get_content_by_section_id', 'get_multiple_sections', 'get_content_stats',
    'get_content_by_id', 'get_content_by_title', 'search_content_titles',
    'update_content_section', 'delete_content_section', 'create_content_section',
    # OpenAI
    'get_openai_client', 'get_embedding_async', 'get_embedding_sync', 
    'get_embeddings_batch_sync', 'average_embeddings'
]