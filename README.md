# Decision Memory Agent

An AI assistant that remembers your decisions, preferences and constraints across sessions, and uses them to change its next answer. Built for the MongoDB hackathon, Track 1: Agentic Memory.

**Live demo:** https://fy2mbc3x7erhwubqegxcef.streamlit.app/

## The problem

Most AI assistants forget everything when the chat ends. In a long-running project, decisions, budgets and constraints get repeated again and again, and old assumptions silently go stale. Memory that never updates, expires or can be deleted is just as bad as no memory.

## The solution

Decision Memory Agent turns each conversation into structured memories stored in MongoDB Atlas. On every new message it retrieves the most relevant memories with Vector Search, uses them to answer, and extracts new memories from what the user said. Memories can be corrected, expire automatically, and be deleted by the user.

## Main features

- **Persistent memory across sessions.** Facts, preferences, decisions, constraints, feedback and outcomes are stored as MongoDB documents.
- **Semantic recall.** MongoDB Vector Search finds relevant memories even when the wording differs, filtered by user and status.
- **Visible memory trace.** Every answer shows which memories were used, their similarity score, and which new memories were saved.
- **Corrections without losing history.** If the user changes a decision, the old memory is marked `superseded` and linked to the new one.
- **Time-based expiry.** Temporary information (for example "exams this week") gets an `expires_at` date and is removed automatically by a MongoDB TTL index.
- **User-controlled forgetting.** A Forget button deletes a memory permanently.
- **Privacy guard.** The extraction step is instructed never to store passwords, PINs, OTPs, card numbers or government IDs.
- **Per-visitor memory.** Each visitor gets a guest ID, and every query is scoped to that ID.

## Architecture

```
User message
    |
    v
Streamlit UI (app.py)
    |
    v
Agent (agent.py)
    |-- 1. Embed the message (Gemini embeddings, 768 dims)
    |-- 2. Recall: MongoDB $vectorSearch, filter {user_id, status: "active"}
    |-- 3. Answer with the recalled memories in the prompt (Groq, Gemini fallback)
    |-- 4. Extract new memories as JSON (type, content, ttl_days)
    |-- 5. Save: embed, detect conflict, supersede old memory, set expires_at
    v
MongoDB Atlas: agent_memory.memories
    - Vector Search index: memory_vector_index
    - TTL index on expires_at
```

## Memory document

```json
{
  "user_id": "guest-a1b2c3",
  "type": "decision",
  "content": "We will use FastAPI for the backend",
  "source": "chat",
  "embedding": [0.012, -0.034, "... 768 numbers"],
  "status": "active",
  "superseded_by": null,
  "created_at": "2026-10-31T09:00:00Z",
  "updated_at": "2026-10-31T09:00:00Z",
  "last_accessed_at": null,
  "expires_at": "only present for temporary memories"
}
```

Memory types: `fact`, `preference`, `decision`, `constraint`, `feedback`, `outcome`.

## How MongoDB is used

| Need | MongoDB feature |
| --- | --- |
| Store memories with lifecycle fields | Documents in `agent_memory.memories` |
| Semantic recall scoped to a user | `$vectorSearch` with `filter` on `user_id` and `status` |
| Expire temporary memories | TTL index on `expires_at` (`expireAfterSeconds=0`) |
| Correct a memory without losing history | `status: "superseded"` and `superseded_by` link |
| Track usage | `last_accessed_at` updated on every recall |

## Tech stack

- Python, Streamlit
- MongoDB Atlas (Vector Search, TTL index), PyMongo
- Gemini `gemini-embedding-001` for embeddings (768 dimensions)
- Groq `openai/gpt-oss-120b` for answers and memory extraction, with Gemini as fallback
- Deployed on Streamlit Community Cloud

## Run it locally

```bash
git clone https://github.com/tarunbha2408/decision-memory-agent.git
cd decision-memory-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
MONGODB_URI=mongodb+srv://USER:PASSWORD@YOUR_CLUSTER.mongodb.net/?retryWrites=true&w=majority
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b
DB_NAME=agent_memory
```

Create the indexes once, then start the app:

```bash
python setup_indexes.py     # TTL index and helper index
python make_index.py        # Atlas Vector Search index (wait until it is queryable)
streamlit run app.py
```

## Demo walkthrough

1. Say `We will use FastAPI for the backend`, then `Our budget is only 5000 rupees`. Two memories are saved.
2. Open the app in a new tab with the same `?uid=` in the URL and ask `What was my tech stack and budget?` The answer uses the stored memories, and the Memory trace shows why.
3. Say `Actually, we will use Flask instead of FastAPI`. Tick "Show superseded memories" to see the old decision kept as history.
4. Say `I have exams this week and I am busy`. The memory shows an expiry countdown and is deleted by the TTL index.
5. Say `My ATM PIN is 4321`. Nothing is saved.
6. Click Forget on any memory to delete it.

## Project structure

```
app.py             Streamlit UI and memory trace
agent.py           Recall, answer and memory extraction
memory.py          Save, recall, supersede, forget
llm.py             Embeddings and LLM calls with fallback
db.py              MongoDB connection
make_index.py      Creates the Atlas Vector Search index
setup_indexes.py   Creates the TTL index
```

## Limitations and future work

- The privacy guard is prompt-based, so it reduces but does not eliminate the chance of storing sensitive text. A rule-based filter would be a good addition.
- Guest IDs separate visitors but are not authentication. A real deployment would add sign-in.
- Conflict detection uses a similarity threshold (0.88) within the same memory type.
- MongoDB checks TTL expiry about once a minute, so deletion is not instant.
- Future work: Change Streams for live updates across multiple agents or users, and recency-aware ranking.

## Team Recall

Department of Computer Science and Engineering, SVNIT Surat. All three members worked together on every part of the project: design, backend, database, UI and demo.

- Tarun Katariya
- Vishal Barik
- Krishwal Kumar
