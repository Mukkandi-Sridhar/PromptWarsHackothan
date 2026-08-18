#!/usr/bin/env bash
set -e

echo "=== SIGNAL Render Single-Service Build ==="
pip install --retries 5 --timeout 60 -r signal/backend/requirements.txt

echo "=== Building React Frontend Asset Bundle ==="
export NODE_VERSION=${NODE_VERSION:-20.18.0}
cd signal/frontend
npm install
npm run build
cd ../..

echo "=== Precomputing Seed Reels & Candidates ==="
cd signal
python -m backend.precompute || true
cd ..

echo "=== Render Build Complete ==="
