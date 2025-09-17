from __future__ import annotations
from typing import Dict, Any, List, Tuple
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools.base import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict
import json
import logging
from .models import OnboardingState
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    messages: List[BaseMessage]
    onboarding_state: OnboardingState


class OnboardingWorkflow:
    def __init__(self, openai_api_key: str, tools: List[BaseTool], session: ClientSession):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            openai_api_key=openai_api_key
        )
        self.tools = tools
        self.session = session
        self.agent_graph = create_react_agent(self.llm, self.tools)

    @classmethod
    async def create(cls, openai_api_key: str) -> OnboardingWorkflow:
        """Create an instance of OnboardingWorkflow with async initialization."""
        mcp_host = os.getenv("MCP_SERVER_HOST", "localhost")
        mcp_port = int(os.getenv("MCP_SERVER_PORT", "8001"))
        mcp_url = f"http://{mcp_host}:{mcp_port}/mcp"

        async with streamablehttp_client(mcp_url) as (reader, writer, _):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
        
        return cls(openai_api_key, tools, session)

    async def close(self):
        """Close the MCP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _update_state(self, state: WorkflowState) -> OnboardingState:
        """Update onboarding state based on conversation."""
        current_message = state["messages"][-1].content
        onboarding_state = state["onboarding_state"]

        extraction_prompt = ChatPromptTemplate.from_template("""
        Based on the conversation, extract and update the onboarding state information.

        Current state:
        - Store ID: {store_id}
        - Team Name: {team_name}
        - Profile Name: {profile_name}
        - B2B Profiles: {b2b_profiles}
        - B2B Identities: {b2b_identities}
        - Selected Profiles: {selected_profiles}
        - Selected Identities: {selected_identities}
        - Step: {step}

        Latest AI response: {ai_response}

        Extract any new information and return a JSON object with the updated state.
        Only include fields that have been updated or newly discovered.
        If the onboarding process is completed, set "step" to "completed".

        Return only valid JSON.
        """)

        try:
            extraction_response = self.llm.invoke(extraction_prompt.format(
                store_id=onboarding_state.store_id or "None",
                team_name=onboarding_state.team_name or "None",
                profile_name=onboarding_state.profile_name or "None",
                b2b_profiles=onboarding_state.b2b_profiles or "None",
                b2b_identities=onboarding_state.b2b_identities or "None",
                selected_profiles=onboarding_state.selected_profiles or "None",
                selected_identities=onboarding_state.selected_identities or "None",
                step=onboarding_state.step,
                ai_response=current_message
            ))

            updates = json.loads(extraction_response.content)

            for key, value in updates.items():
                if hasattr(onboarding_state, key) and value != "None":
                    setattr(onboarding_state, key, value)

            if not onboarding_state.store_id:
                onboarding_state.step = "collect_store_id"
            elif not onboarding_state.team_name or not onboarding_state.profile_name:
                onboarding_state.step = "fetch_store_info"
            elif not onboarding_state.b2b_profiles or not onboarding_state.b2b_identities:
                onboarding_state.step = "fetch_b2b_data"
            elif not onboarding_state.selected_profiles or not onboarding_state.selected_identities:
                onboarding_state.step = "collect_selections"
            elif "onboarding completed" in current_message.lower() or "successfully" in current_message.lower():
                onboarding_state.step = "completed"
            else:
                onboarding_state.step = "in_progress"

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error updating state: {e}", exc_info=True)

        return onboarding_state

    def process_message(self, current_state: WorkflowState) -> Tuple[str, WorkflowState]:
        """Process a user message and return response and updated state."""

        # 1. Run the agent graph
        agent_input = {"messages": current_state["messages"]}
        agent_result = self.agent_graph.invoke(agent_input)

        # Update messages in the state
        current_state["messages"] = agent_result["messages"]

        # 2. Update the custom onboarding state
        updated_onboarding_state = self._update_state(current_state)
        current_state["onboarding_state"] = updated_onboarding_state

        # 3. Extract the final response for the user
        ai_messages = [msg for msg in agent_result["messages"] if isinstance(msg, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process your request."

        return response, current_state