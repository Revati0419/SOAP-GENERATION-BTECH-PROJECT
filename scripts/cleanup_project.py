"""
Project Cleanup and Restructuring Script
-----------------------------------------
Cleans up unnecessary files, organizes structure, and prepares for production
"""

import os
import shutil
from pathlib import Path
import json

class ProjectCleaner:
    def __init__(self, project_root='.'):
        self.root = Path(project_root)
        self.backup_dir = self.root / 'backup_old_files'
        self.deleted_items = []
        self.moved_items = []
        
    def create_backup_dir(self):
        """Create backup directory for moved files"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
            print(f"✅ Created backup directory: {self.backup_dir}")
    
    def delete_parsed_data(self):
        """Delete parsed data directory (20MB, not needed)"""
        parsed_dir = self.root / 'data' / 'parsed'
        
        if parsed_dir.exists():
            print("\n🗑️  DELETING PARSED DATA")
            print("-" * 80)
            print(f"Location: {parsed_dir}")
            
            # Get size
            total_size = sum(f.stat().st_size for f in parsed_dir.rglob('*') if f.is_file())
            print(f"Size: {total_size / (1024*1024):.1f} MB")
            
            # Count files
            file_count = len(list(parsed_dir.glob('*.json')))
            print(f"Files: {file_count}")
            
            confirm = input("\n⚠️  Delete parsed data? This saves 20MB. [y/n]: ").lower()
            
            if confirm == 'y':
                shutil.rmtree(parsed_dir)
                self.deleted_items.append(('directory', str(parsed_dir), total_size))
                print("✅ Deleted parsed data directory")
            else:
                print("⏭️  Skipped")
        else:
            print("ℹ️  Parsed data directory not found")
    
    def cleanup_pycache(self):
        """Remove all __pycache__ directories"""
        print("\n🗑️  CLEANING __pycache__ DIRECTORIES")
        print("-" * 80)
        
        pycache_dirs = list(self.root.rglob('__pycache__'))
        
        if pycache_dirs:
            total_size = 0
            for pdir in pycache_dirs:
                size = sum(f.stat().st_size for f in pdir.rglob('*') if f.is_file())
                total_size += size
                shutil.rmtree(pdir)
                self.deleted_items.append(('pycache', str(pdir), size))
            
            print(f"✅ Removed {len(pycache_dirs)} __pycache__ directories ({total_size / 1024:.1f} KB)")
        else:
            print("✅ No __pycache__ directories found")
    
    def retire_old_markdown_files(self):
        """Move old/messy markdown files to backup"""
        print("\n📦 RETIRING OLD DOCUMENTATION")
        print("-" * 80)
        
        docs_dir = self.root / 'docs'
        
        # Check if docs exist
        if not docs_dir.exists():
            print("ℹ️  No docs directory found")
            return
        
        md_files = list(docs_dir.glob('*.md'))
        
        if not md_files:
            print("ℹ️  No markdown files found")
            return
        
        print(f"Found {len(md_files)} markdown files:")
        for md_file in md_files:
            print(f"  • {md_file.name}")
        
        print(f"\nThese will be moved to: {self.backup_dir / 'old_docs'}")
        confirm = input("\n⚠️  Move old docs to backup? [y/n]: ").lower()
        
        if confirm == 'y':
            backup_docs = self.backup_dir / 'old_docs'
            backup_docs.mkdir(parents=True, exist_ok=True)
            
            for md_file in md_files:
                shutil.move(str(md_file), str(backup_docs / md_file.name))
                self.moved_items.append(('markdown', str(md_file), str(backup_docs / md_file.name)))
            
            print(f"✅ Moved {len(md_files)} files to backup")
        else:
            print("⏭️  Skipped")
    
    def cleanup_old_pipeline_files(self):
        """Remove old/unused pipeline scripts"""
        print("\n🗑️  CLEANING OLD PIPELINE FILES")
        print("-" * 80)
        
        pipeline_dir = self.root / 'pipeline'
        
        # Files to potentially remove (keep only essential ones)
        old_files = [
            'generate_soap.py',  # Old version, we use v2
        ]
        
        files_to_remove = []
        for filename in old_files:
            filepath = pipeline_dir / filename
            if filepath.exists():
                files_to_remove.append(filepath)
        
        if files_to_remove:
            print("Old pipeline files found:")
            for f in files_to_remove:
                print(f"  • {f.name}")
            
            confirm = input("\n⚠️  Move to backup? [y/n]: ").lower()
            
            if confirm == 'y':
                backup_pipeline = self.backup_dir / 'old_pipeline'
                backup_pipeline.mkdir(parents=True, exist_ok=True)
                
                for f in files_to_remove:
                    shutil.move(str(f), str(backup_pipeline / f.name))
                    self.moved_items.append(('pipeline', str(f), str(backup_pipeline / f.name)))
                
                print(f"✅ Moved {len(files_to_remove)} files to backup")
            else:
                print("⏭️  Skipped")
        else:
            print("✅ No old pipeline files found")
    
    def organize_soap_notes(self):
        """Organize SOAP notes output"""
        print("\n📋 ORGANIZING SOAP NOTES")
        print("-" * 80)
        
        soap_dir = self.root / 'data' / 'soap_notes'
        
        if not soap_dir.exists():
            print("ℹ️  No soap_notes directory found")
            return
        
        # Count different types
        json_files = list(soap_dir.glob('*_soap.json'))
        html_files = list(soap_dir.glob('*.html'))
        txt_files = list(soap_dir.glob('*.txt'))
        
        print(f"SOAP notes structure:")
        print(f"  • JSON files: {len(json_files)}")
        print(f"  • HTML files: {len(html_files)}")
        print(f"  • TXT files: {len(txt_files)}")
        
        # Keep only JSON files (main format)
        if html_files or txt_files:
            print(f"\nHTML/TXT files are temporary - move to backup?")
            confirm = input("⚠️  Move HTML/TXT to backup? [y/n]: ").lower()
            
            if confirm == 'y':
                backup_soap = self.backup_dir / 'old_soap_formats'
                backup_soap.mkdir(parents=True, exist_ok=True)
                
                for f in html_files + txt_files:
                    shutil.move(str(f), str(backup_soap / f.name))
                    self.moved_items.append(('soap_format', str(f), str(backup_soap / f.name)))
                
                print(f"✅ Moved {len(html_files) + len(txt_files)} files to backup")
            else:
                print("⏭️  Skipped")
        else:
            print("✅ Only JSON files present (clean!)")
    
    def create_project_structure_doc(self):
        """Create clean PROJECT_STRUCTURE.md"""
        print("\n📝 CREATING PROJECT STRUCTURE DOCUMENTATION")
        print("-" * 80)
        
        structure_doc = """# SOAP Generation - Project Structure

## 📁 Directory Overview

```
SOAP-GENERATION-BTECH-PROJECT/
│
├── 📂 data/                          # All datasets
│   ├── dialect_marathi/              # Translated transcripts (5 dialects)
│   ├── labels/                       # PHQ-8 scores and metadata
│   ├── soap_notes/                   # Generated SOAP notes (OUTPUT)
│   └── sessions_index.csv            # Session metadata
│
├── 📂 src/                           # Core source code (modular)
│   ├── generation/                   # SOAP generation using LLMs
│   ├── translation/                  # Open-source translation
│   ├── ner/                          # Named Entity Recognition
│   ├── rag/                          # RAG for clinical terminology
│   └── utils/                        # Helper functions
│
├── 📂 pipeline/                      # Data processing scripts
│   ├── download.py                   # Download DAIC-WOZ dataset
│   ├── parse_transcripts.py         # Parse raw transcripts
│   ├── translate.py                  # Translate to Marathi
│   ├── transform_dialects.py        # Create dialect variations
│   ├── generate_soap_v2.py          # ⭐ Main SOAP generation
│   └── ...
│
├── 📂 scripts/                       # Utility scripts
│   ├── validate_soap_notes.py       # Automated quality checks
│   ├── manual_review_interface.py   # Interactive review tool
│   └── cleanup_project.py           # This cleanup script
│
├── 📂 configs/                       # Configuration files
│   └── config.yaml                   # Model and path configs
│
├── 📂 logs/                          # Processing logs
│
├── 📂 notebooks/                     # Jupyter notebooks (experiments)
│
├── 📂 tests/                         # Unit tests
│
├── 📂 References/                    # Research papers, docs
│
├── 📂 .venv/                         # Python virtual environment
│
├── requirements.txt                  # Python dependencies
├── README.md                         # Project overview
└── run_pipeline.py                   # Main pipeline orchestrator

```

## 🔄 Data Flow

```
DAIC-WOZ Raw Data
      ↓
[download.py] → Parse transcripts
      ↓
[parse_transcripts.py] → Extract conversations
      ↓
[translate.py] → Translate to Marathi
      ↓
[transform_dialects.py] → Create dialect variations
      ↓
data/dialect_marathi/ (182 sessions × 5 dialects)
      ↓
[generate_soap_v2.py] → Generate SOAP notes
      ↓
data/soap_notes/ (182 SOAP notes - bilingual)
      ↓
[validate_soap_notes.py] → Quality checks
      ↓
[manual_review_interface.py] → Human review
      ↓
Training Dataset (for LoRA/QLoRA fine-tuning)
```

## 🎯 Key Files

### Generation
- **`pipeline/generate_soap_v2.py`** - Main SOAP generation script
  - Uses Ollama (Gemma 2 2B / Llama 3.1 8B)
  - Bilingual output (English + Marathi)
  - Clinical prompt template

### Validation
- **`scripts/validate_soap_notes.py`** - Automated quality checks
  - Completeness, language quality, consistency
  - Smart sampling strategy
  
- **`scripts/manual_review_interface.py`** - Interactive review
  - Manual quality assessment
  - Review logging

### Configuration
- **`configs/config.yaml`** - Central configuration
  - Model names and paths
  - Language settings
  - Entity types

## 📊 Dataset Information

### Input Data
- **Source**: DAIC-WOZ (Distress Analysis Interview Corpus)
- **Sessions**: 182 mental health interviews
- **Languages**: English (original) + Marathi (5 dialects)
- **Metadata**: PHQ-8 scores, demographics

### Output Data
- **Format**: JSON (structured SOAP notes)
- **Sections**: Subjective, Objective, Assessment, Plan
- **Languages**: English + Marathi (parallel)

## 🛠️ Development Workflow

### 1. Initial Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Generate SOAP Notes
```bash
# Single test
python pipeline/generate_soap_v2.py --test --model gemma2:2b

# All sessions
python pipeline/generate_soap_v2.py --model gemma2:2b
```

### 3. Validate Quality
```bash
# Automated checks
python scripts/validate_soap_notes.py

# Manual review
python scripts/manual_review_interface.py
```

### 4. Training (Future)
```bash
# LoRA/QLoRA fine-tuning on validated dataset
python scripts/train_lora.py --config configs/training_config.yaml
```

## 📦 Dependencies

### Core Libraries
- **transformers** - Hugging Face models
- **ollama** - Local LLM inference
- **googletrans** - Translation API
- **PyYAML** - Configuration management

### Optional
- **peft** - LoRA/QLoRA training
- **bitsandbytes** - 4-bit quantization
- **chromadb** - Vector database for RAG

## 🎓 B.Tech Project Components

### Phase 1: Data Generation ✅
- Download and preprocess DAIC-WOZ
- Translate to Marathi dialects
- Generate initial SOAP notes

### Phase 2: Validation (In Progress)
- Automated quality metrics
- Manual review and sampling
- Quality confidence assessment

### Phase 3: Model Training (Next)
- LoRA/QLoRA fine-tuning
- Baseline model creation
- Evaluation metrics

### Phase 4: Human-in-the-Loop (Future)
- Web interface for doctor feedback
- Correction collection system
- Incremental retraining

## 📚 Documentation

- **README.md** - Project overview and quick start
- **PROJECT_STRUCTURE.md** - This file (architecture)
- See `backup_old_files/old_docs/` for archived documentation

## 🗑️ Cleanup Notes

This project has been cleaned up on 2026-03-05:
- Removed parsed data (~20MB, not needed)
- Archived old documentation files
- Cleaned up __pycache__ directories
- Organized SOAP notes output
- Created this structure document

---

**Last Updated**: March 5, 2026
**Version**: 1.0
**Author**: B.Tech Project Team
"""
        
        structure_file = self.root / 'PROJECT_STRUCTURE.md'
        with open(structure_file, 'w', encoding='utf-8') as f:
            f.write(structure_doc)
        
        print(f"✅ Created: {structure_file}")
    
    def create_cleanup_summary(self):
        """Create summary report"""
        print("\n" + "=" * 80)
        print("CLEANUP SUMMARY")
        print("=" * 80)
        
        # Calculate space saved
        total_deleted = sum(size for _, _, size in self.deleted_items)
        
        print(f"\n📊 Statistics:")
        print(f"  • Items deleted: {len(self.deleted_items)}")
        print(f"  • Items moved to backup: {len(self.moved_items)}")
        print(f"  • Space saved: {total_deleted / (1024*1024):.1f} MB")
        
        if self.deleted_items:
            print(f"\n🗑️  Deleted Items:")
            for item_type, path, size in self.deleted_items:
                print(f"  • {item_type:12s}: {Path(path).name:30s} ({size / (1024*1024):.1f} MB)")
        
        if self.moved_items:
            print(f"\n📦 Moved to Backup:")
            for item_type, old_path, new_path in self.moved_items:
                print(f"  • {item_type:12s}: {Path(old_path).name}")
        
        print(f"\n💾 Backup Location: {self.backup_dir}")
        print("\n✅ Project cleanup complete!")
        
        # Save summary
        summary = {
            'date': '2026-03-05',
            'deleted': [
                {'type': t, 'path': p, 'size': s} 
                for t, p, s in self.deleted_items
            ],
            'moved': [
                {'type': t, 'from': f, 'to': t} 
                for t, f, t in self.moved_items
            ],
            'total_space_saved_mb': total_deleted / (1024*1024)
        }
        
        summary_file = self.backup_dir / 'cleanup_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Cleanup summary saved to: {summary_file}")
    
    def run_full_cleanup(self):
        """Run all cleanup tasks"""
        print("=" * 80)
        print("PROJECT CLEANUP AND RESTRUCTURING")
        print("=" * 80)
        print(f"\nProject Root: {self.root.absolute()}")
        print("\nThis script will:")
        print("  1. Delete parsed data (~20MB)")
        print("  2. Clean __pycache__ directories")
        print("  3. Retire old markdown files")
        print("  4. Clean old pipeline files")
        print("  5. Organize SOAP notes")
        print("  6. Create project structure documentation")
        print("\nAll removed items will be backed up to: backup_old_files/")
        
        confirm = input("\n🚀 Proceed with cleanup? [y/n]: ").lower()
        
        if confirm != 'y':
            print("\n❌ Cleanup cancelled")
            return
        
        # Create backup directory
        self.create_backup_dir()
        
        # Run cleanup tasks
        self.delete_parsed_data()
        self.cleanup_pycache()
        self.retire_old_markdown_files()
        self.cleanup_old_pipeline_files()
        self.organize_soap_notes()
        
        # Create new documentation
        self.create_project_structure_doc()
        
        # Summary
        self.create_cleanup_summary()


if __name__ == '__main__':
    cleaner = ProjectCleaner()
    cleaner.run_full_cleanup()
