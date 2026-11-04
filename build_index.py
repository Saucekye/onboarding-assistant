"""Rebuild data/policies.db from the JSON files in data/documents.

Run this after adding or editing a document:  python -m scripts.build_index
"""

from app.config import load_settings
from app.search import build_index

if __name__ == "__main__":
    s = load_settings()
    count = build_index(s.documents_dir, s.database_path)
    print(f"Indexed {count} passages into {s.database_path}")
