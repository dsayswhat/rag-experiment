# client.py (Corrected)
import json
import sys
import time

# 1. Initialization request
initialize_request = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "1.0",
        "clientInfo": {"name": "test_client", "version": "0.1.0"},
        "capabilities": {}
    }
}

# 2. Tool call request
tool_call_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "semantic_search",
        "arguments": {
            "query": "What are the rules for casting spells in combat?"
        }
    }
}

# --- Interaction Logic ---

# Send initialize request and flush the output
json.dump(initialize_request, sys.stdout)
sys.stdout.write('\n')
sys.stdout.flush()

# Wait for and read the initialize response from the server
init_response = sys.stdin.readline()
print(f"Server INIT Response: {init_response.strip()}", file=sys.stderr) # Optional: for debugging

# Now that initialization is complete, send the tool call request
json.dump(tool_call_request, sys.stdout)
sys.stdout.write('\n')
sys.stdout.flush()

# Wait for and read the final tool call response
tool_response = sys.stdin.readline()
print(f"Server TOOL Response: {tool_response.strip()}", file=sys.stderr) # Optional: for debugging