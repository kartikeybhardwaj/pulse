"""Vote model.

Maps to DynamoDB items with PK=POLL#<pollId> SK=VOTE#<alias>.
One vote per user per poll — enforced by the PK/SK uniqueness constraint.
"""

from dataclasses import dataclass


@dataclass
class Vote:
    poll_id: str
    alias: str
    option: str
    voted_at: int = 0

    @classmethod
    def from_db(cls, item: dict) -> "Vote":
        return cls(
            poll_id=item["PK"].split("#", 1)[1],  # POLL#<pollId>
            alias=item["SK"].split("#", 1)[1],  # VOTE#<alias>
            option=item["option"],
            voted_at=int(item.get("votedAt", 0)),
        )
