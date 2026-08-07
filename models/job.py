from dataclasses import dataclass

@dataclass
class Job:
    title: str
    url: str
    institution: str
    platform: str
    location: str
    remote: bool
    posted_date: str
    score: int = 0