import numpy as np
from pathlib import Path
import math
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QListWidget, QAbstractItemView, QListWidgetItem, QComboBox, QSizePolicy, QLabel
from PySide6.QtGui import QPixmap, QColor, QIcon, QPainter, QPen, QBrush
from PySide6.QtCore import Signal, Qt

import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.patches import Patch
import seaborn as sns
from matplotlib.widgets import EllipseSelector
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar2QT

from utils.shared_data import SharedData
from utils.colormaps import resolve_lifetime_cmap
from utils.helper_functions import Helpers


# Phasor plot modes:
#   Lifetime maps tab  → plot_phasor_coordinates() — one selected file, lifetime-coloured scatter.
#   Gallery (tau) tab  → plot_phasor_gallery_*() — multi-file overlay; Layers panel applies here.
#
# Layers panel (Gallery only): checkbox = show/hide; drag or ▲/▼ = z-order; click layer = highlight.
# ROI button: draw ellipse on phasor; dims non-selected pixels on the Lifetime map (display only,
#   does not change analysis masks). Toggle ROI again to clear.


class PhasorPlot(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)  # Make sure to call the superclass initializer
        self.main_window = main_window
        self.shared_info = SharedData()
        self.helpers = Helpers(self.main_window)
        self.w = 2 * math.pi * float(self.shared_info.config["frequency"]) * 1000000
        self.g = None
        self.s = None
        self.xlims = (-0.2, 1.2)  # Set appropriate limits
        self.ylims = (-0.02, 0.8)  # Set appropriate limits
        self.layer_artists = {}
        self._updating_legend = False
        self.figure_phasor = self.main_window.figure_phasor
        self.canvas_phasor = self.main_window.canvas_phasor
        self.fixed_dpi = self.main_window.fixed_dpi
        self.tau_labels_active = True  # Initial state: on
        self._gallery_scatter_initialized = False
        self.initUI()  # Initialize the UI here


    def initUI(self):
        self.layout = QHBoxLayout(self)  # Main layout is horizontal
        plotLayout = QVBoxLayout()  # This layout is for plot-related widgets
        self.layout.addLayout(plotLayout)

        # Add the Matplotlib Navigation Toolbar
        h_layout_nav = QHBoxLayout()
        self.toolbar = NavigationToolbar(self.canvas_phasor, self)
        h_layout_nav.addWidget(self.toolbar, 1)

        # Add "lifetimes labels" button
        self.btn_tau = QPushButton("τ Labels")
        self.btn_tau.clicked.connect(self.toggle_tau_labels)
        #self.btn_tau.setStyleSheet('QPushButton {color: white;}')
        # Initial active color
        self.btn_tau.setStyleSheet('QPushButton {background-color: rgb(60, 162, 161); color: white;}')
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.btn_tau)

        # Add "ROI" button
        self.btn_select = QPushButton("ROI")
        self.btn_select.clicked.connect(self.toggle_roi)
        self.btn_select.setStyleSheet('QPushButton {color: white;}')
        buttonLayout.addWidget(self.btn_select)

        # Create and add the Display dropdown
        self.display_dropdown = QComboBox()
        self.display_dropdown.addItems(["Individual", "Condition"])  # Adding dropdown options
        self.display_dropdown.setStyleSheet('QComboBox {color: white; background-color: rgb(50, 50, 50);}')
        self.display_dropdown.setEnabled(False)
        self.display_dropdown.currentIndexChanged.connect(self.update_plot_type)

        # Dropdown to select scatter type
        self.scatter_dropdown = QComboBox()
        self.scatter_dropdown.addItems(["Scatter", "Histogram", "Contour"])  # Adding dropdown options
        self.scatter_dropdown.setStyleSheet('QComboBox {color: white; background-color: rgb(50, 50, 50);}')
        self.scatter_dropdown.setEnabled(False)
        self.scatter_dropdown.currentIndexChanged.connect(self.update_scatter_type)

        buttonLayout.addWidget(self.display_dropdown)  # Add dropdown next to the ROI button
        buttonLayout.addWidget(self.scatter_dropdown)

        buttonLayout.addStretch(1)  # This pushes the elements to the left
        h_layout_nav.addLayout(buttonLayout)
        plotLayout.addLayout(h_layout_nav)

        # Add phasor plot area below toolbar and ROI selection
        plotLayout.addWidget(self.canvas_phasor, 1)
        self.canvas_phasor.setStyleSheet("""background-color: rgb(18, 18, 18);
                                            border: 1px solid rgb(18, 18, 18);
                                            border-radius: 10px;
                                            padding: 1px;""")

        self.selector = None
        self.add_plot()
        self.ax.callbacks.connect('xlim_changed', self.enforce_xlims)
        self.ax.callbacks.connect('ylim_changed', self.enforce_ylims)
        self.connect_events()

        # Layers panel — active in Gallery (tau) when Display is Individual or Condition
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setSpacing(4)

        layers_label = QLabel("Layers")
        layers_label.setStyleSheet("QLabel { color: dimgray; font-size: 11px; }")
        self.legend_layout.addWidget(layers_label)

        layer_buttons = QHBoxLayout()
        layer_buttons.setContentsMargins(0, 0, 0, 0)
        layer_buttons.setSpacing(4)
        self.btn_layer_up = QPushButton("▲")
        self.btn_layer_up.setFixedWidth(28)
        self.btn_layer_up.setToolTip("Move layer up (draw on top)")
        self.btn_layer_up.setStyleSheet('QPushButton { color: white; }')
        self.btn_layer_up.clicked.connect(self._move_layer_up)

        self.btn_layer_down = QPushButton("▼")
        self.btn_layer_down.setFixedWidth(28)
        self.btn_layer_down.setToolTip("Move layer down (draw behind)")
        self.btn_layer_down.setStyleSheet('QPushButton { color: white; }')
        self.btn_layer_down.clicked.connect(self._move_layer_down)

        layer_buttons.addWidget(self.btn_layer_up)
        layer_buttons.addWidget(self.btn_layer_down)
        layer_buttons.addStretch(1)
        self.legend_layout.addLayout(layer_buttons)

        self.legendWidget = LegendWidget()
        self.legendWidget.setMaximumSize(200, 300)
        self.legendWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.legendWidget.setStyleSheet("""LegendWidget {
                background-color: rgb(18, 18, 18);
                border: 1px solid rgb(18, 18, 18);
                color: white;
                }
                  """)
        self.legend_layout.addWidget(self.legendWidget)
        self.legend_layout.addStretch(1)

        # Add legend_layout to the main layout
        self.layout.addLayout(self.legend_layout)

        self.legendWidget.legendItemSelected.connect(self._on_legend_item_selected)
        self.legendWidget.layersChanged.connect(self._on_layers_changed)

    def update_plot_type(self):
        current_selection = self.display_dropdown.currentText()
        if current_selection == "Individual":
            self.shared_info.phasor_settings["plot_type"] = "individual"
            self.plot_phasor_gallery_individual(data_dict=self.shared_info.results_dict)

        elif current_selection == "Condition":
            self.shared_info.phasor_settings["plot_type"] = "condition"
            self.plot_phasor_gallery_condition(data_dict=self.shared_info.results_dict)

    def update_scatter_type(self):
        current_selection = self.scatter_dropdown.currentText()
        if current_selection == "Scatter":
            self.shared_info.phasor_settings["scatter_type"] = "scatter"
        elif current_selection == "Contour":
            self.shared_info.phasor_settings["scatter_type"] = "contour"
        elif current_selection == "Histogram":
            self.shared_info.phasor_settings["scatter_type"] = "histogram"

        current_selection_dis = self.display_dropdown.currentText()
        if current_selection_dis == "Individual":
            self.plot_phasor_gallery_individual(data_dict=self.shared_info.results_dict)
        elif current_selection_dis == "Condition":
            self.plot_phasor_gallery_condition(data_dict=self.shared_info.results_dict)

    def _prepare_phasor_figure(self):
        """Clear the figure, drop stale layer refs, and create a fresh axes."""
        self.figure_phasor.clear()
        self._discard_layer_artists()
        self.ax = self.figure_phasor.subplots()
        return self.ax

    def add_plot(self, reset_axes=True):
        if reset_axes:
            self._prepare_phasor_figure()
        self._draw_phasor_base()

    def _draw_phasor_base(self):
        dark_gray = (18 / 255, 18 / 255, 18 / 255)

        # Set the figure background to dark gray
        #self.figure_phasor.patch.set_facecolor(dark_gray)
        # Set the figure background to transparent
        self.figure_phasor.patch.set_facecolor('none')

        # Set the axes background to dark gray
        #self.ax.set_facecolor(dark_gray)
        self.ax.set_facecolor('none')

        # Plotting the semi-circle
        r = 0.5
        h = 0.5
        self.x = np.linspace(0, 1, 1000)
        self.y = np.sqrt(r ** 2 - (self.x - h) ** 2)
        self.con_img = self.ax.plot(self.x, self.y, 'dimgray', linewidth=1)

        # plot mono-exponential lifetimes on semicircle
        # Only show lifetimes if active
        if self.tau_labels_active:
            # plot mono-exponential lifetimes on semicircle
            w = 2*math.pi*float(self.shared_info.config["frequency"])*1e6  # angular frequency
            if float(self.shared_info.config["frequency"]) >= 100:
                tau_labels = np.arange(0 * 1e-9, 9 * 1e-9, 1e-9)  # Array from 0 to 8 ns
            elif float(self.shared_info.config["frequency"]) > 50:
                tau_labels = np.arange(0 * 1e-9, 11 * 1e-9, 1e-9)  # Array from 0 to 10 ns
            elif float(self.shared_info.config["frequency"]) < 30:
                tau_labels = np.arange(0 * 1e-9, 15 * 1e-9, 1e-9)  # Array from 0 to 14 ns
            else:
                tau_labels = np.arange(0 * 1e-9, 13 * 1e-9, 1e-9)  # Array from 0 to 12 ns
                
            g_unisem = 1 / (1 + w ** 2 * tau_labels ** 2)  # g-coordinates
            s_unisem = w * tau_labels / (1 + w ** 2 * tau_labels ** 2)  # s-coordinates
            self.ax.plot(g_unisem, s_unisem, 'o', markersize=3, mec='dimgray', mfc='dimgray')  # Points

            # Labels
            for g, s, tau in zip(g_unisem, s_unisem, tau_labels):
                label = f"{int(tau * 1e9)}ns"
                if g >= 0.6:
                    self.ax.text(g + 0.02, s, label, color='dimgray', fontsize=8, ha='left', va='center')
                elif g >= 0.4:
                    self.ax.text(g - 0.05, s+0.01, label, color='dimgray', fontsize=8, ha='left', va='center')
                elif g >= 0.3:
                    self.ax.text(g - 0.05, s, label, color='dimgray', fontsize=8, ha='left', va='center')
                else:
                    self.ax.text(g - 0.01, s, label, color='dimgray', fontsize=8, ha='right', va='center')


        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])

        self.ax.set_xlabel("G", color="dimgray")
        self.ax.set_ylabel("S", color="dimgray")
        self.ax.title.set_color('dimgray')  # Plot title, if you have one

        # Change axes tick color to dimgray
        self.ax.tick_params(axis='x', colors='dimgray')  # Change x-axis tick colors to dimgray
        self.ax.tick_params(axis='y', colors='dimgray')  # Change y-axis tick colors to dimgray

        self.ax.spines['left'].set_color('dimgray')
        self.ax.spines['bottom'].set_color('dimgray')

        # Set right and top spines to be invisible
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)

        self.figure_phasor.patch.set_alpha(0)
        self.canvas_phasor.draw()

    def enforce_xlims(self, ax=None):
        """Enforce the x-axis limits."""
        cur_xlim = self.ax.get_xlim()
        if cur_xlim[0] < self.xlims[0] or cur_xlim[1] > self.xlims[1]:
            self.ax.set_xlim(self.xlims)
            self.canvas_phasor.draw_idle()

    def enforce_ylims(self, ax=None):
        """Enforce the y-axis limits."""
        cur_ylim = self.ax.get_ylim()
        if cur_ylim[0] < self.ylims[0] or cur_ylim[1] > self.ylims[1]:
            self.ax.set_ylim(self.ylims)
            self.canvas_phasor.draw_idle()

    def connect_events(self):
        self.figure_phasor.canvas.mpl_connect('draw_event', self.on_draw)

    def on_draw(self, event):
        self.enforce_xlims()
        self.enforce_ylims()
    
    def toggle_tau_labels(self):
        self.tau_labels_active = not self.tau_labels_active

        if self.tau_labels_active:
            self.btn_tau.setStyleSheet('QPushButton {background-color: rgb(60, 162, 161); color: white;}')
            self.shared_info.phasor_settings["tau_labels"] = True
        else:
            self.btn_tau.setStyleSheet('QPushButton {color: white;}')
            self.shared_info.phasor_settings["tau_labels"] = False

        # Update plot with what tab was last selected by the user
        if self.shared_info.last_active_tab == "Lifetime maps":
            self.plot_phasor_coordinates(cmap="gist_rainbow_r")
        elif self.shared_info.last_active_tab == "Gallery (tau)":
            if self.shared_info.phasor_settings["plot_type"] == "individual":
                self.plot_phasor_gallery_individual(data_dict=self.shared_info.results_dict)
            elif self.shared_info.phasor_settings["plot_type"] == "condition":
                self.plot_phasor_gallery_condition(data_dict=self.shared_info.results_dict)
        else:
            self.add_plot()  # Refresh the plot with/without labels



    def toggle_roi(self):
        if self.toolbar.mode == 'zoom rect':
            self.toolbar.zoom()  # This toggles the zoom mode off if it's on
        #if self.toolbar.mode == 'pan/zoom':
            #self.toolbar.pan()  # This toggles the pan mode off if it's on

        if self.selector is None:
            # Recreate the selector to associate it with the current axes
            self.selector = EllipseSelector(self.ax, self.onselect, useblit=True,
                                            props={'facecolor': 'none', 'edgecolor': (60 / 255, 162 / 255, 161 / 255), 'alpha': 0.8, 'linewidth': 1},
                                            interactive=True)
            self.btn_select.setStyleSheet('QPushButton {background-color: rgb(60, 162, 161); color: white;}')
        else:
            self.deactivate_roi()

    def deactivate_roi(self):
        had_roi = self.selector is not None
        if self.selector is not None:
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector = None
            self.btn_select.setStyleSheet('QPushButton {color: white;}')
            self.canvas_phasor.draw_idle()
        if had_roi and self.btn_select.isEnabled() and self.shared_info.results_dict:
            self.main_window.plotImages.plot_tau_map(masked_image=None)
            self.main_window.canvas_tau.draw_idle()

    def onselect(self, eclick, erelease):
        if self.g is not None and self.s is not None:
            x1, y1 = eclick.xdata, eclick.ydata
            x2, y2 = erelease.xdata, erelease.ydata

            # Center of the ellipse
            x0 = (x1 + x2) / 2
            y0 = (y1 + y2) / 2

            # Calculate semi-major and semi-minor axes lengths
            a = abs(x2 - x1) / 2
            b = abs(y2 - y1) / 2
            if a == 0 or b == 0:
                return

            self.inside_ellipse = ((self.g - x0) ** 2 / a ** 2) + ((self.s - y0) ** 2 / b ** 2) <= 1

            self.helpers.update_data_with_roi(self.inside_ellipse)

    def build_roi_mask_2d(self):
        """Build uint16 mask from current phasor ellipse for the selected file."""
        if not hasattr(self, "inside_ellipse") or self.inside_ellipse is None:
            return None
        selected = self.shared_info.config.get("selected_file")
        if selected not in self.shared_info.results_dict:
            return None

        img_shape = self.shared_info.results_dict[selected]["img_shape"]
        x_dim, y_dim = int(img_shape[1]), int(img_shape[2])
        inside = np.asarray(self.inside_ellipse, dtype=bool)
        if inside.size != x_dim * y_dim:
            return None

        g = self.shared_info.results_dict[selected]["g"]
        valid = inside & (g != 0)
        flat = np.zeros(x_dim * y_dim, dtype=np.uint16)
        flat[valid] = 1
        return flat.reshape(x_dim, y_dim)

    def _prepare_gallery_controls(self):
        """Enable gallery UI and default scatter to Scatter on first gallery visit."""
        self.display_dropdown.setEnabled(True)
        self.scatter_dropdown.setEnabled(True)
        if not self._gallery_scatter_initialized:
            self.shared_info.phasor_settings["scatter_type"] = "scatter"
            self.scatter_dropdown.blockSignals(True)
            self.scatter_dropdown.setCurrentText("Scatter")
            self.scatter_dropdown.blockSignals(False)
            self._gallery_scatter_initialized = True

    def plot_phasor_coordinates(self, cmap=None, vmin=None, vmax=None):
        self._prepare_phasor_figure()
        self.deactivate_roi()
        self.btn_select.setEnabled(True)
        self._draw_phasor_base()

        tau_disp = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])
        tau_cmap = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])[self.shared_info.config["lifetime_map"]]

        self.g = tau_disp["g"]
        self.s = tau_disp["s"]

        mask = (self.g != 0) & (self.s != 0)
        g_scat = self.g[mask]
        s_scat = self.s[mask]

        tau_cmap = tau_cmap * 1e9  # Example normalization, adjust as needed
        tau_cmap = tau_cmap[mask]

        if cmap is None:
            cmap = resolve_lifetime_cmap(self.shared_info.config)

        self.ax.scatter(x=g_scat, y=s_scat, c=tau_cmap, cmap=cmap, vmin=float(self.shared_info.config["lifetime_vmin"]),
                        vmax=float(self.shared_info.config["lifetime_vmax"]), s=16, linewidth=0.4, alpha=0.5)

        self.canvas_phasor.draw()

    def _on_legend_item_selected(self, label):
        if self.shared_info.phasor_settings["plot_type"] == "condition":
            self.highlightPlotPoints_condition(label)
        else:
            self.highlightPlotPoints_individual(label)

    def _current_plot_type(self):
        return self.shared_info.phasor_settings["plot_type"]

    def _sync_layer_state(self, labels):
        plot_type = self._current_plot_type()
        state = self.shared_info.phasor_layers[plot_type]
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

    def _save_layer_state_from_widget(self):
        plot_type = self._current_plot_type()
        state = self.shared_info.phasor_layers[plot_type]
        state["order"] = self.legendWidget.get_layer_order()
        state["visible"] = {
            label: self.legendWidget.is_layer_visible(label)
            for label in state["order"]
        }

    def _move_layer_up(self):
        self.legendWidget.move_selected_up()

    def _move_layer_down(self):
        self.legendWidget.move_selected_down()

    def _on_layers_changed(self, reorder=False):
        if self._updating_legend:
            return
        self._save_layer_state_from_widget()
        if reorder:
            self._redraw_gallery_layers()
        else:
            self._apply_layer_visibility()

    def _safe_remove_artist(self, artist):
        """Remove a matplotlib artist; AxesImage from hist2d cannot use Artist.remove()."""
        if artist is None:
            return
        try:
            artist.remove()
            return
        except NotImplementedError:
            pass
        except (ValueError, AttributeError):
            return

        ax = getattr(artist, "axes", None)
        if ax is None:
            try:
                artist.set_visible(False)
            except Exception:
                pass
            return

        for container in (ax.images, ax.collections, ax.lines, ax.patches):
            try:
                if artist in container:
                    container.remove(artist)
                    return
            except (ValueError, AttributeError, TypeError):
                continue

        try:
            artist.set_visible(False)
        except Exception:
            pass

    def _discard_layer_artists(self):
        """Drop layer references without removing (e.g. after figure.clear())."""
        self.layer_artists = {}
        self._discard_highlight_refs()

    def _discard_highlight_refs(self):
        for attr in ("highlighted_sample", "highlighted_condition"):
            if hasattr(self, attr):
                delattr(self, attr)

    def _clear_layer_artists(self):
        for artists in list(self.layer_artists.values()):
            if isinstance(artists, list):
                for artist in artists:
                    self._safe_remove_artist(artist)
            else:
                self._safe_remove_artist(artists)
        self.layer_artists = {}
        self._clear_highlight()

    def _clear_highlight(self):
        for attr in ("highlighted_sample", "highlighted_condition"):
            if not hasattr(self, attr):
                continue
            target = getattr(self, attr)
            if isinstance(target, list):
                for artist in target:
                    self._safe_remove_artist(artist)
            elif isinstance(target, tuple):
                for artist in target:
                    self._safe_remove_artist(artist)
            else:
                self._safe_remove_artist(target)
            delattr(self, attr)

    def _apply_layer_visibility(self):
        for label, artists in self.layer_artists.items():
            visible = self.legendWidget.is_layer_visible(label)
            if artists is None:
                continue
            if isinstance(artists, list):
                for artist in artists:
                    if artist is not None:
                        artist.set_visible(visible)
            else:
                artists.set_visible(visible)
        self.canvas_phasor.draw_idle()

    def _redraw_gallery_layers(self):
        if self._current_plot_type() == "individual":
            self._draw_gallery_layers_individual()
        else:
            self._draw_gallery_layers_condition()
        self.canvas_phasor.draw()

    def _draw_layer_individual(self, key, value, color):
        g = value['g']
        s = value['s']
        mask = (g != 0) & (s != 0)
        g_scat = g[mask]
        s_scat = s[mask]
        if g_scat.size == 0:
            return None

        histo_bins = max(1, int(math.sqrt(len(g_scat)) / 2))

        if self.shared_info.phasor_settings["scatter_type"] == "scatter":
            return self.ax.scatter(x=g_scat, y=s_scat, label=key, color=color, s=16, alpha=0.5, linewidth=0.4)

        if self.shared_info.phasor_settings["scatter_type"] == "contour":
            counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
            contour_set = self.ax.contour(
                counts.transpose(),
                extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]],
                linewidths=1,
                colors=[color],
            )
            return list(contour_set.collections)

        hist2d = self.ax.hist2d(
            g_scat, s_scat, bins=histo_bins, cmap='jet',
            norm=colors.LogNorm(), alpha=0.75,
        )
        return hist2d[3]

    def _draw_layer_condition(self, condition, g_scat, s_scat, color):
        if g_scat.size == 0:
            return None

        histo_bins = max(1, int(math.sqrt(len(g_scat)) / 2))

        if self.shared_info.phasor_settings["scatter_type"] == "scatter":
            return self.ax.scatter(x=g_scat, y=s_scat, label=condition, color=color, s=16, alpha=0.5, linewidth=0.4)

        if self.shared_info.phasor_settings["scatter_type"] == "contour":
            counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
            contour_set = self.ax.contour(
                counts.transpose(),
                extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]],
                linewidths=1,
                colors=[color],
            )
            return list(contour_set.collections)

        hist2d = self.ax.hist2d(
            g_scat, s_scat, bins=histo_bins, cmap='jet',
            norm=colors.LogNorm(), alpha=0.75,
        )
        return hist2d[3]

    def _draw_gallery_layers_individual(self):
        self._clear_layer_artists()
        order = self.legendWidget.get_layer_order()
        tab20_cmap = plt.get_cmap('tab20')
        num_colors = tab20_cmap.N
        color_map = {label: color for label, color in self.plot_data_colors}

        for zorder, key in enumerate(reversed(order)):
            if not self.legendWidget.is_layer_visible(key):
                continue
            if key not in self.plot_data:
                continue
            color = color_map.get(key, tab20_cmap(list(self.plot_data.keys()).index(key) % num_colors))
            artist = self._draw_layer_individual(key, self.plot_data[key], color)
            if artist is None:
                continue
            self.layer_artists[key] = artist
            artists = artist if isinstance(artist, list) else [artist]
            for item in artists:
                item.set_zorder(2 + zorder)

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])

    def _draw_gallery_layers_condition(self):
        self._clear_layer_artists()
        order = self.legendWidget.get_layer_order()
        condition_points = {condition: {'g': [], 's': []} for condition in self.plot_data_colors.keys()}

        for key, value in self.plot_data.items():
            g = value['g']
            s = value['s']
            condition = value['condition']
            mask = (g != 0) & (s != 0)
            condition_points[condition]['g'].extend(g[mask])
            condition_points[condition]['s'].extend(s[mask])

        for zorder, condition in enumerate(reversed(order)):
            if not self.legendWidget.is_layer_visible(condition):
                continue
            if condition not in condition_points:
                continue
            g_scat = np.array(condition_points[condition]['g'])
            s_scat = np.array(condition_points[condition]['s'])
            color = self.plot_data_colors[condition]
            artist = self._draw_layer_condition(condition, g_scat, s_scat, color)
            if artist is None:
                continue
            self.layer_artists[condition] = artist
            artists = artist if isinstance(artist, list) else [artist]
            for item in artists:
                item.set_zorder(2 + zorder)

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])

    def plot_phasor_gallery_individual(self, data_dict):
        self._prepare_gallery_controls()
        self._prepare_phasor_figure()
        self.deactivate_roi()
        self.btn_select.setEnabled(False)

        self._draw_phasor_base()

        tab20_cmap = plt.get_cmap('tab20')
        num_colors = tab20_cmap.N

        self.plot_data = data_dict
        self.plot_data_colors = [(key, tab20_cmap(i % num_colors)) for i, (key, value) in enumerate(data_dict.items())]

        labels = [label for label, _ in self.plot_data_colors]
        order, visibility = self._sync_layer_state(labels)
        labels_colors_qt = [
            (label, (color[0] * 255, color[1] * 255, color[2] * 255, int(color[3] * 255)))
            for label, color in self.plot_data_colors
        ]
        self._updating_legend = True
        self.legendWidget.updateLegend(labels_colors_qt, order, visibility)
        self._updating_legend = False

        self._draw_gallery_layers_individual()
        self.canvas_phasor.draw()

    def plot_phasor_gallery_condition(self, data_dict):
        self._prepare_gallery_controls()
        self._prepare_phasor_figure()
        self.deactivate_roi()
        self.btn_select.setEnabled(False)
        self._draw_phasor_base()

        tab20_cmap = plt.get_cmap('tab20')
        num_colors = tab20_cmap.N

        self.plot_data = data_dict
        unique_conditions = list(set(value['condition'] for value in data_dict.values()))
        self.plot_data_colors = {condition: tab20_cmap(i % num_colors) for i, condition in enumerate(unique_conditions)}

        order, visibility = self._sync_layer_state(unique_conditions)
        labels_colors_qt = [
            (condition, (color[0] * 255, color[1] * 255, color[2] * 255, int(color[3] * 255)))
            for condition, color in self.plot_data_colors.items()
        ]
        self._updating_legend = True
        self.legendWidget.updateLegend(labels_colors_qt, order, visibility)
        self._updating_legend = False

        self._draw_gallery_layers_condition()
        self.canvas_phasor.draw()

    def highlightPlotPoints_individual(self, label):
        if not self.legendWidget.is_layer_visible(label):
            return
        self.deactivate_roi()
        self.btn_select.setStyleSheet('QPushButton {color: white;}')
        self.btn_select.setEnabled(False)

        self._clear_highlight()

        for i, (key, value) in enumerate(self.plot_data.items()):
            if key == label:
                g = value['g']
                s = value['s']
                histo_bins = (math.sqrt(len(g))) / 2

                mask = (g != 0) & (s != 0)
                g_scat = g[mask]
                s_scat = s[mask]

                color = self.plot_data_colors[i][1]

                if self.shared_info.phasor_settings["scatter_type"] == "scatter":
                    self.highlighted_sample = self.ax.scatter(x=g_scat, y=s_scat, label=key, color=color, s=16, alpha=0.75, linewidth=0.4)

                elif self.shared_info.phasor_settings["scatter_type"] == "contour":
                    counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
                    contour_set = self.ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])
                    self.highlighted_sample = contour_set.collections

                elif self.shared_info.phasor_settings["scatter_type"] == "histogram":
                    counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=int(histo_bins))
                    hist2d = self.ax.contourf(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], cmap='jet_r', norm=colors.LogNorm(), alpha=0.75)
                    self.highlighted_sample = hist2d.collections

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])
        self.canvas_phasor.draw_idle()

    def highlightPlotPoints_condition(self, label):
        if not self.legendWidget.is_layer_visible(label):
            return
        self.deactivate_roi()
        self.btn_select.setStyleSheet('QPushButton {color: white;}')
        self.btn_select.setEnabled(False)

        self._clear_highlight()

        condition_points = {condition: {'g': [], 's': []} for condition in self.plot_data_colors.keys()}
        for key, value in self.plot_data.items():
            g = value['g']
            s = value['s']
            condition = value['condition']
            mask = (g != 0) & (s != 0)
            condition_points[condition]['g'].extend(g[mask])
            condition_points[condition]['s'].extend(s[mask])

        if label in condition_points:
            g_scat = np.array(condition_points[label]['g'])
            s_scat = np.array(condition_points[label]['s'])
            color = self.plot_data_colors[label]
            histo_bins = int(math.sqrt(len(g_scat)) / 2)

            if self.shared_info.phasor_settings["scatter_type"] == "scatter":
                self.highlighted_condition = self.ax.scatter(x=g_scat, y=s_scat, label=label, color=color, s=16, alpha=0.75, linewidth=0.4)

            elif self.shared_info.phasor_settings["scatter_type"] == "contour":
                counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
                contour_set = self.ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])
                self.highlighted_condition = contour_set.collections  # Store the list of contour sets

            elif self.shared_info.phasor_settings["scatter_type"] == "histogram":
                counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=int(histo_bins))
                hist2d = self.ax.contourf(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], cmap='jet_r', norm=colors.LogNorm(), alpha=0.75)
                self.highlighted_condition = hist2d.collections  # Store the QuadMesh

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])
        self.canvas_phasor.draw_idle()
    
    def save_current_view_as_pdf(self, output_path):

        file_ext = Path(output_path).suffix.lower().lstrip('.')
        legend = None
        try:
            scatter_type = self.shared_info.phasor_settings.get("scatter_type", "scatter")
            plot_type = self.shared_info.phasor_settings.get("plot_type", "individual")

            handles = []
            labels = []

            if scatter_type == "contour":
                if plot_type == "individual":
                    for label, color in self.plot_data_colors:
                        patch = Patch(facecolor=color, edgecolor='dimgray', label=label)
                        handles.append(patch)
                        labels.append(label)
                elif plot_type == "condition":
                    for label, color in self.plot_data_colors.items():
                        patch = Patch(facecolor=color, edgecolor='dimgray', label=label)
                        handles.append(patch)
                        labels.append(label)
            else:
                handles, labels = self.ax.get_legend_handles_labels()

            if handles:
                legend = self.ax.legend(
                    handles, labels,
                    loc='upper center',
                    bbox_to_anchor=(0.5, -0.1),
                    fontsize=8,
                    frameon=False,
                    ncol=5
                )

                # Set legend text color to dimgray
                for text in legend.get_texts():
                    text.set_color('dimgray')

            self.figure_phasor.savefig(output_path, format=file_ext, bbox_inches='tight', transparent=True, dpi=300)

        finally:
            if legend:
                self._safe_remove_artist(legend)
            self.canvas_phasor.draw_idle()



class LegendWidget(QListWidget):
    """Gallery layer list: visibility checkboxes, drag-reorder, click-to-highlight."""
    legendItemSelected = Signal(str)
    layersChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.itemClicked.connect(self.onItemClicked)
        self.itemChanged.connect(self.onItemChanged)
        self.model().rowsMoved.connect(self._on_rows_moved)

    def updateLegend(self, labels_colors, order, visibility):
        self.blockSignals(True)
        self.clear()
        color_map = {label: color for label, color in labels_colors}
        ordered_labels = [label for label in order if label in color_map]
        for label, _ in labels_colors:
            if label not in ordered_labels:
                ordered_labels.append(label)

        for label in ordered_labels:
            color = color_map[label]
            item = QListWidgetItem(label)
            item.setIcon(self.createCircularIcon(color))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Checked if visibility.get(label, True) else Qt.Unchecked)
            self.addItem(item)
        self.blockSignals(False)

    def get_layer_order(self):
        return [self.item(i).text() for i in range(self.count())]

    def is_layer_visible(self, label):
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == label:
                return item.checkState() == Qt.Checked
        return True

    def move_selected_up(self):
        row = self.currentRow()
        if row <= 0:
            return False
        item = self.takeItem(row)
        self.insertItem(row - 1, item)
        self.setCurrentRow(row - 1)
        self.layersChanged.emit(True)
        return True

    def move_selected_down(self):
        row = self.currentRow()
        if row < 0 or row >= self.count() - 1:
            return False
        item = self.takeItem(row)
        self.insertItem(row + 1, item)
        self.setCurrentRow(row + 1)
        self.layersChanged.emit(True)
        return True

    def onItemClicked(self, item):
        if item.checkState() == Qt.Checked:
            self.legendItemSelected.emit(item.text())

    def onItemChanged(self, item):
        if self.signalsBlocked():
            return
        self.layersChanged.emit(False)

    def _on_rows_moved(self, *args):
        if self.signalsBlocked():
            return
        self.layersChanged.emit(True)

    def createCircularIcon(self, color):
        # Create a QPixmap with desired size and transparency
        size = 10  # Size of the icon
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Fill the pixmap with transparency

        # Create QPainter to draw on the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)  # Enable antialiasing for smooth edges
        pen = QPen()  # Create a default pen
        pen.setColor(QColor(*color))  # Set the color of the pen
        painter.setPen(pen)  # Apply the pen to the painter

        # Set the brush to fill the circle with the same color
        brush = QBrush(QColor(*color))
        painter.setBrush(brush)

        # Draw a circle that fills the pixmap, considering some padding
        padding = 2
        painter.drawEllipse(padding, padding, size - 2 * padding, size - 2 * padding)
        painter.end()  # Finish painting

        # Create and return a QIcon from the pixmap
        return QIcon(pixmap)

class NavigationToolbar(NavigationToolbar2QT):
    # only display the buttons we need
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Back', 'Forward', 'Zoom', 'Save')] # 'Customize', 'Pan'      
