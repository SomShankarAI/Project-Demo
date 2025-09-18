from __future__ import annotations
from typing import Dict, Any, List, Tuple
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools.base import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from langchain.agents import AgentExecutor
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
    agent_scratchpad: List[BaseMessage]

class OnboardingWorkflow:
    def __init__(self, openai_api_key: str, tools: List[BaseTool], session: ClientSession):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            openai_api_key=openai_api_key
        )
        self.tools = tools
        self.session = session
        self.agent_executor = self._create_agent()
        self.workflow = self._create_workflow()

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

    def _create_agent(self) -> AgentExecutor:
        """Create LangChain agent with MCP tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
             You are an intelligent onboarding assistant. Your goal is to help users complete their onboarding process by collecting the necessary information and using the available tools.
             Your workflow should be:
             1. First, collect the StoreID from the user
             2. Use tool to fetch team and profile information
             3. Use tool to fetch available B2B options
             4. Help the user select their preferred B2B profiles and identities
             5. Use tool to complete the onboarding process
 
             Always be helpful, clear, and guide the user through each step. Don't assume information - ask the user when you need clarification.
             """)
        ])
        self.agent_graph = create_react_agent(model=self.llm,tools= self.tools, debug=True)
        return AgentExecutor(agent = self.agent_graph, tools = self.tools, verbose = True)
    
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
        current_message = state["messages"][-1].content
        onboarding_state = state["onboarding_state"]
        
        # if("agent_scratchpad" not in state):
        #     print("Setting ")
        #     state["agent_scratchpad"] = [HumanMessage("")]

        # Prepare input for agent
        agent_input = {
            "input": current_message,
            "onboarding_state": onboarding_state.model_dump(),
            "agent_scratchpad": []
        }

        #print(type(agent_input["agent_scratchpad"]))
        #print(state)
        
        try:
            # Run agent
            result = self.agent_graph.invoke(agent_input)
            response = result["output"]
            
            # Add AI response to messages
            state["messages"].append(AIMessage(content=response))
            
            return {"messages": state["messages"]}
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            state["messages"].append(AIMessage(content=error_response))
            return {"messages": state["messages"]}

    async def close(self):
        """Close the MCP session."""
        if self.session:
            #await self.session.complete()
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

        # initial_state = WorkflowState(
        #     messages=[HumanMessage(content=message)],
        #     onboarding_state=current_state,
        #     agent_scratchpad=[]
        # )
        
        # Run the workflow
        result = self.workflow.invoke(current_state)
        
        # Extract the AI response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process your request."
        
        # Check if onboarding is completed
        #completed = result["onboarding_state"].step == "completed"
        
        return response, result
        # # 1. Run the agent graph
        # agent_input = {"messages": current_state["messages"]}
        # agent_result = self.workflow.invoke(agent_input)

        # # Update messages in the state
        # current_state["messages"] = agent_result["messages"]

        # # 2. Update the custom onboarding state
        # updated_onboarding_state = self._update_state(current_state)
        # current_state["onboarding_state"] = updated_onboarding_state

        # # 3. Extract the final response for the user
        # ai_messages = [msg for msg in agent_result["messages"] if isinstance(msg, AIMessage)]
        # response = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process your request."

        # return response, current_state