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
        self.phasor_settings = {  # Dictionary to store phasor plot settings
            "plot_type": "individual",
            "scatter_type": "scatter"
        }

    def load_config(self):
        """
        Load the configuration from the embedded YAML content.
        """
        # Embedded YAML content as a string
        config_content = """
        frequency: 40 # frequency in MHz
        min_photons: 200 # threshold for minimum photon counts for the FLIM image
        max_photons: 1000000 # threshold for maximum photon counts for the FLIM image

        bins: "3x3" # binning value for data. Can only be any odd number or 256.

        ref_file: "None"
        ref_lifetime: 4

        subtract_offset: True # set True to calculate the intensity offset (baseline)
        # of FLIM data according to the first "num_offset" data points
        # of a decay curve, and subtract this number from all time bins in
        # the decay curve (the negative values in the results will be changed to 0).
        subtract_offsetRef: True # DEFAULT: choose True to compensate intensity offset for reference data
        num_offset: 9 
        mask_samples: False # choose False to mask by intensity or 1 for import of .tif mask 

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


