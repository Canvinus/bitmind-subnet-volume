import os


WANDB_PROJECT = 'bitmind-subnet'
WANDB_ENTITY = 'bitmindai'

DATASET_META = {
    "real": [
        {"mnt_path": "/mnt/datasets/open-images-v7", "path": "~/datasets/open-images-v7", "create_splits": False},
        {"mnt_path": "/mnt/datasets/ffhq-256", "path": "~/datasets/ffhq-256", "create_splits": False},
        {"mnt_path": "/mnt/datasets/celeb-a-hq", "path": "~/datasets/celeb-a-hq", "create_splits": False}
    ],
    "fake": [
        {"mnt_path": "/mnt/datasets/realvis-xl", "path": "~/datasets/realvis-xl", "create_splits": False},
        {"mnt_path": "/mnt/datasets/stable-diffusion-xl", "path": "~/datasets/stable-diffusion-xl", "create_splits": False},
    ]
}

VALIDATOR_MODEL_META = {
    "prompt_generators": [
        {
            "model": "Gustavosta/MagicPrompt-Stable-Diffusion",
            "tokenizer": "gpt2",
            "device": -1
        }
    ],
    "diffusers": [
        {
            "path": "stabilityai/stable-diffusion-xl-base-1.0",
            "use_safetensors": True,
            "variant": "fp16"
        },
        {
            "path": "SG161222/RealVisXL_V4.0",
            "use_safetensors": True,
            "variant": "fp16"
        },
        {
            "path": "Corcelio/mobius",
            "use_safetensors": True
        }
    ]
}

HUGGINGFACE_CACHE_DIR = os.path.expanduser('~/.cache/huggingface')

TARGET_IMAGE_SIZE = (256, 256)

PROMPT_TYPES = ('random', 'annotation')

PROMPT_GENERATOR_ARGS = {
    m['model']: m for m in VALIDATOR_MODEL_META['prompt_generators']
}

PROMPT_GENERATOR_NAMES = list(PROMPT_GENERATOR_ARGS.keys())

DIFFUSER_ARGS = {
    m['path']: {k: v for k, v in m.items() if k != 'path'}  
    for m in VALIDATOR_MODEL_META['diffusers']
}

DIFFUSER_NAMES = list(DIFFUSER_ARGS.keys())

IMAGE_ANNOTATION_MODEL = "Salesforce/blip2-opt-2.7b-coco"

