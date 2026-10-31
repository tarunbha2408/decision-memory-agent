from llm import generate, generate_json
from memory import save_memory, recall

EXTRACT_PROMPT = """Below is a user message. Extract only information worth remembering long-term.
Memory types: fact, preference, decision, constraint, feedback, outcome.
Rules:
- Write every memory in clear, short English, even if the user wrote in another language.
- NEVER extract private data: passwords, PINs, OTPs, card numbers, government IDs.
- If the information is only true for days or weeks (exams, busy week, trip, illness, a deadline),
  set ttl_days to a number (for example 7 for "this week"). If it is long-term, use null.
- Create ONE memory per idea. Do not split one statement into fragments.
- If nothing is worth remembering, return an empty list [].
Return ONLY JSON in this format:
[{"content": "...", "type": "decision", "ttl_days": null}]

User message: """

def chat(user_id: str, message: str):
    recalled = recall(user_id, message, k=5)
    mem_text = "\n".join(f"- [{m['type']}] {m['content']}" for m in recalled) or "(no stored memories)"
    prompt = f"""You are a helpful decision assistant with long-term memory.
Here are the user's stored memories:
{mem_text}

Use these memories when they are relevant to the user's message. Always reply in English,
keep the answer concise, and do not mention that you are reading from a memory list.
User: {message}"""
    reply = generate(prompt)

    extracted = generate_json(EXTRACT_PROMPT + message)
    saved = []
    if isinstance(extracted, list):
        for e in extracted:
            if not isinstance(e, dict) or not e.get("content"):
                continue
            new_id, old_id = save_memory(
                user_id, e["content"], e.get("type", "fact"), ttl_days=e.get("ttl_days")
            )
            saved.append({"content": e["content"], "type": e.get("type"), "replaced_old": bool(old_id)})
    return reply, recalled, saved
