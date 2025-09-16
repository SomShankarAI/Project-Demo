import asyncio
import logging
from fastmcp import FastMCP
from .tools import MCPTools
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Onboarding MCP Server")

@mcp.tool()
def get_profile_and_team_name_by_store_id(store_id: str) -> dict:
    """
    Get team name and profile name for a given store ID
    
    Args:
        store_id: The store ID to lookup
        
    Returns:
        Dictionary containing team_name and profile_name
    """
    logger.info(f"get_profile_and_team_name_by_store_id called with store_id: {store_id}")
    return MCPTools.get_profile_and_team_name_by_store_id(store_id)

@mcp.tool()
def get_b2b_profiles_and_identities_by_store_id(store_id: str) -> dict:
    """
    Get B2B profiles and identities for a given store ID
    
    Args:
        store_id: The store ID to lookup
        
    Returns:
        Dictionary containing profiles and identities lists
    """
    logger.info(f"get_b2b_profiles_and_identities_by_store_id called with store_id: {store_id}")
    return MCPTools.get_b2b_profiles_and_identities_by_store_id(store_id)

@mcp.tool()
def onboard_user(store_id: str, team_name: str, profile_name: str, 
                selected_profiles: list, selected_identities: list) -> dict:
    """
    Start the user onboarding process
    
    Args:
        store_id: The store ID
        team_name: The team name
        profile_name: The profile name
        selected_profiles: List of selected B2B profiles
        selected_identities: List of selected B2B identities
        
    Returns:
        Dictionary containing onboarding status and details
    """
    logger.info("onboard_user called")
    return MCPTools.onboard_user(
        store_id=store_id,
        team_name=team_name,
        profile_name=profile_name,
        selected_profiles=selected_profiles,
        selected_identities=selected_identities
    )

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Run the FastMCP server"""
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    logger.info(f"Starting FastMCP Tools Server on {host}:{port}...")
    await mcp.run(transport="http", host=host, port=port)

if __name__ == "__main__":
    asyncio.run(main())