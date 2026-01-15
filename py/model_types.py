"""
ModelPulse - Model Type Definitions

Maps ComfyUI loader node types to their model categories and input keys.
"""

# Standard ComfyUI model loaders
# Format: "NodeClassName": ("category", "input_key" or ["input_key1", "input_key2"])
MODEL_LOADERS: dict[str, tuple[str, str | list[str]]] = {
    # Checkpoint loaders
    "CheckpointLoaderSimple": ("checkpoint", "ckpt_name"),
    "CheckpointLoader": ("checkpoint", "ckpt_name"),

    # LoRA loaders
    "LoraLoader": ("lora", "lora_name"),
    "LoraLoaderModelOnly": ("lora", "lora_name"),

    # VAE loaders
    "VAELoader": ("vae", "vae_name"),

    # ControlNet loaders
    "ControlNetLoader": ("controlnet", "control_net_name"),

    # CLIP loaders
    "CLIPLoader": ("clip", "clip_name"),
    "DualCLIPLoader": ("clip", ["clip_name1", "clip_name2"]),

    # UNET loaders
    "UNETLoader": ("unet", "unet_name"),

    # Upscaler loaders
    "UpscaleModelLoader": ("upscaler", "model_name"),

    # Style model loaders
    "StyleModelLoader": ("style_model", "style_model_name"),

    # GLIGEN loaders
    "GLIGENLoader": ("gligen", "gligen_name"),

    # GGUF loaders (ComfyUI-GGUF by city96)
    "UnetLoaderGGUF": ("gguf", "unet_name"),
    "UnetLoaderGGUFAdvanced": ("gguf", "unet_name"),
    "CLIPLoaderGGUF": ("gguf", "clip_name"),
    "DualCLIPLoaderGGUF": ("gguf", ["clip_name1", "clip_name2"]),
    "TripleCLIPLoaderGGUF": ("gguf", ["clip_name1", "clip_name2", "clip_name3"]),
    "QuadrupleCLIPLoaderGGUF": ("gguf", ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]),
}

# Patterns for detecting custom node loaders (Impact Pack, Efficiency Nodes, etc.)
# These are checked if the node class name isn't in MODEL_LOADERS
LOADER_PATTERNS: list[tuple[str, str, list[str]]] = [
    # (pattern_in_class_name, category, possible_input_keys)
    ("Checkpoint", "checkpoint", ["ckpt_name", "checkpoint", "model_name"]),
    ("Lora", "lora", ["lora_name", "lora"]),
    ("VAE", "vae", ["vae_name", "vae"]),
    ("ControlNet", "controlnet", ["control_net_name", "controlnet", "control_net"]),
    ("CLIP", "clip", ["clip_name", "clip"]),
    ("UNET", "unet", ["unet_name", "unet"]),
    ("Upscale", "upscaler", ["model_name", "upscale_model"]),
]

# Model categories for display purposes
MODEL_CATEGORIES: dict[str, dict[str, str]] = {
    "checkpoint": {
        "name": "Checkpoints",
        "icon": "pi-box",
    },
    "lora": {
        "name": "LoRAs",
        "icon": "pi-sparkles",
    },
    "vae": {
        "name": "VAEs",
        "icon": "pi-cog",
    },
    "controlnet": {
        "name": "ControlNets",
        "icon": "pi-sitemap",
    },
    "clip": {
        "name": "CLIP Models",
        "icon": "pi-comments",
    },
    "unet": {
        "name": "UNETs",
        "icon": "pi-server",
    },
    "upscaler": {
        "name": "Upscalers",
        "icon": "pi-expand",
    },
    "style_model": {
        "name": "Style Models",
        "icon": "pi-palette",
    },
    "gligen": {
        "name": "GLIGEN",
        "icon": "pi-th-large",
    },
    "gguf": {
        "name": "GGUF",
        "icon": "pi-database",
    },
}
