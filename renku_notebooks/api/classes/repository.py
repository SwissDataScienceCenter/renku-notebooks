from dataclasses import dataclass

INTERNAL_GITLAB_PROVIDER = "INTERNAL_GITLAB"


@dataclass
class Repository:
    """Information required to clone a git repository."""

    url: str
    provider: str | None = None
    branch: str | None = None
    commit_sha: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, str]):
        return cls(
            url=data["url"],
            branch=data.get("branch"),
            commit_sha=data.get("commit_sha"),
        )


@dataclass
class GitProvider:
    """A git provider."""

    id: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, str]):
        return cls(id=data["id"], url=data["url"])
