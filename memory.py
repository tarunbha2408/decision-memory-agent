from datetime import datetime, timedelta, timezone
from bson import ObjectId
from db import memories
from llm import embed

def now():
    return datetime.now(timezone.utc)

def save_memory(user_id, content, mtype="fact", source="chat", ttl_days=None):
    vec = embed(content)
    similar = recall(user_id, content, k=1, touch=False, mtype=mtype)
    old_id = None
    if similar and similar[0]["score"] > 0.88:
        old_id = similar[0]["_id"]

    doc = {
        "user_id": user_id,
        "type": mtype,
        "content": content,
        "source": source,
        "embedding": vec,
        "status": "active",
        "superseded_by": None,
        "created_at": now(),
        "updated_at": now(),
        "last_accessed_at": None,
    }
    if ttl_days:
        doc["expires_at"] = now() + timedelta(days=ttl_days)

    new_id = memories.insert_one(doc).inserted_id
    if old_id:
        memories.update_one(
            {"_id": old_id},
            {"$set": {"status": "superseded", "superseded_by": new_id, "updated_at": now()}},
        )
    return new_id, old_id

def recall(user_id, query, k=5, touch=True, mtype=None):
    flt = {"user_id": user_id, "status": "active"}
    if mtype:
        flt["type"] = mtype
    pipeline = [
        {"$vectorSearch": {
            "index": "memory_vector_index",
            "path": "embedding",
            "queryVector": embed(query),
            "numCandidates": 100,
            "limit": k,
            "filter": flt,
        }},
        {"$project": {"score": {"$meta": "vectorSearchScore"},
                      "content": 1, "type": 1, "created_at": 1, "expires_at": 1}},
    ]
    results = list(memories.aggregate(pipeline))
    if touch and results:
        memories.update_many(
            {"_id": {"$in": [r["_id"] for r in results]}},
            {"$set": {"last_accessed_at": now()}},
        )
    return results

def list_memories(user_id, include_old=False):
    q = {"user_id": user_id}
    if not include_old:
        q["status"] = "active"
    return list(memories.find(q, {"embedding": 0}).sort("created_at", -1))

def forget(user_id, memory_id):
    return memories.delete_one({"_id": ObjectId(memory_id), "user_id": user_id}).deleted_count
