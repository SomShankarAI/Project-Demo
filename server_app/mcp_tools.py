from typing import Dict, List, Any
import asyncio
import logging
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class GetProfileAndTeamNameInput(BaseModel):
    """Input for GetProfileAndTeamName tool"""
    store_id: str = Field(description="The store ID to lookup")


class GetB2BDataInput(BaseModel):
    """Input for GetB2BProfilesAndIdentities tool"""
    store_id: str = Field(description="The store ID to lookup")


class OnboardUserInput(BaseModel):
    """Input for OnboardUser tool"""
    store_id: str = Field(description="The store ID")
    team_name: str = Field(description="The team name")
    profile_name: str = Field(description="The profile name")
    selected_profiles: List[str] = Field(description="List of selected B2B profiles")
    selected_identities: List[str] = Field(description="List of selected B2B identities")


class GetProfileAndTeamNameTool(BaseTool):
    """Tool to get profile and team name by store ID via MCP"""
    name = "get_profile_and_team_name"
    description = "Get team name and profile name for a given store ID"
    args_schema = GetProfileAndTeamNameInput
    
    def __init__(self, mcp_client: MCPClient):
        super().__init__()
        self.mcp_client = mcp_client
    
    def _run(self, store_id: str) -> Dict[str, str]:
        """Execute the tool"""
        try:
            result = asyncio.run(self.mcp_client.get_profile_and_team_name(store_id))
            logger.info(f"Retrieved profile and team name for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting profile and team name: {e}")
            return {"error": str(e)}
    
    async def _arun(self, store_id: str) -> Dict[str, str]:
        """Execute the tool asynchronously"""
        try:
            result = await self.mcp_client.get_profile_and_team_name(store_id)
            logger.info(f"Retrieved profile and team name for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting profile and team name: {e}")
            return {"error": str(e)}


class GetB2BProfilesAndIdentitiesTool(BaseTool):
    """Tool to get B2B profiles and identities by store ID via MCP"""
    name = "get_b2b_profiles_and_identities"
    description = "Get B2B profiles and identities for a given store ID"
    args_schema = GetB2BDataInput
    
    def __init__(self, mcp_client: MCPClient):
        super().__init__()
        self.mcp_client = mcp_client
    
    def _run(self, store_id: str) -> Dict[str, List[str]]:
        """Execute the tool"""
        try:
            result = asyncio.run(self.mcp_client.get_b2b_profiles_and_identities(store_id))
            logger.info(f"Retrieved B2B data for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting B2B profiles and identities: {e}")
            return {"error": str(e)}
    
    async def _arun(self, store_id: str) -> Dict[str, List[str]]:
        """Execute the tool asynchronously"""
        try:
            result = await self.mcp_client.get_b2b_profiles_and_identities(store_id)
            logger.info(f"Retrieved B2B data for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting B2B profiles and identities: {e}")
            return {"error": str(e)}


class OnboardUserTool(BaseTool):
    """Tool to onboard user via MCP"""
    name = "onboard_user"
    description = "Start the user onboarding process with collected information"
    args_schema = OnboardUserInput
    
    def __init__(self, mcp_client: MCPClient):
        super().__init__()
        self.mcp_client = mcp_client
    
    def _run(self, store_id: str, team_name: str, profile_name: str,
             selected_profiles: List[str], selected_identities: List[str]) -> Dict[str, Any]:
        """Execute the tool"""
        try:
            result = asyncio.run(self.mcp_client.onboard_user(
                store_id=store_id,
                team_name=team_name,
                profile_name=profile_name,
                selected_profiles=selected_profiles,
                selected_identities=selected_identities
            ))
            logger.info(f"Onboarded user for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error onboarding user: {e}")
            return {"error": str(e)}
    
    async def _arun(self, store_id: str, team_name: str, profile_name: str,
                    selected_profiles: List[str], selected_identities: List[str]) -> Dict[str, Any]:
        """Execute the tool asynchronously"""
        try:
            result = await self.mcp_client.onboard_user(
                store_id=store_id,
                team_name=team_name,
                profile_name=profile_name,
                selected_profiles=selected_profiles,
                selected_identities=selected_identities
            )
            logger.info(f"Onboarded user for store {store_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error onboarding user: {e}")
            return {"error": str(e)}