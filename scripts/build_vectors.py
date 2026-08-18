"""
scripts/build_vectors.py — precomputes 384-dimensional vector embeddings for candidate reels and graph nodes locally.
Generates signal/backend/data/vectors.json (~400KB) so runtime backend requires zero heavy ML libraries (torch/chromadb/sentence-transformers).
"""
from __future__ import annotations
import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "signal" / "backend" / "data"

def simple_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministically generates a normalized 384-dim float vector for a given text string."""
    tokens = text.lower().replace("-", " ").replace("_", " ").split()
    vec = [0.0] * dim
    for idx, token in enumerate(tokens):
        for char_idx, char in enumerate(token):
            h = (ord(char) * 31 + idx * 17 + char_idx * 7) % dim
            vec[h] += 1.0 + (char_idx * 0.1)
    
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]

def main():
    cands_path = DATA_DIR / "candidate_library.json"
    candidates = json.loads(cands_path.read_text()) if cands_path.exists() else []

    nodes = [
        "Java", "NullPointerException", "LeetCode", "MacBook M4", "street food", "gaming",
        "Backend Engineering", "Interview Technique", "Developer Tooling", "DSA & Algorithms",
        "SWE Career Path", "Hardware & Architecture", "System Design", "Cloud Computing", "Cybersecurity",
        "Becoming a software engineer · placement anxiety", "Identity Affirmation", "Aspiration",
        "Java / Spring", "Data Structures", "AI & ML", "Career & Culture", "Cloud & Infra"
    ]

    cand_vectors = {}
    for c in candidates:
        text = f"{c.get('title', '')} {c.get('caption', '')} {c.get('category', '')} {' '.join(c.get('tags', []))}"
        cand_vectors[c["id"]] = simple_embed(text)

    node_vectors = {n: simple_embed(n) for n in nodes}

    out_path = DATA_DIR / "vectors.json"
    out_path.write_text(json.dumps({
        "candidates": cand_vectors,
        "nodes": node_vectors
    }, indent=2))
    print(f"Generated {out_path} with {len(cand_vectors)} candidate vectors and {len(node_vectors)} node vectors.")

if __name__ == "__main__":
    main()
