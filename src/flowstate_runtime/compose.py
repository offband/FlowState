from __future__ import annotations

import json
from pathlib import Path

from .models import ComposedRuntime, RuntimeObject
from .store import RuntimeStoreError, get_object, get_stack


def compose_stack(stack_id: str, home: Path | None = None) -> ComposedRuntime:
    stack = get_stack(stack_id, home)
    objects, layer_sources = _compose_layers(stack_id, home, seen=[])
    return ComposedRuntime(stack=stack, objects=objects, layer_sources=layer_sources)


def _compose_layers(
    stack_id: str,
    home: Path | None,
    seen: list[str],
) -> tuple[list[RuntimeObject], list[str]]:
    if stack_id in seen:
        raise RuntimeStoreError(f"Stack inheritance cycle detected: {' -> '.join([*seen, stack_id])}")
    stack = get_stack(stack_id, home)
    objects: list[RuntimeObject] = []
    layer_sources: list[str] = []
    included_object_ids: set[str] = set()

    for parent_stack_id in stack.extends:
        parent_objects, parent_sources = _compose_layers(parent_stack_id, home, [*seen, stack_id])
        for runtime_object, source in zip(parent_objects, parent_sources, strict=True):
            if runtime_object.id not in included_object_ids:
                objects.append(runtime_object)
                layer_sources.append(source)
                included_object_ids.add(runtime_object.id)

    missing = []
    for object_id in stack.layers:
        try:
            runtime_object = get_object(object_id, home)
            if runtime_object.id not in included_object_ids:
                objects.append(runtime_object)
                layer_sources.append(stack.id)
                included_object_ids.add(runtime_object.id)
        except RuntimeStoreError:
            missing.append(object_id)
    if missing:
        raise RuntimeStoreError(f"Stack {stack_id} references missing Runtime Objects: {', '.join(missing)}")
    return objects, layer_sources


def compose_stack_json(stack_id: str, home: Path | None = None) -> str:
    return json.dumps(compose_stack(stack_id, home).to_dict(), indent=2)
