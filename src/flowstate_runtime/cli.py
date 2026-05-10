from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from .auth import ensure_token, read_token, rotate_token
from .bootstrap import read_bootstrap, write_bootstrap
from .client import resolve_runtime
from .compose import compose_stack, compose_stack_json
from .codex import install_codex_bootstrap
from .paths import DEFAULT_ENDPOINT, TOKEN_ENV, exports_dir, runtime_home
from .drift import inspect_drift
from .store import (
    RuntimeStoreError,
    add_stack_layer,
    create_object,
    create_stack,
    ensure_home,
    extend_stack,
    get_object,
    get_stack,
    list_objects,
    list_stacks,
    move_stack_layer,
    object_path,
    remove_stack_layer,
)
from .validate import has_errors, validate_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flow", description="FlowState operational runtime CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize the local FlowState runtime home")

    auth = subparsers.add_parser("auth", help="Authentication helpers")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_sub.add_parser("token", help="Print the local runtime bearer token")
    auth_sub.add_parser("rotate", help="Rotate the local runtime bearer token")

    examples = subparsers.add_parser("examples", help="Example runtime pack commands")
    examples_sub = examples.add_subparsers(dest="examples_command", required=True)
    examples_sub.add_parser("install", help="Install the bundled example runtime pack")

    obj = subparsers.add_parser("object", aliases=["obj"], help="Runtime Object commands")
    obj_sub = obj.add_subparsers(dest="object_command", required=True)
    obj_create = obj_sub.add_parser("create", help="Create a Markdown Runtime Object")
    obj_create.add_argument("id")
    obj_create.add_argument("--title")
    obj_create.add_argument("--force", action="store_true")
    obj_sub.add_parser("list", help="List Runtime Objects")
    obj_inspect = obj_sub.add_parser("inspect", help="Inspect a Runtime Object")
    obj_inspect.add_argument("id")
    obj_path = obj_sub.add_parser("path", help="Print a Runtime Object path")
    obj_path.add_argument("id")

    stack = subparsers.add_parser("stack", help="Runtime Stack commands")
    stack_sub = stack.add_subparsers(dest="stack_command", required=True)
    stack_create = stack_sub.add_parser("create", help="Create a Runtime Stack")
    stack_create.add_argument("id")
    stack_create.add_argument("--title")
    stack_create.add_argument("--force", action="store_true")
    stack_add = stack_sub.add_parser("add", help="Add an object layer to a Runtime Stack")
    stack_add.add_argument("stack")
    stack_add.add_argument("object")
    stack_remove = stack_sub.add_parser("remove", help="Remove an object layer from a Runtime Stack")
    stack_remove.add_argument("stack")
    stack_remove.add_argument("object")
    stack_extend = stack_sub.add_parser("extend", help="Make a Runtime Stack inherit another stack")
    stack_extend.add_argument("stack")
    stack_extend.add_argument("parent")
    stack_move = stack_sub.add_parser("move", help="Move a direct object layer up or down")
    stack_move.add_argument("stack")
    stack_move.add_argument("object")
    stack_move.add_argument("direction", choices=["up", "down"])
    stack_sub.add_parser("list", help="List Runtime Stacks")
    stack_inspect = stack_sub.add_parser("inspect", help="Inspect a composed Runtime Stack")
    stack_inspect.add_argument("id")
    stack_inspect.add_argument("--json", action="store_true")
    stack_manifest = stack_sub.add_parser("manifest", help="Print Runtime Stack manifest and digest")
    stack_manifest.add_argument("id")
    stack_export = stack_sub.add_parser("export", help="Export a composed Runtime Stack")
    stack_export.add_argument("id")
    stack_export.add_argument("--format", choices=["markdown", "json"], default="markdown")
    stack_export.add_argument("--output")

    bootstrap = subparsers.add_parser("bootstrap", help="Project bootstrap commands")
    bootstrap_sub = bootstrap.add_subparsers(dest="bootstrap_command", required=True)
    bootstrap_create = bootstrap_sub.add_parser("create", help="Write .flow/context.toml into a project")
    bootstrap_create.add_argument("stack")
    bootstrap_create.add_argument("--path", default=".")
    bootstrap_create.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    bootstrap_create.add_argument("--auth-env", default=TOKEN_ENV)
    bootstrap_inspect = bootstrap_sub.add_parser("inspect", help="Inspect .flow/context.toml")
    bootstrap_inspect.add_argument("--path", default=".")

    codex = subparsers.add_parser("codex", help="Codex integration helpers")
    codex_sub = codex.add_subparsers(dest="codex_command", required=True)
    codex_install = codex_sub.add_parser("install", help="Install project bootstrap and print Codex MCP config")
    codex_install.add_argument("stack")
    codex_install.add_argument("--path", default=".")
    codex_install.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    codex_install.add_argument("--auth-env", default=TOKEN_ENV)
    codex_install.add_argument("--server-name", default="flowRuntime")
    codex_install.add_argument("--no-instruction", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate Runtime Objects and Stacks")
    validate.add_argument("--json", action="store_true")

    doctor = subparsers.add_parser("doctor", help="Check runtime home, auth, examples, and validation")
    doctor.add_argument("--json", action="store_true")

    resolve = subparsers.add_parser("resolve", help="Resolve the Runtime Stack declared by .flow/context.toml")
    resolve.add_argument("--path", default=".")
    resolve.add_argument("--format", choices=["markdown", "json"], default="markdown")
    resolve.add_argument("--local-fallback", action="store_true")

    drift = subparsers.add_parser("drift", help="Inspect project bootstrap drift against local or remote runtime")
    drift.add_argument("--path", default=".")
    drift.add_argument("--remote", action="store_true")
    drift.add_argument("--json", action="store_true")

    serve = subparsers.add_parser("serve", help="Serve the local MCP-compatible runtime endpoint")
    serve.add_argument("stack", nargs="?", help="Optional default stack ID")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=7777)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        dispatch(args)
    except (RuntimeStoreError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def dispatch(args: argparse.Namespace) -> None:
    if args.command == "init":
        home = ensure_home()
        token = ensure_token()
        print(f"Initialized FlowState runtime home: {home}")
        print(f"Bearer token: export {TOKEN_ENV}={token}")
    elif args.command == "auth":
        if args.auth_command == "rotate":
            print(rotate_token())
        else:
            print(read_token())
    elif args.command == "examples":
        install_examples()
    elif args.command in {"object", "obj"}:
        handle_object(args)
    elif args.command == "stack":
        handle_stack(args)
    elif args.command == "bootstrap":
        if args.bootstrap_command == "create":
            get_stack(args.stack)
            target = write_bootstrap(args.stack, Path(args.path).resolve(), args.endpoint, args.auth_env)
            print(target)
        elif args.bootstrap_command == "inspect":
            print(json.dumps(read_bootstrap(Path(args.path).resolve()), indent=2))
    elif args.command == "codex":
        handle_codex(args)
    elif args.command == "validate":
        handle_validate(args)
    elif args.command == "doctor":
        handle_doctor(args)
    elif args.command == "resolve":
        handle_resolve(args)
    elif args.command == "drift":
        handle_drift(args)
    elif args.command == "serve":
        from .server import run_server

        run_server(host=args.host, port=args.port, default_stack=args.stack)


def handle_object(args: argparse.Namespace) -> None:
    if args.object_command == "create":
        print(create_object(args.id, args.title, overwrite=args.force))
    elif args.object_command == "list":
        for runtime_object in list_objects():
            print(f"{runtime_object.id}\t{runtime_object.title}\t{runtime_object.path}")
    elif args.object_command == "inspect":
        runtime_object = get_object(args.id)
        print(json.dumps(runtime_object.to_layer_dict(1), indent=2))
    elif args.object_command == "path":
        print(object_path(args.id))


def handle_stack(args: argparse.Namespace) -> None:
    if args.stack_command == "create":
        print(create_stack(args.id, args.title, overwrite=args.force))
    elif args.stack_command == "add":
        stack = add_stack_layer(args.stack, args.object)
        print(f"{stack.id}: {', '.join(stack.layers)}")
    elif args.stack_command == "remove":
        stack = remove_stack_layer(args.stack, args.object)
        print(f"{stack.id}: {', '.join(stack.layers)}")
    elif args.stack_command == "extend":
        stack = extend_stack(args.stack, args.parent)
        print(f"{stack.id} extends: {', '.join(stack.extends)}")
    elif args.stack_command == "move":
        stack = move_stack_layer(args.stack, args.object, args.direction)
        print(f"{stack.id}: {', '.join(stack.layers)}")
    elif args.stack_command == "list":
        for stack in list_stacks():
            print(f"{stack.id}\t{stack.title}\t{len(stack.layers)} layers\t{stack.path}")
    elif args.stack_command == "inspect":
        if args.json:
            print(compose_stack_json(args.id))
        else:
            print(compose_stack(args.id).to_markdown(), end="")
    elif args.stack_command == "manifest":
        print(json.dumps(compose_stack(args.id).manifest(), indent=2))
    elif args.stack_command == "export":
        composed = compose_stack(args.id)
        if args.format == "json":
            text = json.dumps(composed.to_dict(), indent=2) + "\n"
            suffix = "json"
        else:
            text = composed.to_markdown()
            suffix = "md"
        if args.output:
            output = Path(args.output)
        else:
            exports_dir().mkdir(parents=True, exist_ok=True)
            output = exports_dir() / f"{args.id}.{suffix}"
        output.write_text(text, encoding="utf-8")
        print(output)


def install_examples() -> None:
    ensure_home()
    package_example = resources.files("flowstate_runtime").joinpath("example_pack")
    with resources.as_file(package_example) as packaged_root:
        example_root = packaged_root
        if not example_root.exists():
            example_root = Path(__file__).resolve().parents[2] / "examples" / "runtime-pack"
        if not example_root.exists():
            raise RuntimeStoreError("Bundled example runtime pack is missing")
        for source_dir_name, target_dir in (("objects", runtime_home() / "objects"), ("stacks", runtime_home() / "stacks")):
            source_dir = example_root / source_dir_name
            target_dir.mkdir(parents=True, exist_ok=True)
            for source in source_dir.iterdir():
                if source.is_file():
                    shutil.copy2(source, target_dir / source.name)
    print(f"Installed example runtime pack into {runtime_home()}")


def handle_codex(args: argparse.Namespace) -> None:
    context_path, instruction_path, config = install_codex_bootstrap(
        args.stack,
        Path(args.path).resolve(),
        args.endpoint,
        args.auth_env,
        args.server_name,
        write_instruction=not args.no_instruction,
    )
    print(f"Wrote {context_path}")
    if instruction_path:
        print(f"Wrote {instruction_path}")
    print("\nAdd to Codex MCP config:\n")
    print(config, end="")
    print(f'\nExport token:\nexport {args.auth_env}="$(flow auth token)"')


def handle_validate(args: argparse.Namespace) -> None:
    issues = validate_runtime()
    if args.json:
        print(json.dumps([issue.to_dict() for issue in issues], indent=2))
    else:
        if not issues:
            print("Runtime validation passed.")
        for issue in issues:
            location = f" ({issue.path})" if issue.path else ""
            print(f"{issue.level.upper()} {issue.code}: {issue.message}{location}")
    if has_errors(issues):
        raise SystemExit(1)


def handle_doctor(args: argparse.Namespace) -> None:
    home = ensure_home()
    issues = validate_runtime()
    payload = {
        "runtime_home": str(home),
        "objects": len(list_objects()),
        "stacks": len(list_stacks()),
        "token_configured": bool(read_token()),
        "validation_errors": sum(1 for issue in issues if issue.level == "error"),
        "validation_warnings": sum(1 for issue in issues if issue.level == "warning"),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def handle_resolve(args: argparse.Namespace) -> None:
    bootstrap = read_bootstrap(Path(args.path).resolve())
    stack_id = bootstrap.get("stack_id")
    markdown = args.format == "markdown"
    try:
        result = resolve_runtime(str(bootstrap["endpoint"]), stack_id, str(bootstrap.get("auth_env") or TOKEN_ENV), markdown)
        print(result if isinstance(result, str) else json.dumps(result, indent=2))
    except Exception as exc:
        if not args.local_fallback:
            raise RuntimeError(str(exc)) from exc
        composed = compose_stack(str(stack_id))
        print(composed.to_markdown() if markdown else json.dumps(composed.to_dict(), indent=2))


def handle_drift(args: argparse.Namespace) -> None:
    result = inspect_drift(Path(args.path).resolve(), remote=args.remote)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"status: {result['status']}")
        for check in result["checks"]:
            marker = "ok" if check["ok"] else "drift"
            print(f"{marker}: {check['name']} - {check['detail']}")
    if result["status"] != "ok":
        raise SystemExit(1)
