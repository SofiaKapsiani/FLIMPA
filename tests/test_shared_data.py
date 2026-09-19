"""Config defaults and gallery layer state structure."""

from utils.shared_data import SharedData


def test_lifetime_colormap_config_keys():
    sd = SharedData()
    assert "lifetime_cmap" in sd.config
    assert "lifetime_cmap_file" in sd.config
    assert sd.config["lifetime_cmap"] == "Rainbow"
    assert sd.config["lifetime_cmap_file"] == "None"
    assert sd.config["lifetime_itegrate"] == "False"


def test_phasor_layers_structure():
    sd = SharedData()
    for mode in ("individual", "condition"):
        assert mode in sd.phasor_layers
        assert "order" in sd.phasor_layers[mode]
        assert "visible" in sd.phasor_layers[mode]
        assert sd.phasor_layers[mode]["order"] == []
        assert sd.phasor_layers[mode]["visible"] == {}


def test_phasor_settings_defaults():
    sd = SharedData()
    assert sd.phasor_settings["plot_type"] in ("individual", "condition")
    assert sd.phasor_settings["scatter_type"] in ("scatter", "histogram", "contour")
