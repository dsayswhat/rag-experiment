# Content Management Guide

A comprehensive guide for adding custom notes, supplementary content, and other materials to the PDF-to-PostgreSQL MCP framework.

## Overview

The vector database system is designed to handle configurable content types including:
- **official**: Content extracted from primary source documents
- **supplementary**: Additional reference materials and extensions
- **notes**: User-generated content, annotations, and custom materials

*Note: Content types are fully configurable via environment variables - these are example classifications.*

## Workflow Options

### 1. MCP Server CRUD Operations

**Best for**: AI-assisted content management and real-time collaboration

#### Implementation Plan
- Extend the MCP server with database operations
- Leverage existing `ContentLoader` class for embedding generation
- Integrate with AI assistants for natural language workflows

#### Planned Methods
```python
# Core CRUD operations
add_note(title: str, content: str, content_types: List[str], tags: List[str]) -> str
update_note(id: str, title: str, content: str, content_types: List[str], tags: List[str]) -> bool
delete_note(id: str) -> bool
get_note(id: str) -> Dict

# Search and discovery
search_notes(query: str, content_types: List[str] = None, tags: List[str] = None, limit: int = 10) -> List[Dict]
semantic_search(query: str, source_types: List[str] = None, limit: int = 10) -> List[Dict]
```

#### Example AI Workflows
```
User: "Claude, I have some research notes about topic X. Read my notes and add them to the database."
Assistant: [Reads markdown file, extracts content, calls add_note() with appropriate classification]

User: "Find all content related to concept Y for my current project."
Assistant: [Calls semantic_search("concept Y") and presents organized results]
```

### 2. File-Based Workflow

**Best for**: Bulk imports, version control, and structured content management

#### Directory Structure
```
content_notes/
├── topics/
│   ├── topic_overview.md
│   └── detailed_analysis.md
├── references/
│   ├── key_concepts.md
│   └── supporting_materials.md
├── custom/
│   ├── extensions.md
│   └── modifications.md
└── project_notes/
    ├── project_01_notes.md
    └── project_02_notes.md
```

#### File Format Standard
```markdown
# Content Title
**Content-Type:** reference, custom
**Tags:** topic, analysis, project_notes, research
**Project:** research_project_alpha
**Date-Created:** 2024-01-15

Main content goes here. Use standard markdown formatting.

## Subsections
- Bullet points
- Tables
- Whatever helps organize the content

### Key Information
| Item | Category | Notes |
|------|----------|-------|
| Concept A | Primary | Core information source |
```

#### Loading Process
```bash
# Load all project notes
python database/load_content.py --sections-dir content_notes/ --source-type notes

# Load specific custom content
python database/load_content.py --sections-dir custom/ --source-type supplementary
```

### 3. Web Interface

**Best for**: Non-technical users and immediate feedback

#### Features
- Simple form with fields for title, content, content types, tags
- Live preview of markdown formatting
- Automatic content classification suggestions
- Direct database insertion with immediate embedding generation
- Search interface for existing content

#### Technical Stack
- Backend: Flask/FastAPI using existing `ContentLoader` class
- Frontend: Simple HTML forms with optional JavaScript enhancements
- Database: Direct integration with existing PostgreSQL schema

### 4. Note-Taking App Integration

**Best for**: Users with existing note-taking workflows

#### Obsidian Integration
- Use frontmatter for metadata
- Sync via file watchers or manual export
- Preserve internal links and graph structure

#### Notion Integration
- Database export to structured format
- API-based sync for real-time updates
- Preserve rich formatting where possible

## Content Classification

### Automatic Classification
The system uses title and content analysis to automatically assign:

**Content Types** (configurable via environment variables):
- `reference` - Primary reference materials
- `procedure` - Step-by-step processes and workflows
- `concept` - Key concepts and definitions
- `analysis` - Analytical content and interpretations
- `example` - Practical examples and case studies
- `guide` - How-to guides and instructions
- `overview` - Summary and introductory content
- `data` - Structured data and datasets
- `notes` - Miscellaneous notes and annotations

**Tags** (automatic + manual):
- Content type duplicates (reference, concept, etc.)
- Thematic tags (technical, analytical, theoretical, practical)
- Project-specific tags (project names, phase numbers)
- Custom organizational tags

### Manual Override
All automatic classifications can be overridden in file headers or API calls:

```markdown
**Content-Type:** reference, supplementary, important
**Tags:** analysis, technical, project_alpha, key_concept
```

## Database Schema Integration

### Core Table Structure
```sql
content_sections (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    source_type TEXT CHECK (source_type IN ('official', 'supplementary', 'notes')),
    source_book TEXT,
    content_type TEXT[],
    tags TEXT[],
    page_range TEXT,
    character_count INTEGER,
    word_count INTEGER,
    file_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Query Examples

#### Semantic Search
```sql
-- Find content similar to a query
SELECT title, content, source_type, tags
FROM content_sections 
ORDER BY embedding <-> '[query_vector]'::vector 
LIMIT 10;
```

#### Filtered Search
```sql
-- Find project notes about concepts
SELECT title, content, tags
FROM content_sections 
WHERE source_type = 'notes'
AND 'concept' = ANY(content_type)
ORDER BY created_at DESC;
```

#### Cross-Source Research
```sql
-- Find official and supplementary reference content
SELECT title, content, source_type
FROM content_sections 
WHERE 'reference' = ANY(content_type)
AND source_type IN ('official', 'supplementary')
ORDER BY source_type, title;
```

## Best Practices

### Content Organization
1. **Use descriptive titles**: "Topic Overview: Market Analysis" vs "Market"
2. **Consistent tagging**: Establish project-specific tag conventions
3. **Link related content**: Reference project phases, related topics
4. **Update existing content**: Use version control or update workflows

### Performance Considerations
1. **Chunk large content**: Break long documents into logical sections
2. **Meaningful embeddings**: Include context in embedding text
3. **Efficient queries**: Use content_type filters before semantic search
4. **Regular maintenance**: Clean up outdated or duplicate content

### Security and Privacy
1. **Public vs private content**: Use tags to separate accessible/restricted content
2. **Backup regularly**: Export content before major changes
3. **Access control**: Consider user permissions for shared projects

## Next Steps

1. **Implement MCP CRUD operations** - Enables AI-assisted workflows
2. **Set up file-based pipeline** - Provides immediate bulk import capability
3. **Create example content** - Templates and samples for common use cases
4. **Build web interface** - User-friendly access for non-technical users
5. **Develop integrations** - Connect with popular note-taking tools

## Troubleshooting

### Common Issues
- **Embedding generation fails**: Check OpenAI API key and quotas
- **Classification incorrect**: Override with manual content-type headers
- **Duplicate content**: Use semantic search to check before adding
- **Performance slow**: Add database indexes, use content_type filters

### Debugging Tools
```bash
# Check database content
psql -d content_database -c "SELECT source_type, COUNT(*) FROM content_sections GROUP BY source_type;"

# Verify embeddings
psql -d content_database -c "SELECT title FROM content_sections WHERE embedding IS NULL;"

# Content classification review
psql -d content_database -c "SELECT DISTINCT unnest(content_type) as types, COUNT(*) FROM content_sections GROUP BY types;"
```