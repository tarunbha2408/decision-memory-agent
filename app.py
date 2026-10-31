import html
import uuid
from datetime import datetime, timezone

import streamlit as st

from agent import chat
from memory import list_memories, forget

st.set_page_config(page_title="Decision Memory Agent", page_icon="🧠", layout="wide")

TYPE_STYLE = {
    "fact": ("#3b82f6", "Fact"),
    "preference": ("#a855f7", "Preference"),
    "decision": ("#00ED64", "Decision"),
    "constraint": ("#f59e0b", "Constraint"),
    "feedback": ("#ec4899", "Feedback"),
    "outcome": ("#14b8a6", "Outcome"),
}

EXAMPLES = [
    "We will use FastAPI for the backend",
    "Our budget is only 5000 rupees",
    "What was my tech stack and budget?",
]

st.markdown(
    """
<style>
.block-container { padding-top: 2rem; max-width: 1000px; }
.hero-title {
    font-size: 2.2rem; font-weight: 800; line-height: 1.1;
    background: linear-gradient(90deg, #00ED64, #3b82f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { color: #93a4bf; margin: 4px 0 18px 0; }
.mem-card {
    border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid var(--c);
    border-radius: 10px; padding: 10px 12px; margin: 8px 0;
    background: rgba(255,255,255,0.03);
}
.mem-card.old { opacity: 0.55; }
.badge {
    display: inline-block; font-size: 0.68rem; font-weight: 700; letter-spacing: .04em;
    text-transform: uppercase; padding: 2px 8px; border-radius: 999px;
    color: var(--c); border: 1px solid var(--c); margin-right: 6px;
}
.meta { color: #93a4bf; font-size: 0.75rem; margin-top: 6px; }
.bar { height: 6px; border-radius: 99px; background: rgba(255,255,255,0.08); margin-top: 8px; overflow: hidden; }
.bar > div { height: 100%; background: linear-gradient(90deg, #00ED64, #3b82f6); }
</style>
""",
    unsafe_allow_html=True,
)


def time_left(exp):
    if not exp:
        return None
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    secs = int((exp - datetime.now(timezone.utc)).total_seconds())
    if secs <= 0:
        return "expiring now"
    days, rest = divmod(secs, 86400)
    hours, rest = divmod(rest, 3600)
    mins = rest // 60
    if days:
        return f"expires in {days}d {hours}h"
    if hours:
        return f"expires in {hours}h {mins}m"
    return f"expires in {mins}m"


def card(m, score=None, note=None, old=False):
    color, label = TYPE_STYLE.get(m.get("type"), ("#93a4bf", str(m.get("type", "memory")).title()))
    content = html.escape(m.get("content", ""))
    meta = []
    if m.get("status") == "superseded":
        meta.append("superseded")
    left = time_left(m.get("expires_at"))
    if left:
        meta.append("⏳ " + left)
    if note:
        meta.append(note)
    meta_html = f'<div class="meta">{" · ".join(meta)}</div>' if meta else ""
    bar = ""
    if score is not None:
        pct = max(0, min(100, int(score * 100)))
        meta_html = f'<div class="meta">relevance {score:.2f}</div>' + meta_html
        bar = f'<div class="bar"><div style="width:{pct}%"></div></div>'
    cls = "mem-card old" if old else "mem-card"
    return (
        f'<div class="{cls}" style="--c:{color}">'
        f'<span class="badge">{label}</span>{content}{meta_html}{bar}</div>'
    )


def render_trace(recalled, saved, expanded=False):
    title = f"🔍 Memory trace · {len(recalled)} used · {len(saved)} saved"
    with st.expander(title, expanded=expanded):
        st.markdown("**Recalled for this answer**")
        if recalled:
            for r in recalled:
                st.markdown(card(r, score=r.get("score")), unsafe_allow_html=True)
        else:
            st.caption("No relevant memories found.")
        st.markdown("**Saved from this message**")
        if saved:
            for s in saved:
                note = "replaced an older memory" if s.get("replaced_old") else "new memory"
                st.markdown(card(s, note=note), unsafe_allow_html=True)
        else:
            st.caption("Nothing new worth remembering.")


with st.sidebar:
    st.markdown("### 🧠 Memory Store")
    if "uid" not in st.query_params:
        st.query_params["uid"] = "guest-" + uuid.uuid4().hex[:6]
    user_id = st.text_input("User ID", value=st.query_params["uid"])
    if user_id and user_id != st.query_params["uid"]:
        st.query_params["uid"] = user_id
    all_mems = list_memories(user_id, include_old=True)
    n_active = sum(1 for m in all_mems if m["status"] == "active")
    n_old = len(all_mems) - n_active
    c1, c2 = st.columns(2)
    c1.metric("Active", n_active)
    c2.metric("Superseded", n_old)
    show_old = st.checkbox("Show superseded memories")
    types = sorted({m["type"] for m in all_mems})
    chosen = st.multiselect("Filter by type", types, default=types)
    st.divider()
    shown = [m for m in all_mems if m["type"] in chosen and (show_old or m["status"] == "active")]
    if not shown:
        st.caption("No memories yet. Tell the assistant something to remember.")
    for m in shown:
        st.markdown(card(m, old=m["status"] != "active"), unsafe_allow_html=True)
        if m["status"] == "active" and st.button("🗑 Forget", key=str(m["_id"])):
            forget(user_id, m["_id"])
            st.rerun()

st.markdown('<div class="hero-title">Decision Memory Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">An assistant that remembers your decisions, preferences and constraints across sessions.</div>',
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

if not st.session_state.history:
    st.markdown("**Try one of these:**")
    for col, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
        if col.button(example, use_container_width=True):
            st.session_state.pending = example
            st.rerun()

last = len(st.session_state.history) - 1
for i, item in enumerate(st.session_state.history):
    with st.chat_message(item["role"]):
        st.write(item["text"])
        if item["role"] == "assistant":
            render_trace(item["recalled"], item["saved"], expanded=(i == last))

prompt = st.chat_input("Ask something or tell me something to remember...")
if not prompt:
    prompt = st.session_state.pop("pending", None)

if prompt:
    st.session_state.history.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Recalling memories and thinking..."):
            reply, recalled, saved = chat(user_id, prompt)
    st.session_state.history.append(
        {"role": "assistant", "text": reply, "recalled": recalled, "saved": saved}
    )
    st.rerun()
