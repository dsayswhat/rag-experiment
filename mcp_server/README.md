# Content MCP Server

Model Context Protocol server for semantic search of PDF content using vector similarity.

## Setup

1. Install dependencies:
```bash
cd mcp_server/
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database URL and OpenAI API key
```

3. Test the server:
```bash
python content_server.py
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "content-search": {
      "command": "python",
      "args": ["/path/to/pdf-to-postgresql-mcp/mcp_server/content_server.py"],
      "env": {
        "DATABASE_URL": "postgresql://username:password@localhost/content_database",
        "OPENAI_API_KEY": "your_openai_api_key"
      }
    }
  }
}
```

## Available Tools

### semantic_search
Search PDF content using semantic similarity.

**Parameters:**
- `query` (required): Search query text
- `content_types` (optional): Filter by content types (reference, concept, procedure, etc.)
- `source_books` (optional): Filter by source documents (reference_manual, guide_book, etc.)
- `limit` (optional): Maximum results (default: 5, max: 20)

**Examples:**
- "How does this process work?"
- "Technical specifications"
- "Key concepts and definitions"