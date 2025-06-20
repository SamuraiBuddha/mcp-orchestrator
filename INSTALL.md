# Installation & Setup

## Prerequisites

1. **LM Studio** with Granite embeddings model:
   - Download and install [LM Studio](https://lmstudio.ai/)
   - Load `text-embedding-granite-embedding-278m-multilingual`
   - Start the server (it will run on `http://localhost:1234`)

2. **Python 3.8+** and pip

## Installation

### From GitHub (recommended)

```bash
# Clone the repository
git clone https://github.com/SamuraiBuddha/mcp-orchestrator.git
cd mcp-orchestrator

# Install in development mode
pip install -e .
```

### Configure MCPs

1. Copy the example registry:
```bash
cp config/registry.json.example config/registry.json
```

2. Edit `config/registry.json` to add your MCPs

3. Copy and configure credentials (if needed):
```bash
cp config/credentials.json.example config/credentials.json
# Edit with your API keys
```

## Claude Desktop Configuration

Replace your entire `claude_desktop_config.json` with just the orchestrator:

### Windows
`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_orchestrator"]
    }
  }
}
```

### macOS
`~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_orchestrator"]
    }
  }
}
```

### Linux
`~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_orchestrator"]
    }
  }
}
```

## Testing

1. Make sure LM Studio is running with Granite loaded
2. Run the demo to test routing:
```bash
python demo.py
```

3. Restart Claude Desktop
4. Claude now has access to ALL your MCPs through just 4 tools!

## Usage in Claude

Instead of remembering 100+ tools, just tell Claude what you want:

- "Create a logo for my project" → Routes to ComfyUI
- "Push this code to GitHub" → Routes to GitHub MCP
- "Remember this for later" → Routes to Memory MCP
- "Show my Docker containers" → Routes to Docker MCP

The orchestrator handles all the routing automatically!

## Adding New MCPs

Edit `config/registry.json`:

```json
{
  "mcps": {
    "your_new_mcp": {
      "description": "What this MCP does",
      "capabilities": ["list", "of", "capabilities"],
      "keywords": ["search", "terms"],
      "command": "python",
      "args": ["-m", "your_mcp_module"],
      "tools": {
        "tool_name": {
          "description": "What this tool does",
          "examples": ["example usage"],
          "parameters": {
            "param1": {"description": "Parameter description"}
          }
        }
      }
    }
  }
}
```

The orchestrator will automatically include it in routing!

## Troubleshooting

### "Cannot connect to LM Studio"
- Make sure LM Studio is running
- Check that Granite embeddings model is loaded
- Verify it's listening on `http://localhost:1234`

### "No matching tools found"
- Lower the confidence threshold in your queries
- Add more keywords to your MCP definitions
- Check that your MCPs are properly configured

### "MCP execution failed"
- Ensure the underlying MCP is installed
- Check that the command and args in registry.json are correct
- Look at the orchestrator logs for details
