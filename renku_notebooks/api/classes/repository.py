from dataclasses import dataclass


@dataclass
class Repository:
    """Information required to clone a git repository."""

    url: str
    branch: str | None = None
    commit_sha: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, str]):
        return cls(
            url=data["url"],
            branch=data.get("branch"),
            commit_sha=data.get("commit_sha"),
        )
