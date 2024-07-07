from utils.shared_data import SharedData

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

        