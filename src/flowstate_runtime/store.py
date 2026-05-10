from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from .models import RuntimeObject, RuntimeStack
from .paths import config_path, exports_dir, keys_dir, objects_dir, runtime_home, stacks_dir


ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


class RuntimeStoreError(ValueError):
    pass


def validate_id(identifier: str) -> str:
    if not ID_PATTERN.match(identifier):
        raise RuntimeStoreError(
            "IDs must start with a letter or number and contain only letters, numbers, dots, underscores, or hyphens."
        )
    return identifier


def ensure_home(home: Path | None = None) -> Path:
    resolved = home or runtime_home()
    for directory in (objects_dir(resolved), stacks_dir(resolved), keys_dir(resolved), exports_dir(resolved)):
        directory.mkdir(parents=True, exist_ok=True)
    config = config_path(resolved)
    if not config.exists():
        config.write_text('version = "1"\n', encoding="utf-8")
    return resolved


def parse_markdown_object(path: Path) -> RuntimeObject:
    text = path.read_text(encoding="utf-8")
    metadata, content = split_frontmatter(text)
    object_id = str(metadata.get("id") or path.stem)
    validate_id(object_id)
    object_type = metadata.get("type", "runtime_object")
    if object_type != "runtime_object":
        raise RuntimeStoreError(f"{path} is not a runtime_object")
    title = str(metadata.get("title") or object_id)
    version = str(metadata.get("version") or "1.0")
    return RuntimeObject(
        id=object_id,
        title=title,
        version=version,
        metadata=metadata,
        content=content.strip() + "\n",
        path=path,
        digest=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        uuid=str(metadata.get("uuid")) if metadata.get("uuid") else None,
    )


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    try:
        _, frontmatter, body = text.split("---\n", 2)
    except ValueError as exc:
        raise RuntimeStoreError("Malformed YAML frontmatter") from exc
    loaded = yaml.safe_load(frontmatter) or {}
    if not isinstance(loaded, dict):
        raise RuntimeStoreError("YAML frontmatter must be a mapping")
    return loaded, body


def render_runtime_object(identifier: str, title: str | None = None) -> str:
    validate_id(identifier)
    resolved_title = title or identifier.replace("-", " ").replace("_", " ").title()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return (
        "---\n"
        f"id: {identifier}\n"
        f"uuid: {uuid4()}\n"
        "type: runtime_object\n"
        f"title: {resolved_title}\n"
        "tags: []\n"
        "version: 1.0\n"
        f"created_at: {now}\n"
        f"updated_at: {now}\n"
        "---\n\n"
        f"# {resolved_title}\n\n"
        "Describe the operational context this object contributes.\n"
    )


def object_path(identifier: str, home: Path | None = None) -> Path:
    validate_id(identifier)
    return objects_dir(home) / f"{identifier}.md"


def stack_path(identifier: str, home: Path | None = None) -> Path:
    validate_id(identifier)
    return stacks_dir(home) / f"{identifier}.yaml"


def create_object(identifier: str, title: str | None = None, home: Path | None = None, overwrite: bool = False) -> Path:
    ensure_home(home)
    path = object_path(identifier, home)
    if path.exists() and not overwrite:
        raise RuntimeStoreError(f"Runtime Object already exists: {identifier}")
    path.write_text(render_runtime_object(identifier, title), encoding="utf-8")
    return path


def list_objects(home: Path | None = None) -> list[RuntimeObject]:
    ensure_home(home)
    objects: list[RuntimeObject] = []
    for path in sorted(objects_dir(home).glob("*.md")):
        objects.append(parse_markdown_object(path))
    return objects


def get_object(identifier: str, home: Path | None = None) -> RuntimeObject:
    path = object_path(identifier, home)
    if not path.exists():
        raise RuntimeStoreError(f"Runtime Object not found: {identifier}")
    return parse_markdown_object(path)


def render_stack(
    identifier: str,
    title: str | None = None,
    layers: list[str] | None = None,
    extends: list[str] | None = None,
) -> str:
    validate_id(identifier)
    resolved_title = title or identifier.replace("-", " ").replace("_", " ").title()
    return yaml.safe_dump(
        {
            "id": identifier,
            "type": "runtime_stack",
            "title": resolved_title,
            "extends": extends or [],
            "layers": layers or [],
        },
        sort_keys=False,
    )


def create_stack(identifier: str, title: str | None = None, home: Path | None = None, overwrite: bool = False) -> Path:
    ensure_home(home)
    path = stack_path(identifier, home)
    if path.exists() and not overwrite:
        raise RuntimeStoreError(f"Runtime Stack already exists: {identifier}")
    path.write_text(render_stack(identifier, title), encoding="utf-8")
    return path


def parse_stack(path: Path) -> RuntimeStack:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise RuntimeStoreError(f"Runtime Stack must be a mapping: {path}")
    stack_id = str(loaded.get("id") or path.stem)
    validate_id(stack_id)
    if loaded.get("type", "runtime_stack") != "runtime_stack":
        raise RuntimeStoreError(f"{path} is not a runtime_stack")
    layers = loaded.get("layers") or []
    if not isinstance(layers, list) or not all(isinstance(layer, str) for layer in layers):
        raise RuntimeStoreError(f"Stack layers must be a list of object IDs: {path}")
    extends_value = loaded.get("extends") or []
    if isinstance(extends_value, str):
        extends = [extends_value]
    elif isinstance(extends_value, list) and all(isinstance(item, str) for item in extends_value):
        extends = extends_value
    else:
        raise RuntimeStoreError(f"Stack extends must be a string or list of stack IDs: {path}")
    return RuntimeStack(
        id=stack_id,
        title=str(loaded.get("title") or stack_id),
        layers=layers,
        path=path,
        extends=extends,
        metadata=loaded,
    )


def list_stacks(home: Path | None = None) -> list[RuntimeStack]:
    ensure_home(home)
    return [parse_stack(path) for path in sorted(stacks_dir(home).glob("*.yaml"))]


def get_stack(identifier: str, home: Path | None = None) -> RuntimeStack:
    path = stack_path(identifier, home)
    if not path.exists():
        raise RuntimeStoreError(f"Runtime Stack not found: {identifier}")
    return parse_stack(path)


def save_stack(stack: RuntimeStack) -> None:
    payload = dict(stack.metadata)
    payload["id"] = stack.id
    payload["type"] = "runtime_stack"
    payload["title"] = stack.title
    payload["extends"] = stack.extends
    payload["layers"] = stack.layers
    stack.path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def add_stack_layer(stack_id: str, object_id: str, home: Path | None = None) -> RuntimeStack:
    get_object(object_id, home)
    stack = get_stack(stack_id, home)
    if object_id not in stack.layers:
        updated = RuntimeStack(stack.id, stack.title, [*stack.layers, object_id], stack.path, stack.extends, stack.metadata)
        save_stack(updated)
        return updated
    return stack


def remove_stack_layer(stack_id: str, object_id: str, home: Path | None = None) -> RuntimeStack:
    stack = get_stack(stack_id, home)
    updated = RuntimeStack(
        stack.id,
        stack.title,
        [layer for layer in stack.layers if layer != object_id],
        stack.path,
        stack.extends,
        stack.metadata,
    )
    save_stack(updated)
    return updated


def extend_stack(stack_id: str, parent_stack_id: str, home: Path | None = None) -> RuntimeStack:
    if stack_id == parent_stack_id:
        raise RuntimeStoreError("A stack cannot extend itself")
    parent_stack = get_stack(parent_stack_id, home)
    stack = get_stack(stack_id, home)
    if _stack_inherits_from(parent_stack, stack_id, home, seen=[]):
        raise RuntimeStoreError(f"Stack inheritance cycle detected: {stack_id} -> {parent_stack_id}")
    if parent_stack_id not in stack.extends:
        updated = RuntimeStack(
            stack.id,
            stack.title,
            stack.layers,
            stack.path,
            [*stack.extends, parent_stack_id],
            stack.metadata,
        )
        save_stack(updated)
        return updated
    return stack


def _stack_inherits_from(stack: RuntimeStack, target_stack_id: str, home: Path | None, seen: list[str]) -> bool:
    if stack.id in seen:
        raise RuntimeStoreError(f"Stack inheritance cycle detected: {' -> '.join([*seen, stack.id])}")
    if target_stack_id in stack.extends:
        return True
    return any(
        _stack_inherits_from(get_stack(parent_id, home), target_stack_id, home, [*seen, stack.id])
        for parent_id in stack.extends
    )


def move_stack_layer(stack_id: str, object_id: str, direction: str, home: Path | None = None) -> RuntimeStack:
    stack = get_stack(stack_id, home)
    if object_id not in stack.layers:
        raise RuntimeStoreError(f"Runtime Object is not a direct layer in {stack_id}: {object_id}")
    index = stack.layers.index(object_id)
    offset = -1 if direction == "up" else 1 if direction == "down" else None
    if offset is None:
        raise RuntimeStoreError("direction must be 'up' or 'down'")
    destination = index + offset
    if destination < 0 or destination >= len(stack.layers):
        return stack
    layers = list(stack.layers)
    layers[index], layers[destination] = layers[destination], layers[index]
    updated = RuntimeStack(stack.id, stack.title, layers, stack.path, stack.extends, stack.metadata)
    save_stack(updated)
    return updated
