GSTD_JETTON_MASTER_TON = "EQDv6cYW9nNiKjN3Nwl8D6ABjUiH1gYfWVGZhfP7-9tZskTO"

# Sovereign Model Tier Mapping
# Public-facing aliases → internal engine IDs
# Developers should use the public aliases (gstd-*) in API calls.
# The backend transparently maps them to the actual engine.
SOVEREIGN_MODELS = {
    # Public Alias     → Internal Engine ID
    "gstd-fast":         "qwen2.5-coder:7b",
    "gstd-creative":     "llama3.1:8b",
    "gstd-sovereign":    "qwen2.5-coder:32b",
    "gstd-ultra":        "llama3.3:70b",
}

# Tier display names (for UI / SDK consumers)
MODEL_TIERS = {
    "gstd-fast":      {"name": "Fast",         "tier": "Tier 1", "cost_gstd": 0.01},
    "gstd-creative":  {"name": "Creative",     "tier": "Tier 1", "cost_gstd": 0.01},
    "gstd-sovereign": {"name": "Professional", "tier": "Tier 2", "cost_gstd": 0.05},
    "gstd-ultra":     {"name": "Ultra",        "tier": "Tier 3", "cost_gstd": 0.10},
}

# Default model for SDK operations
DEFAULT_MODEL = "gstd-fast"
