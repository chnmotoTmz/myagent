from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ImageType(Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"

class AIModel(Enum):
    STABLE_DIFFUSION = "Stable Diffusion"
    DALL_E = "DALL-E"
    MIDJOURNEY = "Midjourney"

class ImageStyle(Enum):
    REALISTIC = "写実的"
    ILLUSTRATION = "イラスト"
    WATERCOLOR = "水彩画"
    MANGA = "漫画"
    OTHER = "その他"

@dataclass
class AIGeneratedImage:
    id: str
    prompt: str
    negative_prompt: Optional[str]
    model: AIModel
    seed: int
    width: int
    height: int
    style: ImageStyle
    url: str
    alt: str
    caption: str
    usage: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "model": self.model.value,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "style": self.style.value,
            "url": self.url,
            "alt": self.alt,
            "caption": self.caption,
            "usage": self.usage
        }

@dataclass
class ThumbnailVariant:
    platform: str
    url: str
    width: int
    height: int

@dataclass
class ThumbnailSet:
    main: dict
    variants: List[ThumbnailVariant]

    def get_variant(self, platform: str) -> Optional[ThumbnailVariant]:
        return next(
            (variant for variant in self.variants if variant.platform == platform),
            None
        )

    def add_variant(self, variant: ThumbnailVariant) -> None:
        if not self.get_variant(variant.platform):
            self.variants.append(variant)

class ImageManager:
    def __init__(self):
        self.ai_images: List[AIGeneratedImage] = []
        self.thumbnails: ThumbnailSet = None

    def add_ai_image(self, image: AIGeneratedImage) -> None:
        self.ai_images.append(image)

    def get_ai_image(self, image_id: str) -> Optional[AIGeneratedImage]:
        return next(
            (img for img in self.ai_images if img.id == image_id),
            None
        )

    def set_thumbnail(self, main_thumbnail: dict, variants: List[ThumbnailVariant] = None) -> None:
        self.thumbnails = ThumbnailSet(
            main=main_thumbnail,
            variants=variants or []
        )

    def add_thumbnail_variant(self, variant: ThumbnailVariant) -> None:
        if self.thumbnails:
            self.thumbnails.add_variant(variant)

    def get_thumbnail_for_platform(self, platform: str) -> dict:
        if not self.thumbnails:
            return None
        
        variant = self.thumbnails.get_variant(platform)
        if variant:
            return {
                "url": variant.url,
                "width": variant.width,
                "height": variant.height
            }
        return self.thumbnails.main 