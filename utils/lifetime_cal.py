import numpy as np
import pandas as pd
import sdtfile as sdt
from ptufile import PtuFile
from skimage.io import imread
from scipy import signal # for image binning
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QInputDialog

from utils.mainwindow import *
from utils.shared_data import SharedData 
import math
from PIL import Image # load mask files
import os
from utils.errors import (
    UnsupportedFileFormatError,
    FileLoadingError,
    DataProcessingError,
    MaskingError,
    show_error_message
)

class LifetimeData(QObject):
    progressUpdated = Signal(int, str)
    analysisFinished = Signal()
   
    def __init__(self, main_window, app):
        super().__init__()
        
        self.main_window = main_window
        self.app = app

        self.shared_info = SharedData()
        self.should_stop = False 

        # getting config parameters
        self.ref_filename = self.shared_info.config["ref_file"]
        self.ref_lifetime = float(self.shared_info.config["ref_lifetime"])*1e-9


    # --- Image loading and lifetime calculation --- #
    def load_raw_data(self, file_name, bin_width, data_type="sample", sample_count = 0):
        """Function for loading raw data files."""
        try:
            if file_name.endswith('.sdt'):
                """ read Becker & Hickl .sdt files"""
                sdt_file = sdt.SdtFile(file_name)
                data = np.moveaxis(sdt_file.data[0], -1, 0).astype(np.float32)
                t_series = sdt_file.times[0].astype(np.float32)

                # check if x and y dimentions are equal
                if data.shape[1] != data.shape[2]:
                    if data_type == "reference":
                        # reference files with unequal space dimentions can not be anlysed, raise error
                        raise DataProcessingError(f"Reference file must have identical x and y dimensions. \nCurrent dimensions are: {data.shape[1]}x{data.shape[2]}")
                    elif data_type == "sample":
                        if sample_count == 0: 
                            show_error_message(self.main_window, "File Error", f"For best visualisation results we recommend files having identical x and y dimensions. \nCurrent dimensions are: {data.shape[1]}x{data.shape[2]}")

            elif file_name.endswith('.ptu'):
                """read PicoQuant .ptu files"""
                print("loading ptu ...")
                ptu = PtuFile(os.path.join(file_name))
                try:
                    print(f"Frequency from metadata: {ptu.frequency/1000000} MHz")
                except:
                    pass

                # check if x and y dimentions are equal
                if ptu.shape[1] != ptu.shape[2]:
                    if data_type == "reference":
                        # reference files with unequal space dimentions can not be anlysed, raise error
                        raise DataProcessingError(f"Reference file must have identical x and y dimensions. \nCurrent dimensions are: {ptu.shape[1]}x{ptu.shape[2]}")
                    elif data_type == "sample":
                        if sample_count == 0: 
                            show_error_message(self.main_window, "File Error", f"For best visualisation results we recommend files having identical x and y dimensions. \nCurrent dimensions are: {ptu.shape[1]}x{ptu.shape[2]}")

                num_channels = ptu.shape[3]
                # Prepare the list of channels
                items = [f"Channel {i}" for i in range(num_channels)]
                if self.shared_info.ptu_channel is None:
                    items = [f"Channel {i}" for i in range(num_channels)]
                    item, ok = QInputDialog.getItem(
                        self.main_window, "Select Channel", 
                        "Select a channel to analyse: \n(this will be applied to all the images imported)", 
                        items, 0, False)
                    self.shared_info.ptu_channel = items.index(item)
                    if not ok:
                        raise DataProcessingError("Channel selection cancelled by user.")   

                # check if file time dimentions are larger than 100
                initial_t_series = np.asarray(ptu.coords['H'], dtype=np.float32)
                if self.shared_info.ptu_time_binning == None:
                    if initial_t_series.shape[0] > 100:
                        # get options for binning time dimentions
                        final_shapes, final_time_resolution, bin_factors = self.ptu_select_time_bins(t_series=initial_t_series)
                        # combine final time dimentions and resolutions into a list of options
                        items = [
                            f"Time dimensions: {final_shape}, resolution: {resolution} ps, "
                            for resolution, final_shape in zip(final_time_resolution, final_shapes)
                        ]
                        item, ok = QInputDialog.getItem(
                            self.main_window, "Bin time dimentions", 
                            "Select a bin factor: \n(this will be applied to all the images imported)\n\n Note: binning time dimentions will result to faster analysis  \nhowever, it can reduce the accuracy of the analysis.", 
                            items, 0, False)
                        if not ok:
                            raise DataProcessingError("Channel selection cancelled by user.")   
                        self.shared_info.ptu_time_binning = bin_factors[items.index(item)]

                print("extracting data ...")
                time_slice = slice(None, None, self.shared_info.ptu_time_binning)
                full_selection = (..., time_slice)
                if self.shared_info.ptu_time_binning >2:
                    # disable temporal offset subtraction (baseline correction)
                    # large time binning (factor > 2) merges the electronic noise floor with the signal's rising edge
                    # this leads to over-subtraction and distortion of the decay curve
                    self.shared_info.config["subtract_offset"] = False 
                    # update parameters box in main window
                    self.main_window.parameters_data.update_offset(enable_offset=False)
                    

                # decode image with the specified channel and selection
                data_array = ptu.decode_image(
                    full_selection,
                    channel=self.shared_info.ptu_channel,
                    asxarray=False,
                    keepdims=False,
                    frame=-1 # sums up all time channels
                )

                data = np.transpose(data_array, (2, 1, 0))
                t_series = initial_t_series[time_slice]

                print("finished loading ptu file ...")
            
            elif file_name.endswith('.tiff') or file_name.endswith('.tif'):
                data = imread(file_name)
                data = data.squeeze()
            
                # check if x and y dimentions are equal
                if data.shape[1] != data.shape[2]:
                    if data_type == "reference":
                        # reference files with unequal space dimentions can not be anlysed, raise error
                        raise DataProcessingError(f"Reference file must have identical x and y dimensions. \nCurrent dimensions are: {data.shape[1]}x{data.shape[2]}")
                    elif data_type == "sample":
                        if sample_count == 0: 
                            show_error_message(self.main_window, "File Error", f"For best visualisation results we recommend files having identical x and y dimensions. \nCurrent dimensions are: {data.shape[1]}x{data.shape[2]}")

                if bin_width != None:
                    if bin_width == "estimate":
                        t_series = []
                    else:
                        t_series = np.asarray([i*10**(-9) * bin_width for i in range(data.shape[0])], dtype =np.float32)
                else:
                    raise UnsupportedFileFormatError()

            else:
                raise UnsupportedFileFormatError()

            # Check the dimensions of the data
            if data.ndim < 3:
                raise DataProcessingError(
                    f"Image is not raw 3D FLIM data. Image dimensions should be >= 3, but current dimensions: {data.ndim}"
                )

            return data, t_series
        
        # error messages if the files can not be loaded properly
        except UnsupportedFileFormatError as e:
            show_error_message(self.main_window, "File Error", str(e))
            raise
        except DataProcessingError as e:
            show_error_message(self.main_window, "Processing Error", str(e))
            raise
        except Exception as e:
            # tiff loading error
            error_msg = str(e)

            if "Unable to allocate" in error_msg or "incorrect StripByteCounts count" in error_msg:
                show_error_message(
                    self.main_window,
                    "File Error",
                    f"The file '{file_name}' seems too large or has corrupted TIFF structure.\n\n"
                    "Recommended fix:\n"
                    "- Open the file in ImageJ (Fiji).\n"
                    "- Re-save it as TIFF with dimensions ordered as (t, x, y).\n"
                    "- This will reduce memory usage and correct internal strip errors."
                )
            else:
                show_error_message(
                    self.main_window,
                    "Loading Error",
                    f"An unexpected error occurred while loading the file:\n{e}"
                )

            raise FileLoadingError(f"Error loading file '{file_name}': {e}")

       
    def ptu_select_time_bins(self, t_series):
        """Select time bins and resolution for binning time dimentions of large files (time dimentions > 512)"""
        n = t_series.shape[0]
        final_time_resolution = []
        final_shapes = []
        bin_factors = []
        target_final_shape = 50
        
        # Do not round the initial resolution
        initial_time_resolution = (t_series[1] - t_series[0]) * 10**12

        power = 0
        while True:
            bin_factor = 2**power
            
            # Calculate the final shape correctly
            final_shape = n // bin_factor + min(1, n % bin_factor)
            
            if final_shape < target_final_shape:
                break

            final_time_resolution.append(np.round((initial_time_resolution * bin_factor),2))
            final_shapes.append(final_shape)
            bin_factors.append(bin_factor)
            power += 1

        return final_shapes, final_time_resolution, bin_factors

        
    def load_irf(self, file_name):
        try:
            if file_name.endswith('.sdt'):
                sdt_file = sdt.SdtFile(file_name)
                data = np.moveaxis(sdt_file.data[0], -1, 0).astype(np.float32)
                data = np.squeeze(data)
                t_series = sdt_file.times[0].astype(np.float32)
                
                # Check if the data is one-dimensional
                if data.ndim != 1:
                    raise DataProcessingError(f"IRF data must be one-dimensional. Current dimensions: {data.shape}")
                
                # Reshape the data to (data.shape[0], 1, 1)
                data = data.reshape((data.shape[0], 1, 1)).astype(np.float32)

            elif file_name.endswith('.csv'):
                # Load the CSV file
                irf = np.genfromtxt(file_name, delimiter=',', skip_header=0).T

                # Check the number of columns
                num_columns = irf.shape[0]
                if num_columns != 2:
                        raise DataProcessingError("Please provide a file with only 2 columns")

                # Extract the IRF data from the selected column
                data = irf[1]
                data = data.reshape((data.shape[0], 1, 1)).astype(np.float32)
                t_series = irf[0]  
            else:
                raise UnsupportedFileFormatError("Only .sdt and .csv file formats are supported for IRF data.")
            
            return data, t_series

        except UnsupportedFileFormatError as e:
            show_error_message(self.main_window, "File Error", str(e))
            raise
        except DataProcessingError as e:
            show_error_message(self.main_window, "Processing Error", str(e))
            raise
        except Exception as e:
            show_error_message(self.main_window, "Loading Error", f"An unexpected error occurred while loading the file: {e}")
            raise FileLoadingError(f"Error loading file '{file_name}': {e}")

    
    def mask_data(self, masks_dir, file_name, data):
        """Mask data based on manual masks provided"""
        try:
            im = Image.open(os.path.join(masks_dir, file_name.split('.')[0] + ' segmentation.tif'))
            mask_arr = np.array(im, dtype=np.float32)
            # Create a masked version of the data
            masked_data = np.where(mask_arr == 0, np.zeros_like(data), data)
            return masked_data, mask_arr
        except Exception as e:
            show_error_message(self.main_window, "Masking Error", f"Error masking data for file '{file_name}': {e}")
            raise MaskingError(f"Error masking data for file '{file_name}': {e}")
        

    def calc_w(self):
        """ Calculate w (angular frequeny) """
        freq= float(self.shared_info.config["frequency"])*1e6
        w = 2*math.pi*freq # angular frequency
        return w
    


    def calc_Coordinates(self, data, t_series, bins, min_photons, offset_type="subtract_offset", max_photons_t=False, mode_same=False):
        """Import data, mask based on minimum photon counts per pixel threshold,
        bin data and calculate s and g coordinates """

        intensity = data.sum(0)  # sum along the time channels to reduce the matrix to 2 dimensions (x and y only), where the values of x and y are the photon counts at each pixel

        # Create intensity mask, masking out pixels with less photons than the threshold value
        masked_data = np.where(intensity < int(min_photons), 0, data)
        if max_photons_t and self.shared_info.config["max_photons"] != "None":
            masked_data = np.where(intensity > int(self.shared_info.config["max_photons"]), 0, masked_data)

        kernel = np.ones((1, bins, bins))
        if mode_same:
            binData = signal.fftconvolve(masked_data, kernel, mode='same', axes=None)
        else:
            binData = signal.fftconvolve(masked_data, kernel, mode='valid', axes=None)

        img_dim = binData.shape
        if mode_same:
            # because of binning some background pixels may have been assigned lifetime values
            # set background pixels back to zero
            binData = np.where(masked_data.sum(0) == 0, 0, binData)
        binData = np.reshape(binData, (data.shape[0], -1))  # reshape array stacking x and y dimensions

        # subtract offset of the decay curve
        if self.shared_info.config[offset_type] != "False":
            offset_fraction = float(self.shared_info.config["fraction_offset"])/100
            num_offset_bins = int(offset_fraction * binData.shape[0])
            # get the average photon counts in the first time-bins and subtract this from the rest of the time bins
            binData = binData - np.mean(binData[:num_offset_bins], axis=0)
            # set negative values to zero
            binData = binData.clip(min=0)

        binData_int = binData.sum(0)  # sum along time-channels, to get photon counts per pixel
        binData_int = np.reshape(binData_int, (-1))  # reshape to match binData dimensions

        # Calculate g = (I(t)*cos(wt))/I(t) and s= (I(t)*sin(wt))/I(t) ) coordinates for the reference data (!!! need to understand better)
        # calculates cos(wt) and sin(wt) and reconstruct matrices so that they have the same dimensions as binData
        cos = np.tile(np.cos(self.calc_w() * t_series), [binData.shape[1], 1]).T
        sin = np.tile(np.sin(self.calc_w() * t_series), [binData.shape[1], 1]).T
        # Calculate the s and g
        # background pixels have been set to zero, but these need to be included in order to visualize the lifetime maps later on in the analysis
        g = np.divide((binData * cos).sum(0), binData_int, out=np.zeros_like(binData_int), where=binData_int != 0)
        g = np.nan_to_num(g)  # replace NaN with zero, to maintain background pixels
        s = np.divide((binData * sin).sum(0), binData_int, out=np.zeros_like(binData_int), where=binData_int != 0)
        s = np.nan_to_num(s)  # replace NaN with zero, to maintain background pixels

        return g, s, img_dim, masked_data
    
    def ref_lifetimes(self, ref_g, ref_s,):
        """Correct reference sample modulation and phase lifetimes based on the expected reference lifetime value """

        # remove zeros values from arrays
        gRef_m = np.mean(ref_g[ref_g != 0])
        sRef_m = np.mean(ref_s[ref_s != 0])

        mod_exp = 1/np.sqrt(1 +((self.ref_lifetime*self.calc_w())**2))  # Expected modulation value based on expected lifetime of reference (1/sqrt(1+w^2*lifetime^2))
        phase_exp = math.atan(self.calc_w()*self.ref_lifetime) # Expected phase value based on expected lifetime of reference (tan^-1(w*lifetime))

        # Calculate the modulation and phase correction from the reference sample
        mod_Cor = mod_exp/np.sqrt((gRef_m**2)+(sRef_m**2))
        phase_Cor = phase_exp - math.atan2(sRef_m,gRef_m)

        return mod_Cor, phase_Cor

    def ref_correction(self):
        '''Load reference file and calculate modulation and phase correction'''
        print("reference analysis")

        # load sdt reference file and time data
        ref_data, t_series, bins_ref = self.shared_info.ref_files_dict[self.ref_filename].values()

        t_series = np.asarray(t_series)
        
        # calculate reference g and s coordinates
        ref_g, ref_s, _, _ = self.calc_Coordinates( data=ref_data, t_series=t_series, bins =bins_ref, min_photons=0,
                                                   offset_type="subtract_offset", max_photons_t = False, mode_same = False)
        # extract corrected modulation and phase correction from the reference sample
        M_ref, phi_ref = self.ref_lifetimes(ref_g, ref_s)
        return M_ref, phi_ref

    def data_lifetimes(self, g_data, s_data, M_Cor, phi_Cor):
        """ Calculate corrected g and s coordinates and modulation and phase lifetimes of the data using the corrected reference lifetimes """

        # correct g and s coordinates based on reference lifetime
        G_dd = (g_data*np.cos(phi_Cor) - s_data*np.sin(phi_Cor))*M_Cor
        S_dd = (g_data*np.sin(phi_Cor) + s_data*np.cos(phi_Cor))*M_Cor

        #Phase lifetime check
        phase_lifetime=self.calc_w()**(-1)*np.divide(S_dd, G_dd, out=np.zeros_like(G_dd), where=G_dd!=0)

        #Mod lifetime check
        phi=np.arctan(np.divide(S_dd, G_dd, out=np.zeros_like(G_dd), where=G_dd!=0))
        M=G_dd/np.cos(phi)

        # ignore zero values
        with np.errstate(invalid='ignore'):
            mod_lifetime = np.sqrt(np.maximum(np.divide(1, M, out=np.zeros_like(M), where=M!=0)**2 - 1, 0)) / self.calc_w()

        return G_dd, S_dd, mod_lifetime, phase_lifetime
    
            

    # --- Back end scripts --- #
    def get_bins(self):
        ''' Get number of bins from config file '''
        if self.shared_info.config["bins"] == "None":
            data_bins = 1
        elif self.shared_info.config["bins"] == "3x3":
            data_bins = 3
        elif self.shared_info.config["bins"] == "7x7":
            data_bins = 7
        elif self.shared_info.config["bins"] == "9x9":
            data_bins = 9
        elif self.shared_info.config["bins"] == "12x12":
            data_bins = 12
        
        return data_bins

    def lifetime_parameters(self, filename, M_ref, phi_ref):
        '''Load sample files, apply masks and calculate coordinates'''
        raw_data= self.shared_info.raw_data_dict[filename]['data']
        t_series= self.shared_info.raw_data_dict[filename]['t_series']
        condition= self.shared_info.raw_data_dict[filename]['condition']
        mask_data= self.shared_info.raw_data_dict[filename]['masked_data']

        t_series = np.asarray(t_series)

        if t_series.size == 0:  # Check if t_series is empty
            freq= float(self.shared_info.config["frequency"])*1e6
            t_resolution = 1 / ( freq* raw_data.shape[0])
            t_series = np.asarray([i * t_resolution for i in range(raw_data.shape[0])], dtype =np.float32)
            self.shared_info.raw_data_dict[filename]['t_series'] = t_series
            print("bind width estimated as:", t_resolution*10**9, "ns")
  
        # analyse manually masked data if availabe
        if mask_data is not None:
            data = mask_data
        else:
            data = raw_data

        # calculate sample g and s coordinates
        g, s, img_shape, out_data = self.calc_Coordinates( data, t_series, bins = self.get_bins(), min_photons= self.shared_info.config["min_photons"],
                                                           offset_type="subtract_offset",max_photons_t = True, mode_same = True)
        # correct g and s coordinates & modulation and phase lifetimes based on reference sample
        g_data, s_data, M_data, phi_data  = self.data_lifetimes(g, s,  M_ref,  phi_ref)
        return  out_data, g_data, s_data, M_data, phi_data, img_shape, condition
    
    def analyse_data(self):
    
        try:
            '''Perform the analysis'''

            # Initiate dictionary
            M_ref, phi_ref = self.ref_correction()

            total_files = len(self.shared_info.raw_data_dict)
            files_exclude = 0

            # Determine the number of files to exclude
            for filename, file_info in self.shared_info.raw_data_dict.items():
                condition = file_info['condition']
                if file_info['analyse'] == 'no' or (filename in self.shared_info.results_dict and self.shared_info.results_dict[filename]['condition'] == condition) or (filename in self.shared_info.ref_files_dict.keys()):
                    files_exclude += 1

            total_files -= files_exclude

            if total_files == 0:
                # If there are no files to analyze, set progress bar to 100% and emit analysisFinished signal
                self.progressUpdated.emit(100, "")
                return

            processed_files = 0
            total_files +=1
            # Loop through files in directory
            for filename, file_info in self.shared_info.raw_data_dict.items():
                if self.should_stop:
                    return self.shared_info.results_dict  # Exit if stop flag is set
                condition = file_info['condition']
                # Check if the filename and condition are already in self.results_dict
                if filename in self.shared_info.results_dict and self.shared_info.results_dict[filename]['condition'] == condition or (filename in self.shared_info.ref_files_dict.keys()):
                    continue  # Skip this file if it is already processed

                if file_info['analyse'] == 'yes':
                    # Emit progress signal
                    processed_files += 1
                    progress_percentage = int((processed_files / total_files) * 100)
                    self.progressUpdated.emit(progress_percentage, filename)

                    # Extract the lifetime parameters for each sample
                    sample_data, g_data, s_data, M_data, phi_data, img_shape, condition = self.lifetime_parameters(filename, M_ref, phi_ref)
                    # Save coordinates and lifetimes in results dictionary
                    self.shared_info.results_dict[filename] = {
                        'sample_data': sample_data, 'g': g_data, 's': s_data, 'M': M_data,
                        'phi': phi_data, 'average': (M_data + phi_data) / 2, 'phasor_mask': None,
                        'img_shape': img_shape, 'condition': condition, 'mask': self.shared_info.raw_data_dict[filename]['mask_arr']
                    }

            
            # Save key output parameters into a pandas df format
            lifetime_means_dict = []
            for sample_name, sample_data in self.shared_info.results_dict.items():
                condition = sample_data['condition']
                for region_index, (M_value, phi_value, average_value) in enumerate(zip(
                    get_tau_roi(mask=sample_data['mask'], tau_map=sample_data['M']),
                    get_tau_roi(mask=sample_data['mask'], tau_map=sample_data['phi']),
                    get_tau_roi(mask=sample_data['mask'], tau_map=sample_data['average']))):
                    lifetime_means_dict.append({
                        'sample': sample_name,
                        'condition': condition,
                        'region': region_index + 1,  # Adjust based on your region numbering
                        'M': M_value,
                        'M_mean': round(np.asarray(sample_data['M'][sample_data['M'] >0]*1e9).mean(), 3),
                        'phi': phi_value,
                        'phi_mean': round(np.asarray(sample_data['phi'][sample_data['phi'] >0]*1e9).mean(), 3),
                        'average': average_value,
                        'average_mean': round(np.asarray(sample_data['average'][sample_data['average'] >0]*1e9).mean(), 3),
                    })

            # Convert the list of dictionaries directly into a DataFrame
            self.shared_info.df_stats = pd.DataFrame(lifetime_means_dict)

            processed_files += 1
            progress_percentage = int((processed_files / total_files) * 100)
            self.progressUpdated.emit(progress_percentage, filename)
            
            # Emit the analysis finished signal
            self.analysisFinished.emit()
            return self.shared_info.results_dict
        except Exception as e:
            show_error_message(self.main_window, "Analysis Error", f"An error occurred during data analysis: {str(e)}")

                


def get_tau_roi(mask, tau_map):
    """ Get lifetime mean for each region of interest in the manual mask"""

    # Initialize an empty list to hold the tau values for each region of interest
    tau_roi = []
    if mask is not None:
        # Identify unique regions (excluding 0 for background)
        regions = np.unique(mask[mask != 0])
        
        # Iterate over each region to extract the tau values
        for region in regions:
            # Create a boolean mask for the current region
            region_mask = (mask == region)
            
            # Flatten the mask to match the flattened tau array structure, if necessary
            region_mask_flattened = region_mask.reshape(-1)
            
            # Use the mask to select tau values for the current region
            tau_region = tau_map[region_mask_flattened]
            tau_region = tau_region[tau_region > 0]  # Filter out zero values

            # Store mean of each tau roi, rounded to 3 decimal places
            tau_roi.append(round(float(tau_region.mean()) * 1e9, 3))
    
    else:
        tau_roi.append(round(np.asarray(tau_map[tau_map >0]*1e9).mean(), 3))

    return tau_roi