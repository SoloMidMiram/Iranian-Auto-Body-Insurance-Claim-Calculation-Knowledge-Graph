"""Static collection checks for the Stage 0 remediation baseline."""

from __future__ import annotations

import ast
import re
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
TESTS = REPOSITORY / "tests"
CANONICAL_REVIEW_DOCUMENT = REPOSITORY / "docs" / "BODY_CASE_REVIEW_MODEL.md"
SHIPPED_REVIEW_REFERENCE = TESTS / "BODY_CASE_REVIEW_MODEL.md"


def _duplicate_definitions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    duplicates: list[str] = []

    def inspect(body: list[ast.stmt], namespace: str) -> None:
        definitions: dict[str, int] = {}
        for node in body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            previous = definitions.get(node.name)
            if previous is not None:
                duplicates.append(
                    f"{namespace}.{node.name} is defined at lines {previous} and {node.lineno}"
                )
            else:
                definitions[node.name] = node.lineno
            inspect(node.body, f"{namespace}.{node.name}")

    inspect(tree.body, path.relative_to(REPOSITORY).as_posix())
    return duplicates


def _generated_blocks(document: Path) -> dict[str, str]:
    text = document.read_text(encoding="utf-8")
    names = re.findall(r"<!-- BEGIN GENERATED: ([a-z-]+) -->", text)
    blocks: dict[str, str] = {}
    for name in names:
        begin = f"<!-- BEGIN GENERATED: {name} -->"
        end = f"<!-- END GENERATED: {name} -->"
        assert text.count(begin) == 1, f"{document}: expected one {begin} marker"
        assert text.count(end) == 1, f"{document}: expected one {end} marker"
        blocks[name] = text.split(begin, 1)[1].split(end, 1)[0].strip()
    return blocks


def test_python_test_names_are_unique_within_each_namespace():
    duplicates = [
        duplicate
        for path in sorted(TESTS.glob("test_*.py"))
        for duplicate in _duplicate_definitions(path)
    ]
    assert not duplicates, "duplicate definitions shadow pytest collection:\n" + "\n".join(
        duplicates
    )


def test_shipped_review_reference_generated_blocks_match_canonical_document():
    canonical = _generated_blocks(CANONICAL_REVIEW_DOCUMENT)
    shipped = _generated_blocks(SHIPPED_REVIEW_REFERENCE)
    assert canonical
    assert shipped == canonical
