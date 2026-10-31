import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ["MONGODB_URI"])
db = client[os.getenv("DB_NAME", "agent_memory")]
memories = db["memories"]
