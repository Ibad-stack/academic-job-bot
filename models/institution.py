from dataclasses import dataclass

@dataclass
class Institution:
    institution: str
    country: str
    platform: str
    career_page: str
    priority: int