# Database Setup

Vector-enabled PostgreSQL database for PDF content with semantic search capabilities.

## Prerequisites

- PostgreSQL 12+ with pgvector extension
- Python 3.8+
- OpenAI API key

## Setup

### 1. Install PostgreSQL and pgvector

**Ubuntu/Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**macOS (Homebrew):**
```bash
brew install postgresql pgvector
```

**Or use Docker:**
```bash
docker run -d \
  --name content-db \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=content_database \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 2. Create Database

```bash
sudo -u postgres createdb content_database
sudo -u postgres psql content_database < database/schema.sql
```

### 3. Install Python Dependencies

```bash
cd database/
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database URL and OpenAI API key
```

### 5. Load Content

```bash
# Recommended: Use environment variables (.env file)
python database/load_content.py --sections-dir output/

# Or specify database URL directly
python database/load_content.py \
  --sections-dir output/ \
  --db-url "postgresql://username:password@localhost/content_database"

# Performance tuning options
python database/load_content.py \
  --sections-dir output/ \
  --batch-size 10  # Smaller batches for rate-limited APIs

# Handle large sections (oversized content blocks)
python database/load_content.py \
  --sections-dir output/ \
  --max-chunk-size 16000  # Smaller chunks for memory/token limits

# Disable batching (fallback to individual processing)
python database/load_content.py \
  --sections-dir output/ \
  --no-batching
```

## Usage Examples

### Basic Content Search

```python
import psycopg2
import openai

# Connect to database
conn = psycopg2.connect("postgresql://user:pass@localhost/content_database")

# Generate query embedding
client = openai.OpenAI()
query = "relevant search term"
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=query
)
query_vector = response.data[0].embedding

# Semantic search
cursor = conn.cursor()
cursor.execute("""
    SELECT title, content, source_book 
    FROM content_sections 
    ORDER BY embedding <-> %s::vector 
    LIMIT 5
""", (query_vector,))

results = cursor.fetchall()
for title, content, book in results:
    print(f"{title} ({book})")
    print(content[:200] + "...")
    print()
```

### Filtered Search

```sql
-- All reference content from official sources
SELECT title, content_type, tags 
FROM content_sections 
WHERE 'reference' = ANY(content_type) 
AND source_type = 'official'
ORDER BY title;

-- Concepts with semantic similarity
SELECT title, content, page_range
FROM content_sections 
WHERE 'concept' = ANY(content_type)
ORDER BY embedding <-> '[your_query_vector]'::vector 
LIMIT 10;
```

### Content Overview

```sql
-- Content summary by type
SELECT 
    unnest(content_type) as type,
    COUNT(*) as count
FROM content_sections 
GROUP BY type 
ORDER BY count DESC;

-- Books and section counts
SELECT source_book, COUNT(*) as sections
FROM content_sections 
GROUP BY source_book 
ORDER BY source_book;
```

## Database Schema

### content_sections Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | TEXT | Section title |
| content | TEXT | Full section content |
| embedding | VECTOR(1536) | OpenAI embedding |
| source_type | TEXT | 'dolmenwood_official', 'homebrew', 'campaign_notes' |
| source_book | TEXT | Book name (e.g., 'players_book') |
| section_id | TEXT | Original section identifier |
| content_type | TEXT[] | Content classifications |
| tags | TEXT[] | Searchable tags |
| page_range | TEXT | Source page numbers |
| character_count | INTEGER | Section character count |
| word_count | INTEGER | Section word count |
| file_path | TEXT | Original file location |

## Performance Notes

### Loading Performance
- **Batched processing**: Default batch size of 20 sections reduces database transactions significantly
- **Batched embeddings**: OpenAI API calls reduced through efficient batching  
- **Smart text chunking**: Large sections (>32K chars) are split at sentence boundaries and embeddings averaged
- **Automatic fallback**: Individual processing used if batch operations fail
- **Configurable batch size**: Adjust `--batch-size` for your rate limits and memory constraints
- **Configurable chunk size**: Adjust `--max-chunk-size` for token limits (default: 32K chars ≈ 8K tokens)

### Database Performance
- Vector search uses ivfflat index (adjust `lists` parameter for your data size)
- For large datasets, consider using HNSW index instead
- Content types and tags use GIN indexes for fast array searches
- Full-text search available via PostgreSQL's built-in tsvector

### Large Section Handling
- **Chunking threshold**: Sections >32K characters are automatically chunked
- **Boundary preservation**: Chunks split at sentence endings or paragraph breaks when possible  
- **Embedding averaging**: Multiple chunk embeddings are averaged into a single section embedding
- **Examples from processing**:
  - Large reference section: 76K chars → 3 chunks → averaged embedding
  - Medium content section: 36K chars → 2 chunks → averaged embedding
  - Most sections: <32K chars → single embedding (no chunking)

### Loading Time Comparison
- **Individual processing**: ~2-5 minutes for 77 sections (rate limited by API calls)
- **Batched processing**: ~30-60 seconds for 77 sections (significant improvement)
- **Large sections**: Additional ~10-30 seconds for chunking (but preserves full content)

## Troubleshooting

**pgvector not found:**
- Ensure pgvector extension is installed and enabled
- Run `CREATE EXTENSION vector;` in your database

**OpenAI API errors:**
- Check your API key and quota
- Consider rate limiting for large imports

**Memory issues:**
- Process sections in batches for very large datasets
- Adjust vector index parameters