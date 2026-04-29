# Zoho  AI Chatbot

An AI-powered conversational chatbot that connects to Zoho Projects via its REST API. Users authenticate with their own Zoho OAuth credentials and interact through a chat UI using natural language. The backend is a multi-agent LangGraph system on FastAPI — one agent handles queries, another handles write actions with human-in-the-loop confirmation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Next.js 14 Frontend                    │
│  Login Page → OAuth redirect → Chat UI                 │
│  ChatWindow · MessageBubble · ConfirmDialog (HIL)       │
└────────────────────┬────────────────────────────────────┘
                     │ /api/* proxy
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                        │
│                                                         │
│  GET  /auth/login      → Zoho OAuth redirect            │
│  GET  /auth/callback   → Token exchange + session       │
│  GET  /auth/me         → Current user info              │
│  POST /chat            → Send message to agent graph    │
│  POST /chat/confirm    → Confirm or cancel HIL action   │
│  GET  /health          → Health check                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              LangGraph Multi-Agent System               │
│                                                         │
│   ┌──────────┐    query    ┌─────────────────────────┐  │
│   │  Router  │────────────▶│  Query Agent            │  │
│   │  (LLM)   │             │  list_projects          │  │
│   └────┬─────┘             │  list_tasks             │  │
│        │ action            │  get_task_details       │  │
│        │                   │  list_project_members   │  │
│   ┌────▼─────────────────┐ │  get_task_utilisation   │  │
│   │  Action Agent        │ └─────────────────────────┘  │
│   │  create_task  ──┐    │                               │
│   │  update_task    │HIL │                               │
│   │  delete_task  ──┘    │                               │
│   └──────────────────────┘                               │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                     Memory                              │
│  Short-term: in-process dict per session                │
│    - message history, current project/task context      │
│  Long-term: SQLite via SQLAlchemy                       │
│    - last accessed project restored on next login       │
└─────────────────────────────────────────────────────────┘
```

### The 8 Tools

| # | Tool | Agent | Operation |
|---|------|-------|-----------|
| 1 | `list_projects` | Query | Fetch all projects |
| 2 | `list_tasks` | Query | List tasks with filters |
| 3 | `get_task_details` | Query | Full task details by ID |
| 4 | `list_project_members` | Query | Members + roles |
| 5 | `get_task_utilisation` | Query | Task load per member |
| 6 | `create_task` | Action (HIL) | Create a new task |
| 7 | `update_task` | Action (HIL) | Update status/assignee/due/priority |
| 8 | `delete_task` | Action (HIL) | Delete a task |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Zoho account with a registered OAuth app
- An OpenAI API key (GPT-4o-mini)

### 1. Register a Zoho OAuth App

1. Go to [Zoho API Console](https://api-console.zoho.com/)
2. Click **Add Client** → choose **Server-based Applications**
3. Set **Authorized Redirect URI** to: `http://localhost:8000/auth/callback`
4. Note your **Client ID** and **Client Secret**
5. The app requests these scopes automatically:
   ```
   ZohoProjects.portals.READ
   ZohoProjects.projects.READ
   ZohoProjects.tasks.READ
   ZohoProjects.tasks.CREATE
   ZohoProjects.tasks.UPDATE
   ZohoProjects.tasks.DELETE
   ZohoProjects.users.READ
   ```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv backend/.venv

# Windows
backend\.venv\Scripts\activate

# Mac/Linux
source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Create your .env file
copy backend\.env.example backend\.env   # Windows
cp backend/.env.example backend/.env     # Mac/Linux
```

Edit `backend/.env`:

```env
ZOHO_CLIENT_ID=your_client_id_here
ZOHO_CLIENT_SECRET=your_client_secret_here
ZOHO_REDIRECT_URI=http://localhost:8000/auth/callback
OPENAI_API_KEY=sk-...
SECRET_KEY=any-random-string-at-least-32-chars
DATABASE_URL=sqlite+aiosqlite:///./chatbot.db
FRONTEND_URL=http://localhost:3000
```

Start the backend:

```bash
# From the project root
backend\.venv\Scripts\python -m uvicorn backend.main:app --port 8000 --host 0.0.0.0

# With auto-reload (dev mode) — use the helper script to avoid venv reload loop
backend\.venv\Scripts\python backend/start.py
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Usage

1. Visit `http://localhost:3000`
2. Click **Sign in with Zoho** — you'll be redirected to Zoho's OAuth screen
3. Authorize the app
4. You're redirected back to the chat interface

### Example Conversations

| You say | What happens |
|---------|-------------|
| `What projects do I have?` | Router → Query Agent → `list_projects` |
| `Show tasks for the first one` | Short-term memory resolves "first one" → `list_tasks` |
| `Create a task called API Integration` | Router → Action Agent → HIL confirmation dialog |
| `Delete task #123` | Action Agent → shows exactly what will be deleted → waits for Yes/No |
| `Who has the most tasks this month?` | Query Agent → `get_task_utilisation` → summary |
| `Update task 456 to In Progress` | Action Agent → HIL → `update_task` on confirm |

---

## Project Structure

```
zoho/
├── backend/
│   ├── agents/
│   │   ├── action_agent.py     # Write operations + intent parsing
│   │   ├── graph.py            # LangGraph StateGraph + run_graph()
│   │   ├── query_agent.py      # Read-only operations
│   │   ├── supervisor.py       # Orchestrator class
│   │   └── tools.py            # All 8 LangChain tools
│   ├── auth/
│   │   ├── middleware.py       # Session cookie auth
│   │   └── zoho_oauth.py       # OAuth helpers
│   ├── db/
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   └── models.py           # User, ConversationMemory, ChatSession
│   ├── memory/
│   │   ├── long_term.py        # DB-backed per-user memory
│   │   └── short_term.py       # In-process session memory
│   ├── routers/
│   │   ├── auth.py             # /auth/* endpoints
│   │   └── chat.py             # /chat endpoints
│   ├── schemas/
│   │   ├── auth.py             # Pydantic auth models
│   │   └── chat.py             # Pydantic chat models
│   ├── zoho/
│   │   └── client.py           # ZohoClient with auto token refresh
│   ├── config.py               # Settings via pydantic-settings
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx        # Login / landing page
│       │   └── chat/page.tsx   # Chat page (auth-gated)
│       ├── components/
│       │   ├── ChatWindow.tsx  # Main chat UI
│       │   ├── ConfirmDialog.tsx # HIL confirmation
│       │   └── MessageBubble.tsx # Message rendering
│       └── lib/
│           └── api.ts          # Backend API client
└── README.md
```

---

## Known Limitations

- **Concurrency**: The `_request_context` pattern for passing `ZohoClient` into LangGraph nodes is safe for async but not for true multi-threaded deployments. Use a proper context-var approach for production.
- **Portal caching**: Portal ID is cached per `ZohoClient` instance (per request). A Redis cache would be better at scale.
- **Streaming**: Responses are returned in full — no streaming. Easily added with FastAPI `StreamingResponse` + LangChain streaming callbacks.
- **SQLite**: Fine for development. Swap `DATABASE_URL` for a PostgreSQL connection string in production.
- **Session storage**: Short-term memory lives in-process. In a multi-worker deployment, use Redis.
- **Token storage**: Access/refresh tokens are stored in plaintext in SQLite. Encrypt at rest for production.
