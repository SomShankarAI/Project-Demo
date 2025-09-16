import asyncio
import json
import logging
from typing import Dict, List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Client to interact with MCP Tools Server using Model Context Protocol"""
    
    def __init__(self):
        self.session = None
        self._lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """Ensure MCP connection is established"""
        if self.session is None:
            async with self._lock:
                if self.session is None:
                    # Create server parameters for stdio connection
                    server_params = StdioServerParameters(
                        command="python",
                        args=["run_mcp_server.py"],
                        env=None
                    )
                    
                    # Create stdio client and session
                    stdio_transport = stdio_client(server_params)
                    self.session = ClientSession(stdio_transport[0], stdio_transport[1])
                    
                    # Initialize the session
                    await self.session.initialize()
                    
                    logger.info("MCP client session initialized")
    
    async def get_profile_and_team_name(self, store_id: str) -> Dict[str, str]:
        """Call GetProfileAndTeamNameByStoreId MCP tool"""
        try:
            await self._ensure_connection()
            
            result = await self.session.call_tool(
                "get_profile_and_team_name_by_store_id",
                {"store_id": store_id}
            )
            
            # Parse the result
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                raise ValueError("Empty response from MCP tool")
                
        except Exception as e:
            logger.error(f"Error calling get_profile_and_team_name: {e}")
            # Fallback to direct tool call for development
            from ..mcp_server.tools import MCPTools
            return MCPTools.get_profile_and_team_name_by_store_id(store_id)
    
    async def get_b2b_profiles_and_identities(self, store_id: str) -> Dict[str, List[str]]:
        """Call GetB2BProfilesAndIdentitiesByStoreId MCP tool"""
        try:
            await self._ensure_connection()
            
            result = await self.session.call_tool(
                "get_b2b_profiles_and_identities_by_store_id",
                {"store_id": store_id}
            )
            
            # Parse the result
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                raise ValueError("Empty response from MCP tool")
                
        except Exception as e:
            logger.error(f"Error calling get_b2b_profiles_and_identities: {e}")
            # Fallback to direct tool call for development
            from ..mcp_server.tools import MCPTools
            return MCPTools.get_b2b_profiles_and_identities_by_store_id(store_id)
    
    async def onboard_user(self, store_id: str, team_name: str, profile_name: str,
                          selected_profiles: List[str], selected_identities: List[str]) -> Dict[str, Any]:
        """Call OnboardUser MCP tool"""
        try:
            await self._ensure_connection()
            
            result = await self.session.call_tool(
                "onboard_user",
                {
                    "store_id": store_id,
                    "team_name": team_name,
                    "profile_name": profile_name,
                    "selected_profiles": selected_profiles,
                    "selected_identities": selected_identities
                }
            )
            
            # Parse the result
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                raise ValueError("Empty response from MCP tool")
                
        except Exception as e:
            logger.error(f"Error calling onboard_user: {e}")
            # Fallback to direct tool call for development
            from ..mcp_server.tools import MCPTools
            return MCPTools.onboard_user(
                store_id=store_id,
                team_name=team_name,
                profile_name=profile_name,
                selected_profiles=selected_profiles,
                selected_identities=selected_identities
            )
    
    async def close(self):
        """Close the MCP session"""
        if self.session:
            await self.session.close()
            self.session = None