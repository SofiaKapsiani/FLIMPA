"""Movable secondary window for per-pixel decay curves (baseline check)."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from utils.decay_inspector import PixelDecay, get_pixel_decay
from utils.decay_fitting import (
    DECAY_FIT_UI_ENABLED,
    DecayFitResult,
    fit_single_exponential,
    predict_decay_at_tau,
    shift_model_on_time_axis,
)

_TEAL = "#3ca2a1"
_FIT_COLOR = "#FFB347"
_MAP_TAU_COLOR = "#B388FF"
_BG = (18 / 255, 18 / 255, 18 / 255)
_CURSOR_COLOR = "#FFE066"
_T0_LINE_COLOR = "#FF9F43"
_ZERO_MARKER_COLOR = "#5a9e9d"
_MAP_SHIFT_SLIDER_SCALE = 100  # slider value / scale = ns
_MAP_SHIFT_MAX_NS = 5.0


def _series_from_t0(t: np.ndarray, y: np.ndarray, t0_ns: float | None) -> tuple[np.ndarray, np.ndarray]:
    """Return curve samples at/after t₀ (fit region); hide the pre-t₀ zero plateau."""
    if t0_ns is None or t.size == 0:
        return t, y
    mask = t >= float(t0_ns) - 1e-9
    if not np.any(mask):
        return t, y
    return t[mask], y[mask]


def _plot_times(
    t: np.ndarray,
    y: np.ndarray,
    *,
    t0_ns: float | None,
    align_at_t0: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Restrict to the fit window; optionally re-zero the axis at t₀."""
    t_out, y_out = _series_from_t0(t, y, t0_ns)
    if align_at_t0 and t0_ns is not None and t_out.size:
        t_out = t_out - float(t0_ns)
    return t_out, y_out


def _draw_t0_region(ax, t0_ns: float, fraction_pct: float | None, t_min: float):
    """Mark baseline window and where τ fitting begins."""
    ax.axvspan(t_min, t0_ns, color="white", alpha=0.06, zorder=0)
    ax.axvline(
        t0_ns, color=_T0_LINE_COLOR, linestyle="--", linewidth=1.2, alpha=0.9, zorder=2,
        label=f"t₀ fit start ({fraction_pct:g}%)" if fraction_pct is not None else "t₀ fit start",
    )


def _aggregate_max_per_time(t: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One point per delay time; if times repeat, keep the largest count."""
    t = np.asarray(t, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if t.size == 0:
        return t, y
    order = np.argsort(t)
    t, y = t[order], y[order]
    t_key = np.round(t, 6)
    unique_keys = np.unique(t_key)
    if unique_keys.size == t.size:
        return t, y
    t_out = np.empty(unique_keys.size, dtype=np.float64)
    y_out = np.empty(unique_keys.size, dtype=np.float64)
    for i, key in enumerate(unique_keys):
        mask = t_key == key
        t_out[i] = float(t[mask].mean())
        y_out[i] = float(y[mask].max())
    return t_out, y_out


def _zero_display_height(y_max: float) -> float:
    return max(y_max * 0.06, 0.12)


class DecayCurveWindow(QMainWindow):
    """Independent, draggable window showing photon counts vs delay time."""

    def __init__(self, main_window):
        super().__init__(None)
        self.main_window = main_window
        self.setWindowTitle("FLIMPA — Baseline check")
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setMinimumSize(420, 320)
        self.resize(520, 380)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.info_label = QLabel("Enable Baseline check in Lifetime maps Settings, then click on the lifetime image.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: rgb(200, 200, 200); padding: 4px;")
        layout.addWidget(self.info_label)

        self.figure = Figure(figsize=(5, 3.2), dpi=100, facecolor=_BG)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=1)

        controls = QHBoxLayout()
        self.log_check = QCheckBox("Log scale (Y)")
        self.log_check.setStyleSheet("color: white;")
        self.log_check.toggled.connect(self._redraw_last)
        controls.addWidget(self.log_check)

        # FUTURE: orange 1-exp fit overlay — gated by DECAY_FIT_UI_ENABLED
        if DECAY_FIT_UI_ENABLED:
            self.show_fit_check = QCheckBox("Show fit (1 exp)")
            self.show_fit_check.setStyleSheet("color: white;")
            self.show_fit_check.setChecked(True)
            self.show_fit_check.setToolTip(
                "Requires Baseline correction = True and % time channels set (defines t₀)."
            )
            self.show_fit_check.toggled.connect(self._redraw_last)
            controls.addWidget(self.show_fit_check)

        self.show_map_tau_check = QCheckBox("Show map τ curve")
        self.show_map_tau_check.setStyleSheet("color: white;")
        self.show_map_tau_check.setChecked(True)
        self.show_map_tau_check.setToolTip(
            "Overlay a 1-exp model using τ from the lifetime map. "
            "Use IRF (purple row) chooses reconvolution vs a plain exponential."
        )
        self.show_map_tau_check.toggled.connect(self._redraw_last)
        controls.addWidget(self.show_map_tau_check)

        self.align_t0_check = QCheckBox("Start plot at t₀")
        self.align_t0_check.setStyleSheet("color: white;")
        self.align_t0_check.setChecked(True)
        self.align_t0_check.setToolTip(
            "Shift the time axis so t₀ = 0 and hide the empty baseline region on the left."
        )
        self.align_t0_check.toggled.connect(self._redraw_last)
        controls.addWidget(self.align_t0_check)

        controls.addStretch(1)
        layout.addLayout(controls)

        # FUTURE: extra orange-fit test controls stay hidden unless DECAY_FIT_UI_ENABLED
        if DECAY_FIT_UI_ENABLED:
            test_row = QHBoxLayout()
            test_label = QLabel("Test:")
            test_label.setStyleSheet("color: rgb(255, 180, 80);")
            test_row.addWidget(test_label)

            self.peak_align_check = QCheckBox("Align model peak to data")
            self.peak_align_check.setStyleSheet("color: white;")
            self.peak_align_check.setChecked(True)
            self.peak_align_check.setToolTip(
                "TEST: shift IRF⊗exp / map model so its peak matches the measured peak."
            )
            self.peak_align_check.toggled.connect(self._redraw_last)
            test_row.addWidget(self.peak_align_check)
            test_row.addStretch(1)
            layout.addLayout(test_row)

        slide_row = QHBoxLayout()
        self.use_irf_check = QCheckBox("Use IRF")
        self.use_irf_check.setStyleSheet("color: rgb(180, 140, 255);")
        self.use_irf_check.setChecked(True)
        self.use_irf_check.setToolTip(
            "On: purple curve is IRF ⊗ exponential (needs a reference file).\n"
            "Off: purple curve is a plain monoexponential."
        )
        self.use_irf_check.toggled.connect(self._redraw_last)
        slide_row.addWidget(self.use_irf_check)

        map_shift_label = QLabel("Move map τ:")
        map_shift_label.setStyleSheet("color: rgb(180, 140, 255);")
        slide_row.addWidget(map_shift_label)

        self.map_shift_slider = QSlider(Qt.Horizontal)
        self.map_shift_slider.setRange(-500, 500)
        self.map_shift_slider.setValue(0)
        self.map_shift_slider.setToolTip("Slide the purple map-τ curve ±5 ns (display only).")
        self.map_shift_slider.valueChanged.connect(self._on_map_shift_slider_changed)
        slide_row.addWidget(self.map_shift_slider, stretch=1)

        self.map_shift_spin = QDoubleSpinBox()
        self.map_shift_spin.setRange(-_MAP_SHIFT_MAX_NS, _MAP_SHIFT_MAX_NS)
        self.map_shift_spin.setDecimals(2)
        self.map_shift_spin.setSingleStep(0.05)
        self.map_shift_spin.setSuffix(" ns")
        self.map_shift_spin.setKeyboardTracking(False)
        self.map_shift_spin.setStyleSheet(
            "color: rgb(180, 140, 255); background: rgb(40, 40, 40); padding: 2px;"
        )
        self.map_shift_spin.valueChanged.connect(self._on_map_shift_spin_changed)
        slide_row.addWidget(self.map_shift_spin)

        self.map_shift_reset_btn = QPushButton("Reset")
        self.map_shift_reset_btn.setToolTip("Reset map curve slide to 0 ns")
        self.map_shift_reset_btn.clicked.connect(self._reset_map_shift)
        slide_row.addWidget(self.map_shift_reset_btn)
        layout.addLayout(slide_row)

        self._map_shift_ns = 0.0

        self._last_decay: PixelDecay | None = None
        self._last_fit: DecayFitResult | None = None
        self._plot_ax = None
        self._cursor_vline = None
        self._cursor_label = None
        self._cursor_active = False
        self._cursor_cids: list[int] = []
        self._data_xlim: tuple[float, float] | None = None
        self._data_ylim: tuple[float, float] | None = None
        self._t_min_ns: float | None = None
        self._t_max_ns: float | None = None
        self._connect_cursor_handlers()
        self._draw_empty_axes()

    def _set_map_shift_ns(self, shift_ns: float, *, redraw: bool = True):
        shift_ns = float(np.clip(shift_ns, -_MAP_SHIFT_MAX_NS, _MAP_SHIFT_MAX_NS))
        self._map_shift_ns = shift_ns
        slider_val = int(round(shift_ns * _MAP_SHIFT_SLIDER_SCALE))
        self.map_shift_slider.blockSignals(True)
        self.map_shift_spin.blockSignals(True)
        self.map_shift_slider.setValue(slider_val)
        self.map_shift_spin.setValue(shift_ns)
        self.map_shift_slider.blockSignals(False)
        self.map_shift_spin.blockSignals(False)
        if redraw:
            self._redraw_last()

    def _on_map_shift_slider_changed(self, value: int):
        self._set_map_shift_ns(value / _MAP_SHIFT_SLIDER_SCALE, redraw=True)

    def _on_map_shift_spin_changed(self, value: float):
        self._set_map_shift_ns(float(value), redraw=True)

    def _reset_map_shift(self):
        self._set_map_shift_ns(0.0, redraw=True)

    def _reset_map_shift_silent(self):
        self._set_map_shift_ns(0.0, redraw=False)

    def _connect_cursor_handlers(self):
        self._disconnect_cursor_handlers()
        self._cursor_cids = [
            self.canvas.mpl_connect("button_press_event", self._on_cursor_press),
            self.canvas.mpl_connect("motion_notify_event", self._on_cursor_motion),
            self.canvas.mpl_connect("button_release_event", self._on_cursor_release),
            self.canvas.mpl_connect("axes_leave_event", self._on_cursor_leave),
        ]

    def _disconnect_cursor_handlers(self):
        for cid in self._cursor_cids:
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._cursor_cids = []

    def _clear_time_cursor(self):
        for artist in (self._cursor_vline, self._cursor_label):
            if artist is not None:
                try:
                    artist.remove()
                except Exception:
                    pass
        self._cursor_vline = None
        self._cursor_label = None

    def _lock_plot_limits(self):
        if self._plot_ax is None:
            return
        if self._data_xlim is not None:
            self._plot_ax.set_xlim(self._data_xlim)
        if self._data_ylim is not None:
            self._plot_ax.set_ylim(self._data_ylim)

    def _store_plot_limits(self, ax):
        self._data_xlim = ax.get_xlim()
        self._data_ylim = ax.get_ylim()
        ax.set_autoscale_on(False)

    def _delay_percent(self, x_ns: float) -> float:
        if self._t_min_ns is None or self._t_max_ns is None:
            return 0.0
        span = self._t_max_ns - self._t_min_ns
        if span <= 0:
            return 0.0
        return float(np.clip((x_ns - self._t_min_ns) / span * 100.0, 0.0, 100.0))

    def _update_time_cursor(self, x_ns: float):
        if self._plot_ax is None:
            return
        ax = self._plot_ax
        self._clear_time_cursor()

        pct = self._delay_percent(x_ns)
        self._cursor_vline = ax.axvline(
            x_ns, color=_CURSOR_COLOR, linestyle=":", linewidth=1.4, zorder=15,
        )
        self._cursor_label = ax.annotate(
            f"{pct:.1f}%",
            xy=(x_ns, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(-10, -6),
            textcoords="offset points",
            ha="right",
            va="top",
            color=_CURSOR_COLOR,
            fontsize=9,
            fontweight="bold",
            annotation_clip=True,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=(0.1, 0.1, 0.1, 0.85), edgecolor=_CURSOR_COLOR),
            zorder=20,
        )
        self._lock_plot_limits()
        self.canvas.draw_idle()

    def _cursor_event_ax(self, event):
        if self._plot_ax is None:
            return None
        if event.inaxes is self._plot_ax:
            return self._plot_ax
        return None

    def _on_cursor_press(self, event):
        if self._cursor_event_ax(event) is not None and event.button == 1 and event.xdata is not None:
            self._cursor_active = True
            self._update_time_cursor(float(event.xdata))

    def _on_cursor_motion(self, event):
        ax = self._cursor_event_ax(event)
        if ax is None or event.xdata is None:
            return
        if self._cursor_active or (event.button == 1):
            self._update_time_cursor(float(event.xdata))

    def _on_cursor_release(self, event):
        self._cursor_active = False

    def _on_cursor_leave(self, event):
        if event.inaxes is self._plot_ax:
            self._cursor_active = False
            self._clear_time_cursor()
            self.canvas.draw_idle()

    def show_and_raise(self, *, activate: bool = True):
        if not self.isVisible():
            self.show()
        self.raise_()
        if activate:
            self.activateWindow()

    def show_pixel(self, x_click: float, y_click: float, display_shape: tuple[int, int] | None):
        filename = self.main_window.shared_info.config.get("selected_file")
        decay = get_pixel_decay(filename, x_click, y_click, display_shape)
        if decay is None:
            self.info_label.setText("No data loaded for the selected file.")
            self._draw_empty_axes()
            self.show_and_raise(activate=False)
            return
        self._last_decay = decay
        self._reset_map_shift_silent()
        self._redraw_last()
        self.show_and_raise(activate=False)

    def _redraw_last(self):
        if self._last_decay is not None:
            self._plot_decay(self._last_decay)

    def _draw_empty_axes(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._plot_ax = ax
        ax.set_facecolor(_BG)
        ax.tick_params(colors="white", labelsize=8)
        ax.set_xlabel("Time (ns)", color="white", fontsize=9)
        ax.set_ylabel("Photon counts", color="white", fontsize=9)
        ax.set_title("Decay curve", color="white", fontsize=10)
        for spine in ax.spines.values():
            spine.set_color("white")
        self._clear_time_cursor()
        self.figure.tight_layout()
        self._store_plot_limits(ax)
        self.canvas.draw_idle()

    def _plot_decay(self, decay: PixelDecay):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._plot_ax = ax
        ax.set_facecolor(_BG)

        t = np.asarray(decay.t_ns, dtype=np.float64)
        y = np.asarray(decay.counts, dtype=np.float64)
        t, y = _aggregate_max_per_time(t, y)
        use_log = self.log_check.isChecked() and np.any(y > 0)

        fit = None
        t0_ns = decay.t0_ns if decay.fit_allowed else None
        align_at_t0 = bool(t0_ns is not None and self.align_t0_check.isChecked())
        self.align_t0_check.setEnabled(t0_ns is not None)
        if not self.align_t0_check.isEnabled():
            self.align_t0_check.setChecked(False)

        has_map_tau = decay.tau_ns is not None and decay.tau_ns > 0
        peak_align = self.peak_align_check.isChecked() if DECAY_FIT_UI_ENABLED else True
        use_irf = self.use_irf_check.isChecked()
        map_shift_ns = self._map_shift_ns
        self._last_fit = None

        show_map = has_map_tau and self.show_map_tau_check.isChecked()
        self.show_map_tau_check.setEnabled(has_map_tau)
        self.use_irf_check.setEnabled(show_map)
        self.map_shift_slider.setEnabled(show_map)
        self.map_shift_spin.setEnabled(show_map)
        self.map_shift_reset_btn.setEnabled(show_map)

        if DECAY_FIT_UI_ENABLED:
            if decay.fit_allowed and t0_ns is not None:
                self._last_fit = fit_single_exponential(
                    t, y, tau_hint_ns=decay.tau_ns, t0_ns=t0_ns,
                    peak_align=peak_align, use_irf=use_irf,
                )
                fit = self._last_fit

        if use_log:
            t_m, y_m = _plot_times(t, y, t0_ns=t0_ns, align_at_t0=align_at_t0)
            pos = y_m > 0
            ax.semilogy(
                t_m[pos], y_m[pos], linestyle="none", marker="o",
                color=_TEAL, markersize=4, label="Measured",
            )
            ax.set_ylabel("Photon counts (log)", color="white", fontsize=9)
        else:
            t_m, y_m = _plot_times(t, y, t0_ns=t0_ns, align_at_t0=align_at_t0)
            y_max = float(np.max(y_m)) if y_m.size else float(np.max(y)) if y.size else 0.0
            y_top = max(y_max * 1.15, 0.5)
            zero_h = _zero_display_height(y_top)

            pos = y_m > 0
            zero = y_m == 0
            if np.any(pos):
                ax.plot(
                    t_m[pos], y_m[pos], linestyle="none", marker="o",
                    color=_TEAL, markersize=4, label="Measured",
                )
            if np.any(zero):
                ax.plot(
                    t_m[zero], np.full(np.sum(zero), zero_h), linestyle="none", marker="o",
                    color=_ZERO_MARKER_COLOR, markersize=3, alpha=0.55,
                    markerfacecolor=_ZERO_MARKER_COLOR, label="0 counts (raised)",
                )
            ax.set_ylim(0, y_top)
            ax.set_ylabel("Photon counts", color="white", fontsize=9)

        if DECAY_FIT_UI_ENABLED and fit is not None and self.show_fit_check.isChecked():
            model = np.asarray(fit.model_counts, dtype=np.float64)
            t_fit, model_fit = _plot_times(t, model, t0_ns=t0_ns, align_at_t0=align_at_t0)
            if use_log:
                mpos = model_fit > 0
                ax.semilogy(
                    t_fit[mpos], model_fit[mpos], "-", color=_FIT_COLOR, linewidth=1.8,
                    label=f"Fit τ={fit.tau_ns:.2f} ns",
                )
            else:
                ax.plot(
                    t_fit, model_fit, "-", color=_FIT_COLOR, linewidth=1.8,
                    label=f"Fit τ={fit.tau_ns:.2f} ns",
                )

        map_model = None
        if has_map_tau:
            map_model = predict_decay_at_tau(
                t, y, decay.tau_ns,
                t0_ns=t0_ns,
                peak_align=peak_align,
                use_irf=use_irf,
            )

        if map_model is not None and self.show_map_tau_check.isChecked():
            map_model = np.asarray(map_model, dtype=np.float64)
            if abs(map_shift_ns) > 1e-12:
                map_model = shift_model_on_time_axis(t, map_model, map_shift_ns)
            t_map, map_plot = _plot_times(
                t, map_model, t0_ns=t0_ns if decay.fit_allowed else None, align_at_t0=align_at_t0,
            )
            map_label = f"Map τ={decay.tau_ns:.2f} ns"
            map_label += " (IRF)" if use_irf else " (exp)"
            if abs(map_shift_ns) > 1e-12:
                map_label += f" Δt={map_shift_ns:+.2f}"
            if use_log:
                mpos = map_plot > 0
                ax.semilogy(
                    t_map[mpos], map_plot[mpos], "--", color=_MAP_TAU_COLOR, linewidth=1.6,
                    label=map_label,
                )
            else:
                ax.plot(
                    t_map, map_plot, "--", color=_MAP_TAU_COLOR, linewidth=1.6,
                    label=map_label,
                )

        if t0_ns is not None and decay.fit_allowed and t.size and not align_at_t0:
            _draw_t0_region(ax, t0_ns, decay.baseline_fraction_pct, float(t.min()))

        if t.size:
            if align_at_t0 and t0_ns is not None:
                self._t_min_ns = 0.0
                self._t_max_ns = float(t.max() - t0_ns)
            else:
                self._t_min_ns = float(t.min())
                self._t_max_ns = float(t.max())
            ax.set_xlim(self._t_min_ns, self._t_max_ns)
        else:
            self._t_min_ns = None
            self._t_max_ns = None

        ax.set_xlabel(
            "Time since t₀ (ns)" if align_at_t0 else "Time (ns)",
            color="white", fontsize=9,
        )
        title = f"{decay.filename}  —  pixel (x={decay.x}, y={decay.y})"
        ax.set_title(title, color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("white")
        ax.legend(facecolor=(0.25, 0.25, 0.25), edgecolor="white", labelcolor="white", fontsize=8)
        ax.grid(True, alpha=0.2, color="gray")

        parts = [
            f"pixel (x={decay.x}, y={decay.y})",
            f"Σ photons = {decay.total_photons:,}",
        ]
        if decay.block_size > 1:
            parts.append(f"{decay.block_size}×{decay.block_size} block")
        if decay.tau_ns is not None:
            parts.append(f"τ map ≈ {decay.tau_ns:.2f} ns")
            if self.show_map_tau_check.isChecked():
                parts.append("IRF reconvolution" if use_irf else "monoexponential")
        if DECAY_FIT_UI_ENABLED and fit is not None:
            parts.append(f"fit τ = {fit.tau_ns:.2f} ns")
            if fit.used_irf:
                parts.append("IRF on")
            else:
                parts.append("IRF off")
            if abs(fit.peak_shift_ns) > 1e-6:
                parts.append(f"peak Δt = {fit.peak_shift_ns:.2f} ns")
        if DECAY_FIT_UI_ENABLED and peak_align:
            parts.append("peak-align on")
        if abs(map_shift_ns) > 1e-12:
            parts.append(f"map slide = {map_shift_ns:+.2f} ns")
        if decay.masked_out:
            parts.append("outside mask or zero signal")
        self.info_label.setText("  |  ".join(parts))

        self._clear_time_cursor()
        self.figure.tight_layout()
        self._store_plot_limits(ax)
        self.canvas.draw_idle()
