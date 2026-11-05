"""Actor receives only public scenario, allowed facts and visible conversation."""
from typing import Mapping, Protocol, Sequence


class Actor(Protocol):
    def respond(self, public_context: Mapping[str, object], visible_history: Sequence[Mapping[str, str]], question: str) -> str:
        """Speak as the German client without adding unknown facts; not implemented."""
        ...
