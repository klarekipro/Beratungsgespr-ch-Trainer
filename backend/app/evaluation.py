"""Evaluation is grounded in events and criteria, not Actor self-scoring."""
from typing import Mapping, Protocol, Sequence


class Evaluation(Protocol):
    def evaluate(self, events: Sequence[Mapping[str, object]], criteria: Mapping[str, object]) -> Mapping[str, object]:
        """Assess evidence, distinguishing granted facts from actually spoken facts."""
        ...
