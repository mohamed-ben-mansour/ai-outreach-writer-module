# Agentic Outreach API

A multi-agent AI system that generates personalized sales outreach messages, validates them, waits for human approval, and sends them automatically via email or LinkedIn.

Built with FastAPI, LangGraph, Google Gemini, and MCP.

---

## How It Works

A request comes in with a prospect, channel, offer, and sender personality. Five agents run in sequence inside a LangGraph pipeline:

```
Planner → Researcher → Strategist → Writer → Critic
                                         ↑         |
                                         └─REVISING─┘
```

1. **Planner** — looks at the current state and decides what to do next
2. **Researcher** — fetches LinkedIn posts, company news, CRM history, and loads prospect memory
3. **Strategist** — calls Gemini to pick the best hook and build a messaging strategy
4. **Writer** — calls Gemini to write the message, respects channel length limits, can emulate the sender's voice from past message samples
5. **Critic** — scores the message 0-100, runs hard rule checks (length, banned phrases, placeholders), loops back to the Writer with specific feedback if it fails

If `ENABLE_HUMAN_REVIEW=true`, the pipeline pauses after the Critic approves and waits for a human decision before sending.

---

## Project Structure

```
agentic-outreach/
├── app/
│   ├── main.py          # FastAPI endpoints + human review routes
│   ├── models.py        # All Pydantic models and enums
│   ├── config.py        # Settings loaded from .env
│   ├── agents.py        # Agent logic (Planner, Researcher, Strategist, Writer, Critic)
│   ├── orchestrator.py  # Builds initial state, delegates to LangGraph
│   ├── graph.py         # LangGraph StateGraph — wires agents and routing
│   ├── llm_service.py   # All Gemini API calls with exponential backoff
│   ├── tools.py         # Research tools (mock + real API stubs)
│   ├── memory.py        # Per-prospect + global learning memory
│   ├── send_tools.py    # Email (Gmail SMTP) and LinkedIn (Unipile) sending
│   └── mcp_server.py    # MCP server — exposes pipeline as tools for external agents
├── Dockerfile
├── docker-compose.yml
├── .env
├── .env.example
└── requirements.txt
```

---

## Quickstart

### Option 1 — Docker (recommended)

```bash
cp .env.example .env
# Fill in GOOGLE_API_KEY in .env
docker-compose up --build
```

### Option 2 — Local

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in GOOGLE_API_KEY in .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is at `http://localhost:8000`
Swagger UI is at `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | yes | Gemini API key from [makersuite.google.com](https://makersuite.google.com/app/apikey) |
| `GEMINI_MODEL` | no | Default: `gemini-2.5-flash-lite-preview-06-17` |
| `GEMINI_FALLBACK_MODEL` | no | Default: `models/gemma-3-27b-it` — used if primary fails |
| `MIN_QUALITY_SCORE` | no | Default: `80` — minimum score for a message to pass |
| `MAX_ITERATIONS` | no | Default: `3` — max Writer→Critic revision cycles |
| `USE_MOCK_DATA` | no | Default: `true` — uses fake LinkedIn/news/CRM data |
| `ENABLE_HUMAN_REVIEW` | no | Default: `false` — pause pipeline for human approval before sending |
| `GMAIL_ADDRESS` | for email send | Your Gmail address |
| `GMAIL_APP_PASSWORD` | for email send | Gmail App Password (not your account password) |
| `UNIPILE_API_KEY` | for LinkedIn send | From your Unipile dashboard |
| `UNIPILE_DSN` | for LinkedIn send | e.g. `api4.unipile.com:13465` |
| `UNIPILE_DEFAULT_ACCOUNT_ID` | for LinkedIn send | Your connected LinkedIn account ID in Unipile |

---

## API Endpoints

### Generate a message

```
POST /api/generate/simple
```

Returns the final message, score, and warnings. If `ENABLE_HUMAN_REVIEW=true`, returns a `review_url` instead of sending immediately.

```json
{
  "target_prospect": "Sarah Chen",
  "target_company": "Ramp",
  "prospect_role": "VP of Sales",
  "channel": "linkedin_dm",
  "stage": "first_touch",
  "intent": "direct_outreach",
  "personality": {
    "base_template": "soft_sell",
    "personality_traits": ["curious", "direct"],
    "never_use_phrases": ["synergies", "circle back"],
    "touchdowns_per_message": 2,
    "urgency_level": 2,
    "humor_sarcasm": 3,
    "voice_samples": [
      "Hey John, saw your post about the Q3 push — respect. Curious if a quick chat makes sense?",
      "Not gonna pitch you hard — just thought our audit might save you some pain before the ramp-up."
    ]
  },
  "company_details": {
    "company_name": "SalesForce AI",
    "elevator_pitch": "We help SDR teams double their reply rates using AI personalization.",
    "social_proof": ["Used by 500+ sales teams"]
  },
  "selected_offer": {
    "offer_name": "SDR Efficiency Audit",
    "solution_summary": "A diagnostic of your SDR workflow with a prioritized action plan.",
    "proof_points": ["Teams saw 40% more meetings in 30 days"],
    "cta": "Open to a quick 15-min chat?"
  }
}
```

```
POST /api/generate        — same pipeline, returns full step-by-step history
```

### Human review (when ENABLE_HUMAN_REVIEW=true)

```
GET  /api/review/{task_id}            — see the draft waiting for approval
POST /api/review/{task_id}/decision   — approve or reject
```

Approve and send via email:
```json
{ "approved": true, "prospect_email": "sarah@ramp.com" }
```

Approve and send via LinkedIn:
```json
{ "approved": true, "prospect_linkedin_id": "ACoAAA..." }
```

Reject with feedback (triggers a rewrite):
```json
{ "approved": false, "feedback": "Too formal, make it more casual and shorter" }
```

---

## Sender Voice Emulation

Pass `voice_samples` in the `personality` block — 3 to 5 real messages you've written before. The Writer will analyze your sentence rhythm, vocabulary, punctuation habits, and opening/closing patterns, then write in your voice instead of a generic AI tone.

---

## Memory System

The system remembers every prospect across runs:

- hooks and angles already used (so it never repeats them)
- how many times the prospect has been contacted
- whether they ever replied
- do-not-contact flag

Memory is in-process by default (lost on restart). Swap `_InMemoryStore` in `memory.py` for Redis or Postgres — the interface is already designed for it.

---

## MCP — Agent-to-Agent

The pipeline is exposed as an MCP server at `/mcp`. Any external agent that speaks MCP (Claude Desktop, another LangGraph agent) can connect and call:

- `generate_outreach` — run the full pipeline
- `check_prospect` — look up prospect memory
- `mark_do_not_contact` — flag a prospect

Add to your `mcp.json`:
```json
{
  "mcpServers": {
    "agentic-outreach": {
      "url": "http://localhost:8000/mcp",
      "transport": "sse"
    }
  }
}
```

---

## Email Setup (Gmail SMTP — free)

1. Enable 2FA on your Google account
2. Go to `myaccount.google.com` → Security → App Passwords
3. Generate a password for "Mail"
4. Set `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` in `.env`

## LinkedIn Setup (Unipile)

1. Sign up at [unipile.com](https://unipile.com)
2. Connect your LinkedIn account
3. Copy your DSN, API key, and account ID into `.env`
