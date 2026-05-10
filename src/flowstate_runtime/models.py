from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeObject:
    id: str
    title: str
    version: str
    content: str
    path: Path
    digest: str
    uuid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tags(self) -> list[str]:
        value = self.metadata.get("tags", [])
        return value if isinstance(value, list) else []

    def to_layer_dict(self, index: int) -> dict[str, Any]:
        return {
            "index": index,
            "id": self.id,
            "title": self.title,
            "version": self.version,
            "uuid": self.uuid,
            "digest": self.digest,
            "path": str(self.path),
            "metadata": self.metadata,
            "content": self.content,
        }


@dataclass(frozen=True)
class RuntimeStack:
    id: str
    title: str
    layers: list[str]
    path: Path
    extends: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComposedRuntime:
    stack: RuntimeStack
    objects: list[RuntimeObject]
    layer_sources: list[str] = field(default_factory=list)

    def manifest(self) -> dict[str, Any]:
        return {
            "runtime": f"flow://{self.stack.id}",
            "title": self.stack.title,
            "stack_id": self.stack.id,
            "layer_count": len(self.objects),
            "digest": self.digest(),
            "object_ids": [runtime_object.id for runtime_object in self.objects],
            "source_stacks": self.layer_sources,
            "recommended_tools": [
                "get_active_runtime_context",
                "get_runtime_stack",
                "get_runtime_stack_markdown",
                "get_runtime_stack_provenance",
            ],
            "instruction": "Use this Runtime Stack as the operational source of truth for project context.",
        }

    def digest(self) -> str:
        import hashlib

        payload = "|".join(
            [
                self.stack.id,
                *[
                    f"{runtime_object.id}:{runtime_object.digest}"
                    for runtime_object in self.objects
                ],
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime": f"flow://{self.stack.id}",
            "manifest": self.manifest(),
            "stack": {
                "id": self.stack.id,
                "title": self.stack.title,
                "path": str(self.stack.path),
                "metadata": self.stack.metadata,
                "extends": self.stack.extends,
                "layers": self.stack.layers,
            },
            "layers": [
                {
                    **runtime_object.to_layer_dict(index),
                    "source_stack": self.layer_sources[index - 1]
                    if index - 1 < len(self.layer_sources)
                    else self.stack.id,
                }
                for index, runtime_object in enumerate(self.objects, start=1)
            ],
            "rendered_markdown": self.to_markdown(),
        }

    def to_markdown(self) -> str:
        lines: list[str] = [
            f"# {self.stack.title}",
            "",
            f"> Runtime: flow://{self.stack.id}",
            f"> Layers: {len(self.objects)}",
            f"> Digest: {self.digest()}",
            "",
            "## Runtime Layers",
            "",
        ]
        for index, runtime_object in enumerate(self.objects, start=1):
            lines.append(f"{index}. {runtime_object.title} (`{runtime_object.id}`)")
        lines.extend(["", "## Runtime Context", ""])
        for index, runtime_object in enumerate(self.objects, start=1):
            lines.extend(
                [
                    f"### Layer {index}: {runtime_object.title}",
                    "",
                    f"- Object ID: `{runtime_object.id}`",
                    f"- Source Stack: `{self.layer_sources[index - 1] if index - 1 < len(self.layer_sources) else self.stack.id}`",
                    f"- Source: `{runtime_object.path}`",
                    f"- Version: `{runtime_object.version}`",
                    f"- Digest: `{runtime_object.digest}`",
                    "",
                    runtime_object.content.strip(),
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"
