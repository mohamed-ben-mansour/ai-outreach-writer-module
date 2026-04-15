# Agentic Outreach API

A multi-agent AI system that generates personalized sales outreach messages
using Google Gemini 2.5 Flash. The system runs a pipeline of specialized
AI agents that research, strategize, write, and validate messages tailored
to a specific prospect, channel, and offer.

---

## How It Works

The system runs five agents in sequence:
Planner → Researcher → Strategist → Writer → Critic


1. **Planner** - Looks at the current state and decides what step to run next
2. **Researcher** - Fetches LinkedIn posts, company news, and CRM history
3. **Strategist** - Uses Gemini to analyze signals and build a messaging strategy
4. **Writer** - Uses Gemini to write the actual message with full sentence attribution
5. **Critic** - Uses Gemini to score and validate the message, loops back if it fails

---

## Project Structure
agentic-outreach/
├── app/
│ ├── init.py # Makes app a Python package
│ ├── main.py # FastAPI endpoints
│ ├── models.py # All Pydantic models and enums
│ ├── config.py # Settings loaded from .env
│ ├── llm_service.py # All Gemini API calls
│ ├── agents.py # Agent node implementations
│ ├── orchestrator.py # Pipeline control loop
│ └── tools.py # Research tools (mock + real stubs)
├── .env # Your environment variables (not committed)
├── .env.example # Environment variable template
├── requirements.txt # Python dependencies
├── README.md # This file
└── HOW_TO_RUN.md # Setup and execution guide