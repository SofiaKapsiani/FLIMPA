import yaml

class SharedData:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern implementation: ensures only one instance of SharedData exists.
        """
        if not cls._instance:
            cls._instance = super(SharedData, cls).__new__(cls, *args, **kwargs)
            cls._instance.init()
        return cls._instance

    def init(self):
        """
        Initialize the instance attributes, including loading the configuration.
        """
        self.ref_files_dict = {}  # Dictionary to store reference files
        self.config = self.load_config()  # Load configuration from embedded YAML content
        self.raw_data_dict = {}  # Dictionary to store raw data
        self.intensity_img_dict = {}  # Dictionary to store intensity images
        self.results_dict = {}  # Dictionary to store results
        self.df_stats = {}  # Dictionary to store statistical data
        self.ptu_channel = {}  # Dictionary to store PTU file channels
        self.ptu_time_binning = {}  # Dictionary to store PTU time binning selection
        self.phasor_settings = {  # Dictionary to store phasor plot settings
            "plot_type": "individual",
            "scatter_type": "scatter",
            "tau_labels": True,
        }
        self.last_active_tab= {} # Dictionary to store the last tab selected in the GUI

    def load_config(self):
        """
        Load the configuration from the embedded YAML content.
        """
        # Embedded YAML content as a string
        config_content = """
        frequency: 40 # frequency in MHz
        min_photons: 0 # threshold for minimum photon counts for the FLIM image
        max_photons: 1000000 # threshold for maximum photon counts for the FLIM image

        bins: "3x3" # binning value for data. Can only be any odd number or 256.

        ref_file: "None"
        ref_lifetime: 4

        subtract_offset: True # set True to calculate the intensity offset (baseline)
        # assumption that first time bins contain only the background signal 
        # calculate average of first time bins and substract them from the rest of the time points
        # as data from different sources may have different number of time bins, provide a fraction 
        #subtract_offsetRef: True # DEFAULT: choose True to compensate intensity offset for reference data
        fraction_offset: 3.5 # assumption that 3.5 precent of the first time bins are background signal
        mask_samples: False # choose False to mask by intensity or True for import of .tif mask 

        vmin_int: 0
        vmax_int: 1000

        selected_file: "None"

        lifetime_vmin: 0
        lifetime_vmax: 10
        lifetime_map: "average"
        lifetime_itegrate: "False"

        tau_violin: "average"
        """

        # Load and parse the YAML content into a Python dictionary
        return yaml.safe_load(config_content)


