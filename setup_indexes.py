from db import memories
memories.create_index("expires_at", expireAfterSeconds=0)
memories.create_index([("user_id", 1), ("status", 1)])
print("Indexes ready")
