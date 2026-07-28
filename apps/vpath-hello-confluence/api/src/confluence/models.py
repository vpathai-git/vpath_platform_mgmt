"""Minimal DTOs the api returns to the web. Shaped from Confluence Cloud v2."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Space:
    id: str
    key: str
    name: str
    type: str

    def to_dict(self) -> dict:
        return {"id": self.id, "key": self.key, "name": self.name, "type": self.type}


@dataclass
class PageNode:
    """A page and its child pages — the space's structure as a tree."""

    id: str
    title: str
    children: list["PageNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "children": [c.to_dict() for c in self.children],
        }
