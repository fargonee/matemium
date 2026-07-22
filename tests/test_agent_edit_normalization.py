from matemium.agent.edit_normalization import has_edit_proposal, normalize_model_edit


def fenced(source: str) -> str:
    return f"Certainly, here is the updated code:\n```python\n{source}\n```"


def test_full_file_rename_is_generically_reduced_to_small_diff() -> None:
    current = "from canvas import CanvasScene\n\nclass QuadraticGraphs(CanvasScene):\n    pass"
    proposed = current.replace("QuadraticGraphs", "QuadraticGraphsNew")
    edit = normalize_model_edit(fenced(proposed), current)
    assert edit is not None
    assert edit.full_file is None
    assert "class QuadraticGraphs(CanvasScene):" in edit.search
    assert "class QuadraticGraphsNew(CanvasScene):" in edit.replace
    assert current.replace(edit.search, edit.replace) == proposed


def test_same_algorithm_minimizes_arbitrary_localized_update() -> None:
    current = "from canvas import CanvasScene\n\nclass Demo(CanvasScene):\n    title = 'Old'\n    color = 'blue'"
    proposed = current.replace("title = 'Old'", "title = 'New'")
    edit = normalize_model_edit(fenced(proposed), current)
    assert edit is not None
    assert current.replace(edit.search, edit.replace) == proposed


def test_explicit_patch_requires_unique_exact_precondition() -> None:
    proposal = "<<<<<<< SEARCH\nx = 1\n=======\nx = 2\n>>>>>>> REPLACE"
    assert normalize_model_edit(proposal, "x = 1") is not None
    assert normalize_model_edit(proposal, "x = 1\nx = 1") is None
    assert normalize_model_edit(proposal, "x = 3") is None


def test_large_or_ambiguous_full_file_rewrite_is_rejected() -> None:
    header = "from canvas import CanvasScene\nclass Demo(CanvasScene):\n"
    current = header + "\n".join(f"    value_{i} = {i}" for i in range(100))
    rewrite = header + "\n".join(f"    changed_{i} = {i}" for i in range(100))
    assert normalize_model_edit(fenced(rewrite), current) is None
    assert has_edit_proposal(fenced(rewrite))


def test_new_file_can_remain_full_file() -> None:
    proposed = "from canvas import CanvasScene\nclass Demo(CanvasScene):\n    pass"
    edit = normalize_model_edit(fenced(proposed), "")
    assert edit is not None
    assert edit.full_file == proposed
