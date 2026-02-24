import json
from pathlib import Path

from bestcard.domain.models import CardPolicy


class PolicyStore:
    def __init__(self, policy_file: str):
        self.policy_file = Path(policy_file)

    def load_cards(self) -> list[CardPolicy]:
        if not self.policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_file}")

        with self.policy_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        return [CardPolicy.model_validate(item) for item in data]
