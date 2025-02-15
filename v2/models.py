# models.py
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum


class ConversationState(Enum):
    WAITING_FOR_PROMPT = 0
    WAITING_FOR_SIZE = 1
    WAITING_FOR_STYLE = 2


@dataclass
class ImageConfig:
    SIZE_MAPPING: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: {
            "square-p": (1152, 896),
            "portrait": (1216, 832),
            "highscreen": (1344, 768),
            "panorama-p": (1536, 640),
            "square": (1024, 1024),
            "panorama": (640, 1536),
            "square-l": (896, 1152),
            "landscape": (832, 1216),
            "widescreen": (768, 1344),
        }
    )

    STYLE_PRESETS: List[List[str]] = field(
        default_factory=lambda: [
            ["photographic", "enhance", "anime"],
            ["digital-art", "comic-book", "fantasy-art"],
            ["line-art", "analog-film", "neon-punk"],
            ["isometric", "low-poly", "origami"],
            ["modeling-compound", "cinematic", "3d-model"],
            ["pixel-art", "tile-texture", "None"],
        ]
    )

    SIZE_PRESETS: List[List[str]] = field(
        default_factory=lambda: [
            ["landscape", "widescreen", "panorama"],
            ["square-l", "square", "square-p"],
            ["portrait", "highscreen", "panorama-p"],
        ]
    )


@dataclass
class GenerationParams:
    prompt: str
    style: str = "None"
    size: str = "square"
