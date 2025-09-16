from typing import Dict, Any, List
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
import json
import logging
from ..shared.models import OnboardingState
from .mcp_client import MCPClient
from .mcp_tools import (
    GetProfileAndTeamNameTool,
    GetB2BProfilesAndIdentitiesTool,
    OnboardUserTool
)

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    onboarding_state: OnboardingState
    agent_scratchpad: List[BaseMessage]


class OnboardingWorkflow:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            openai_api_key=openai_api_key
        )
        self.mcp_client = MCPClient()
        
        # Create MCP tools for LLM
        self.tools = [
            GetProfileAndTeamNameTool(self.mcp_client),
            GetB2BProfilesAndIdentitiesTool(self.mcp_client),
            OnboardUserTool(self.mcp_client)
        ]
        
        # Create agent with tools
        self.agent = self._create_agent()
        self.workflow = self._create_workflow()
    
    def _create_agent(self):
        """Create LangChain agent with MCP tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent onboarding assistant. Your goal is to help users complete their onboarding process by collecting the necessary information and using the available tools.

Your workflow should be:
1. First, collect the Store ID from the user
2. Use get_profile_and_team_name tool to fetch team and profile information
3. Use get_b2b_profiles_and_identities tool to fetch available B2B options
4. Help the user select their preferred B2B profiles and identities
5. Use onboard_user tool to complete the onboarding process

Available tools:
- get_profile_and_team_name: Get team name and profile name for a store ID
- get_b2b_profiles_and_identities: Get available B2B profiles and identities for a store ID  
- onboard_user: Complete the onboarding process with all collected information

Always be helpful, clear, and guide the user through each step. Don't assume information - ask the user when you need clarification.

Current onboarding state: {onboarding_state}
"""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
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
        
        # Prepare input for agent
        agent_input = {
            "input": current_message,
            "onboarding_state": onboarding_state.dict()
        }
        
        try:
            # Run agent
            result = self.agent.invoke(agent_input)
            response = result["output"]
            
            # Add AI response to messages
            state["messages"].append(AIMessage(content=response))
            
            return {"messages": state["messages"]}
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            state["messages"].append(AIMessage(content=error_response))
            return {"messages": state["messages"]}
    
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
            onboarding_state=current_state,
            agent_scratchpad=[]
        )
        
        # Run the workflow
        result = self.workflow.invoke(initial_state)
        
        # Extract the AI response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process your request."
        
        # Check if onboarding is completed
        completed = result["onboarding_state"].step == "completed"
        
        return response, result["onboarding_state"], completed