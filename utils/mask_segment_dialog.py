"""
Parameter dialog for auto-segmentation (Instruments → Auto segment).

Field definitions and defaults come from utils.auto_segmentation.ALGORITHMS.

FUTURE / NOT IN UI: dialog is kept for later. Gated by AUTO_SEGMENT_UI_ENABLED in auto_segmentation.py.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from utils.auto_segmentation import ALGORITHMS


class AutoSegmentDialog(QDialog):
    """Algorithm picker + per-algorithm numeric parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-segment")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Runs on the intensity image for the selected file. "
                "You can refine the result with Brush and Eraser afterwards."
            )
        )

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(list(ALGORITHMS.keys()))
        self.algorithm_combo.currentIndexChanged.connect(self._rebuild_fields)
        layout.addWidget(self.algorithm_combo)

        self.form = QFormLayout()
        layout.addLayout(self.form)
        self._spinboxes: dict[str, QDoubleSpinBox | QSpinBox] = {}

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._rebuild_fields()

    def _rebuild_fields(self):
        """Rebuild spinboxes when the user switches algorithm in the combo box."""
        while self.form.rowCount():
            self.form.removeRow(0)
        self._spinboxes.clear()

        name = self.algorithm_combo.currentText()
        spec = ALGORITHMS[name]
        for key, label in spec["fields"]:
            default = spec["defaults"][key]
            if isinstance(default, int):
                widget = QSpinBox()
                widget.setRange(1, 10000)
                widget.setValue(default)
            else:
                widget = QDoubleSpinBox()
                widget.setRange(0.001, 10000.0)
                widget.setDecimals(4)
                widget.setSingleStep(0.05)
                widget.setValue(float(default))
            self._spinboxes[key] = widget
            self.form.addRow(label, widget)

    def get_params(self) -> tuple[str, dict]:
        name = self.algorithm_combo.currentText()
        params = {}
        for key, widget in self._spinboxes.items():
            params[key] = widget.value() if isinstance(widget, QSpinBox) else float(widget.value())
        return name, params
