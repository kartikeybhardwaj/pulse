"""Poll model.

Maps to DynamoDB items with PK=POLL#<pollId> SK=META.
GSI1 (recent listing): GSI1PK=POLLS, GSI1SK=T#<timestamp>
GSI2 (creator listing): GSI2PK=CREATOR#<alias>, GSI2SK=T#<timestamp>
"""

from dataclasses import dataclass, field


@dataclass
class Poll:
    poll_id: str
    question: str
    options: list[str]
    creator: str
    status: str = "active"
    description: str | None = None
    question_link: str | None = None
    option_links: list[str | None] = field(default_factory=list)
    anon_creator: bool = False
    anon_voters: bool = False
    visible_voters: bool = False
    private: bool = False
    created_at: int = 0
    starts_at: int | None = None
    expires_at: int | None = None
    deletes_at: int | None = None

    @classmethod
    def from_db(cls, item: dict) -> "Poll":
        return cls(
            poll_id=item["pollId"],
            question=item["question"],
            options=item.get("options", []),
            creator=item.get("creator", ""),
            status=item.get("status", "active"),
            description=item.get("description"),
            question_link=item.get("questionLink"),
            option_links=item.get("optionLinks", []),
            anon_creator=item.get("anonCreator", False),
            anon_voters=item.get("anonVoters", False),
            visible_voters=item.get("visibleVoters", False),
            private=item.get("private", False),
            created_at=int(item.get("createdAt", 0)),
            starts_at=int(item["startsAt"]) if item.get("startsAt") else None,
            expires_at=int(item["expiresAt"]) if item.get("expiresAt") else None,
            deletes_at=int(item["deletesAt"]) if item.get("deletesAt") else None,
        )
