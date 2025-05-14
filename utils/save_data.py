import os
from tifffile import imwrite
import math
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec

def save_tau(output_dir, progress_dialog,  lifetime_type, results_dict, config):
    """
    Save the selected lifetime map (phi, M, or average) as .tif and .png files in a specified directory.
    
    Parameters:
    output_dir (str): Directory where the .tif and .png files will be saved.
    lifetime_type (str): The type of lifetime map to save ("phi", "M", or "average").
    results_dict (dict): Dictionary containing the lifetime analysis results.
    config (dict): Configuration dictionary containing settings like colormap and value range.
    """
    try: 
        # Create the output directory if it doesn't exist
        if not os.path.exists(str(output_dir)):
            os.makedirs(str(output_dir))
        
        # Iterate through the results dictionary and save the data
        for filename in results_dict.keys():
            print("filename:", filename)
            # Ensure the data arrays have the same x and y dimensions as the sample data
            x_dim, y_dim = results_dict[filename]['sample_data'].shape[1], results_dict[filename]['sample_data'].shape[2]
            
            # Reshape the lifetime data to match the dimensions of the sample data
            lifetime_data = results_dict[filename][lifetime_type].reshape((x_dim, y_dim)) * 10**9
            
            # Define the file paths
            lifetime_path_tif = os.path.join(output_dir, f"{filename}_{lifetime_type}_raw.tif")
            
            # Save the data as .tif files
            imwrite(lifetime_path_tif, lifetime_data)
            
            # Define the file paths for .png
            lifetime_path_png = os.path.join(output_dir, f"{filename}_{lifetime_type}.png")
            
            # Function to save the data as PNG
            def save_as_png(data, path):
                fig, ax = plt.subplots()
                ax.set_xticks([])
                ax.set_yticks([])
                tau_img = data.astype('float')
                tau_img[tau_img == 0] = np.nan  # Handle NaNs

                img_plot = ax.imshow(tau_img, cmap='gist_rainbow_r', 
                                    vmin=float(config["lifetime_vmin"]), vmax=float(config["lifetime_vmax"]))
                
                # Optional: integrate lifetime image with intensity image
                if config["lifetime_itegrate"] == "True":
                    intensity = results_dict[filename]["sample_data"].sum(0)
                    ax.imshow(intensity, cmap='gray', vmin=0, vmax=int(intensity[intensity != 0].max() - intensity[intensity != 0].mean()), alpha=0.5)
                
                ax.patch.set_facecolor((0, 0, 0, 1.0))

                divider = make_axes_locatable(ax)
                cax = divider.append_axes("right", size="5%", pad=0.05)
                cbar = fig.colorbar(img_plot, cax=cax, orientation='vertical')
                cbar.ax.tick_params(colors='black', labelsize=8)
            
                # Optional: handle masked image
                if 'mask_arr' in results_dict[filename] and results_dict[filename]['mask_arr'] is not None:
                    mask_arr = results_dict[filename]['mask_arr']
                    colors = [(0, 0, 0, 1), (0, 0, 0, 0)]  # Fully opaque and fully transparent
                    cmap = LinearSegmentedColormap.from_list("custom_black", colors, N=2)
                    masked_image_prepared = np.reshape(mask_arr, (x_dim, y_dim))
                    ax.imshow(masked_image_prepared, cmap=cmap, alpha=0.8)
                
                # Save the figure
                plt.savefig(path, bbox_inches='tight', dpi=72)
                plt.close(fig)
            
            # Save the selected lifetime data as PNG
            save_as_png(lifetime_data, lifetime_path_png)
        
        print(f"{lifetime_type} lifetime maps saved to {output_dir}")
    finally:
        # Close the progress dialog after saving is complete
        progress_dialog.close()


def save_gallery_view(output_dir, progress_dialog, file_name, data_dict, config):
    """
    Save the gallery view as a .png file in a specified directory.
    
    Parameters:
    data_dict (dict): Dictionary containing the lifetime analysis results.
    output_dir (str): Directory where the .png file will be saved.
    config (dict): Configuration dictionary containing settings like colormap and value range.
    """
    try:
        # Create the output directory if it doesn't exist
        if not os.path.exists(str(output_dir)):
            os.makedirs(str(output_dir))
        
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
            image_size_inches = 1.3 * 1.3
        rows = int(np.ceil(n / cols))  # Calculate required rows

        # Calculate figure dimensions
        fig_width = cols * image_size_inches
        fig_height = rows * image_size_inches 

        # Create figure
        fig = plt.figure(figsize=(fig_width, fig_height))
        gs = GridSpec(rows + 1, cols, height_ratios=[1] * rows + [0.05], figure=fig)
        images = []  # List to store the images for colorbar reference

        # Create a black background image
        dim_img = int(np.sqrt(next(iter(data_dict.values()))[config["lifetime_map"]].shape))
        black_background = np.zeros((dim_img, dim_img))

        for i, key in enumerate(data_dict):
            row = i // cols
            col = i % cols
            ax_gal = fig.add_subplot(gs[row, col])
            tau = data_dict[key][config["lifetime_map"]]

            tau_img = np.reshape(tau * 1e9, (dim_img, dim_img))
            tau_img[tau_img == 0] = np.nan  # Handle NaNs

            # Plot the black background first
            ax_gal.imshow(black_background, cmap='gray', aspect='equal', vmin=0, vmax=1)

            # Overlay the tau_img on top of the black background
            im = ax_gal.imshow(tau_img, cmap='gist_rainbow_r', aspect='equal',
                            vmin=float(config["lifetime_vmin"]),
                            vmax=float(config["lifetime_vmax"]))
            intensity = data_dict[key]["sample_data"].sum(0)
            # optional: integrate lifetime image with intensity image
            if config.get("lifetime_itegrate") == "True":
                ax_gal.imshow(intensity, cmap='gray', vmin=0,
                            vmax=int(intensity[intensity != 0].max() - intensity[intensity != 0].mean()),
                            alpha=0.5)

            images.append(im)  # Add the image to the list
            fontsize = 8 if len(key) < 25 else 6
            ax_gal.set_title(key, color='black', fontsize=fontsize)
            ax_gal.patch.set_facecolor('black')
            ax_gal.axis('off')
            
        # Set figure background color to black

        cbar_ax = fig.add_subplot(gs[-1, :])
        cbar = fig.colorbar(images[-1], cax=cbar_ax, orientation='horizontal', aspect=40)

        cbar.ax.xaxis.set_tick_params(color='black', labelsize=8)  # Color the ticks white
        for label in cbar.ax.get_xticklabels():
            label.set_color('black')  # Color the tick labels white
        cbar.ax.set_xlabel(cbar.ax.get_xlabel(), color='black')  # Set colorbar label color to white, if you have set a label

        # Save the figure
        gallery_path_png = os.path.join(output_dir, f"{file_name}.png")
        fig.subplots_adjust(top=0.95)
        plt.savefig(gallery_path_png, bbox_inches='tight', dpi=300, transparent=True)
        plt.close(fig)
    finally:
        # Close the progress dialog after saving is complete
        progress_dialog.close()



def save_intensity_images(output_dir, progress_dialog, intensity_img_dict, raw_data_dict, config):
    """
    Save the intensity images as .tif and .png files in a specified directory.
    
    Parameters:
    intensity_img_dict (dict): Dictionary containing the intensity images.
    raw_data_dict (dict): Dictionary containing the raw data including masks.
    output_dir (str): Directory where the .tif and .png files will be saved.
    """
    try:
        # Create the output directory if it doesn't exist
        if not os.path.exists(str(output_dir)):
            os.makedirs(str(output_dir))
        
        # Iterate through the intensity images dictionary and save the data
        for filename in intensity_img_dict.keys():
            print("filename:", filename)
            # Get intensity image and masks
            intensity_image = intensity_img_dict[filename]['intensity_image']
            masked_image = intensity_img_dict[filename]['mask']
            mask_arr = raw_data_dict[filename]['mask_arr']

            image = np.where(masked_image == 0, 0, intensity_image)
            if mask_arr is not None:
                image = np.where(mask_arr == 0, 0, image)
            
            # Define the file paths
            intensity_path_tif = os.path.join(output_dir, f"{filename}_intensity_raw.tif")
            intensity_path_png = os.path.join(output_dir, f"{filename}_intensity.png")
            
            # Save the intensity image as .tif file
            imwrite(intensity_path_tif, image)
            
            # Function to save the intensity image as PNG
            def save_as_png(image, path, masked_image):
                fig, ax = plt.subplots()
                ax.set_xticks([])
                ax.set_yticks([])
                image = np.where(masked_image == 0, 0, image)
                if mask_arr is not None:
                    image = np.where(mask_arr == 0, 0, image)
                img_plot = ax.imshow(image, cmap='gray', vmin=config["vmin_int"], vmax=config["vmax_int"])

                # Create a colorbar with a fixed aspect ratio that matches the image's aspect ratio
                divider = make_axes_locatable(ax)
                cax = divider.append_axes("right", size="5%", pad=0.1)
                cbar = fig.colorbar(img_plot, cax=cax, orientation='vertical',)
                cbar.ax.tick_params(colors='black', labelsize=8)

                ax.patch.set_facecolor((0, 0, 0, 1.0))
                
                # Save the figure
                plt.savefig(path, bbox_inches='tight', dpi=72, )
                plt.close(fig)
            
            # Save the intensity image as PNG
            save_as_png(intensity_image, intensity_path_png, masked_image)
    finally:
        # Close the progress dialog after saving is complete
        progress_dialog.close()
        print(f"Intensity images saved to {output_dir}")


def save_gallery_int_view(output_dir, progress_dialog, file_name, data_dict, config):
    """
    Save the gallery view as a .png file in a specified directory.
    
    Parameters:
    data_dict (dict): Dictionary containing the lifetime analysis results.
    output_dir (str): Directory where the .png file will be saved.
    config (dict): Configuration dictionary containing settings like colormap and value range.
    """
    try:
        # Create the output directory if it doesn't exist
        if not os.path.exists(str(output_dir)):
            os.makedirs(str(output_dir))
        
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
            image_size_inches = 1.3 * 1.3
        rows = int(np.ceil(n / cols))  # Calculate required rows

        # Calculate figure dimensions
        fig_width = cols * image_size_inches
        fig_height = rows * image_size_inches 

        # Create figure
        fig = plt.figure(figsize=(fig_width, fig_height))
        gs = GridSpec(rows + 1, cols, height_ratios=[1] * rows + [0.05], figure=fig)
        images = []  # List to store the images for colorbar reference

        for i, key in enumerate(data_dict):
            row = i // cols
            col = i % cols
            ax_gal = fig.add_subplot(gs[row, col])
        # Access the correct intensity data
            intensity = data_dict[key]["sample_data"].sum(0)  # Adjust as necessary

            im = ax_gal.imshow(intensity, cmap='gray', aspect='equal',
                            vmin=config["vmin_int"], vmax=config["vmax_int"])
        

            images.append(im)  # Add the image to the list
            fontsize = 8 if len(key) < 25 else 6
            ax_gal.set_title(key, color='black', fontsize=fontsize)
            ax_gal.axis('off')

        # Add a single colorbar for all plots
        cbar_ax = fig.add_subplot(gs[-1, :])
        cbar = fig.colorbar(images[-1], cax=cbar_ax, orientation='horizontal', aspect=40)

        cbar.ax.xaxis.set_tick_params(color='black', labelsize=8)  # Color the ticks white
        for label in cbar.ax.get_xticklabels():
            label.set_color('black')  # Color the tick labels white
        cbar.ax.set_xlabel(cbar.ax.get_xlabel(), color='black')  # Set colorbar label color to white, if you have set a label

        # Save the figure
        gallery_path_png = os.path.join(output_dir, f"{file_name}.png")
        fig.patch.set_facecolor('black')
        fig.subplots_adjust(top=0.95)
        plt.savefig(gallery_path_png, bbox_inches='tight', dpi=300, transparent = True)
        plt.close(fig)
    finally:
        # Close the progress dialog after saving is complete
        progress_dialog.close()


def save_phasor_plot(output_dir, data_dict, phasor_settings, frequency):
    """
    Save the gallery view as a .png file in a specified directory.
    
    Parameters:
    data_dict (dict): Dictionary containing the lifetime analysis results.
    output_dir (str): Directory where the .png file will be saved.
    phasor_settings (dict): Configuration dictionary containing settings like scatter_type.
    frequency (int): laser frequency
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(str(output_dir)):
        os.makedirs(str(output_dir))
    
    fig, ax = plt.subplots()
    
    r = 0.5
    h = 0.5
    x = np.linspace(0, 1, 1000)
    y = np.sqrt(r ** 2 - (x - h) ** 2)
    ax.plot(x, y, 'black', linewidth=1)

    # plot mono-exponential lifetimes on semicircle
    if phasor_settings.get("tau_labels", True):
            # plot mono-exponential lifetimes on semicircle
            w = 2*math.pi*int(frequency)*1e6  # angular frequency
            if int(frequency) >= 100:
                tau_labels = np.arange(0 * 1e-9, 9 * 1e-9, 1e-9)  # Array from 0 to 8 ns
            elif int(frequency) > 50:
                tau_labels = np.arange(0 * 1e-9, 11 * 1e-9, 1e-9)  # Array from 0 to 10 ns
            elif int(frequency) < 30:
                tau_labels = np.arange(0 * 1e-9, 15 * 1e-9, 1e-9)  # Array from 0 to 14 ns
            else:
                tau_labels = np.arange(0 * 1e-9, 13 * 1e-9, 1e-9)  # Array from 0 to 12 ns
            g_unisem = 1 / (1 + w ** 2 * tau_labels ** 2)  # g-coordinates
            s_unisem = w * tau_labels / (1 + w ** 2 * tau_labels ** 2)  # s-coordinates
            ax.plot(g_unisem, s_unisem, 'o', markersize=3, mec='black', mfc='dimgray')  # Points

            # Labels
            for g, s, tau in zip(g_unisem, s_unisem, tau_labels):
                label = f"{int(tau * 1e9)}ns"
                if g >= 0.7:
                    ax.text(g + 0.02, s, label, color='black', fontsize=8, ha='left', va='center')
                elif g >= 0.3:
                    ax.text(g - 0.03, s, label, color='black', fontsize=8, ha='left', va='center')
                else:
                    ax.text(g - 0.025, s, label, color='black', fontsize=8, ha='right', va='center')

    ax.set_xlim([-0.005, 1])
    ax.set_ylim([0, 0.65])
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    tab20_cmap = plt.get_cmap('tab20')
    num_colors = tab20_cmap.N
    legend_handles = []  # List to hold the legend handles

    for i, (key, value) in enumerate(data_dict.items()):
        g = value['g']
        s = value['s']
        histo_bins = (math.sqrt(len(g))) / 2
        mask = (g != 0) & (s != 0)
        g_scat = g[mask]
        s_scat = s[mask]
        color = tab20_cmap(i % num_colors)

        if phasor_settings["scatter_type"] == "scatter":
            ax.scatter(x=g_scat, y=s_scat, label=key, color=color, s=16, alpha=0.5, linewidth=0.4)
        
        elif phasor_settings["scatter_type"] == "contour":
            counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
            contour = ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])
            legend_handles.append(Patch(facecolor=color, edgecolor='black', label=key))  # Create a legend handle
        
        elif phasor_settings["scatter_type"] == "histogram":
            ax.hist2d(g_scat, s_scat, bins=int(histo_bins), cmap='jet', norm=colors.LogNorm(), alpha=0.75)

    # Adding manually created legend handles if they exist
    if legend_handles:
        ax.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, edgecolor="black", frameon=False)
    else:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, edgecolor="black", frameon=False)
    
    ax.set_xlim([-0.005, 1])
    ax.set_ylim([0, 0.65])
    
    phasor_path_png = os.path.join(output_dir, "phasor_plot_individual.png")
    plt.savefig(phasor_path_png, bbox_inches='tight', dpi=300, transparent=True)
    plt.close(fig)


def save_phasor_plot_condition(output_dir, data_dict, phasor_settings, frequency):
    """
    Save condition-based phasor plots as a .png file in a specified directory.

    Parameters:
    output_dir (str): Directory where the .png file will be saved.
    data_dict (dict): Dictionary containing the lifetime analysis results grouped by conditions.
    phasor_settings (dict): Configuration dictionary containing settings like scatter_type.
    frequency (int): laser frequency
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    fig, ax = plt.subplots()

    # Base circle for reference
    r = 0.5
    h = 0.5
    x = np.linspace(0, 1, 1000)
    y = np.sqrt(r ** 2 - (x - h) ** 2)
    ax.plot(x, y, 'black', linewidth=1)
    ax.set_xlim([-0.005, 1])
    ax.set_ylim([0, 0.65])
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # plot mono-exponential lifetimes on semicircle
    if phasor_settings.get("tau_labels", True): 
        w = 2 * math.pi * int(frequency) * 1e6  # angular frequency
        tau_labels = np.arange(0 * 1e-9, 14 * 1e-9, 1e-9)  # Array from 0 to 13ns with step size of 1ns
        g_unisem = 1 / (1 + w ** 2 * tau_labels ** 2)  # Calculate g-coordinates
        s_unisem = w * tau_labels / (1 + w ** 2 * tau_labels ** 2)  # Calculate s-coordinates
        p1 = ax.plot(g_unisem, s_unisem, 'o', markersize=3, mec='black', mfc='dimgray')

        # plot mono-exponential lifetimes on semicircle
        if phasor_settings.tau_labels:
                # plot mono-exponential lifetimes on semicircle
                w = 2*math.pi*int(frequency)*1e6  # angular frequency
                if int(frequency) >= 100:
                    tau_labels = np.arange(0 * 1e-9, 9 * 1e-9, 1e-9)  # Array from 0 to 8 ns
                elif int(frequency) > 50:
                    tau_labels = np.arange(0 * 1e-9, 11 * 1e-9, 1e-9)  # Array from 0 to 10 ns
                elif int(frequency) < 30:
                    tau_labels = np.arange(0 * 1e-9, 15 * 1e-9, 1e-9)  # Array from 0 to 14 ns
                else:
                    tau_labels = np.arange(0 * 1e-9, 13 * 1e-9, 1e-9)  # Array from 0 to 12 ns
                g_unisem = 1 / (1 + w ** 2 * tau_labels ** 2)  # g-coordinates
                s_unisem = w * tau_labels / (1 + w ** 2 * tau_labels ** 2)  # s-coordinates
                ax.plot(g_unisem, s_unisem, 'o', markersize=3, mec='black', mfc='dimgray')  # Points

                # Labels
                for g, s, tau in zip(g_unisem, s_unisem, tau_labels):
                    label = f"{int(tau * 1e9)}ns"
                    if g >= 0.7:
                        ax.text(g + 0.02, s, label, color='black', fontsize=8, ha='left', va='center')
                    elif g >= 0.3:
                        ax.text(g - 0.03, s, label, color='black', fontsize=8, ha='left', va='center')
                    else:
                        ax.text(g - 0.025, s, label, color='black', fontsize=8, ha='right', va='center')

    tab20_cmap = plt.get_cmap('tab20')
    num_colors = tab20_cmap.N

    # Prepare legend handles and data aggregation by conditions
    legend_handles = []
    unique_conditions = list(set(value['condition'] for value in data_dict.values()))
    plot_data_colors = {condition: tab20_cmap(i % num_colors) for i, condition in enumerate(unique_conditions)}
    condition_points = {condition: {'g': [], 's': []} for condition in unique_conditions}

    for key, value in data_dict.items():
        g = value['g']
        s = value['s']
        condition = value['condition']
        mask = (g != 0) & (s != 0)
        condition_points[condition]['g'].extend(g[mask])
        condition_points[condition]['s'].extend(s[mask])

    # Plotting by condition
    for condition, points in condition_points.items():
        g_scat = np.array(points['g'])
        s_scat = np.array(points['s'])
        color = plot_data_colors[condition]
        histo_bins = int(math.sqrt(len(g_scat)) / 2)

        if phasor_settings["scatter_type"] == "scatter":
            ax.scatter(x=g_scat, y=s_scat, label=condition, color=color, s=16, alpha=0.5, linewidth=0.4)
        elif phasor_settings["scatter_type"] == "contour":
            counts, xbins, ybins = np.histogram2d(x=g_scat, y=s_scat, bins=50)
            ax.contour(counts.transpose(), extent=[xbins[0], xbins[-1], ybins[0], ybins[-1]], linewidths=1, colors=[color])
            legend_handles.append(Patch(facecolor=color, edgecolor='black', label=condition))  # Correct label reference
        elif phasor_settings["scatter_type"] == "histogram":
            ax.hist2d(g_scat, s_scat, bins=histo_bins, cmap='jet', norm=plt.colors.LogNorm(), alpha=0.75)

    # Using manual legend handles for contour plots
    if legend_handles:
        ax.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, edgecolor="black", frameon=False)
    
    phasor_path_png = os.path.join(output_dir, "phasor_plot_condition.png")
    plt.savefig(phasor_path_png, bbox_inches='tight', dpi=300, transparent=True)
    plt.close(fig)


def save_violin_plot(output_dir, progress_dialog, config, df, file_name):
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        fig, ax = plt.subplots()
        tau = config["tau_violin"]
        sns.violinplot(y=tau, x="condition", data=df, ax=ax, saturation=1, inner='quartile', color='white')
        sns.swarmplot(y=tau, x="condition", data=df, ax=ax, zorder=1, s=6, edgecolor='#000000', alpha=0.8, linewidth=1, palette="Set2")
        ax.set(xlabel='Condition', ylabel='{} lifetime (ns)'.format(tau))
        fig.tight_layout()
        violin_path_png = os.path.join(output_dir, f"{file_name}_{tau}.png")
        plt.savefig(violin_path_png, bbox_inches='tight', dpi=300, transparent=True)
        plt.close(fig)
    finally:
        # Close the progress dialog after saving is complete
        progress_dialog.close()


def save_df_csv(output_dir, df_stats):
    """
    Export mean lifetime values per image in a .csv file

    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    df_export = df_stats.drop(columns=['M_mean', 'phi_mean', 'average_mean'], errors='ignore')
    df_export.to_csv(os.path.join(output_dir, "lifetime_values.csv"))