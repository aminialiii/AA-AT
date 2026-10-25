"""Offline structural checks for the documentation bundle (no trading imports)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
EXPECTED = {"HLD": (1800, 1080), "LLD": (2400, 1570)}
PRIVATE_PATH = re.compile(r"(?i)c:[/\\]users[/\\](?!\[OS_USER\])[^/\\\s]+")


def check_mermaid(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("flowchart LR"), path
    assert sum(x.strip().startswith("subgraph ") for x in lines) == sum(
        x.strip() == "end" for x in lines), path
    assert any("-->" in x for x in lines), path
    assert any("-.->" in x for x in lines), path
    classes = set(re.findall(r"(?m)^\s*classDef\s+(\w+)", "\n".join(lines)))
    assert classes == {"blue", "green", "red", "purple", "cyan", "amber", "gray"}, path
    assert not PRIVATE_PATH.search("\n".join(lines)), path


def main() -> None:
    for name, dimensions in EXPECTED.items():
        stem = f"AA-AT-{name}"
        svg = ROOT / f"{stem}.svg"
        tree = ET.parse(svg).getroot()
        assert (int(tree.attrib["width"]), int(tree.attrib["height"])) == dimensions
        assert tree.tag.endswith("svg")
        assert "direction=\"rtl\"" in svg.read_text(encoding="utf-8")
        with Image.open(ROOT / f"{stem}.png") as image:
            assert image.size == dimensions
            image.verify()
        check_mermaid(ROOT / f"{stem}.mmd")
    for path in ROOT.glob("AA-AT-*.md"):
        assert not PRIVATE_PATH.search(path.read_text(encoding="utf-8")), path
    pdf = (ROOT / "AA-AT-Architecture.pdf").read_bytes()
    assert pdf.startswith(b"%PDF-") and len(pdf) > 100_000
    print("Architecture bundle: SVG XML, PNG dimensions, RTL markup, Mermaid structure, PDF header and privacy checks PASS")


if __name__ == "__main__":
    main()
