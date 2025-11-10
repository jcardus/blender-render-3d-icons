#!/bin/bash

# Set the directory containing GLB files (default: glb)
MODEL_DIR="${MODEL_DIR:-glb}"

# Set output directory (default: ./render/)
OUTPUT_PATH="${OUTPUT_PATH:-./render/}"

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Run Blender with the render script
MODEL_DIR="$MODEL_DIR" OUTPUT_PATH="$OUTPUT_PATH" blender -b -P render.py
