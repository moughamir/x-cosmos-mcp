import os
from pathlib import Path
from typing import List, Dict, Optional

from app.config import settings

PROMPT_DIR = Path(settings.paths.prompt_dir)

def get_prompt_files() -> List[Dict[str, str]]:
    """Lists all available prompt files, returning a unique path for each."""
    if not PROMPT_DIR.exists() or not PROMPT_DIR.is_dir():
        return []
    
    prompts = []
    for f in PROMPT_DIR.glob('**/*'):
        if f.is_file() and (f.name.endswith('.j2') or f.name.endswith('.md')):
            try:
                relative_path = str(f.relative_to(PROMPT_DIR))
                prompts.append({"path": relative_path, "filename": f.name})
            except Exception:
                pass
    return sorted(prompts, key=lambda x: x['path'])

def get_prompt_content(path: str) -> Optional[str]:
    """Reads the content of a specific prompt file."""
    if ".." in path:
        return None
    
    file_path = PROMPT_DIR / path
    if file_path.is_file():
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception:
            return None
    return None

def save_prompt_content(path: str, content: str) -> bool:
    """Saves content to a specific prompt file."""
    if ".." in path:
        return False

    file_path = PROMPT_DIR / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception:
        return False