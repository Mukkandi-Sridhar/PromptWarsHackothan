#!/usr/bin/env bash
set -e

echo "=== SIGNAL Render Single-Service Build ==="
pip install -r signal/backend/requirements.txt

echo "=== Building React Frontend Asset Bundle ==="
cd signal/frontend
npm install
npm run build
cd ../..

echo "=== Precomputing Seed Reels & Candidates ==="
cd signal
python -m backend.precompute || true
cd ..

echo "=== Render Build Complete ==="
