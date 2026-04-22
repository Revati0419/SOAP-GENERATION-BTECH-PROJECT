import chromadb
from chromadb.utils import embedding_functions

# Use a multilingual embedding model
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

client = chromadb.PersistentClient(path="./.cache/vector_db")
collection = client.get_or_create_collection(name="clinical_terms", embedding_function=emb_fn)

# The 10 Section Key-Terms for RAG
terms = [
    "Chief Complaint: मुख्य तक्रार, प्राथमिक लक्षणे",
    "HPI: सध्याच्या आजाराचा इतिहास, आजाराची सुरुवात",
    "Trauma: आघाताचा इतिहास, जुने वाईट प्रसंग, पस्तावा",
    "Psychosocial: मनोसामाजिक इतिहास, कुटुंब, मित्र, सामाजिक परिस्थिती",
    "Functional: कार्यक्षम स्थिती, छंद, दैनंदिन काम, शिक्षण",
    "Medical: वैद्यकीय इतिहास, शारीरिक आजार, शस्त्रक्रिया",
    "Past Psych: पूर्व मनोरुग्ण इतिहास, पूर्वीचे उपचार, जुने निदान",
    "Biological: जैविक निरीक्षणे, झोप, भूक, थकवा",
    "MSE: मानसिक स्थिती तपासणी, वागणूक, बोलणे, विचार",
    "Plan: उपचार योजना, औषधे, सुरक्षा, पाठपुरावा"
]

collection.add(
    documents=terms,
    ids=[f"id_{i}" for i in range(len(terms))]
)
print("✅ Clinical Knowledge Base Updated for 10 Subsections!")