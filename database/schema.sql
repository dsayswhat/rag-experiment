-- Content Database Schema
-- Vector-enabled content storage

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database if it doesn't exist (run manually)
-- CREATE DATABASE content_db;

-- Core content table for sections with vector embeddings
CREATE TABLE content_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI ada-002 dimensions (adjust if using different model)
    
    -- Source metadata
    source_type TEXT NOT NULL DEFAULT 'official',
    source_book TEXT, -- Source document identifier (e.g., 'players_book', 'manual_v2', etc.)
    section_id TEXT, -- Extracted section ID for traceability
    
    -- Content classification  
    content_type TEXT[] DEFAULT '{}', -- User-configurable content types (e.g., ['reference', 'procedure', 'concept'])
    tags TEXT[] DEFAULT '{}', -- Flexible tagging for custom organization
    
    -- Document info
    page_range TEXT, -- "10-12" or "15" for single page
    character_count INTEGER,
    word_count INTEGER,
    
    -- Timestamps and versioning
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- File path for reference
    file_path TEXT -- Path to original markdown file
);

-- Indexes for performance
CREATE INDEX content_sections_embedding_idx ON content_sections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX content_sections_content_type_idx ON content_sections USING GIN (content_type);
CREATE INDEX content_sections_tags_idx ON content_sections USING GIN (tags);
CREATE INDEX content_sections_source_type_idx ON content_sections (source_type);
CREATE INDEX content_sections_source_book_idx ON content_sections (source_book);
CREATE INDEX content_sections_title_idx ON content_sections (title);

-- Full text search index for content
CREATE INDEX content_sections_content_fts_idx ON content_sections USING GIN (to_tsvector('english', content));
CREATE INDEX content_sections_title_fts_idx ON content_sections USING GIN (to_tsvector('english', title));

-- Function to update timestamp on updates
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER content_sections_updated_at
    BEFORE UPDATE ON content_sections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- View for easy content browsing
CREATE VIEW content_overview AS
SELECT 
    id,
    title,
    source_type,
    source_book,
    content_type,
    tags,
    page_range,
    character_count,
    word_count,
    created_at
FROM content_sections
ORDER BY source_book, page_range;

-- Example queries for reference:

-- Semantic search (after embeddings are populated):
-- SELECT title, content, source_book 
-- FROM content_sections 
-- ORDER BY embedding <-> '[your_query_vector]'::vector 
-- LIMIT 10;

-- Filtered search:
-- SELECT title, content 
-- FROM content_sections 
-- WHERE 'reference' = ANY(content_type) 
-- AND source_type = 'official'
-- ORDER BY title;

-- Combined semantic + filter:
-- SELECT title, content, source_book
-- FROM content_sections 
-- WHERE 'procedure' = ANY(content_type)
-- ORDER BY embedding <-> '[your_query_vector]'::vector 
-- LIMIT 5;

-- Full text search:
-- SELECT title, content 
-- FROM content_sections 
-- WHERE to_tsvector('english', content) @@ plainto_tsquery('english', 'castle dragon');