import streamlit as st
import httpx
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Configuration
SERVER_URL = f"http://{os.getenv('SERVER_HOST', 'localhost')}:{os.getenv('SERVER_PORT', '8000')}"

# Page configuration
st.set_page_config(
    page_title="ACIS Onboarding Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #667eea;
    }
    
    .assistant-message {
        background-color: #e8f4fd;
        border-left-color: #1f77b4;
    }
    
    .state-info {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = "default"
    if "onboarding_state" not in st.session_state:
        st.session_state.onboarding_state = {}
    if "completed" not in st.session_state:
        st.session_state.completed = False


def send_message(message: str) -> Dict[str, Any]:
    """Send message to the server and get response"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{SERVER_URL}/chat",
                json={
                    "message": message,
                    "session_id": st.session_state.session_id
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        st.error(f"Connection error: {e}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"Server error: {e}")
        return None


def reset_session():
    """Reset the current session"""
    try:
        with httpx.Client(timeout=10.0) as client:
            client.delete(f"{SERVER_URL}/session/{st.session_state.session_id}")
        
        # Clear session state
        st.session_state.messages = []
        st.session_state.onboarding_state = {}
        st.session_state.completed = False
        st.success("Session reset successfully!")
    except Exception as e:
        st.error(f"Error resetting session: {e}")


def display_onboarding_state(state: Dict[str, Any]):
    """Display current onboarding state"""
    if not state:
        return
    
    st.markdown("### 📊 Current Onboarding Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Basic Information:**")
        st.write(f"• Store ID: {state.get('store_id', 'Not provided')}")
        st.write(f"• Team Name: {state.get('team_name', 'Not fetched')}")
        st.write(f"• Profile Name: {state.get('profile_name', 'Not fetched')}")
        st.write(f"• Current Step: {state.get('step', 'initial')}")
    
    with col2:
        st.markdown("**B2B Information:**")
        
        profiles = state.get('b2b_profiles', [])
        if profiles:
            st.write("Available Profiles:")
            for profile in profiles:
                st.write(f"  - {profile}")
        else:
            st.write("• Available Profiles: Not fetched")
        
        identities = state.get('b2b_identities', [])
        if identities:
            st.write("Available Identities:")
            for identity in identities:
                st.write(f"  - {identity}")
        else:
            st.write("• Available Identities: Not fetched")
    
    # Show selections if made
    selected_profiles = state.get('selected_profiles', [])
    selected_identities = state.get('selected_identities', [])
    
    if selected_profiles or selected_identities:
        st.markdown("**Your Selections:**")
        if selected_profiles:
            st.write(f"Selected Profiles: {', '.join(selected_profiles)}")
        if selected_identities:
            st.write(f"Selected Identities: {', '.join(selected_identities)}")


def main():
    """Main application function"""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 ACIS Onboarding Assistant</h1>
        <p>Your intelligent guide through the onboarding process</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🛠️ Controls")
        
        if st.button("🔄 Reset Session", type="secondary"):
            reset_session()
            st.rerun()
        
        st.markdown("### ℹ️ How it works")
        st.markdown("""
        1. **Provide Store ID**: Start by giving your store identifier
        2. **Review Information**: The system fetches your team and profile details
        3. **Select Options**: Choose from available B2B profiles and identities
        4. **Complete Onboarding**: Confirm and finalize your setup
        """)
        
        # Display current state
        if st.session_state.onboarding_state:
            with st.expander("📋 Current State", expanded=False):
                display_onboarding_state(st.session_state.onboarding_state)
    
    # Main chat interface
    st.markdown("### 💬 Chat with the Assistant")
    
    # Display completion message if onboarding is done
    if st.session_state.completed:
        st.markdown("""
        <div class="success-message">
            <h3>🎉 Onboarding Completed!</h3>
            <p>Your onboarding process has been successfully completed. You can start a new session if needed.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong> {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>Assistant:</strong> {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    
    # Chat input
    if not st.session_state.completed:
        user_input = st.chat_input("Type your message here...")
        
        if user_input:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Send to server and get response
            with st.spinner("Processing your message..."):
                response_data = send_message(user_input)
            
            if response_data:
                # Add assistant response to chat
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_data["response"]
                })
                
                # Update state
                st.session_state.onboarding_state = response_data["state"]
                st.session_state.completed = response_data["completed"]
                
                # Rerun to update the display
                st.rerun()
    
    # Welcome message for new users
    if not st.session_state.messages:
        st.markdown("""
        <div class="chat-message assistant-message">
            <strong>Assistant:</strong> Welcome to the ACIS Onboarding Assistant! 👋<br><br>
            I'm here to help you through the onboarding process. To get started, I'll need your Store ID. 
            You can say something like "My store ID is ABC123" or just provide the ID directly.
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()