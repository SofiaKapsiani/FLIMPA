# helper_functions.py

from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt
from utils.shared_data import SharedData

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar2QT
import numpy as np

class Helpers:
    def __init__(self, main_window):
        self.main_window = main_window
        self.shared_info = SharedData()
       
    def displaySelectedtau(self):
        '''display image file that the user has selected'''
        self.main_window.figure_tau.clear()
        if self.shared_info.results_dict != {}:
            self.main_window.plotImages.plot_tau_map(masked_image=None)
            self.main_window.phasor_componets.plot_phasor_coordinates(cmap="gist_rainbow_r")
    
    def delete_selected_files(self):
        """delete files selected by user"""
        # Collect the rows to delete
        rows_to_delete = []
        filenames_to_delete = []

        for filename, file_info in self.shared_info.raw_data_dict.items():
            if file_info['analyse'] == 'yes':
                for row in range(self.main_window.fileTable.rowCount()):
                    item = self.main_window.fileTable.item(row, 0)
                    if item and item.text() == filename:
                        rows_to_delete.append(row)
                        filenames_to_delete.append(filename)
                        break

        # Delete the rows from the table in reverse order to avoid index shifting issues
        for row in sorted(rows_to_delete, reverse=True):
            self.main_window.fileTable.removeRow(row)

        # Delete the entries from the dictionary
        for filename in filenames_to_delete:
            del self.shared_info.raw_data_dict[filename]
            # Also delete from results_dict if present
            if filename in self.shared_info.results_dict:
                del self.shared_info.results_dict[filename]
            if filename in self.shared_info.intensity_img_dict:
                del self.shared_info.intensity_img_dict[filename]
    
    def update_data_with_roi(self,  inside_ellipse):
        # highlight areas selected by ROI tool
        if self.main_window.tau_disp != None:
           tau_map = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])[self.shared_info.config["lifetime_map"]]
           M_mask = np.zeros_like(tau_map)
           M_mask[inside_ellipse] = tau_map[inside_ellipse]
           self.main_window.plotImages.plot_tau_map( masked_image=M_mask)

    def resizeIntensity(self):
        # resize your figures based on the current window size
        if self.shared_info.config["selected_file"] in self.shared_info.intensity_img_dict:
            self.main_window.plotImages.plot_img()
            self.main_window.canvas.draw()
    
    def resizeTau(self):
        # Implement the logic to resize your figures based on the current window size
        try: 
            self.main_window.plotImages.plot_tau_map()
            # Ensure the canvas is properly updated
            self.main_window.canvas_tau.draw()

        except: 
            pass
    
    def resizeViolin(self):
        # Implement the logic to resize your figures based on the current window size
        try: 
            self.main_window.plotImages.violin_plots()
            self.main_window.canvas_violin.draw()
        
        except: 
            pass
    
    def resizeGallery(self):
        try: 
            self.main_window.figure_gallery.clear()
            n = len(self.shared_info.results_dict.keys())  # Number of images
            if n ==1:
                cols=1
                image_size_inches = 1.3*2.6
            elif n ==2:
                cols=2
                image_size_inches = 1.3*1.8
            else:
                cols = 3  # Desired columns
                image_size_inches = 1.3*1.3
            rows = int(np.ceil(n / cols))  # Calculate required rows

            # Calculate figure dimensions
            fig_width = cols * image_size_inches
            fig_height = rows * image_size_inches
            if rows >1:
                fig_height -= 0.40
            
            dpi = self.main_window.fixed_dpi  # Using fixed DPI
            new_width = fig_width * dpi
            new_height = fig_height * dpi


            # Resize the canvas accordingly
            self.main_window.canvas_gallery.resize(new_width, new_height)
            
            # Force a redraw of the canvas
            self.main_window.plotImages.gallery_imgs(data_dict=self.shared_info.results_dict)
            self.main_window.canvas_gallery.draw_idle()

            self.main_window.scroll_area.updateGeometry()
            self.main_window.scroll_area.viewport().update()
            self.main_window.canvas_gallery.update()
            
            # Update the geometry of the scroll area widget
            self.main_window.scroll_area.widget().setMinimumSize(new_width, new_height)
        
        except: 
            pass
    
    def resizeGallery_I(self):
        try: 
            self.main_window.figure_gallery_I.clear()
            n = len(self.shared_info.results_dict.keys())  # Number of images
            if n ==1:
                cols=1
                image_size_inches = 1.3*2.6
            elif n ==2:
                cols=2
                image_size_inches = 1.3*1.8
            else:
                cols = 3  # Desired columns
                image_size_inches = 1.3*1.3
            rows = int(np.ceil(n / cols))  # Calculate required rows

            # Calculate figure dimensions
            fig_width = cols * image_size_inches
            fig_height = rows * image_size_inches
            if rows >1:
                fig_height -= 0.40
            
            dpi = self.main_window.fixed_dpi  # Using fixed DPI
            new_width = fig_width * dpi
            new_height = fig_height * dpi

            # Resize the canvas accordingly
            self.main_window.canvas_gallery_I.resize(new_width, new_height)
            
            # Force a redraw of the canvas
            self.main_window.plotImages.gallery_imgs_I(data_dict=self.shared_info.results_dict)
            self.main_window.canvas_gallery_I.draw_idle()

            self.main_window.scroll_area_I.updateGeometry()
            self.main_window.scroll_area_I.viewport().update()
            self.main_window.canvas_gallery_I.update()
            
            # Update the geometry of the scroll area widget
            self.main_window.scroll_area_I.widget().setMinimumSize(new_width, new_height)
        
        except: 
            pass
    
    def update_table_widget(self):
        """update table showing lifetime values per image based on user settings"""
        # Get the selected grouping option
        grouping_option = self.main_window.tab_settings.widget_dict.get("table_Group by").currentText()

        # Regenerate the DataFrame based on the grouping option
        if grouping_option == "Condition":
            grouped_df = self.shared_info.df_stats.groupby('condition').agg({
                'M': 'mean',
                'phi': 'mean',
                'average': 'mean'
            }).reset_index()
        elif grouping_option == "Sample":
            grouped_df = self.shared_info.df_stats.groupby(['sample', 'condition']).agg({
                'M_mean': 'mean',
                'phi_mean': 'mean',
                'average_mean': 'mean'
            }).reset_index()
        elif grouping_option == "None":
            grouped_df = self.shared_info.df_stats.drop(columns=['M_mean', 'phi_mean', 'average_mean'], errors='ignore')

        # Round the values to 2 decimal places
        grouped_df = grouped_df.round(3)

        # Clear the existing table content
        self.main_window.table_widget.clear()

        # Set the table row and column count based on the grouped DataFrame
        self.main_window.table_widget.setRowCount(grouped_df.shape[0])
        self.main_window.table_widget.setColumnCount(grouped_df.shape[1])

        # Set the table headers
        self.main_window.table_widget.setHorizontalHeaderLabels(grouped_df.columns)

        # Set a standard column width
        standard_column_width = 80  # Adjust this value as needed
        for col in range(grouped_df.shape[1]):
            self.main_window.table_widget.setColumnWidth(col, standard_column_width)

        # Populate the table with DataFrame contents and make items non-editable
        for i in range(grouped_df.shape[0]):
            for j in range(grouped_df.shape[1]):
                item = QTableWidgetItem(str(grouped_df.iloc[i, j]))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make the item non-editable
                self.main_window.table_widget.setItem(i, j, item)

class NavigationToolbar_violin(NavigationToolbar2QT):
    # only display the buttons we need
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Back', 'Forward', 'Pan', 'Zoom', 'Subplots', 'Save')] # 'Customize',
