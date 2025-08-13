import numpy as np
from pathlib import Path
import math
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QListWidget, QAbstractItemView, QListWidgetItem, QComboBox, QSizePolicy
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
from utils.helper_functions import Helpers
from utils.mainwindow import *


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
        self.is_individual_connected = False
        self.is_condition_connected = False
        self.figure_phasor = self.main_window.figure_phasor
        self.canvas_phasor = self.main_window.canvas_phasor
        self.fixed_dpi = self.main_window.fixed_dpi
        self.tau_labels_active = True  # Initial state: on
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

        # Initialize the LegendWidget and add it to the layout
        self.legend_layout = QVBoxLayout()

        self.legendWidget = LegendWidget()
        self.legendWidget.setMaximumSize(200, 300)
        self.legendWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.legendWidget.setStyleSheet("""LegendWidget {
                background-color: rgb(18, 18, 18);
                border: 1px solid rgb(18, 18, 18);
                }
                  """)
        self.legend_layout.addStretch(1)
        self.legend_layout.addWidget(self.legendWidget)

        # Add legend_layout to the main layout
        self.layout.addLayout(self.legend_layout)

        if self.shared_info.phasor_settings["plot_type"] == "condition":
            self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_condition)
        elif self.shared_info.phasor_settings["plot_type"] == "individual":
            self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_individual)

    def update_plot_type(self):
        current_selection = self.display_dropdown.currentText()
        if current_selection == "Individual":
            self.shared_info.phasor_settings["plot_type"] = "individual"
            self.plot_phasor_gallery_individual(data_dict=self.shared_info.results_dict)
            if not self.is_individual_connected:
                self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_individual)
                self.is_individual_connected = True
            if self.is_condition_connected:
                self.legendWidget.legendItemSelected.disconnect(self.highlightPlotPoints_condition)
                self.is_condition_connected = False

        elif current_selection == "Condition":
            self.shared_info.phasor_settings["plot_type"] = "condition"
            self.plot_phasor_gallery_condition(data_dict=self.shared_info.results_dict)
            if not self.is_condition_connected:
                self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_condition)
                self.is_condition_connected = True
            if self.is_individual_connected:
                self.legendWidget.legendItemSelected.disconnect(self.highlightPlotPoints_individual)
                self.is_individual_connected = False

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

    def add_plot(self):
        self.figure_phasor.clear()
        self.ax = self.figure_phasor.subplots()
       
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
            w = 2*math.pi*int(self.shared_info.config["frequency"])*1e6  # angular frequency
            if int(self.shared_info.config["frequency"]) >= 100:
                tau_labels = np.arange(0 * 1e-9, 9 * 1e-9, 1e-9)  # Array from 0 to 8 ns
            elif int(self.shared_info.config["frequency"]) > 50:
                tau_labels = np.arange(0 * 1e-9, 11 * 1e-9, 1e-9)  # Array from 0 to 10 ns
            elif int(self.shared_info.config["frequency"]) < 30:
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

        # Change text color to dimgray
        self.ax.xaxis.label.set_color('dimgray')  # X-axis label
        self.ax.yaxis.label.set_color('dimgray')  # Y-axis label
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
        if self.selector is not None:
            self.selector.set_active(False)
            self.selector.set_visible(False)
            self.selector = None
            self.btn_select.setStyleSheet('QPushButton {color: white;}')
            self.canvas_phasor.draw_idle()  # Ensure the canvas is refreshed to remove ROI visuals

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

            self.inside_ellipse = ((self.g - x0) ** 2 / a ** 2) + ((self.s - y0) ** 2 / b ** 2) <= 1

            self.helpers.update_data_with_roi(self.inside_ellipse)

    def plot_phasor_coordinates(self, cmap=None, vmin=None, vmax=None):
        self.figure_phasor.clear()  # Clear the figure to remove all axes
        self.ax = self.figure_phasor.add_subplot(111)  # Recreate the axes
        self.deactivate_roi()
        self.btn_select.setEnabled(True)
        self.add_plot()

        tau_disp = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])
        tau_cmap = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])[self.shared_info.config["lifetime_map"]]

        self.g = tau_disp["g"]
        self.s = tau_disp["s"]

        mask = (self.g != 0) & (self.s != 0)
        g_scat = self.g[mask]
        s_scat = self.s[mask]

        tau_cmap = tau_cmap * 1e9  # Example normalization, adjust as needed
        tau_cmap = tau_cmap[mask]

        self.ax.scatter(x=g_scat, y=s_scat, c=tau_cmap, cmap=cmap, vmin=float(self.shared_info.config["lifetime_vmin"]),
                        vmax=float(self.shared_info.config["lifetime_vmax"]), s=16, linewidth=0.4, alpha=0.5)

        self.canvas_phasor.draw()

    def plot_phasor_gallery_individual(self, data_dict):
        self.display_dropdown.setEnabled(True)
        self.scatter_dropdown.setEnabled(True)
        self.figure_phasor.clear()
        self.ax = self.figure_phasor.subplots()
        self.deactivate_roi()
        self.btn_select.setEnabled(False)

        # It's essential to call add_plot to ensure initial plot setup is redone
        self.add_plot()

        # Get the 'tab20' colormap
        tab20_cmap = plt.get_cmap('tab20')
        num_colors = tab20_cmap.N  # Get the number of colors in the colormap

        self.plot_data = data_dict
        self.plot_data_colors = [(key, tab20_cmap(i % num_colors)) for i, (key, value) in enumerate(data_dict.items())]
        # Update the legend
        labels_colors_qt = [(label, (color[0] * 255, color[1] * 255, color[2] * 255, int(color[3] * 255))) for label, color in self.plot_data_colors]
        self.legendWidget.updateLegend(labels_colors_qt, self.shared_info.phasor_settings['plot_type'])

        self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_individual)

        for i, (key, value) in enumerate(data_dict.items()):
            g = value['g']
            s = value['s']
            histo_bins = (math.sqrt(len(g))) / 2

            mask = (g != 0) & (s != 0)
            g_scat = g[mask]
            s_scat = s[mask]

            color = tab20_cmap(i % num_colors)

            if self.shared_info.phasor_settings["scatter_type"] == "scatter":
                self.ax.scatter(x=g_scat, y=s_scat, label=key, color=color, s=16, alpha=0.5, linewidth=0.4)

            elif self.shared_info.phasor_settings["scatter_type"] == "contour":
                counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
                self.ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])

            elif self.shared_info.phasor_settings["scatter_type"] == "histogram":
                self.ax.hist2d(g_scat, s_scat, bins=int(histo_bins), cmap='jet', norm=colors.LogNorm(), alpha=0.75)

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])

        # Add legend outside the plot
        self.canvas_phasor.draw()

    def plot_phasor_gallery_condition(self, data_dict):
        self.figure_phasor.clear()
        self.ax = self.figure_phasor.subplots()
        self.deactivate_roi()
        self.btn_select.setEnabled(False)
        self.add_plot()

        tab20_cmap = plt.get_cmap('tab20')
        num_colors = tab20_cmap.N

        self.plot_data = data_dict
        unique_conditions = list(set(value['condition'] for value in data_dict.values()))
        self.plot_data_colors = {condition: tab20_cmap(i % num_colors) for i, condition in enumerate(unique_conditions)}

        labels_colors_qt = [(condition, (color[0] * 255, color[1] * 255, color[2] * 255, int(color[3] * 255))) for condition, color in self.plot_data_colors.items()]
        self.legendWidget.updateLegend(labels_colors_qt, self.shared_info.phasor_settings['plot_type'])
        self.legendWidget.legendItemSelected.connect(self.highlightPlotPoints_condition)

        condition_points = {condition: {'g': [], 's': []} for condition in unique_conditions}

        for key, value in data_dict.items():
            g = value['g']
            s = value['s']
            condition = value['condition']
            mask = (g != 0) & (s != 0)
            condition_points[condition]['g'].extend(g[mask])
            condition_points[condition]['s'].extend(s[mask])

        for condition, points in condition_points.items():
            g_scat = np.array(points['g'])
            s_scat = np.array(points['s'])
            color = self.plot_data_colors[condition]
            histo_bins = int(math.sqrt(len(g_scat)) / 2)

            if self.shared_info.phasor_settings["scatter_type"] == "scatter":
                self.ax.scatter(x=g_scat, y=s_scat, label=condition, color=color, s=16, alpha=0.5, linewidth=0.4)

            elif self.shared_info.phasor_settings["scatter_type"] == "contour":
                counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
                self.ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])

            elif self.shared_info.phasor_settings["scatter_type"] == "histogram":
                self.ax.hist2d(g_scat, s_scat, bins=histo_bins, cmap='jet', norm=colors.LogNorm(), alpha=0.75)

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])
        self.canvas_phasor.draw()

    def highlightPlotPoints_individual(self, label):
        self.deactivate_roi()
        self.btn_select.setStyleSheet('QPushButton {color: white;}')
        self.btn_select.setEnabled(False)

        # Remove the previous highlighted sample plot if it exists
        if hasattr(self, 'highlighted_sample') and self.highlighted_sample:
            if isinstance(self.highlighted_sample, list):  # Handle contour plots
                for artist in self.highlighted_sample:
                    artist.remove()
            elif hasattr(self.highlighted_sample, 'remove'):
                self.highlighted_sample.remove()
            elif isinstance(self.highlighted_sample, tuple):
                for artist in self.highlighted_sample:
                    artist.remove()
            del self.highlighted_sample

        for i, (key, value) in enumerate(self.plot_data.items()):
            if key == label:
                g = value['g']
                s = value['s']
                histo_bins = (math.sqrt(len(g))) / 2

                mask = (g != 0) & (s != 0)
                g_scat = g[mask]
                s_scat = s[mask]

                color = self.plot_data_colors[i][1]  # Use the saved color mapping

                # Highlight by using a higher alpha value or different plot parameters
                if self.shared_info.phasor_settings["scatter_type"] == "scatter":
                    self.highlighted_sample = self.ax.scatter(x=g_scat, y=s_scat, label=key, color=color, s=16, alpha=0.75, linewidth=0.4)

                elif self.shared_info.phasor_settings["scatter_type"] == "contour":
                    counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
                    contour_set = self.ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])
                    self.highlighted_sample = contour_set.collections  # Store the list of contour sets

                elif self.shared_info.phasor_settings["scatter_type"] == "histogram":
                    counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=int(histo_bins))
                    hist2d = self.ax.contourf(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], cmap='jet_r', norm=colors.LogNorm(), alpha=0.75)
                    self.highlighted_sample = hist2d.collections  # Store the QuadMesh

        self.ax.set_xlim([-0.005, 1])
        self.ax.set_ylim([0, 0.65])
        self.canvas_phasor.draw_idle()

    def highlightPlotPoints_condition(self, label):
        self.deactivate_roi()
        self.btn_select.setStyleSheet('QPushButton {color: white;}')
        self.btn_select.setEnabled(False)

        # Remove the previous highlighted condition plot if it exists
        if hasattr(self, 'highlighted_condition') and self.highlighted_condition:
            if isinstance(self.highlighted_condition, list):  # Handle contour plots
                for artist in self.highlighted_condition:
                    artist.remove()
            elif hasattr(self.highlighted_condition, 'remove'):
                self.highlighted_condition.remove()
            elif isinstance(self.highlighted_condition, tuple):
                for artist in self.highlighted_condition:
                    artist.remove()
            del self.highlighted_condition

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
                legend.remove()
            self.canvas_phasor.draw_idle()



class LegendWidget(QListWidget):
    # Define a new signal that emits the selected label's text
    legendItemSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemClicked.connect(self.onItemClicked)

    def updateLegend(self, labels_colors, plot_type):
        self.clear()
        if plot_type == "condition":
            unique_labels_colors = {label: color for label, color in labels_colors}  # Remove duplicates
            for label, color in unique_labels_colors.items():
                it = QListWidgetItem(label)
                it.setIcon(self.createCircularIcon(color))
                self.addItem(it)
        elif plot_type == "individual":
            for label, color in labels_colors:
                it = QListWidgetItem(label)
                it.setIcon(self.createCircularIcon(color))
                self.addItem(it)

    def onItemClicked(self, item):
        # Emit the signal with the text of the selected item
        self.legendItemSelected.emit(item.text())

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
