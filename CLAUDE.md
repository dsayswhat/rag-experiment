# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: Getting Started
⚠️ **ALWAYS READ THE DOCUMENTATION FIRST** when starting a new chat session. Use this command to understand the current project state:
- Read `docs/project_status.md` for overall progress and priorities
- Read `docs/content_management.md` for content workflows
- Read `docs/extraction_guide.md` and `docs/technical_notes.md` for extraction details
- Read `database/README.md` and `mcp_server/README.md` for component-specific information

## Repository Overview

This is a generic PDF-to-PostgreSQL MCP framework for extracting, storing, and searching document content using vector databases. Originally developed for tabletop RPG content management, it has been refactored into a universal system suitable for any PDF-based documentation, reference materials, or knowledge management workflows.

## Repository Structure

- **archive/**: Archived example content (original development materials)
- **core/**: Centralized framework configuration and utilities (renamed from shared/)
- **extraction/**: PDF text extraction system (renamed from scripts/)
- **database/**: PostgreSQL + pgvector database implementation
- **mcp_server/**: Model Context Protocol server for AI assistant integration
- **output/**: Generated markdown sections from PDF extraction
- **docs/**: Framework documentation and guides

## Core Configuration System

### Location
`core/` - Centralized framework configuration and utilities used by all project components

### Key Modules
- **`config.py`**: Environment-based configuration management with automatic .env loading
- **`database.py`**: Database connection utilities, query helpers, and ContentSection model
- **`openai_utils.py`**: OpenAI API integration for embeddings (sync/async, batching, averaging)

### Environment Setup
- **Configuration**: Copy `.env.example` to `.env` and configure your database URL and OpenAI API key
- **Dependencies**: Each component has its own requirements.txt that includes shared dependencies
- **Python 3.8+** required

## Developer Notes
- Remember to run `source venv/bin/activate` before you try to test python scripts in this project.

## PDF Extraction System

### Location
`extraction/` - Complete system for extracting high-quality text from PDFs using PyMuPDF4LLM

### Key Scripts
- **`extract-dolmenwood.py`**: Example page-based extraction with flexible page ranges
- **`pdf_extractor.py`**: Generic memory-efficient section-based extraction using header detection

### Usage Examples
```bash
# Page-based extraction (example implementation)
python3 extraction/extract-dolmenwood.py data/sample_document.pdf --pages 15 16

# Section-based extraction (semantic chunks)
python3 extraction/pdf_extractor.py data/sample_document.pdf --start-page 15

# Full document processing
python3 extraction/pdf_extractor.py data/sample_document.pdf
```

### Output
- **Markdown files**: Structured text with semantic formatting (`output/`)
- **JSON metadata**: Extraction statistics and page information
- **Section files**: Semantic content chunks for vector storage
- **PostgreSQL ready**: Optimized for database ingestion

## Content Management

The framework supports flexible content organization:
- **Source documents**: Original PDFs to be processed
- **Extracted content**: Structured markdown outputs
- **Content types**: User-configurable classification system
- **Metadata tracking**: Source, tags, and processing information

## Common File Operations

When organizing content:
- Use descriptive filenames that indicate content type
- Group related documents logically
- Maintain consistent directory structure
- Tag content appropriately for searchability

## File Formats

- **PDFs**: Source documents for processing
- **Markdown**: Extracted text content with semantic structure
- **JSON**: Metadata and extraction statistics
- **SQL**: Database schema and query files
- **Python**: Framework code and utilities

## PDF Extraction Technical Notes

### PyMuPDF4LLM Selection
After comprehensive testing, PyMuPDF4LLM was chosen over alternatives:
- **Superior quality**: 99+ more characters extracted vs basic PyMuPDF
- **No text duplication**: Avoids issues found in pdfplumber
- **Semantic structure**: Automatic Markdown formatting
- **LLM optimization**: Designed for AI/ML workflows

### Section Detection
- **Headers**: Uses `##### Title` patterns to identify section boundaries
- **Memory efficiency**: PDF open/close per section
- **Natural boundaries**: Never cuts off mid-section
- **Vector ready**: Creates semantic chunks perfect for PostgreSQL storage

### Current Status
✅ Production-ready text extraction system  
✅ Section-based semantic chunking with configurable content types  
✅ Memory-efficient processing  
✅ PostgreSQL schema with pgvector support implemented  
✅ Database loading scripts with OpenAI embedding integration  
✅ Database successfully populated and tested with vector search  
✅ Generic configuration system for all components  
✅ MCP server with semantic search capability implemented  
✅ MCP server local testing completed  
✅ Claude Code integration operational  
✅ Framework refactoring to generic system completed  

### Next Phase Priorities
1. **MCP CRUD Operations** (HIGH) - Add create/update/delete capabilities for content management
2. **Extraction Quality Evaluation** (HIGH) - Assess whether custom PDF extraction would improve content quality vs current PyMuPDF4LLM approach
3. **Content Restructuring** (MEDIUM) - Implement granular rechunking strategy
4. **Example Configurations** (MEDIUM) - Create sample configs for different content domains
5. **AI Assistant Integration** (LOW) - Expand beyond Claude Code to other platforms

[... rest of the file remains unchanged ...]