from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .compose import compose_stack
from .store import RuntimeStoreError, list_objects, list_stacks, object_path


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


def validate_runtime(home: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_object_ids: dict[str, str] = {}

    for runtime_object in list_objects(home):
        expected_path = object_path(runtime_object.id, home)
        if runtime_object.path != expected_path:
            issues.append(
                ValidationIssue(
                    "warning",
                    "object_id_path_mismatch",
                    f"Object id {runtime_object.id} does not match expected path {expected_path.name}",
                    str(runtime_object.path),
                )
            )
        for field in ("id", "title", "version", "type"):
            if field not in runtime_object.metadata:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"missing_object_{field}",
                        f"Runtime Object {runtime_object.id} is missing frontmatter field: {field}",
                        str(runtime_object.path),
                    )
                )
        if "uuid" not in runtime_object.metadata:
            issues.append(
                ValidationIssue(
                    "warning",
                    "missing_object_uuid",
                    f"Runtime Object {runtime_object.id} has no stable uuid",
                    str(runtime_object.path),
                )
            )
        if runtime_object.id in seen_object_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "duplicate_object_id",
                    f"Duplicate Runtime Object id {runtime_object.id}",
                    str(runtime_object.path),
                )
            )
        seen_object_ids[runtime_object.id] = str(runtime_object.path)

    for stack in list_stacks(home):
        for field in ("id", "title", "type", "layers"):
            if field not in stack.metadata:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"missing_stack_{field}",
                        f"Runtime Stack {stack.id} is missing field: {field}",
                        str(stack.path),
                    )
                )
        try:
            compose_stack(stack.id, home)
        except RuntimeStoreError as exc:
            issues.append(
                ValidationIssue(
                    "error",
                    "invalid_stack_composition",
                    str(exc),
                    str(stack.path),
                )
            )

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.level == "error" for issue in issues)
