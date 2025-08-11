# PDF-to-PostgreSQL MCP Framework

A complete, domain-agnostic framework for extracting high-quality text from PDFs, storing it in a searchable vector database, and providing AI assistant integration through a Model Context Protocol server.

## Overview

**Status: OPERATIONAL** - Complete system from PDF extraction to AI assistant integration.

This framework provides a production-ready solution for PDF-based content management with AI integration:

1. **Text Extraction**: Clean, structured text extraction from any PDF documents
2. **Semantic Chunking**: Intelligent section-based content organization  
3. **Vector Database**: PostgreSQL + pgvector storage with OpenAI embeddings
4. **Content Classification**: Configurable categorization system for any content domain
5. **MCP Server**: Model Context Protocol server providing semantic search for AI assistants
6. **Modular Architecture**: Centralized configuration and utilities across all components

Perfect for technical documentation, research papers, legal documents, manuals, and any PDF-based knowledge management workflows with AI assistant integration.

## Key Features

### Text Extraction
- **High-Quality Extraction**: Uses PyMuPDF4LLM for superior text extraction compared to traditional methods
- **Markdown Formatting**: Outputs structured Markdown with headers, bold text, and proper formatting
- **Semantic Chunking**: Intelligent section-based organization
- **Batch Processing**: Handle multiple PDFs in a single operation

### Vector Database  
- **PostgreSQL + pgvector**: Production-ready vector storage with semantic search
- **OpenAI Embeddings**: High-quality text embeddings using text-embedding-ada-002
- **Configurable Classification**: User-defined content types and categories
- **Multi-Source Support**: Official documents, supplementary materials, and custom notes

### AI Integration
- **MCP Server**: Claude Code and Claude Desktop compatible
- **Semantic Search**: Vector similarity search with filtering capabilities
- **CRUD Operations**: Create, read, update content through AI assistants
- **Configurable Domains**: Adapt for any content type or industry

## Quick Start

### 1. Text Extraction Only

```bash
# Clone and setup extraction environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Extract document sections
python extraction/pdf_extractor.py data/sample_document.pdf
```

### 2. Full Vector Database Setup

See **[Database Setup Guide](database/README.md)** for complete PostgreSQL + pgvector installation and content loading.

```bash
# Quick version (after PostgreSQL setup):
cd database/
pip install -r requirements.txt
cp .env.example .env  # Edit with your database URL and OpenAI API key
python load_content.py --sections-dir ../output/
```

### 3. AI Assistant Integration

See **[MCP Server Guide](mcp_server/README.md)** for Claude integration setup.

```bash
# Start MCP server
cd mcp_server/
pip install -r requirements.txt
python content_server.py
```

## Architecture

### Directory Structure
```
pdf-to-postgresql-mcp/
├── core/                    # Framework utilities
│   ├── config.py           # Environment configuration
│   ├── database.py         # Database utilities
│   └── openai_utils.py     # AI integration
├── extraction/             # PDF processing
│   ├── pdf_extractor.py    # Generic section extraction
│   └── extract-dolmenwood.py  # Example implementation
├── database/               # Vector database
│   ├── schema.sql          # PostgreSQL schema
│   ├── load_content.py     # Content loading
│   └── README.md           # Setup guide
├── mcp_server/             # AI integration
│   ├── content_server.py   # MCP server
│   └── README.md           # Integration guide
├── docs/                   # Documentation
└── output/                 # Extracted content
```

## Configuration

### Content Types
The framework supports fully configurable content types via environment variables:

```bash
# Example configurations for different domains
CONTENT_TYPES="reference,procedure,concept,analysis,example"  # Technical docs
CONTENT_TYPES="statute,regulation,case,procedure,form"        # Legal docs
CONTENT_TYPES="spell,location,rule,lore,equipment"            # Gaming docs
```

### Environment Setup
```bash
# Copy and configure environment
cp .env.example .env

# Edit .env with your settings:
DATABASE_URL="postgresql://user:pass@localhost/content_database"
OPENAI_API_KEY="your_openai_api_key"
CONTENT_DOMAIN="technical_documentation"
CONTENT_TYPES="reference,procedure,concept,guide,example"
```

## Usage Examples

### Basic Text Extraction
```bash
# Extract all content from a document
python extraction/pdf_extractor.py data/technical_manual.pdf

# Extract specific pages
python extraction/pdf_extractor.py data/manual.pdf --pages 15 16 17

# Batch process multiple documents
python extraction/pdf_extractor.py data/*.pdf
```

### Database Operations
```bash
# Load extracted content into database
python database/load_content.py --sections-dir output/

# Load with custom source type
python database/load_content.py --sections-dir notes/ --source-type supplementary
```

### AI Assistant Integration
```bash
# Start MCP server for AI integration
python mcp_server/content_server.py

# Use with Claude Code (server runs automatically)
# Or configure for Claude Desktop (see mcp_server/README.md)
```

## Content Management

The framework supports multiple content workflows:

1. **PDF Extraction**: Process existing documents
2. **Custom Content**: Add notes and supplementary materials
3. **AI Integration**: Search and manage content through AI assistants
4. **Version Control**: Track changes and updates

See [Content Management Guide](docs/content_management.md) for detailed workflows.

## Use Cases

### Technical Documentation
- API documentation processing
- User manual digitization
- Knowledge base creation
- Support documentation search

### Research & Academic
- Research paper analysis
- Literature review assistance
- Citation and reference management
- Academic content organization

### Legal & Compliance
- Regulatory document processing
- Legal research assistance
- Policy and procedure management
- Compliance documentation

### Enterprise Knowledge Management
- Internal documentation systems
- Training material digitization
- Procedural knowledge capture
- Expert system development

## Performance

- **Processing Speed**: ~1-2 seconds per page for text extraction
- **Memory Efficiency**: Processes documents incrementally
- **Database Performance**: Vector search with configurable indexing
- **AI Integration**: Batched embedding generation for efficiency

## Documentation

- **[Installation Guide](database/README.md)** - Complete setup instructions
- **[Extraction Guide](docs/extraction_guide.md)** - PDF processing details
- **[Content Management](docs/content_management.md)** - Workflow documentation
- **[Technical Notes](docs/technical_notes.md)** - Implementation details
- **[MCP Integration](mcp_server/README.md)** - AI assistant setup

## Requirements

- **Python 3.8+**
- **PostgreSQL 12+** with pgvector extension
- **OpenAI API key** for embeddings
- **2GB+ RAM** for processing large documents

## Framework Design

This framework was designed with the following principles:

1. **Domain Agnostic**: Works with any PDF-based content
2. **Modular Architecture**: Composable components for different use cases
3. **Production Ready**: Robust error handling and performance optimization
4. **AI Native**: Built for AI assistant integration from the ground up
5. **Extensible**: Easy to customize and extend for specific needs

## Contributing

The framework is designed to be easily extended and customized. Key extension points:

- **Content Classification**: Add custom content type detection
- **Extraction Methods**: Implement domain-specific extraction logic
- **AI Integration**: Extend MCP server with additional capabilities
- **Database Schema**: Add custom metadata fields and indexes

## License

This project is provided as-is for educational and development purposes. Please ensure compliance with relevant licenses for dependencies and content sources.