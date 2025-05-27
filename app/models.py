from dataclasses import dataclass, field
from typing import List

@dataclass
class ContextItem:
    role: str
    content: str

@dataclass
class ChatPayload:
    message: str = ''
    context: List[ContextItem] = field(default_factory=list)
    displayName: str = "unknown"
    token_length: int = 0
    vocab_complexity: int = 0
    tone: int = 0
