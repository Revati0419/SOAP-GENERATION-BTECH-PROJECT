"""
Utility functions for the SOAP generation pipeline
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_config(config_path: str = "configs/config.yaml") -> Dict:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    if not config_file.exists():
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / config_path
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(filepath: str) -> Dict:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict, filepath: str, indent: int = 2) -> None:
    """Save data to JSON file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent.parent


def format_conversation(turns: List[Dict], max_turns: int = 60) -> str:
    """Format conversation turns into readable text"""
    lines = []
    
    if len(turns) > max_turns:
        # Take first half and last half for context
        selected = turns[:max_turns//2] + turns[-max_turns//2:]
    else:
        selected = turns
    
    for turn in selected:
        role = turn.get('role', 'Unknown')
        text = turn.get('text', '') or turn.get('text_en', '')
        if text:
            lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def chunk_text(text: str, max_length: int = 500) -> List[str]:
    """Split text into chunks for processing"""
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += ". " + sentence if current_chunk else sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def get_device() -> str:
    """Detect available device (CUDA/CPU)"""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"
