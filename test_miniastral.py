import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
is_model_compatible = importlib.import_module("nocte.task_router").is_model_compatible

# Test miniastral
model = 'miniastral'
vram = 6
ram = 16

compatible = is_model_compatible(model, vram, ram)
print(f"Model: {model}")
print(f"Hardware: {vram}GB VRAM, {ram}GB system RAM")
print(f"Compatible: {compatible}")

# Also test with 8GB RAM
compatible2 = is_model_compatible(model, 6, 8)
print(f"Compatible with 6GB VRAM, 8GB RAM: {compatible2}")