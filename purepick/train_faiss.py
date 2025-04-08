import os
import json
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Ensure the "purepick" directory exists
os.makedirs("purepick", exist_ok=True)

# Load allergen data
with open("purepick/allergen_data.json", "r") as file:
    data = json.load(file)

df = pd.DataFrame(data)

# Load Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Convert allergen descriptions into embeddings
embeddings = model.encode(df["Ingredients"].tolist())

# Store in FAISS for fast similarity search
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(np.array(embeddings))

# ✅ Ensure directory exists before saving
faiss_index_path = "purepick/allergen_index.faiss"
csv_path = "purepick/allergen_database.csv"

faiss.write_index(index, faiss_index_path)
df.to_csv(csv_path, index=False)

print(f"✅ FAISS index saved at: {faiss_index_path}")
print(f"✅ Allergen database saved at: {csv_path}")
