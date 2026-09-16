from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


@dataclass
class Node:
    text: str = ""
    resource_id: str = ""
    content_desc: str = ""
    cls: str = ""
    package: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    clickable: bool = False
    long_clickable: bool = False
    scrollable: bool = False
    password: bool = False
    focused: bool = False
    enabled: bool = True
    children: list["Node"] = field(default_factory=list)

    @property
    def editable(self) -> bool:
        return self.cls.endswith("EditText") or self.password


def _flag(value: str) -> bool:
    return value == "true"


def parse_bounds(s: str) -> tuple[int, int, int, int]:
    match = _BOUNDS_RE.search(s or "")
    if not match:
        return (0, 0, 0, 0)
    left, top, right, bottom = (int(g) for g in match.groups())
    return (left, top, right, bottom)


def _node_from_el(el: ET.Element) -> Node:
    a = el.attrib
    return Node(
        text=a.get("text", ""),
        resource_id=a.get("resource-id", ""),
        content_desc=a.get("content-desc", ""),
        cls=a.get("class", ""),
        package=a.get("package", ""),
        bounds=parse_bounds(a.get("bounds", "")),
        clickable=_flag(a.get("clickable", "false")),
        long_clickable=_flag(a.get("long-clickable", "false")),
        scrollable=_flag(a.get("scrollable", "false")),
        password=_flag(a.get("password", "false")),
        focused=_flag(a.get("focused", "false")),
        enabled=_flag(a.get("enabled", "true")),
        children=[_node_from_el(c) for c in el if c.tag == "node"],
    )


def parse(xml: str) -> Node:
    root_el = ET.fromstring(xml)
    root = Node(cls=root_el.tag)  # synthetic "hierarchy" root
    root.children = [_node_from_el(c) for c in root_el if c.tag == "node"]
    return root


def flatten(node: Node) -> list[Node]:
    out = [node]
    for child in node.children:
        out.extend(flatten(child))
    return out


def actionable(nodes: list[Node]) -> list[Node]:
    result: list[Node] = []
    for n in nodes:
        if not n.enabled:
            continue
        left, top, right, bottom = n.bounds
        if right <= left or bottom <= top:
            continue
        if n.clickable or n.long_clickable or n.scrollable or n.editable:
            result.append(n)
    return result


def _short_rid(resource_id: str) -> str:
    return resource_id.split("/")[-1] if "/" in resource_id else resource_id


def label(node: Node) -> str:
    if node.text.strip():
        return node.text.strip()
    if node.content_desc.strip():
        return node.content_desc.strip()
    if node.resource_id:
        return _short_rid(node.resource_id)
    if node.cls:
        return node.cls.split(".")[-1]
    return "?"


def center(node: Node) -> tuple[int, int]:
    left, top, right, bottom = node.bounds
    return ((left + right) // 2, (top + bottom) // 2)
