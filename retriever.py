from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()

class ChromaClient:
    def __init__ (self):
        self.embeddings = HuggingFaceEmbeddings(model_name = os.getenv("EMBEDDING_MODEL"))

        self.db = Chroma(
            persist_directory="./chroma_db",
            embedding_function = self.embeddings
        )

    def search(self,query,k =3,filters = None):
        if filters:
            return self.db.similarity_search(query,k=k,filter = filters)
        return self.db.similarity_search(query,k=k)
    
chroma = ChromaClient()

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
    
    return chroma.search(query, k=3, filters=filters)
