from PySide6.QtWidgets import QMessageBox

class UnsupportedFileFormatError(Exception):
    """Exception raised for unsupported file formats."""
    def __init__(self, message="Only .sdt, .ptu or .tif file formats are currently supported."):
        self.message = message
        super().__init__(self.message)

class FileLoadingError(Exception):
    """Exception raised for errors that occur during file loading."""
    def __init__(self, message="An error occurred while loading the file."):
        self.message = message
        super().__init__(self.message)

class DataProcessingError(Exception):
    """Exception raised for errors that occur during data processing."""
    def __init__(self, message="An error occurred during data processing."):
        self.message = message
        super().__init__(self.message)

class MaskingError(Exception):
    """Exception raised for errors that occur during data masking."""
    def __init__(self, message="Only .tif files are supported for masking. Please make sure that the file name is 'file_name segmentation.tif'"):
        self.message = message
        super().__init__(self.message)

def show_error_message(parent, title, message):
    """Function to display an error message."""
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()