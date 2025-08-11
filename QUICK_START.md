# Quick Start Guide

Get up and running with the PDF-to-PostgreSQL MCP Framework in under 10 minutes.

## Prerequisites

- Python 3.8+
- Git
- 2GB+ RAM

## Option 1: Text Extraction Only (Fastest)

Perfect for trying out the PDF extraction capabilities without database setup.

```bash
# 1. Clone and setup
git clone <repository-url>
cd pdf-to-postgresql-mcp
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Extract your first document
python extraction/pdf_extractor.py pdf/sample_document.pdf

# 3. View results
ls output/
```

**Result**: Clean Markdown files with structured content extraction in the `output/` directory.

## Option 2: Full Framework with AI Integration

Complete setup with vector database and AI assistant integration.

### Step 1: Environment Setup
```bash
# Clone and setup Python environment
git clone <repository-url>
cd pdf-to-postgresql-mcp
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section below)
```

### Step 2: Database Setup
```bash
# Install PostgreSQL with pgvector (Ubuntu/Debian example)
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Create database
sudo -u postgres createdb content_database
sudo -u postgres psql content_database < database/schema.sql

# Install database dependencies
cd database/
pip install -r requirements.txt
cd ..
```

### Step 3: Process Your First Document
```bash
# Extract content from PDF
python extraction/pdf_extractor.py pdf/your_document.pdf

# Load into database
python database/load_content.py --sections-dir output/
```

### Step 4: Start AI Integration
```bash
# Install MCP server dependencies
cd mcp_server/
pip install -r requirements.txt

# Start server (for Claude Code - auto-detected)
python content_server.py

# Or configure for Claude Desktop (see mcp_server/README.md)
```

## Configuration

Edit `.env` with your settings:

```bash
# Database connection
DATABASE_URL=postgresql://username:password@localhost/content_database

# OpenAI API key (required for embeddings)
OPENAI_API_KEY=sk-your-api-key-here

# Configure for your content domain
CONTENT_DOMAIN=technical_documentation
CONTENT_TYPES=reference,procedure,concept,guide,example
DEFAULT_SOURCE_TYPE=official
```

## Example Configurations

### Technical Documentation
```bash
CONTENT_DOMAIN=technical_docs
CONTENT_TYPES=reference,procedure,concept,api,guide
```

### Legal Documents
```bash
CONTENT_DOMAIN=legal_docs
CONTENT_TYPES=statute,regulation,case,procedure,form
```

### Research Papers
```bash
CONTENT_DOMAIN=research
CONTENT_TYPES=abstract,methodology,analysis,conclusion,reference
```

## Testing Your Setup

### 1. Verify PDF Extraction
```bash
python extraction/pdf_extractor.py pdf/sample_document.pdf
ls output/  # Should show extracted markdown files
```

### 2. Test Database Connection
```bash
python -c "from core.database import get_db_connection; print('Database connected!' if get_db_connection() else 'Connection failed')"
```

### 3. Verify AI Integration
```bash
cd mcp_server/
python content_server.py &  # Start server in background
# Should start without errors
```

## Next Steps

1. **Process Your Documents**: Use `extraction/pdf_extractor.py` to extract content from your PDFs
2. **Load into Database**: Use `database/load_content.py` to create vector embeddings
3. **Try AI Search**: Use Claude Code or configure Claude Desktop for semantic search
4. **Add Custom Content**: Follow the [Content Management Guide](docs/content_management.md)

## Common Issues

### "No module named 'core'"
```bash
# Make sure you're in the project root directory
cd pdf-to-postgresql-mcp
source venv/bin/activate
```

### "Database connection failed"
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database exists
sudo -u postgres psql -l | grep content_database
```

### "OpenAI API error"
```bash
# Check your API key in .env
cat .env | grep OPENAI_API_KEY

# Verify API key has sufficient credits
```

## Docker Quick Start (Alternative)

For a containerized setup:

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name content-db \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=content_database \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Configure .env to use Docker database
DATABASE_URL=postgresql://postgres:your_password@localhost/content_database
```

## Support

- **Documentation**: See `docs/` directory for detailed guides
- **Configuration**: Check `core/config.py` for all available settings
- **Examples**: Look in `extraction/extract-dolmenwood.py` for implementation examples

Ready to start processing your documents! 🚀