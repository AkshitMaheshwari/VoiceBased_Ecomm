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

def retreive(query,user_memory):
    filters = {}

    if user_memory.pref["brand"]:
        filters['brand'] = user_memory.pref["brand"]

    if user_memory.pref["category"]:
        filters["category"] = user_memory.pref["category"]

    if user_memory.pref["budget"]:
        filters["price"] = {"$lte":user_memory.pref["budget"]}
    
    return chroma.search(query,k=3,filters = filters if filters else None)
