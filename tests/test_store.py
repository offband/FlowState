from pathlib import Path

from flowstate_runtime.store import create_object, create_stack, get_object, get_stack, list_objects, list_stacks


def test_runtime_object_round_trip(tmp_path: Path) -> None:
    create_object("python-base", "Python Base", home=tmp_path)

    runtime_object = get_object("python-base", home=tmp_path)

    assert runtime_object.id == "python-base"
    assert runtime_object.title == "Python Base"
    assert "Python Base" in runtime_object.content
    assert [item.id for item in list_objects(home=tmp_path)] == ["python-base"]


def test_runtime_stack_round_trip(tmp_path: Path) -> None:
    create_stack("project-alpha", "Project Alpha", home=tmp_path)

    stack = get_stack("project-alpha", home=tmp_path)

    assert stack.id == "project-alpha"
    assert stack.title == "Project Alpha"
    assert stack.layers == []
    assert [item.id for item in list_stacks(home=tmp_path)] == ["project-alpha"]
