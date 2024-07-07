from PySide6.QtWidgets import QTableWidgetItem, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from scipy.ndimage import measurements
import seaborn as sns
from mpl_toolkits.axes_grid1 import make_axes_locatable
from utils.shared_data import SharedData 

class PlotImages():

    def __init__(self, main_window):
        self.main_window = main_window
        self.shared_info = SharedData()
        
        # input images
        self.canvas = self.main_window.canvas
        self.figure  = self.main_window.figure
        # lifetime images (single)
        self.canvas_tau = self.main_window.canvas_tau
        self.figure_tau  = self.main_window.figure_tau
        # lifetime gallery images
        self.canvas_gallery = self.main_window.canvas_gallery
        self.figure_gallery  = self.main_window.figure_gallery
        # intensity gallery images
        self.canvas_gallery_I = self.main_window.canvas_gallery_I
        self.figure_gallery_I = self.main_window.figure_gallery_I
        # violin plots
        self.figure_violin = self.main_window.figure_violin
        self.canvas_violin = self.main_window.canvas_violin
        self.fileTable = self.main_window.fileTable
        self.dpi = main_window.fixed_dpi 
        
        

    def visualise_image(self, intensity_image, filename):
        '''Visualise images once loaded'''
        try:
            self.figure.clear()
            min_photon_counts = int(self.shared_info.config.get("min_photons", 0))
            max_photon_counts = int(self.shared_info.config.get("max_photons", 0))
            masked_image_min = np.where(intensity_image < min_photon_counts, 0, intensity_image)
            masked_image = np.where(intensity_image > max_photon_counts, 0, masked_image_min)
            self.shared_info.intensity_img_dict[filename] = {'intensity_image': intensity_image, 'mask': masked_image}
            self.plot_img()

            # Add filename to the table
            rowPosition = self.fileTable.rowCount()
            if self.fileTable.rowCount() == 0:
                self.fileTable.setColumnCount(2)  # Adjust to have two columns
                self.fileTable.setHorizontalHeaderLabels(["File name", "Condition"])

            # Add checkbox
            chkBoxItem = QTableWidgetItem(filename)
            chkBoxItem.setBackground(QColor(40, 40, 40))
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chkBoxItem.setCheckState(Qt.Checked)

            # Create condition item
            conditionItem = QTableWidgetItem(self.shared_info.raw_data_dict[filename]["condition"])
            # make condition item read only
            conditionItem.setFlags(conditionItem.flags() & ~Qt.ItemIsEditable)


            self.fileTable.insertRow(rowPosition)
            self.fileTable.setItem(rowPosition, 0, chkBoxItem)
            self.fileTable.setItem(rowPosition, 1, conditionItem)

            # Ensure the canvas is properly updated
            self.canvas.draw()
            self.canvas.updateGeometry()

            # Update the parent widget layout to ensure proper placement
            self.canvas.parent().updateGeometry()
            self.canvas.parent().adjustSize()

        except Exception as e:
            print(f"Error loading image: {e}")

    def handleCheckboxChange(self, item):
        # Check if the change is in the checkbox column (column 0)
        if item.column() == 0:
            filename = item.text()  # Assuming the filename is stored as text in the checkbox item
            if item.checkState() == Qt.Checked:
                self.shared_info.raw_data_dict[filename]['analyse'] = 'yes'
            else:
                self.shared_info.raw_data_dict[filename]['analyse'] = 'no'


    def displaySelectedImage(self, item):
        '''Display intensity image file that the user has selected'''
        filename = item.text()
        self.shared_info.config["selected_file"] = filename
        if filename in self.shared_info.intensity_img_dict:
            self.figure.clear()
            self.plot_img()
    



    def plot_img(self):
        '''Function for image and mask plotting'''
        self.figure.clear()

        data = self.shared_info.intensity_img_dict[self.shared_info.config["selected_file"]]
        masked_image = data['mask']
        intensity_image = data['intensity_image']
        manual_mask = self.shared_info.raw_data_dict[self.shared_info.config["selected_file"]]['mask_arr']
        

        ax = self.figure.add_subplot(111)  # Add a subplot to the figure
        ax.set_xticks([])
        ax.set_yticks([])

        # Display the image on the axes
        img_plot = ax.imshow(intensity_image, cmap='gray')

        # Adjust colorbar size to match the image
        # Create a colorbar with a fixed aspect ratio that matches the image's aspect ratio
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.1)
        cbar =self.figure.colorbar(img_plot, cax=cax, orientation='vertical')
        cbar.ax.tick_params(colors='white', labelsize=8)

        # display manual masks if present
        if manual_mask is not None:
            colors_m = [(186/255, 219/255, 219/255, 0),  # fully transparent (for zero)
                (186/255, 219/255, 219/255, 1)] # fully opaque (for non-zero) 
            cmap_m = LinearSegmentedColormap.from_list("custom_red", colors_m, N=2)
            m_masked_image_prepared = np.where(manual_mask > 0, 1, 0)
            # Display the masked_image with the custom colormap
            ax.imshow(m_masked_image_prepared, cmap=cmap_m, alpha=0.35)
            for region in np.unique(manual_mask):
                if region == 0:
                    continue  # Skip background
                region_mask = (manual_mask == region)
                centroid = measurements.center_of_mass(region_mask)
                ax.text(centroid[1], centroid[0], str(int(region)), color='white', fontsize=8, ha='center', va='center')

        # Define a custom colormap for the masked image
        colors = [(60/255, 162/255, 161/255, 0),  # fully transparent (for zero)
                (60/255, 162/255, 161/255, 1)] # fully opaque (for non-zero) 
        cmap = LinearSegmentedColormap.from_list("custom_red", colors, N=2)
        
        masked_image_prepared = np.where(masked_image > 0, 0, 1)
        # Display the masked_image with the custom colormap
        ax.imshow(masked_image_prepared, cmap=cmap, alpha=0.35)
    
        self.canvas.draw()
        self.canvas.figure.tight_layout()


    def plot_tau_map(self, masked_image= None):
        '''Function for plotting lifetime maps'''
        self.figure_tau.clear()
        tau = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])[self.shared_info.config["lifetime_map"]]
        
        dim_img = int(np.sqrt(tau.shape)[0]) # get size of array with lifetime values
        tau_img = np.reshape(tau*1e9, (dim_img, dim_img)) # reshape into a 2D array (i.e. the lifetime image)
        tau_img = tau_img.astype('float') # convert all values to float
        tau_img[tau_img == 0] = np.nan

        ax = self.figure_tau.add_subplot(111)  # Add a subplot to the figure
        ax.set_xticks([])
        ax.set_yticks([])
        # Display the image on the axes
        img_plot = ax.imshow(tau_img, cmap='gist_rainbow_r', 
                             vmin=float(self.shared_info.config["lifetime_vmin"]), vmax=float(self.shared_info.config["lifetime_vmax"]))
        
        # optional: integrate lifetime image with intensity image
        if self.shared_info.config["lifetime_itegrate"] == "True":
            intenisty = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])["sample_data"].sum(0)
            ax.imshow(intenisty, cmap='gray', vmin=0, vmax=int(intenisty[intenisty!=0].max()-intenisty[intenisty!=0].mean()),  alpha = 0.6)
        else:
            pass

        ax.patch.set_facecolor((0, 0, 0, 1.0))

        # Adjust colorbar size to match the image
        # Create a colorbar with a fixed aspect ratio that matches the image's aspect ratio
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar =self.figure_tau.colorbar(img_plot, cax=cax, orientation='vertical',)
        cbar.ax.tick_params(colors='white', labelsize=8)

        if masked_image is not None: # Define a custom colormap for the masked image
            colors = [(0, 0, 0, 1),  
                    (0, 0, 0, 0)] 
            cmap = LinearSegmentedColormap.from_list("custom_black", colors, N=2)

            masked_image_prepared = np.reshape(masked_image, (dim_img, dim_img))
            
            # Display the masked_image with the custom colormap
            ax.imshow(masked_image_prepared, cmap=cmap, alpha=0.8)


        self.canvas_tau.draw()
        self.canvas_tau.figure.tight_layout()
    
    
    

    def gallery_imgs(self, data_dict):
        self.main_window.gallery_layout_grid.setRowStretch(1, 1)
        self.main_window.gallery_layout_grid.setColumnStretch(1, 1)
        self.figure_gallery.clear()  # Clear the figure for new content

        # Parameters
        n = len(data_dict.keys())  # Number of images
        if n == 1:
            cols = 1
            image_size_inches = 1.3 * 2.6
        elif n == 2:
            cols = 2
            image_size_inches = 1.3 * 1.8
        else:
            cols = 3  # Desired columns
            image_size_inches = 1.3 * 1.28
        rows = int(np.ceil(n / cols))  # Calculate required rows

        # Calculate figure dimensions
        fig_width = cols * image_size_inches
        fig_height = rows * image_size_inches

        if rows >1:
            fig_height -= 0.40

        # Set figure size
        self.figure_gallery.set_size_inches(fig_width, fig_height)

        gs = GridSpec(rows + 1, cols, height_ratios=[1] * rows + [0.05], figure=self.figure_gallery)
        images = []  # List to store the images for colorbar reference

        for i, key in enumerate(data_dict):
            row = i // cols
            col = i % cols
            ax_gal = self.figure_gallery.add_subplot(gs[row, col])
            tau = data_dict[key][self.shared_info.config["lifetime_map"]]

            dim_img = int(np.sqrt(tau.shape))
            tau_img = np.reshape(tau * 1e9, (dim_img, dim_img))
            tau_img[tau_img == 0] = np.nan  # Handle NaNs

            im = ax_gal.imshow(tau_img, cmap='gist_rainbow_r', aspect='equal',
                            vmin=float(self.shared_info.config["lifetime_vmin"]),
                            vmax=float(self.shared_info.config["lifetime_vmax"]))

            # optional: integrate lifetime image with intensity image
            if self.shared_info.config["lifetime_itegrate"] == "True":
                intenisty = data_dict[key]["sample_data"].sum(0)
                ax_gal.imshow(intenisty, cmap='gray', vmin=0,
                            vmax=int(intenisty[intenisty != 0].max() - intenisty[intenisty != 0].mean()),
                            alpha=0.5)

            images.append(im)  # Add the image to the list
            ax_gal.set_title(key, color='white', fontsize=10)
            ax_gal.axis('off')

        # Add a single colorbar for all plots
        cbar_ax = self.figure_gallery.add_subplot(gs[-1, :])
        cbar = self.figure_gallery.colorbar(images[-1], cax=cbar_ax, orientation='horizontal', aspect=40)

        cbar.ax.xaxis.set_tick_params(color='white', labelsize=8)  # Color the ticks white
        for label in cbar.ax.get_xticklabels():
            label.set_color('white')  # Color the tick labels white
        cbar.ax.set_xlabel(cbar.ax.get_xlabel(), color='white')  # Set colorbar label color to white, if you have set a label

        self.main_window.gallery_layout_grid.addWidget(self.canvas_gallery, 0, 0, 1, 1)

        self.canvas_gallery.draw_idle()  # Refresh the canvas
        self.canvas_gallery.resize(fig_width * self.dpi,
                                fig_height * self.dpi)
        self.canvas_gallery.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Ensure the canvas resizes based on its figure size
        fig_width = fig_width * self.dpi
        fig_height = fig_height * self.dpi
        self.canvas_gallery.setMinimumSize(fig_width, fig_height)


    def gallery_imgs_I(self, data_dict):
        # Plot gallery of intensity images
        self.main_window.gallery_layout_grid_I.setRowStretch(1, 1)
        self.main_window.gallery_layout_grid_I.setColumnStretch(1, 1)
        self.figure_gallery_I.clear()  # Clear the figure for new content

        # Parameters
        n = len(data_dict.keys())  # Number of images
        if n == 1:
            cols = 1
            image_size_inches = 1.3 * 2.6
        elif n == 2:
            cols = 2
            image_size_inches = 1.3 * 1.8
        else:
            cols = 3  # Desired columns
            image_size_inches = 1.3 * 1.28
        rows = int(np.ceil(n / cols))  # Calculate required rows

        # Calculate figure dimensions
        fig_width = cols * image_size_inches
        fig_height = rows * image_size_inches  # Extra height for colorbar
        if rows >1:
            fig_height -= 0.40
        # Set figure size
        self.figure_gallery_I.set_size_inches(fig_width, fig_height)

        gs = GridSpec(rows + 1, cols, height_ratios=[1] * rows + [0.05], figure=self.figure_gallery_I)
        images = []  # List to store the images for colorbar reference

        for i, key in enumerate(data_dict):
            row = i // cols
            col = i % cols

            ax_int = self.figure_gallery_I.add_subplot(gs[row, col])
            
            # Access the correct intensity data
            intensity = data_dict[key]["sample_data"].sum(0)  # Adjust as necessary

            im = ax_int.imshow(intensity, cmap='gray', aspect='equal',
                            vmin=self.shared_info.config["vmin_int"], vmax=self.shared_info.config["vmax_int"])
        
            images.append(im)  # Add the image to the list
            ax_int.set_title(key, color='white', fontsize=10)
            ax_int.axis('off')
        
        self.main_window.gallery_layout_grid_I.addWidget(self.canvas_gallery_I, 0, 0, 1, 1)
        
        # Add a single colorbar for all plots
        cbar_ax = self.figure_gallery_I.add_subplot(gs[-1, :])
        cbar = self.figure_gallery_I.colorbar(images[-1], cax=cbar_ax, orientation='horizontal', aspect=40)

        cbar.ax.xaxis.set_tick_params(color='white', labelsize=8)  # Color the ticks white
        for label in cbar.ax.get_xticklabels():
            label.set_color('white')  # Color the tick labels white
        cbar.ax.set_xlabel(cbar.ax.get_xlabel(), color='white')  # Set colorbar label color to white, if you have set a label

        # Adjust layout to include padding for colorbar ticks and labels
        self.figure_gallery_I.subplots_adjust(bottom=0.15)

        self.canvas_gallery_I.draw_idle()  # Refresh the canvas
        self.canvas_gallery_I.resize(fig_width * self.dpi,
                                    fig_height * self.dpi)
        self.canvas_gallery_I.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Ensure the canvas resizes based on its figure size
        fig_width = fig_width * self.dpi
        fig_height = fig_height * self.dpi
        self.canvas_gallery_I.setMinimumSize(fig_width, fig_height)



    
    def violin_plots(self):
        self.figure_violin.clear()  # Clear the figure
        dark_gray = (18 / 255, 18 / 255, 18 / 255)

        # Set the figure background to dark gray
        self.figure_violin.patch.set_facecolor(dark_gray)

        df = self.shared_info.df_stats
        tau = self.shared_info.config["tau_violin"]

        ax = self.figure_violin.add_subplot(111)  # Add a subplot
        ax.set_facecolor(dark_gray)

        sns.violinplot(y=tau, x="condition", data=df, ax=ax, saturation=1, inner='quartile', edgecolor='white', color='#121212')
        sns.swarmplot(y=tau, x="condition", data=df, ax=ax, zorder=1, s=5, edgecolor='white', alpha=0.8, linewidth=1, palette="Set2")
        ax.set(xlabel='Condition', ylabel='{} lifetime (ns)'.format(tau))

        # Set text colors to white
        ax.title.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')

        # Set the color of the spines
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')

        self.figure_violin.tight_layout()
        # Manually adjust the margins
        #self.figure_violin.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.15)
        self.canvas_violin.draw_idle()  # Refresh the canvas


    def update_mask_for_current_image(self):
        '''Update image mask everytime the min photon counts have been updated'''
        min_photon_counts = int(self.shared_info.config.get("min_photons", 0))
        max_photon_counts = int(self.shared_info.config.get("max_photons", 0))

        # Iterate over all images and update their masks
        for filename, data in self.shared_info.intensity_img_dict.items():
            intensity_image = data['intensity_image']
            # Assuming you have a method to compute the mask based on the intensity image and min_photon_counts
            # For example, if your masks are binary (0 or intensity value), adjust this logic accordingly
            new_mask_min = np.where(intensity_image >= min_photon_counts, intensity_image, 0)
            new_mask = np.where(new_mask_min >= max_photon_counts, 0, new_mask_min)
            # Update the mask in the storage
            self.shared_info.intensity_img_dict[filename]['mask'] = new_mask
            self.plot_img()
    