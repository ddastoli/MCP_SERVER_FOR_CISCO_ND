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
async def collect_nd_switches(fabric_name: str = None, max_results: int = 1000) -> str:
    """
    Collects switches from Nexus Dashboard inventory endpoint.
    API: /api/v1/manage/inventory/switches?max=1000
    Args:
        fabric_name (str, optional): Filter by a specific fabric name.
        max_results (int, optional): Maximum number of switches to return.
    Returns:
        str: JSON with summary and normalized switch details.
    """
    await nd_auth_manager.initialize()
    token = await nd_auth_manager.get_access_token()
    nd_host = os.getenv("ND_HOST")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if max_results <= 0:
        max_results = 1000

    page_size = min(1000, max_results)
    offset = 0
    all_switches = []

    async with httpx.AsyncClient(verify=False) as client:
        try:
            while len(all_switches) < max_results:
                url = f"https://{nd_host}/api/v1/manage/inventory/switches?max={page_size}&offset={offset}"
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                payload = response.json()

                switches_page = payload.get("switches", [])
                if not isinstance(switches_page, list) or not switches_page:
                    break

                all_switches.extend(switches_page)

                remaining = (
                    payload.get("meta", {})
                    .get("counts", {})
                    .get("remaining")
                )
                offset += len(switches_page)

                if remaining in (None, 0):
                    break
        except Exception as e:
            logger.error(f"Error fetching switches from ND: {e}")
            return f"Error fetching switches from ND: {e}"

    if fabric_name:
        fabric_name_lower = fabric_name.lower()
        all_switches = [
            sw for sw in all_switches
            if str(sw.get("fabricName", "")).lower() == fabric_name_lower
        ]

    if not all_switches:
        return "No switches found matching the criteria."

    normalized = []
    for sw in all_switches[:max_results]:
        normalized.append({
            "fabricName": sw.get("fabricName"),
            "hostname": sw.get("hostname"),
            "switchId": sw.get("switchId"),
            "serialNumber": sw.get("serialNumber"),
            "model": sw.get("model"),
            "softwareVersion": sw.get("softwareVersion"),
            "switchRole": sw.get("switchRole"),
            "fabricType": sw.get("fabricType"),
            "fabricManagementIp": sw.get("fabricManagementIp"),
            "advisoryLevel": sw.get("advisoryLevel"),
            "anomalyLevel": sw.get("anomalyLevel"),
            "systemUpTime": sw.get("systemUpTime"),
            "vpcConfigured": sw.get("vpcConfigured"),
            "vendor": sw.get("additionalData", {}).get("vendor"),
            "platformType": sw.get("additionalData", {}).get("platformType"),
            "discoveryStatus": sw.get("additionalData", {}).get("discoveryStatus")
        })

    result = {
        "summary": {
            "returned": len(normalized),
            "totalMatched": len(all_switches),
            "fabricFilter": fabric_name or "all"
        },
        "switches": normalized
    }
    return json.dumps(result, indent=2)


@mcp.tool()
async def collect_nd_anomalies_v2(
    severity: str = None,
    fabric_name: str = None,
    active_only: bool = True,
    max_results: int = 200
) -> str:
    """
    Collects anomalies from Nexus Dashboard using /api/v1/analyze/anomalies/details.
    Args:
        severity (str, optional): Filter by severity (critical, major, minor, warning, info).
        fabric_name (str, optional): Filter by a specific fabric name.
        active_only (bool, optional): If True, excludes cleared/expired anomalies.
        max_results (int, optional): Maximum anomalies to include in output.
    Returns:
        str: Formatted anomaly summary and details.
    """
    await nd_auth_manager.initialize()
    token = await nd_auth_manager.get_access_token()
    nd_host = os.getenv("ND_HOST")
    url = f"https://{nd_host}/api/v1/analyze/anomalies/details?max=1000"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if max_results <= 0:
        max_results = 200

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            logger.error(f"Error fetching anomalies from ND: {e}")
            return f"Error fetching anomalies from ND: {e}"

    anomalies = payload.get("anomalies")
    if not isinstance(anomalies, list):
        anomalies = payload.get("value", {}).get("data", [])

    if not isinstance(anomalies, list):
        return "Error parsing anomalies response from ND: expected 'anomalies' list."

    severity_lower = severity.lower() if severity else None
    fabric_name_lower = fabric_name.lower() if fabric_name else None

    filtered = []
    for anomaly in anomalies:
        anomaly_severity = str(anomaly.get("severity", "")).lower()
        anomaly_fabric = str(anomaly.get("fabricName", "")).lower()

        if severity_lower and anomaly_severity != severity_lower:
            continue
        if fabric_name_lower and anomaly_fabric != fabric_name_lower:
            continue
        if active_only and (anomaly.get("cleared") is True or anomaly.get("expired") is True):
            continue

        filtered.append(anomaly)

    if not filtered:
        return "No anomalies found matching the criteria."

    limited = filtered[:max_results]
    counts = {"critical": 0, "major": 0, "minor": 0, "warning": 0, "info": 0, "other": 0}
    for anomaly in limited:
        sev = str(anomaly.get("severity", "other")).lower()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["other"] += 1

    lines = []
    lines.append("=" * 140)
    lines.append(f"Nexus Dashboard Anomalies - Returned: {len(limited)} / Matched: {len(filtered)}")
    lines.append("=" * 140)
    lines.append("")
    lines.append("Severity Summary:")
    lines.append(f"  Critical: {counts['critical']}")
    lines.append(f"  Major:    {counts['major']}")
    lines.append(f"  Minor:    {counts['minor']}")
    lines.append(f"  Warning:  {counts['warning']}")
    lines.append(f"  Info:     {counts['info']}")
    lines.append(f"  Other:    {counts['other']}")
    lines.append("")

    for idx, anomaly in enumerate(limited, 1):
        anomaly_id = anomaly.get("anomalyId", "N/A")
        anomaly_type = anomaly.get("anomalyType") or anomaly.get("mnemonicTitle") or "N/A"
        anomaly_text = anomaly.get("anomalyString") or anomaly.get("anomalyReason") or anomaly.get("mnemonicDescription") or "N/A"
        anomaly_fabric = anomaly.get("fabricName", "N/A")
        anomaly_severity = anomaly.get("severity", "N/A")
        start_time = anomaly.get("startTimestamp") or anomaly.get("startDate") or "N/A"
        end_time = anomaly.get("endTimestamp") or anomaly.get("endDate") or "N/A"
        verification_status = anomaly.get("verificationStatus", "N/A")
        cleared = anomaly.get("cleared", False)
        expired = anomaly.get("expired", False)
        score = anomaly.get("anomalyScore", "N/A")

        anomaly_objects = anomaly.get("anomalyObjects", [])
        primary_obj = {}
        if isinstance(anomaly_objects, list) and anomaly_objects:
            primary_obj = next((obj for obj in anomaly_objects if obj.get("isPrimary")), anomaly_objects[0])

        affected_name = primary_obj.get("name") or primary_obj.get("identifier") or "N/A"
        affected_type = primary_obj.get("objectType") or "N/A"
        node_names = anomaly.get("nodeNames", [])
        node_list = ", ".join(node_names[:8]) if isinstance(node_names, list) and node_names else "N/A"

        lines.append(f"{idx}. [{anomaly_fabric}] {anomaly_type} ({anomaly_severity})")
        lines.append(f"   ID: {anomaly_id}")
        lines.append(f"   Score: {score} | Verification: {verification_status} | Cleared: {cleared} | Expired: {expired}")
        lines.append(f"   Affected: {affected_name} ({affected_type})")
        lines.append(f"   Nodes: {node_list}")
        lines.append(f"   Start: {start_time}")
        lines.append(f"   End:   {end_time}")
        lines.append(f"   Reason: {anomaly_text}")
        lines.append("")

    lines.append("=" * 140)
    return "\n".join(lines)




if __name__ == "__main__":
    logger.info("Starting MCP server NDmcp on STDIO...")
    mcp.run()
