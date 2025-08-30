import fastapi
import google.generativeai
import torch
import transformers
import diffusers
import trimesh
import numpy as np

print("✓ FastAPI imported successfully")
print("✓ Google Generative AI imported successfully")
print("✓ PyTorch imported successfully")
print("✓ Transformers imported successfully")
print("✓ Diffusers imported successfully")
print("✓ Trimesh imported successfully")
print("✓ NumPy imported successfully")

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current CUDA device: {torch.cuda.current_device()}")

print("All core dependencies imported successfully!")
