"""Policy owns the secret card, disclosure state and deterministic transitions."""
from typing import Mapping, Protocol


class Policy(Protocol):
    def apply(self, decision: Mapping[str, object], state: Mapping[str, object]) -> Mapping[str, object]:
        """Validate a decision; return new state and auditable disclosure events.

        Implement this from the verified PoC in a later mission. Actor never
        selects permissions. No state transition implementation exists here.
        """
        ...
