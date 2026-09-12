# DevOps Multi-Agent

A multi-agent DevOps assistant built with:

- Python
- LangGraph
- LangChain
- Google Gemini

## Agents

The system currently contains three specialist agents:

- Kubernetes Agent
- AWS Agent
- Linux Agent

## Architecture

```text
User
 │
 ▼
Supervisor
 │
 ├── Kubernetes Agent
 ├── AWS Agent
 └── Linux Agent