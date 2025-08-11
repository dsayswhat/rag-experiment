## Initialization request
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": true}, "sampling": {}, "elicitation": {}}, "clientInfo": {"name": "ExampleClient", "title": "Example Client Display Name", "version": "1.0.0"}}}
## initialized notification
{"jsonrpc": "2.0","method": "notifications/initialized"}

## tools/list
{"jsonrpc": "2.0","id": 1,"method": "tools/list","params": { }}

## Generic tool call : 

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "location": "New York"
    }
  }
}


## response as of 8/3 2:50 

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "semantic_search",
        "description": "Search Dolmenwood content using semantic similarity. Returns relevant sections based on the meaning of your query.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Search query (e.g., 'surprise check in combat', 'fire spells', 'village locations')"
            },
            "content_types": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Filter by content types: spell, location, rule, lore, equipment, ancestry, class, services, example"
            },
            "source_books": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Filter by source books: players_book, campaign_book, monster_book"
            },
            "limit": {
              "type": "integer",
              "description": "Maximum number of results (default: 5, max: 20)",
              "minimum": 1,
              "maximum": 20
            }
          },
          "required": [
            "query"
          ]
        }
      },
      {
        "name": "get_content",
        "description": "Retrieve specific Dolmenwood content by ID, section ID, or title. Use this when you need to get exact content rather than search.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string",
              "description": "UUID of the content section"
            },
            "section_id": {
              "type": "string",
              "description": "Section identifier (e.g., hex coordinates, spell names)"
            },
            "title": {
              "type": "string",
              "description": "Exact or partial title to search for"
            },
            "exact_match": {
              "type": "boolean",
              "description": "For title searches, whether to match exactly (default: false for partial matching)",
              "default": false
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
          },
          "oneOf": [
            {
              "required": [
                "id"
              ]
            },
            {
              "required": [
                "section_id"
              ]
            },
            {
              "required": [
                "title"
              ]
            }
          ]
        }
      }
    ]
  }
}



## semantic search
{  "jsonrpc": "2.0",  "id": 2,  "method": "tools/call",  "params": {    "name": "semantic_search",    "arguments": {      "query": "combat magic rules"    }  }}

## get content
{  "jsonrpc": "2.0",  "id": 2,  "method": "tools/call",  "params": {    "name": "get_content",    "arguments": {      "title": "0810"    }  }}