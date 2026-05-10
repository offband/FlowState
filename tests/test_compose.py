from pathlib import Path

import pytest

from flowstate_runtime.compose import compose_stack
from flowstate_runtime.store import RuntimeStoreError, add_stack_layer, create_object, create_stack, extend_stack


def test_compose_preserves_order_and_provenance(tmp_path: Path) -> None:
    create_object("python-base", "Python Base", home=tmp_path)
    create_object("review-flow", "Review Flow", home=tmp_path)
    create_stack("project-alpha", "Project Alpha", home=tmp_path)
    add_stack_layer("project-alpha", "python-base", home=tmp_path)
    add_stack_layer("project-alpha", "review-flow", home=tmp_path)

    composed = compose_stack("project-alpha", home=tmp_path)
    payload = composed.to_dict()

    assert payload["runtime"] == "flow://project-alpha"
    assert [layer["id"] for layer in payload["layers"]] == ["python-base", "review-flow"]
    assert payload["layers"][0]["path"].endswith("python-base.md")
    assert "Layer 1: Python Base" in payload["rendered_markdown"]


def test_compose_supports_stack_inheritance_without_duplicate_layers(tmp_path: Path) -> None:
    create_object("python-base", "Python Base", home=tmp_path)
    create_object("review-flow", "Review Flow", home=tmp_path)
    create_stack("base", "Base Runtime", home=tmp_path)
    create_stack("project-alpha", "Project Alpha", home=tmp_path)
    add_stack_layer("base", "python-base", home=tmp_path)
    add_stack_layer("project-alpha", "python-base", home=tmp_path)
    add_stack_layer("project-alpha", "review-flow", home=tmp_path)
    extend_stack("project-alpha", "base", home=tmp_path)

    composed = compose_stack("project-alpha", home=tmp_path)
    payload = composed.to_dict()

    assert [layer["id"] for layer in payload["layers"]] == ["python-base", "review-flow"]
    assert payload["layers"][0]["source_stack"] == "base"
    assert payload["layers"][1]["source_stack"] == "project-alpha"
    assert payload["manifest"]["source_stacks"] == ["base", "project-alpha"]


def test_extend_stack_rejects_indirect_cycle(tmp_path: Path) -> None:
    create_stack("base", "Base Runtime", home=tmp_path)
    create_stack("project-alpha", "Project Alpha", home=tmp_path)
    extend_stack("project-alpha", "base", home=tmp_path)

    with pytest.raises(RuntimeStoreError, match="Stack inheritance cycle detected"):
        extend_stack("base", "project-alpha", home=tmp_path)
