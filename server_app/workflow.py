from __future__ import annotations
from typing import Dict, Any, List
from langchain.schema import BaseMessage, HumanMessage, AIMessage, BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
import json
import logging
from ..shared.models import OnboardingState
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
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

        # Create agent with tools
        self.agent_graph = create_react_agent(self.llm, self.tools)
        self.workflow = self._create_workflow()

    @classmethod
    async def create(cls, openai_api_key: str) -> OnboardingWorkflow:
        """Create an instance of OnboardingWorkflow with async initialization."""
        server_params = StdioServerParameters(
            command="python",
            args=["run_mcp_server.py"],
            env=None
        )
        # It's important to manage the lifecycle of the stdio_client
        # In this architecture, it will be managed by the FastAPI lifespan
        read, write = await stdio_client(server_params).__aenter__()
        session = await ClientSession(read, write).__aenter__()
        await session.initialize()
        tools = await load_mcp_tools(session)
        
        return cls(openai_api_key, tools, session)

    async def close(self):
        """Close the MCP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("agent", self._run_agent)
        workflow.add_node("update_state", self._update_state)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add edges
        workflow.add_edge("agent", "update_state")
        workflow.add_edge("update_state", END)

        return workflow.compile()

    def _run_agent(self, state: WorkflowState) -> Dict[str, Any]:
        """Run the agent with current state"""
        result = self.agent_graph.invoke(state)
        return {"messages": result["messages"]}

    def _update_state(self, state: WorkflowState) -> Dict[str, Any]:
        """Update onboarding state based on conversation"""
        current_message = state["messages"][-1].content
        onboarding_state = state["onboarding_state"]

        # Use LLM to extract state information from the conversation
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

            # Parse and update state
            updates = json.loads(extraction_response.content)

            for key, value in updates.items():
                if hasattr(onboarding_state, key) and value != "None":
                    setattr(onboarding_state, key, value)

            # Determine current step based on available information
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
            logger.error(f"Error updating state: {e}")
            # Keep current state if extraction fails

        return {"onboarding_state": onboarding_state}

    def process_message(self, message: str, current_state: OnboardingState) -> tuple[str, OnboardingState, bool]:
        """Process a user message and return response, updated state, and completion status"""
        initial_state = WorkflowState(
            messages=[HumanMessage(content=message)],
            onboarding_state=current_state
        )

        # Run the workflow
        result = self.workflow.invoke(initial_state)

        # Extract the AI response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process your request."

        # Check if onboarding is completed
        completed = result["onboarding_state"].step == "completed"

        return response, result["onboarding_state"], completed