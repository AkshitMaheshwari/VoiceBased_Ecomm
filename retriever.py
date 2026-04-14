from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"

class ChromaClient:
    def __init__ (self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        )

        self.db = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function = self.embeddings
        )

    def search(self,query,k =3,filters = None):
        if filters:
            return self.db.similarity_search(query,k=k,filter = filters)
        return self.db.similarity_search(query,k=k)
    
chroma = None


def get_chroma():
    global chroma
    if chroma is None:
        chroma = ChromaClient()
    return chroma

def retrieve(query, user_memory):
    """Retrieve products with proper Chroma filter format."""
    conditions = []

    if user_memory.pref["brand"]:
        conditions.append({"brand": user_memory.pref["brand"]})

    if user_memory.pref["category"]:
        conditions.append({"category": user_memory.pref["category"]})

    if user_memory.pref["budget"]:
        conditions.append({"price": {"$lte": user_memory.pref["budget"]}})
    
    # Chroma requires $and for multiple filters
    if len(conditions) > 1:
        filters = {"$and": conditions}
    elif len(conditions) == 1:
        filters = conditions[0]
    else:
        filters = None
    
    return get_chroma().search(query, k=3, filters=filters)
