#!/bin/bash

# Set the directory containing GLB files (default: glb)
MODEL_DIR="${MODEL_DIR:-models}"

# Set output directory (default: ./render/)
OUTPUT_PATH="${OUTPUT_PATH:-../IdeaProjects/flutter_manager/assets/map/icons/}"

# Set textures directory (optional: directory containing texture files)
# TEXTURES_DIR="${TEXTURES_DIR:-./glb/Textures}"

# Search recursively for model files (default: 0)
# RECURSIVE="${RECURSIVE:-0}"

# Extensions to search for (default: glb,gltf,blend,fbx,obj)
# EXTENSIONS="${EXTENSIONS:-glb,gltf,blend,fbx,obj}"

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Run Blender with the render script
#MODEL_DIR="$MODEL_DIR"

# Example: Render all FBX files recursively in ./cars directory
# UNLIT=0 MODEL_DIR=./cars RECURSIVE=1 EXTENSIONS=fbx TEXTURES_DIR=./textures OUTPUT_PATH="$OUTPUT_PATH" blender -b -P render.py

# Example: Render specific model file
export MODEL_DIR="./uber" RECURSIVE=1 UNLIT=0 EXTENSIONS="fbx"  TEXTURES_DIR=./textures TEXTURE_FILE=./textures/city_vehicles_pallete.png OUTPUT_PATH="$OUTPUT_PATH" IMG=75
FILE_FILTER=suv blender -b -P render.py
