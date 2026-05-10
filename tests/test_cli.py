from pathlib import Path

import pytest

from flowstate_runtime import cli


def test_cli_init_and_examples(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path))

    cli.main(["init"])
    cli.main(["examples", "install"])
    cli.main(["stack", "inspect", "ai-builder"])

    output = capsys.readouterr().out
    assert "Initialized FlowState runtime home" in output
    assert "Installed example runtime pack" in output
    assert "AI Builder Runtime" in output
    assert "GitHub Issue Resolution" in output


def test_cli_bootstrap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    repo.mkdir()

    cli.main(["init"])
    cli.main(["examples", "install"])
    cli.main(["bootstrap", "create", "ai-builder", "--path", str(repo)])

    context = repo / ".flow" / "context.toml"
    assert context.exists()
    assert 'runtime = "flow://ai-builder"' in context.read_text(encoding="utf-8")


def test_cli_codex_install_and_drift(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    repo.mkdir()

    cli.main(["init"])
    cli.main(["examples", "install"])
    cli.main(["codex", "install", "ai-builder", "--path", str(repo)])
    cli.main(["bootstrap", "inspect", "--path", str(repo)])
    cli.main(["drift", "--path", str(repo)])

    output = capsys.readouterr().out
    assert "Add to Codex MCP config" in output
    assert "flowRuntime" in output
    assert '"stack_id": "ai-builder"' in output
    assert "status: ok" in output


def test_cli_bootstrap_rejects_missing_stack(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path / "home"))

    with pytest.raises(SystemExit) as exc:
        cli.main(["bootstrap", "create", "missing-stack", "--path", str(tmp_path / "repo")])

    assert exc.value.code == 1
    assert "Runtime Stack not found: missing-stack" in capsys.readouterr().err


def test_cli_bootstrap_inspect_rejects_invalid_runtime(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("FLOWSTATE_HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    context_dir = repo / ".flow"
    context_dir.mkdir(parents=True)
    (context_dir / "context.toml").write_text(
        'runtime = "http://example.com/nope"\nendpoint = "http://localhost:7777/mcp"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(["bootstrap", "inspect", "--path", str(repo)])

    assert exc.value.code == 1
    assert "Bootstrap runtime must use flow:// scheme" in capsys.readouterr().err
