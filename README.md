# LLM-based Onboarding Application

This application consists of three main components:
1. **MCP Tools Server** - Hosts the MCP tools for data retrieval and onboarding
2. **Server App** - FastAPI-based LLM server with LangChain/LangGraph workflow
3. **Client App** - Streamlit-based web interface for user interaction

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure your OpenAI API key:
```bash
cp .env.example .env
```

3. Start the MCP Tools Server:
```bash
python mcp_server/main.py
```

4. Start the Server App:
```bash
python server_app/main.py
```

5. Start the Client App:
```bash
streamlit run client_app/main.py
```

## Project Structure

```
├── mcp_server/          # MCP Tools Server
├── server_app/          # FastAPI LLM Server
├── client_app/          # Streamlit Client
├── shared/              # Shared models and utilities
├── requirements.txt
├── .env.example
└── README.md
```

## Usage

1. Open the Streamlit client in your browser
2. Enter your StoreId when prompted
3. The system will guide you through the onboarding process
4. Review and confirm your B2B profiles and identities
5. Complete the onboarding process