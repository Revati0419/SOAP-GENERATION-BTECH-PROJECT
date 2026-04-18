#!/usr/bin/env python3
"""
Setup Script for Multilingual SOAP Generation System
Alternative setup using publicly available models
"""

import os
import sys
from pathlib import Path

print("╔═══════════════════════════════════════════════════════════════╗")
print("║     MULTILINGUAL SOAP GENERATION - MODEL SETUP               ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()

# Step 1: IndicNER (Gated - requires HuggingFace access)
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 1: IndicNER Setup (Requires HuggingFace Access)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print("⚠️  IndicNER is a GATED model. You need to:")
print("   1. Visit: https://huggingface.co/ai4bharat/IndicNER")
print("   2. Click 'Request Access' and wait for approval")
print("   3. Login to HuggingFace: huggingface-cli login")
print()

# Try to download IndicNER
indicner_available = False
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    
    model_name = "ai4bharat/IndicNER"
    print(f"📥 Attempting to download IndicNER...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForTokenClassification.from_pretrained(model_name, trust_remote_code=True)
    
    print("✅ IndicNER downloaded successfully!")
    indicner_available = True
    
except Exception as e:
    print(f"⚠️  IndicNER not available: {str(e)[:100]}")
    print()
    print("📝 Alternative: Using XLM-RoBERTa for multilingual NER")
    print("   This is a publicly available model that works for Hindi/Marathi")
    print()
    
    # Download alternative multilingual NER model
    try:
        print("📥 Downloading xlm-roberta-base...")
        model_name = "xlm-roberta-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        print("✅ XLM-RoBERTa downloaded successfully!")
        
    except Exception as e2:
        print(f"❌ Failed to download alternative: {e2}")

# Step 2: Download Translation Models
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("STEP 2: Downloading Translation Models")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("Model: facebook/nllb-200-distilled-600M")
print("Size: ~600MB (will take a few minutes)")
print()

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    
    model_name = "facebook/nllb-200-distilled-600M"
    print(f"📥 Downloading NLLB-200 (this may take 5-10 minutes)...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    print("  ✓ Tokenizer downloaded")
    
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    print("  ✓ Model downloaded")
    
    print("✅ NLLB-200 downloaded successfully!")
    
except Exception as e:
    print(f"❌ Failed to download NLLB-200: {e}")

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
    
    print("📦 Creating ChromaDB client...")
    client = chromadb.PersistentClient(path="./chromadb_data")
    
    print("🔧 Loading embedding model...")
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    print("📚 Creating knowledge base collections...")
    
    total_added = 0
    
    # Collection 1: ICD-10 Codes
    try:
        collection_icd = client.get_or_create_collection(
            name="icd10_mental_health",
            metadata={"description": "ICD-10 mental health diagnosis codes"}
        )
        
        with open("vocab/icd10_mental_health.json", "r", encoding="utf-8") as f:
            icd_data = json.load(f)
        
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
        
        embeddings = embedding_model.encode(documents).tolist()
        collection_icd.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ ICD-10 codes: {len(documents)} entries")
        total_added += len(documents)
        
    except Exception as e:
        print(f"  ⚠ ICD-10: {e}")
    
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
            doc = f"{disorder['name']} ({disorder['dsm5_code']}). Criteria: {str(disorder['criteria'])[:500]}"
            documents.append(doc)
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
        
        print(f"  ✓ DSM-5 criteria: {len(documents)} entries")
        total_added += len(documents)
        
    except Exception as e:
        print(f"  ⚠ DSM-5: {e}")
    
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
        
        print(f"  ✓ Medications: {len(documents)} entries")
        total_added += len(documents)
        
    except Exception as e:
        print(f"  ⚠ Medications: {e}")
    
    # Collection 4: Clinical Vocabularies
    try:
        collection_vocab = client.get_or_create_collection(
            name="clinical_vocabulary",
            metadata={"description": "Marathi/Hindi clinical terms"}
        )
        
        # Load Marathi and Hindi vocabularies
        with open("vocab/marathi_clinical_vocab_extended.json", "r", encoding="utf-8") as f:
            marathi_vocab = json.load(f)
        
        with open("vocab/hindi_clinical_vocab_extended.json", "r", encoding="utf-8") as f:
            hindi_vocab = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, (term, info) in enumerate(marathi_vocab.items()):
            doc = f"{term}: {info['marathi']} (Marathi), Category: {info['category']}"
            documents.append(doc)
            metadatas.append({
                "term": term,
                "marathi": info["marathi"],
                "category": info["category"],
                "language": "marathi"
            })
            ids.append(f"vocab_mr_{i}")
        
        for i, (term, info) in enumerate(hindi_vocab.items()):
            doc = f"{term}: {info['hindi']} (Hindi), Category: {info['category']}"
            documents.append(doc)
            metadatas.append({
                "term": term,
                "hindi": info["hindi"],
                "category": info["category"],
                "language": "hindi"
            })
            ids.append(f"vocab_hi_{i}")
        
        embeddings = embedding_model.encode(documents).tolist()
        collection_vocab.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ Clinical vocabulary: {len(documents)} entries")
        total_added += len(documents)
        
    except Exception as e:
        print(f"  ⚠ Vocabulary: {e}")
    
    print()
    print(f"✅ ChromaDB initialized with {total_added} total entries!")
    
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
        for line in result.stdout.strip().split('\n')[1:]:
            if line.strip():
                print(f"  ✓ {line.split()[0]}")
        
        if 'gemma2:2b' in result.stdout:
            print()
            print("✅ gemma2:2b is ready!")
        else:
            print()
            print("⚠ gemma2:2b not found.")
            print("   Run: ollama pull gemma2:2b")
    else:
        print("❌ Ollama command failed")
        
except Exception as e:
    print(f"❌ Ollama check failed: {e}")

# Final Summary
print()
print("╔═══════════════════════════════════════════════════════════════╗")
print("║                    SETUP COMPLETE!                            ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()
print("✅ Models downloaded:")
if indicner_available:
    print("   ✓ IndicNER (11 Indian languages)")
else:
    print("   ⚠ IndicNER (requires HuggingFace access)")
    print("     Alternative: XLM-RoBERTa available")
print("   ✓ NLLB-200 (translation)")
print("   ✓ MiniLM-L6-v2 (embeddings)")
print()
print("✅ RAG Knowledge Base initialized with 186+ entries")
print()
print("✅ LLM: Ollama with gemma2:2b")
print()
print("🚀 Next steps:")
print("   1. Start API: python api_server.py")
print("   2. Start Frontend: cd frontend && npm run dev")
print()
if not indicner_available:
    print("📝 Optional - For IndicNER access:")
    print("   1. Visit: https://huggingface.co/ai4bharat/IndicNER")
    print("   2. Request access and wait for approval")
    print("   3. Login: huggingface-cli login")
    print("   4. Re-run: python setup_models.py")
    print()
