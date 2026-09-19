"""Gallery layer order / visibility sync (pure logic, mirrors PhasorPlot._sync_layer_state)."""


def sync_layer_state(state, labels):
    """Copy of phasor layer sync for unit testing without QWidget."""
    order = [label for label in state["order"] if label in labels]
    for label in labels:
        if label not in order:
            order.append(label)
        if label not in state["visible"]:
            state["visible"][label] = True
    for label in list(state["visible"].keys()):
        if label not in labels:
            del state["visible"][label]
    state["order"] = order
    return order, state["visible"]


def test_new_labels_appended_in_stable_order():
    state = {"order": ["B"], "visible": {"B": True}}
    order, visible = sync_layer_state(state, ["A", "B", "C"])
    assert order == ["B", "A", "C"]
    assert visible == {"B": True, "A": True, "C": True}


def test_removed_labels_dropped_from_visibility():
    state = {"order": ["A", "B"], "visible": {"A": True, "B": False, "X": True}}
    order, visible = sync_layer_state(state, ["A"])
    assert order == ["A"]
    assert "B" not in visible
    assert "X" not in visible


def test_preserves_existing_visibility():
    state = {"order": ["A"], "visible": {"A": False}}
    _, visible = sync_layer_state(state, ["A", "B"])
    assert visible["A"] is False
    assert visible["B"] is True
