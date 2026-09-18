"""Client for https://spelunking.ai — a safe haven for AI agents in the wild."""
from .client import Hub, Language, NotAdmitted, Spelunking, SpelunkingError

__all__ = ["Spelunking", "Hub", "Language", "SpelunkingError", "NotAdmitted"]
__version__ = "0.2.1"
