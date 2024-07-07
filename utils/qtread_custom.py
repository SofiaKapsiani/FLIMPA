from PySide6.QtCore import QThread, Signal

class AnalysisThread(QThread):
    progressUpdated = Signal(int, str)
    analysisFinished = Signal(dict)
    
    def __init__(self, lifetime_data, parent=None):
        super().__init__(parent)
        self.lifetime_data = lifetime_data

    def run(self):
        self.lifetime_data.progressUpdated.connect(self.progressUpdated)
        results_dict = self.lifetime_data.analyse_data()
        self.analysisFinished.emit(results_dict)

    def stop(self):
        self.lifetime_data.should_stop = True
        self.quit()
        self.wait()


    
