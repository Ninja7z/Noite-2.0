import sys
sys.path.insert(0, r'c:\Users\crist\Noite-2.0-worktrees\stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001\src')
from nocte.task_router import is_model_compatible

# Test various models with the new tuple return
test_models = [
    ('mistral:7b', 6, 16),
    ('mistral:7b', 6, 8),
    ('gemma:2b', 6, 16),
    ('phi3:3.8b', 6, 16),
    ('qwen2.5:7b', 6, 16),
    ('miniastral', 6, 16),  # Should return None since no 'b' suffix
    ('qwen2.5-coder:7b-instruct-q4_K_M', 6, 16),  # Has '7b' in name
]

print(f"Hardware: 6GB VRAM, 16GB system RAM")
print("=" * 70)
print(f"{'Model':30s} | {'Fits':^5s} | {'Category':^12s}")
print("-" * 70)

for model, vram, ram in test_models:
    result = is_model_compatible(model, vram, ram)
    if result is None:
        compatible, category = "None", "indeterminado"
    else:
        compatible, category = result
    print(f"{model:30s} | {str(compatible):^5s} | {category:^12s}")

print("=" * 70)
print("\nClassification:")
print("  🟢 Confortável: margem >= 20% VRAM livre após carregado")
print("  🟡 Limitado: cabe, mas margem < 20% ou offload significativo necessário")
print("  🔴 Inviável: excede recursos ou performance impraticável")