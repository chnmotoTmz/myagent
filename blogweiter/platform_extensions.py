from dataclasses import dataclass
from typing import List, Optional

@dataclass
class HatenaBlogExtension:
    custom_theme: str
    syntax_highlighting: bool = False
    add_hatena_bookmark_button: bool = True
    star_ui_enabled: bool = True
    entry_header_enabled: bool = True
    entry_footer_enabled: bool = True
    enable_ads: bool = True
    ogp_image_url: Optional[str] = None
    related_entries: List[dict] = None
    footnotes: List[dict] = None

    def __post_init__(self):
        if self.related_entries is None:
            self.related_entries = []
        if self.footnotes is None:
            self.footnotes = []

@dataclass
class AmebaBlogExtension:
    theme_id: str
    frame_id: Optional[str] = None
    enable_theme_color: bool = True
    theme_color: str = "#ff6600"
    enable_custom_header: bool = True
    custom_header_image_url: Optional[str] = None
    enable_reading_time: bool = True
    enable_nice_button: bool = True
    enable_comments_nice: bool = True
    enable_theme_affiliates: bool = True
    related_articles: List[dict] = None
    popular_articles: List[dict] = None

    def __post_init__(self):
        if self.related_articles is None:
            self.related_articles = []
        if self.popular_articles is None:
            self.popular_articles = []

class PlatformExtensionFactory:
    @staticmethod
    def create_hatena_extension(
        custom_theme: str,
        **kwargs
    ) -> HatenaBlogExtension:
        return HatenaBlogExtension(custom_theme=custom_theme, **kwargs)

    @staticmethod
    def create_ameba_extension(
        theme_id: str,
        **kwargs
    ) -> AmebaBlogExtension:
        return AmebaBlogExtension(theme_id=theme_id, **kwargs) 