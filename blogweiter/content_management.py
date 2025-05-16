from dataclasses import dataclass, field
from logger import log_debug
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Set

class TagCategory(Enum):
    MAIN = "main"
    SUB = "sub"
    KEYWORD = "keyword"
    SEASONAL = "seasonal"
    SERIES = "series"
    LEVEL = "level"

class UpdateFrequency(Enum):
    YEARLY = "yearly"
    SEASONAL = "seasonal"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    NEVER = "never"

@dataclass
class Tag:
    name: str
    category: TagCategory
    parent_tag: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    usage_count: int = 0

    def add_child(self, child_tag: str) -> None:
        self.children.add(child_tag)

    def remove_child(self, child_tag: str) -> None:
        self.children.discard(child_tag)

@dataclass
class TagManager:
    tags: Dict[str, Tag] = field(default_factory=dict)
    tag_hierarchy: Dict[str, Set[str]] = field(default_factory=dict)

    def add_tag(self, name: str, category: TagCategory, parent_tag: Optional[str] = None) -> None:
        if name not in self.tags:
            tag = Tag(name=name, category=category, parent_tag=parent_tag)
            self.tags[name] = tag
            
            if parent_tag:
                if parent_tag in self.tags:
                    self.tags[parent_tag].add_child(name)
                    if parent_tag not in self.tag_hierarchy:
                        self.tag_hierarchy[parent_tag] = set()
                    self.tag_hierarchy[parent_tag].add(name)

    def remove_tag(self, name: str) -> None:
        if name in self.tags:
            tag = self.tags[name]
            if tag.parent_tag:
                parent = self.tags.get(tag.parent_tag)
                if parent:
                    parent.remove_child(name)
                if tag.parent_tag in self.tag_hierarchy:
                    self.tag_hierarchy[tag.parent_tag].discard(name)
            
            # 子タグの親参照を削除
            for child in tag.children:
                if child in self.tags:
                    self.tags[child].parent_tag = None
            
            del self.tags[name]

    def get_tag_hierarchy(self, tag_name: str) -> List[str]:
        hierarchy = []
        current_tag = self.tags.get(tag_name)
        
        while current_tag:
            hierarchy.insert(0, current_tag.name)
            if current_tag.parent_tag:
                current_tag = self.tags.get(current_tag.parent_tag)
            else:
                break
                
        return hierarchy

    def get_children(self, tag_name: str) -> Set[str]:
        return self.tag_hierarchy.get(tag_name, set())

@dataclass
class ContentLifecycleManager:
    content_type: str
    update_frequency: UpdateFrequency
    last_review_date: datetime
    next_review_date: datetime
    review_points: List[str]
    outdated_threshold: Dict[str, float]
    performance_metrics: Dict[str, any]

    def is_review_due(self) -> bool:
        return datetime.now() >= self.next_review_date

    def calculate_next_review_date(self) -> datetime:
        if self.update_frequency == UpdateFrequency.YEARLY:
            return self.last_review_date + timedelta(days=365)
        elif self.update_frequency == UpdateFrequency.SEASONAL:
            return self.last_review_date + timedelta(days=90)
        elif self.update_frequency == UpdateFrequency.QUARTERLY:
            return self.last_review_date + timedelta(days=90)
        elif self.update_frequency == UpdateFrequency.MONTHLY:
            return self.last_review_date + timedelta(days=30)
        return None

    def is_content_outdated(self) -> bool:
        if not self.performance_metrics.get("peak_period"):
            return False

        current_views = self.performance_metrics.get("avg_monthly_views", 0)
        peak_views = self.performance_metrics["peak_period"]["page_views"]
        threshold = self.outdated_threshold["views_drop_percent"] / 100

        return current_views < (peak_views * (1 - threshold))

    def update_review_status(self) -> None:
        self.last_review_date = datetime.now()
        self.next_review_date = self.calculate_next_review_date()

    def add_review_point(self, point: str) -> None:
        if point not in self.review_points:
            self.review_points.append(point)

    def update_performance_metrics(self, metrics: Dict[str, any]) -> None:
        self.performance_metrics.update(metrics)

class ContentManager:
    tag_manager: TagManager = field(default_factory=TagManager)
    lifecycle_manager: Optional[ContentLifecycleManager] = None

    def initialize_lifecycle(self, content_type: str, update_frequency: UpdateFrequency) -> None:
        self.lifecycle_manager = ContentLifecycleManager(
            content_type=content_type,
            update_frequency=update_frequency,
            last_review_date=datetime.now(),
            next_review_date=datetime.now(),
            review_points=[],
            outdated_threshold={"views_drop_percent": 30, "time_period_months": 6},
            performance_metrics={}
        )
        self.lifecycle_manager.next_review_date = self.lifecycle_manager.calculate_next_review_date()

    def add_tag_with_hierarchy(self, tag_path: List[str], category: TagCategory) -> None:
        parent = None
        for i, tag_name in enumerate(tag_path):
            self.tag_manager.add_tag(tag_name, category, parent)
            parent = tag_name

    def get_all_tags_for_category(self, category: TagCategory) -> List[str]:
        return [
            tag.name for tag in self.tag_manager.tags.values()
            if tag.category == category
        ]

    def check_content_status(self) -> Dict[str, any]:
        if not self.lifecycle_manager:
            return {"error": "Lifecycle manager not initialized"}

        return {
            "review_due": self.lifecycle_manager.is_review_due(),
            "is_outdated": self.lifecycle_manager.is_content_outdated(),
            "next_review_date": self.lifecycle_manager.next_review_date,
            "review_points": self.lifecycle_manager.review_points
        }
