# MCP (Model Context Protocol) for Cisco ND

This project provides a simple MCP (Model Context Protocol) server that interacts with a Cisco ND controller.
If you'd like to understand how this works in detail, please check out [this blog post](https://medium.com/@cpaggen/putting-ai-to-work-with-your-cisco-application-centric-infrastructure-fabric-a-mcp-server-for-aci-838e6fe62022)

- Tested with **Claude Desktop** and **Visual Studio Code** in Agent mode with Copilot.
- The server runs in **STDIO mode**, intended for local execution.

## Features

- Exposes two tools for Nexus Dashboard interaction (see `app/main.py` for details).
- Easily configurable via environment variables.

## Setup

1. **Specify Nexus Dashboard credentials** in the `.env` file.
2. If you want Claude or VS Code to run the Python code directly (no container), install [UV](https://docs.astral.sh/uv/)
3. **Register the MCP server** with Claude or VS Code.

   For VS Code, create a `.vscode/mcp.json` file like this in your workspace:

   ```json
   {
  "servers": {
    "ciscoNdServer": {
      "type": "stdio",
      "command": "/path-to-bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/path-to-your-app/main.py"
      ]
    }
  }
}
```
    - Make sure to update the `command` and the path to your `main.py` as needed.
3. Instruct Claude Desktop or VS Code to use it:
   - See [Claude Desktop Quickstart](https://modelcontextprotocol.io/quickstart/user)
   - See [VS Code Copilot MCP Servers](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

4. **Install MCP client tools locally** if you invoke the MCP server with `uv run mcp` as above.
   - Use ```uv add "mcp[cli]"``` or ```pip install "mcp[cli]"```

## Docker Support

You can run the server directly using UV, or build a Docker image and run it as a container. If using Docker, adapt the `mcp.json` config accordingly.

> **Note:** Local installation of MCP client tools is recommended for debugging the server code.
