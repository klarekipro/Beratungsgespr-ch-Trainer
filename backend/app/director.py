"""Future Director boundary; the verified implementation stays in research."""
from typing import Mapping, Protocol


class Director(Protocol):
    def classify(self, question: str, allowed_information: Mapping[str, str]) -> Mapping[str, object]:
        """Return categories, reasons and confidence for the current question only."""
        ...
