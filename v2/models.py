from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

# from enum import Enum
from enum import Enum, auto


class ConversationState(Enum):
    WAITING_FOR_PROMPT = auto()
    WAITING_FOR_CONTROL_TYPE = auto()
    WAITING_FOR_IMAGE = auto()
    WAITING_FOR_SIZE = auto()
    WAITING_FOR_STYLE = auto()
    WAITING_FOR_UPSCALE_METHOD = auto()
    WAITING_FOR_UPSCALE_PROMPT = auto()
    WAITING_FOR_FORMAT = auto()
    WAITING_FOR_METHOD = auto()
    WAITING_FOR_REIMAGINE_PROMPT = auto()
    WAITING_FOR_PROMPT_V2 = auto()
    WAITING_FOR_ASPECT_RATIO_V2 = auto()
    WAITING_FOR_IMAGE_V2 = auto()
    WAITING_FOR_UNCROP_IMAGE = auto()
    WAITING_FOR_UNCROP_ASPECT_RATIO = auto()
    WAITING_FOR_UNCROP_PROMPT = auto()
    WAITING_FOR_UNCROP_POSITION = auto()


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
    control_image: Optional[str] = None  # Added for control-based generation


@dataclass
class ReimagineParams:
    prompt: str
    control_image: str
    control_strength: float = 0.83
    negative_prompt: str = "2 faces, 2 heads, bad anatomy, blurry, cloned face, cropped image, cut-off, deformed hands, disconnected limbs, disgusting, disfigured, draft, duplicate artifact, extra fingers, extra limb, floating limbs, gloss proportions, grain, gross proportions, long body, long neck, low-res, mangled, malformed, malformed hands, missing arms, missing limb, morbid, mutation, mutated, mutated hands, mutilated, mutilated hands, multiple heads, negative aspect, out of frame, poorly drawn, poorly drawn face, poorly drawn hands, signatures, surreal, tiling, twisted fingers, ugly"
    seed: int = 0
    output_format: str = "jpeg"
    style: str = "None"
    method: str = "image"  # New field for method selection (image or sketch)


@dataclass
class UnCropParams:
    image_path: str
    target_aspect_ratio: str  # e.g., "16:9", "1:1", "4:5", etc.
    prompt: str = ""
    creativity: float = 0.35
    seed: int = 0
    output_format: str = "png"
    position: str = "auto"  # New field for position control
