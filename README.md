# MCP (Model Context Protocol) for Cisco ND

This project provides a simple MCP (Model Context Protocol) server that interacts with a Cisco ND controller.
If you'd like to understand how this works in detail, please check out [this blog post](https://medium.com/@cpaggen/putting-ai-to-work-with-your-cisco-application-centric-infrastructure-fabric-a-mcp-server-for-aci-838e6fe62022)

- Tested with **Claude Desktop** and **Visual Studio Code** in Agent mode with Copilot.
- The server runs in **STDIO mode**, intended for local execution.

## Features

- Exposes two tools for Nexus Dashboard interaction (see `app/main.py` for details).
- Easily configurable via environment variables.

## Setup

1. **Clone the repository** and navigate to the project directory.
2. **Create a Python virtual environment** and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Specify Nexus Dashboard credentials** in the `.env` file.
4. **Update the .vscode/mcp.json** file with the correct path to your Python environment and the server script.
5. If you want Claude or VS Code to run the Python code directly (no container), install [UV](https://docs.astral.sh/uv/)
6. **Register the MCP server** with Claude or VS Code.

   For VS Code, create a `.vscode/mcp.json` file like this in your workspace:

   ```json
   {
     "servers": {
       "ciscoNdServer": {
         "type": "stdio",
         "command": "/Users/user/.local/bin/uv",
         "args": [
           "run",
           "--with",
           "mcp[cli]",
           "mcp",
           "run",
           "/Users/user/Coding/MCP_server_for_Cisco_ND/app/main.py"
         ]
       }
     }
   }
   ```

7. Instruct Claude Desktop or VS Code to use it:
   - See [Claude Desktop Quickstart](https://modelcontextprotocol.io/quickstart/user)
   - See [VS Code Copilot MCP Servers](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

8. **Install MCP client tools locally** if you invoke the MCP server with `uv run mcp` as above.
   - Use ```uv add "mcp[cli]"``` or ```pip install "mcp[cli]"```
9. **Test the server** by sending a request from your agent (Claude or VS Code) that triggers one of the tools. For example, ask for a list of all tenants in the Nexus Dashboard.

## Example ND Queries (from real usage)

Use prompts like these in Claude Desktop or VS Code Agent mode to call your MCP tools:

- **List onboarded fabrics**
  - "Give me the names of the fabrics onboarded on my ND"

- **Anomalies by fabric**
  - "Give me all anomalies on my Nexus Dashboard related to fabric ACI1"
  - "Give me the details of all anomalies for fabric ACI1"

- **Anomalies across all fabrics**
  - "Collect all anomalies active on Nexus Dashboard"
  - "Show me a summary of all active anomalies in my ND"
  - "Check again for anomalies"

- **Include cleared/expired anomalies**
  - "Show me all ND anomalies"
  - "Include all"

- **Interface-related anomaly checks**
  - "Is there any anomaly related to interfaces?"

- **Switch inventory**
  - "Give me the list of all switches belonging to fabric ACI1"
  - "Group ACI1 switches by role and anomaly level"
  - "Give me the grouped view for all fabrics"

- **Logical policy retrieval (generic)**
  - "Get all VRFs in my fabric ACI1"
  - "Get all tenants in fabric ACI1"
  - "Get security groups / EPGs / contracts in ACI1"
  - "For VXLAN fabric VXLAN2, get networks"

These examples map to tools currently implemented in `app/main.py`, including:
`list_nd_fabrics`, `collect_nd_anomalies_v2`, `collect_nd_switches`, and `collect_nd_fabric_policy`.

## Docker Support

You can run the server directly using UV, or build a Docker image and run it as a container. If using Docker, adapt the `mcp.json` config accordingly.

> **Note:** Local installation of MCP client tools is recommended for debugging the server code.
