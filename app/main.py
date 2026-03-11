import httpx
import asyncio
import os
import json
import logging
from   auth_manager import nd_auth_manager 
from   mcp.server.fastmcp import FastMCP

# set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NDmcp")

mcp = FastMCP("NDmcp") 

@mcp.tool()
async def list_nd_fabrics() -> str:
    """
    Lists fabrics onboarded on Nexus Dashboard.
    Returns:
        str: The JSON response from ND.
    """
    await nd_auth_manager.initialize()
    token = await nd_auth_manager.get_access_token()
    nd_host = os.getenv("ND_HOST")
    url = f"https://{nd_host}/api/v1/manage/fabrics"  # Adjust endpoint if your ND uses a different path

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, timeout=15.0)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"Error fetching fabrics from ND: {e}"

@mcp.tool()
async def collect_nd_all_interfaces() -> str:
    """
    Collects all interfaces from all fabrics onboarded on ND.
    Returns:
        str: JSON list of all interfaces from all fabrics.
    """

    await nd_auth_manager.initialize()
    token = await nd_auth_manager.get_access_token()
    nd_host = os.getenv("ND_HOST")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    fabrics_url = f"https://{nd_host}/api/v1/manage/fabrics"
    async with httpx.AsyncClient(verify=False) as client:
        try:
            fabrics_resp = await client.get(fabrics_url, headers=headers, timeout=15.0)
            fabrics_resp.raise_for_status()
            fabrics = fabrics_resp.json().get("fabrics", [])
        except Exception as e:
            return f"Error fetching fabrics from ND: {e}"

        all_interfaces = []
        for fabric in fabrics:
            fabric_name = fabric.get("name")
            if not fabric_name:
                continue
            interfaces_url = f"https://{nd_host}/api/v1/analyze/interfaces?max=500&offset=0&fabricName={fabric_name}"
            try:
                intf_resp = await client.get(interfaces_url, headers=headers, timeout=15.0)
                intf_resp.raise_for_status()
                interfaces = intf_resp.json().get("interfaces", [])
                for intf in interfaces:
                    all_interfaces.append({
                        "fabric": fabric_name,
                        "interface": intf.get("interfaceName"),
                        "type": intf.get("interfaceType"),
                        "node": intf.get("switchName"),
                        "operState": intf.get("operationalStatus")
                    })
            except Exception as e:
                all_interfaces.append({"fabric": fabric_name, "error": str(e)})

    return json.dumps(all_interfaces, indent=2)


@mcp.tool()
async def collect_nd_anomalies(severity: str = None, fabric_name: str = None) -> str:
    """
    Collects anomalies/events from Nexus Dashboard Insights across all fabrics.
    Args:
        severity (str, optional): Filter by severity (critical, major, minor, warning, info). Default: all.
        fabric_name (str, optional): Filter by specific fabric name. Default: all fabrics.
    Returns:
        str: Formatted summary of anomalies with details.
    """
    await nd_auth_manager.initialize()
    token = await nd_auth_manager.get_access_token()
    nd_host = os.getenv("ND_HOST")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        # Get anomalies from ND Insights
        anomalies_url = f"https://{nd_host}/api/v1/analyze/anomalies/summary?filter=acknowledged%3Afalse+AND+cleared%3Afalse"
        params = {"category": "anomaly", "$page": 0, "$size": 500}
        
        if severity:
            params["severity"] = severity.lower()
        
        try:
            anomalies_resp = await client.get(anomalies_url, headers=headers, params=params)
            anomalies_resp.raise_for_status()
            data = anomalies_resp.json()
            anomalies = data.get("value", {}).get("data", [])
        except Exception as e:
            logger.error(f"Error fetching anomalies from ND: {e}")
            return f"Error fetching anomalies from ND: {e}"

        # Filter by fabric if specified
        if fabric_name:
            anomalies = [a for a in anomalies if a.get("fabricName") == fabric_name]

        if not anomalies:
            return "No anomalies found matching the criteria."

        # Organize anomalies by severity
        by_severity = {"critical": [], "major": [], "minor": [], "warning": [], "info": []}
        for anomaly in anomalies:
            sev = anomaly.get("severity", "info").lower()
            if sev in by_severity:
                by_severity[sev].append(anomaly)

        # Create summary
        output = "\n" + "="*150 + "\n"
        output += f"Nexus Dashboard Anomalies Summary - Total: {len(anomalies)}\n"
        output += "="*150 + "\n\n"

        # Summary by severity
        output += "Anomalies by Severity:\n"
        output += f"  Critical: {len(by_severity['critical'])}\n"
        output += f"  Major:    {len(by_severity['major'])}\n"
        output += f"  Minor:    {len(by_severity['minor'])}\n"
        output += f"  Warning:  {len(by_severity['warning'])}\n"
        output += f"  Info:     {len(by_severity['info'])}\n\n"

        # Detailed list
        for sev_level in ["critical", "major", "minor", "warning", "info"]:
            if by_severity[sev_level]:
                output += f"\n{sev_level.upper()} Anomalies ({len(by_severity[sev_level])}):\n"
                output += "-"*150 + "\n"
                
                for idx, anomaly in enumerate(by_severity[sev_level][:50], 1):  # Limit to 50 per severity
                    fabric = anomaly.get("fabricName", "N/A")
                    event_type = anomaly.get("type", "N/A")
                    description = anomaly.get("description", "N/A")
                    affected = anomaly.get("affectedObject", "N/A")
                    timestamp = anomaly.get("timestamp", "N/A")
                    
                    output += f"{idx}. [{fabric}] {event_type}\n"
                    output += f"   Description: {description}\n"
                    output += f"   Affected: {affected}\n"
                    output += f"   Time: {timestamp}\n\n"

        output += "="*150 + "\n"
        return output


if __name__ == "__main__":
    logger.info("Starting MCP server NDmcp on STDIO...")
    mcp.run()
