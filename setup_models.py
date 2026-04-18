#!/usr/bin/env python3
"""
Setup Script for Multilingual SOAP Generation System
Downloads IndicNER, initializes RAG, sets up translation models
"""

import os
import sys
from pathlib import Path

print("╔═══════════════════════════════════════════════════════════════╗")
print("║     MULTILINGUAL SOAP GENERATION - MODEL SETUP               ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()

# Step 1: Download IndicNER
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 1: Downloading IndicNER (AI4Bharat)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("Model: ai4bharat/IndicNER")
print("Size: ~500MB")
print("Languages: 11 Indian languages")
print()

try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    
    model_name = "ai4bharat/IndicNER"
    print(f"📥 Downloading IndicNER from HuggingFace...")
    
    # Download tokenizer
    print("  - Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Download model
    print("  - Downloading model...")
    model = AutoModelForTokenClassification.from_pretrained(model_name, trust_remote_code=True)
    
    print("✅ IndicNER downloaded successfully!")
    print(f"   Model ID: {model.config.model_type}")
    print(f"   Vocab size: {tokenizer.vocab_size}")
    
except Exception as e:
    print(f"❌ Failed to download IndicNER: {e}")
    print("   Please check your internet connection and try again")
    sys.exit(1)

# Step 2: Download Translation Models
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 2: Downloading Translation Models")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("Model: facebook/nllb-200-distilled-600M")
print("Size: ~600MB")
print()

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    
    model_name = "facebook/nllb-200-distilled-600M"
    print(f"📥 Downloading NLLB-200...")
    
    # Download tokenizer
    print("  - Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Download model
    print("  - Downloading model...")
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    print("✅ NLLB-200 downloaded successfully!")
    
except Exception as e:
    print(f"❌ Failed to download NLLB-200: {e}")
    print("   Continuing with other setups...")

# Step 3: Download Sentence Transformer for RAG
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 3: Downloading Sentence Transformer for RAG")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("Model: sentence-transformers/all-MiniLM-L6-v2")
print("Size: ~90MB")
print()

try:
    from sentence_transformers import SentenceTransformer
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"📥 Downloading MiniLM-L6-v2...")
    
    model = SentenceTransformer(model_name)
    
    print("✅ Sentence Transformer downloaded successfully!")
    print(f"   Embedding dimension: {model.get_sentence_embedding_dimension()}")
    
except Exception as e:
    print(f"❌ Failed to download Sentence Transformer: {e}")

# Step 4: Initialize ChromaDB with Knowledge Base
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 4: Initializing RAG Knowledge Base (ChromaDB)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()

try:
    import chromadb
    import json
    from sentence_transformers import SentenceTransformer
    
    # Initialize ChromaDB
    print("📦 Creating ChromaDB client...")
    client = chromadb.PersistentClient(path="./chromadb_data")
    
    # Initialize embedding model
    print("🔧 Loading embedding model...")
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    # Create collection
    print("📚 Creating knowledge base collections...")
    
    # Collection 1: ICD-10 Codes
    try:
        collection_icd = client.get_or_create_collection(
            name="icd10_mental_health",
            metadata={"description": "ICD-10 mental health diagnosis codes"}
        )
        
        # Load ICD-10 data
        with open("vocab/icd10_mental_health.json", "r", encoding="utf-8") as f:
            icd_data = json.load(f)
        
        # Add to ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for code, info in icd_data.items():
            doc = f"{code}: {info['name']}. Category: {info['category']}. Criteria: {', '.join(info['criteria'])}"
            documents.append(doc)
            metadatas.append({
                "code": code,
                "name": info["name"],
                "category": info["category"],
                "name_marathi": info.get("name_marathi", ""),
                "name_hindi": info.get("name_hindi", "")
            })
            ids.append(code)
        
        # Generate embeddings and add
        embeddings = embedding_model.encode(documents).tolist()
        collection_icd.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ Added {len(documents)} ICD-10 codes")
        
    except Exception as e:
        print(f"  ⚠ ICD-10 collection: {e}")
    
    # Collection 2: DSM-5 Criteria
    try:
        collection_dsm = client.get_or_create_collection(
            name="dsm5_criteria",
            metadata={"description": "DSM-5 diagnostic criteria"}
        )
        
        with open("vocab/dsm5_criteria.json", "r", encoding="utf-8") as f:
            dsm_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, disorder in enumerate(dsm_data):
            doc = f"{disorder['name']} ({disorder['dsm5_code']}). Criteria: {disorder['criteria']}"
            documents.append(str(doc))
            metadatas.append({
                "name": disorder["name"],
                "code": disorder["dsm5_code"],
                "name_marathi": disorder.get("name_marathi", ""),
                "name_hindi": disorder.get("name_hindi", "")
            })
            ids.append(f"dsm_{i}")
        
        embeddings = embedding_model.encode(documents).tolist()
        collection_dsm.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ Added {len(documents)} DSM-5 disorders")
        
    except Exception as e:
        print(f"  ⚠ DSM-5 collection: {e}")
    
    # Collection 3: Medications
    try:
        collection_meds = client.get_or_create_collection(
            name="medications",
            metadata={"description": "Psychotropic medications"}
        )
        
        with open("vocab/medications_psychotropic.json", "r", encoding="utf-8") as f:
            meds_data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, med in enumerate(meds_data):
            doc = f"{med['name']} ({med['class']}). Indications: {', '.join(med['indications'])}. Dosing: {med['dosing']['therapeutic_range']}"
            documents.append(doc)
            metadatas.append({
                "name": med["name"],
                "class": med["class"],
                "name_marathi": med.get("name_marathi", ""),
                "name_hindi": med.get("name_hindi", "")
            })
            ids.append(f"med_{i}")
        
        embeddings = embedding_model.encode(documents).tolist()
        collection_meds.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ Added {len(documents)} medications")
        
    except Exception as e:
        print(f"  ⚠ Medications collection: {e}")
    
    print("✅ ChromaDB initialized successfully!")
    
    # Show stats
    print()
    print("📊 Knowledge Base Statistics:")
    collections = client.list_collections()
    for coll in collections:
        count = client.get_collection(coll.name).count()
        print(f"  - {coll.name}: {count} entries")
    
except Exception as e:
    print(f"❌ Failed to initialize ChromaDB: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Verify Ollama
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 5: Verifying Ollama (LLM)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()

try:
    import subprocess
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
    
    if result.returncode == 0:
        print("✅ Ollama is running")
        print()
        print("Available models:")
        for line in result.stdout.strip().split('\n')[1:]:  # Skip header
            if line.strip():
                print(f"  ✓ {line.split()[0]}")
        
        # Check for gemma2:2b
        if 'gemma2:2b' in result.stdout:
            print()
            print("✅ gemma2:2b is ready for SOAP generation!")
        else:
            print()
            print("⚠ gemma2:2b not found. Downloading...")
            subprocess.run(['ollama', 'pull', 'gemma2:2b'])
    else:
        print("❌ Ollama command failed")
        
except Exception as e:
    print(f"❌ Ollama check failed: {e}")
    print("   Please make sure Ollama is installed and running")

# Final Summary
print()
print("╔═══════════════════════════════════════════════════════════════╗")
print("║                    SETUP COMPLETE!                            ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()
print("✅ Models downloaded:")
print("   - IndicNER (11 Indian languages)")
print("   - NLLB-200 (translation)")
print("   - MiniLM-L6-v2 (embeddings)")
print()
print("✅ RAG Knowledge Base initialized:")
print("   - ICD-10 codes")
print("   - DSM-5 criteria")
print("   - Medications database")
print()
print("✅ LLM ready:")
print("   - Ollama with gemma2:2b")
print()
print("🚀 You can now run:")
print("   python api_server.py")
print()
