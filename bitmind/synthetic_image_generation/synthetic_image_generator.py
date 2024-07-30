from transformers import pipeline
from diffusers import DiffusionPipeline
from transformers import set_seed
from datasets import load_dataset
import bittensor as bt
import numpy as np
import torch
import random
import time
import re
import gc
import os
import warnings

from bitmind.constants import (
    PROMPT_GENERATOR_NAMES,
    PROMPT_GENERATOR_ARGS,
    DIFFUSER_NAMES,
    DIFFUSER_ARGS,
    PROMPT_TYPES,
    IMAGE_ANNOTATION_MODEL
)
from bitmind.synthetic_image_generation.image_annotation_generator import ImageAnnotationGenerator

warnings.filterwarnings("ignore", category=FutureWarning, module='diffusers')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow


class SyntheticImageGenerator:

    def __init__(
        self,
        prompt_type='random',
        prompt_generator_name=PROMPT_GENERATOR_NAMES[0],
        diffuser_name=DIFFUSER_NAMES[0],
        use_random_diffuser=False,
        image_cache_dir=None
    ):
        if prompt_type not in PROMPT_TYPES:
            raise ValueError(f"Invalid prompt type '{prompt_type}'. Options are {PROMPT_TYPES}")
        if prompt_generator_name not in PROMPT_GENERATOR_NAMES:
            raise ValueError(f"Invalid prompt generator name '{prompt_generator_name}'. Options are {PROMPT_GENERATOR_NAMES}")
        if not use_random_diffuser and diffuser_name not in DIFFUSER_NAMES:
            raise ValueError(f"Invalid diffuser name '{diffuser_name}'. Options are {DIFFUSER_NAMES}")

        self.use_random_diffuser = use_random_diffuser
        self.prompt_type = prompt_type
        self.prompt_generator_name = prompt_generator_name

        if self.use_random_diffuser and diffuser_name is not None:
            bt.logging.warning("Warning: diffuser_name will be ignored (use_random_diffuser=True)")
            self.diffuser_name = None
        else:
            self.diffuser_name = diffuser_name

        self.image_annotation_generator = None
        if self.prompt_type == 'annotation':
            bt.logging.info(f"Loading image captioning model ({IMAGE_ANNOTATION_MODEL})...")
            self.image_annotation_generator = ImageAnnotationGenerator(model_name=IMAGE_ANNOTATION_MODEL)
        else:
            bt.logging.info(f"Loading prompt generation model ({prompt_generator_name})...")
            self.prompt_generator = pipeline(
                'text-generation', **PROMPT_GENERATOR_ARGS[prompt_generator_name])

        self.image_cache_dir = image_cache_dir
        if image_cache_dir is not None:
            os.makedirs(self.image_cache_dir, exist_ok=True)

    def generate(self, k: int = 1, real_images=None) -> list:
        """
        Generates k synthetic images. If self.prompt_type is 'annotation', a BLIP2 captioning pipeline is used
        to produce prompts by captioning real images. If self.prompt_type is 'random', an LLM is used to generate
        prompts.

        Args:
            k (int): Number of images to generate.

        Returns:
            list: List of dictionaries containing 'prompt', 'image', and 'id'.
        """
        bt.logging.info("Generating prompts...")
        if self.prompt_type == 'annotation':
            if real_images is None:
                raise ValueError(f"real_images can't be None if self.prompt_type is 'annotation'")
            prompts = [
                self.generate_image_caption(real_images[i])
                for i in range(k)
            ]
        elif self.prompt_type == 'random':
            prompts = [
                self.generate_random_prompt(retry_attempts=10)
                for _ in range(k)
            ]
        else:
            raise NotImplementedError

        if self.use_random_diffuser:
            self.load_diffuser('random')
        else:
            self.load_diffuser(self.diffuser_name)

        bt.logging.info("Generating images...")
        gen_data = []
        for prompt in prompts:
            image_name = f"{time.time()}.jpg"
            gen_image = self.diffuser(prompt=prompt).images[0]
            gen_data.append({
                'prompt': prompt,
                'image': gen_image,
                'id': image_name
            })
            if self.image_cache_dir is not None:
                path = os.path.join(self.image_cache_dir, image_name)
                gen_image.save(path)

        self.clear_gpu()  # remove diffuser from gpu

        return gen_data

    def clear_gpu(self):
        if self.diffuser is not None:
            bt.logging.debug(f"Deleting previous diffuser, freeing memory")
            self.diffuser.to('cpu')
            del self.diffuser
            gc.collect()
            torch.cuda.empty_cache()

    def load_diffuser(self, diffuser_name) -> None:
        """
        loads a huggingface diffuser model.
        """
        if diffuser_name == 'random':
            diffuser_name = np.random.choice(DIFFUSER_NAMES, 1)[0]

        bt.logging.info(f"Loading image generation model ({diffuser_name})...")
        self.diffuser_name = diffuser_name
        self.diffuser = DiffusionPipeline.from_pretrained(
            diffuser_name, torch_dtype=torch.float16, **DIFFUSER_ARGS[diffuser_name])
        self.diffuser.to("cuda")

    def generate_image_caption(self, image_sample) -> str:
        """

        """
        self.image_annotation_generator.load_model()
        annotation = self.image_annotation_generator.process_image(
            image_info=image_sample,
            dataset_name=image_sample['source'],
            image_index=image_sample['id'],
            resize=False,
            verbose=0
        )[0]
        self.image_annotation_generator.clear_gpu()
        return annotation['description']

    def generate_random_prompt(self, retry_attempts: int = 10) -> str:
        """
        Generates a prompt for image generation.

        Args:
            retry_attempts (int): Number of attempts to generate a valid prompt.

        Returns:
            str: Generated prompt.
        """
        seed = random.randint(100, 1000000)
        set_seed(seed)

        starters = [
            'A photorealistic portrait',
            'A photorealistic image of a person',
            'A photorealistic landscape',
            'A photorealistic scene'
        ]
        quality = [
            'RAW photo', 'subject', '8k uhd',  'soft lighting', 'high quality', 'film grain'
        ]
        device = [
            'Fujifilm XT3', 'iphone', 'canon EOS r8' , 'dslr',
        ]

        for _ in range(retry_attempts):
            starting_text = np.random.choice(starters, 1)[0]
            response = self.prompt_generator(
                starting_text, max_length=(77 - len(starting_text)), num_return_sequences=1, truncation=True)

            prompt = response[0]['generated_text'].strip()
            prompt = re.sub('[^ ]+\.[^ ]+','', prompt)
            prompt = prompt.replace("<", "").replace(">", "")

            # temporary removal of extra context (like "featured on artstation") until we've trained our own prompt generator
            prompt = re.split('[,;]', prompt)[0] + ', '
            prompt += ', '.join(np.random.choice(quality, np.random.randint(len(quality)//2, len(quality))))
            prompt += ', ' + np.random.choice(device, 1)[0]
            if prompt != "":
                return prompt
