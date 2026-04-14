import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

embedding = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
)
csv_path = "DataCleaning/cleaned_data.csv"
df = pd.read_csv(csv_path)
documents = []

for _, row in df.iterrows():
    content = f"""
    Product Name: {row['product_name']}
Brand: {row['brand']}
Category: {row['category_name']}
Price: {row['final_price']} {row['currency']}
Rating: {row['rating']} ({row['review_count']} reviews)

Description:
{row['description']}

Specifications:
{row.get('specifications', '')}

Top Reviews:
{row.get('top_reviews', '')}

Customer Reviews:
{row.get('customer_reviews', '')}

Tags:
{row.get('tags', '')}
"""

    metadata = {
        "product_id": str(row["product_id"]),
        "product_name": row["product_name"],
        "brand": row["brand"],
        "category": row["category_name"],
        "price": float(row["final_price"]),
        "rating": float(row["rating"]),
        "review_count": int(row["review_count"]),
        "currency": row["currency"]
    }
    documents.append(Document(page_content=content, metadata=metadata))

db = Chroma.from_documents(
    documents = documents,
    embedding = embedding,
    persist_directory = "chroma_db"
)

print("completed saving to chroma database")

