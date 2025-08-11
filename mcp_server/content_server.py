#!/usr/bin/env python3
"""
Content MCP Server
Provides semantic search capabilities for content collections
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime # Import datetime to see timestamps
from typing import List, Optional, Dict, Any
from mcp.server import NotificationOptions

# Add the parent directory to the path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_config, ContentSection, semantic_search_query, get_embedding_async, get_content_by_id, get_content_by_title, get_content_by_section_id, search_content_titles, update_content_section, delete_content_section, create_content_section
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

# Get configuration
config = get_config()

# Initialize MCP server
app = Server(config.mcp_server_name)


async def semantic_search(
    query: str,
    content_types: Optional[List[str]] = None,
    source_books: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    limit: int = 5
) -> List[ContentSection]:
    """
    Perform semantic search on content using core utilities
    """
    # --> Add debugging prints here <--
    print(f"[{datetime.now()}] DEBUG: Starting semantic search for query: '{query}'", file=sys.stderr)
    
    # Generate embedding for the query
    print(f"[{datetime.now()}] DEBUG: Generating embedding...", file=sys.stderr)
    sys.stderr.flush() # Ensure the message prints immediately
    
    query_embedding = await get_embedding_async(query)
    
    print(f"[{datetime.now()}] DEBUG: Embedding generated. Querying database...", file=sys.stderr)
    sys.stderr.flush()
    
    # Use shared database function
    results = semantic_search_query(
        query_embedding=query_embedding,
        content_types=content_types,
        source_books=source_books,
        source_types=source_types,
        limit=limit
    )
    
    print(f"[{datetime.now()}] DEBUG: Database query complete. Found {len(results)} results.", file=sys.stderr)
    sys.stderr.flush()
    
    return results



@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="semantic_search",
            description="Search content using semantic similarity. Returns relevant sections based on the meaning of your query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'how to process requests', 'error handling', 'configuration settings')"
                    },
                    "content_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"Filter by content types: {', '.join(config.content_types)}"
                    },
                    "source_books": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Filter by source books (e.g., manual_v1, reference_guide, api_docs)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {config.default_search_limit}, max: {config.max_search_limit})",
                        "minimum": 1,
                        "maximum": config.max_search_limit
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_content",
            description="Retrieve specific content by ID, section ID, or title. Use this when you need to get exact content rather than search.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "UUID of the content section"
                    },
                    "section_id": {
                        "type": "string", 
                        "description": "Section identifier (e.g., chapter numbers, topic codes, section names)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Exact or partial title to search for"
                    },
                    "exact_match": {
                        "type": "boolean",
                        "description": "For title searches, whether to match exactly (default: false for partial matching)",
                        "default": False
                    },
                    "source_book": {
                        "type": "string",
                        "description": "Filter by source book (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "For title searches, maximum results to return (default: 5)",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5
                    }
                } #,
                #"oneOf": [
                #    {"required": ["id"]},
                #    {"required": ["section_id"]},
                #    {"required": ["title"]}
                # ]
            }
        ),
        Tool(
            name="update_content",
            description="Update an existing content section. Allows editing title, content, tags, content types, and other metadata. Can regenerate embeddings when content is changed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "UUID of the content section to update (required)"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the content section"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content text"
                    },
                    "content_type": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"New content types: {', '.join(config.content_types)}"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags for flexible categorization"
                    },
                    "source_book": {
                        "type": "string",
                        "description": "New source book identifier"
                    },
                    "section_id": {
                        "type": "string",
                        "description": "New section identifier"
                    },
                    "page_range": {
                        "type": "string",
                        "description": "New page range (e.g., '10-12' or '15')"
                    },
                    "regenerate_embedding": {
                        "type": "boolean",
                        "description": "Whether to regenerate the vector embedding (automatically true if content is updated)",
                        "default": False
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="create_content",
            description="Create a new content section in the database. Useful for adding notes, custom content, or other materials.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the content section (required)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content text (required)"
                    },
                    "content_type": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"Content types: {', '.join(config.content_types)}"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for flexible categorization"
                    },
                    "source_book": {
                        "type": "string",
                        "description": "Source book identifier (optional, defaults to 'campaign_notes')"
                    },
                    "section_id": {
                        "type": "string",
                        "description": "Section identifier (e.g., hex coordinates, spell name)"
                    },
                    "page_range": {
                        "type": "string",
                        "description": "Page range (e.g., '10-12' or '15')"
                    },
                    "source_type": {
                        "type": "string",
                        "description": "Source type (defaults to 'campaign_notes'). Options: dolmenwood_official, homebrew, campaign_notes"
                    }
                },
                "required": ["title", "content"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    if name == "semantic_search":
         # --> And a print here for the handler <--
        print(f"[{datetime.now()}] DEBUG: Tool 'semantic_search' called.", file=sys.stderr)
        sys.stderr.flush()
        
        query = arguments.get("query")
        if not query:
            return [TextContent(type="text", text="Error: query parameter is required")]
        
        content_types = arguments.get("content_types")
        source_books = arguments.get("source_books") 
        limit = min(arguments.get("limit", config.default_search_limit), config.max_search_limit)
        
        try:
            # Perform semantic search
            results = await semantic_search(
                query=query,
                content_types=content_types,
                source_books=source_books,
                limit=limit
            )
            
            if not results:
                return [TextContent(type="text", text=f"No results found for query: '{query}'")]
            
            # Format results
            response_parts = [f"Found {len(results)} result(s) for: '{query}'\n"]
            
            for i, section in enumerate(results, 1):
                response_parts.append(f"## Result {i}: {section.title}")
                response_parts.append(f"**Source:** {section.source_book} ({section.page_range})")
                if section.content_type:
                    response_parts.append(f"**Content Type:** {', '.join(section.content_type)}")
                if section.tags:
                    response_parts.append(f"**Tags:** {', '.join(section.tags)}")
                response_parts.append("")
                response_parts.append(section.content)
                response_parts.append("\n" + "="*50 + "\n")
            
            return [TextContent(type="text", text="\n".join(response_parts))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Search failed: {str(e)}")]
    
    elif name == "get_content":
        print(f"[{datetime.now()}] DEBUG: Tool 'get_content' called.", file=sys.stderr)
        sys.stderr.flush()
        
        # Determine which search method to use
        content_id = arguments.get("id")
        section_id = arguments.get("section_id") 
        title = arguments.get("title")
        exact_match = arguments.get("exact_match", False)
        source_book = arguments.get("source_book")
        limit = arguments.get("limit", 5)
        
        try:
            results = []
            
            if content_id:
                # Search by UUID
                result = get_content_by_id(content_id)
                if result:
                    results = [result]
                    
            elif section_id:
                # Search by section ID
                result = get_content_by_section_id(section_id, source_book)
                if result:
                    results = [result]
                    
            elif title:
                # Search by title
                if exact_match:
                    results = get_content_by_title(title, exact_match=True)
                else:
                    results = search_content_titles(title, limit=limit)
                    # Filter by source book if specified
                    if source_book:
                        results = [r for r in results if r.source_book == source_book]
            
            else:
                return [TextContent(type="text", text="Error: Must provide id, section_id, or title")]
            
            if not results:
                search_type = "ID" if content_id else "section ID" if section_id else "title"
                search_value = content_id or section_id or title
                return [TextContent(type="text", text=f"No content found for {search_type}: '{search_value}'")]
            
            # Format results - reuse the same formatting as semantic search
            if len(results) == 1:
                section = results[0]
                response_parts = [f"# {section.title}"]
                response_parts.append(f"**Source:** {section.source_book} ({section.page_range})")
                response_parts.append(f"**ID:** {section.id}")
                if section.section_id:
                    response_parts.append(f"**Section ID:** {section.section_id}")
                if section.content_type:
                    response_parts.append(f"**Content Type:** {', '.join(section.content_type)}")
                if section.tags:
                    response_parts.append(f"**Tags:** {', '.join(section.tags)}")
                response_parts.append("")
                response_parts.append(section.content)
                
                return [TextContent(type="text", text="\n".join(response_parts))]
            else:
                # Multiple results
                response_parts = [f"Found {len(results)} result(s):\n"]
                
                for i, section in enumerate(results, 1):
                    response_parts.append(f"## Result {i}: {section.title}")
                    response_parts.append(f"**Source:** {section.source_book} ({section.page_range})")
                    response_parts.append(f"**ID:** {section.id}")
                    if section.section_id:
                        response_parts.append(f"**Section ID:** {section.section_id}")
                    if section.content_type:
                        response_parts.append(f"**Content Type:** {', '.join(section.content_type)}")
                    if section.tags:
                        response_parts.append(f"**Tags:** {', '.join(section.tags)}")
                    response_parts.append("")
                    response_parts.append(section.content)
                    response_parts.append("\n" + "="*50 + "\n")
                
                return [TextContent(type="text", text="\n".join(response_parts))]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Content retrieval failed: {str(e)}")]
    
    elif name == "update_content":
        print(f"[{datetime.now()}] DEBUG: Tool 'update_content' called.", file=sys.stderr)
        sys.stderr.flush()
        
        content_id = arguments.get("id")
        if not content_id:
            return [TextContent(type="text", text="Error: id parameter is required")]
        
        # Extract update parameters
        title = arguments.get("title")
        content = arguments.get("content")
        content_type = arguments.get("content_type")
        tags = arguments.get("tags")
        source_book = arguments.get("source_book")
        section_id = arguments.get("section_id")
        page_range = arguments.get("page_range")
        regenerate_embedding = arguments.get("regenerate_embedding", False)
        
        # If content is being updated, we should regenerate the embedding
        if content is not None:
            regenerate_embedding = True
        
        try:
            # First verify the content exists
            existing_content = get_content_by_id(content_id)
            if not existing_content:
                return [TextContent(type="text", text=f"Error: Content with ID '{content_id}' not found")]
            
            # Handle embedding regeneration if needed
            if regenerate_embedding and content is not None:
                print(f"[{datetime.now()}] DEBUG: Regenerating embedding for updated content...", file=sys.stderr)
                sys.stderr.flush()
                
                # Generate new embedding
                new_embedding = await get_embedding_async(content)
                
                # Update the database with embedding - we need to handle this separately
                # since update_content_section doesn't handle embeddings
                from core.database import get_db_connection, get_db_cursor
                
                with get_db_connection() as conn:
                    with get_db_cursor(conn) as cursor:
                        cursor.execute(
                            "UPDATE content_sections SET embedding = %s WHERE id = %s",
                            [new_embedding, content_id]
                        )
                        conn.commit()
                
                print(f"[{datetime.now()}] DEBUG: Embedding updated successfully.", file=sys.stderr)
                sys.stderr.flush()
            
            # Update the content section
            success = update_content_section(
                content_id=content_id,
                title=title,
                content=content,
                content_type=content_type,
                tags=tags,
                source_book=source_book,
                section_id=section_id,
                page_range=page_range
            )
            
            if success:
                # Retrieve and return the updated content
                updated_content = get_content_by_id(content_id)
                if updated_content:
                    response_parts = [f"✅ Content updated successfully!\n"]
                    response_parts.append(f"# {updated_content.title}")
                    response_parts.append(f"**Source:** {updated_content.source_book} ({updated_content.page_range})")
                    response_parts.append(f"**ID:** {updated_content.id}")
                    if updated_content.section_id:
                        response_parts.append(f"**Section ID:** {updated_content.section_id}")
                    if updated_content.content_type:
                        response_parts.append(f"**Content Type:** {', '.join(updated_content.content_type)}")
                    if updated_content.tags:
                        response_parts.append(f"**Tags:** {', '.join(updated_content.tags)}")
                    response_parts.append("")
                    response_parts.append(updated_content.content)
                    
                    if regenerate_embedding:
                        response_parts.append(f"\n🔄 Vector embedding regenerated")
                    
                    return [TextContent(type="text", text="\n".join(response_parts))]
                else:
                    return [TextContent(type="text", text="✅ Content updated successfully (but could not retrieve updated version)")]
            else:
                return [TextContent(type="text", text=f"❌ Failed to update content with ID '{content_id}'")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Update failed: {str(e)}")]
    
    elif name == "create_content":
        print(f"[{datetime.now()}] DEBUG: Tool 'create_content' called.", file=sys.stderr)
        sys.stderr.flush()
        
        title = arguments.get("title")
        content = arguments.get("content")
        
        if not title or not content:
            return [TextContent(type="text", text="Error: title and content parameters are required")]
        
        # Extract optional parameters
        content_type = arguments.get("content_type", [])
        tags = arguments.get("tags", [])
        source_book = arguments.get("source_book", "campaign_notes")
        section_id = arguments.get("section_id")
        page_range = arguments.get("page_range")
        source_type = arguments.get("source_type", "campaign_notes")
        
        try:
            # Generate embedding for the content
            print(f"[{datetime.now()}] DEBUG: Generating embedding for new content...", file=sys.stderr)
            sys.stderr.flush()
            
            embedding = await get_embedding_async(content)
            
            print(f"[{datetime.now()}] DEBUG: Creating content section in database...", file=sys.stderr)
            sys.stderr.flush()
            
            # Create the content section
            section_id_result = create_content_section(
                title=title,
                content=content,
                content_type=content_type,
                tags=tags,
                source_book=source_book,
                section_id=section_id,
                page_range=page_range,
                source_type=source_type,
                embedding=embedding
            )
            
            if section_id_result:
                # Retrieve and return the created content
                created_content = get_content_by_id(section_id_result)
                if created_content:
                    response_parts = [f"✅ Content created successfully!\n"]
                    response_parts.append(f"# {created_content.title}")
                    response_parts.append(f"**Source:** {created_content.source_book} ({created_content.page_range or 'N/A'})")
                    response_parts.append(f"**ID:** {created_content.id}")
                    if created_content.section_id:
                        response_parts.append(f"**Section ID:** {created_content.section_id}")
                    if created_content.content_type:
                        response_parts.append(f"**Content Type:** {', '.join(created_content.content_type)}")
                    if created_content.tags:
                        response_parts.append(f"**Tags:** {', '.join(created_content.tags)}")
                    response_parts.append(f"**Source Type:** {created_content.source_type}")
                    response_parts.append("")
                    response_parts.append(created_content.content)
                    response_parts.append(f"\n🔄 Vector embedding generated and stored")
                    
                    return [TextContent(type="text", text="\n".join(response_parts))]
                else:
                    return [TextContent(type="text", text="✅ Content created successfully (but could not retrieve created version)")]
            else:
                return [TextContent(type="text", text=f"❌ Failed to create content section")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Content creation failed: {str(e)}")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Main entry point"""
    # Run the MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=config.mcp_server_name,
                server_version=config.mcp_server_version,
                capabilities=app.get_capabilities(
                    NotificationOptions(
                        tools_changed=True,
                        prompts_changed=True,
                        resources_changed=True
                    ),
                    None  # experimental_capabilities
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())