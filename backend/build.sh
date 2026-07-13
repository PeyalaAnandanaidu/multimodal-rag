#!/usr/bin/env bash
set -e

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🤖 Pre-downloading CLIP model..."
python -c "
from transformers import CLIPModel, CLIPProcessor
print('Downloading CLIP model...')
CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
print('CLIP model downloaded!')
"

echo "✅ Build complete!"