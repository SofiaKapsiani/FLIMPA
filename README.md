<div align="center">
  <img src="https://github.com/user-attachments/assets/5ec8fe13-b097-4274-88fb-25c60c28637c" alt="icon_filimpa" width="550" height="300">
</div>

# Project background

**FLIMPA** is an open-source software designed for the phasor plot analysis of raw Time-Correlated Single Photon Counting (TCSPC) Fluorescence Lifetime Imaging Microscopy (FLIM) data.
Developed in Python, it offers an intuitive graphical user interface (GUI) for the comprehensive analysis and visualisation of FLIM data.

To run the software, you can download the executable (.exe) file here.

> **FLIMPA: An open-source software for Fluorescence Lifetime Imaging Microscopy Phasor plot Analysis**          
> Sofia Kapsiani     
> <a href="https://www.ceb-mng.org/" target="_blank">Molecular Neuroscience Group, University of Cambridge</a>


##  Features

- Phasor plot generation and analysis
- Table of mean fluorescence lifetime value per image
- ROI selection 
- Gallery plotting of fluorescence lifetime and intensity maps
- Violin plot visualisation

  ![intro_gif](https://github.com/user-attachments/assets/29e7e1b6-820c-4dcf-a1ac-674f7d70acbf)


# Installation

The software can be easily run on Windows using the .exe file. Alternatively, you can clone the GitHub repository and run the software following these steps:

1. **Download the repository:**
    ```bash
    git clone https://github.com/your-username/phasor-plot-analysis.git
    cd phasor-plot-analysis
    ```

2. **Create and activate a virtual environment:**
    ```bash
    conda create --name f_env python=3.11 -y
    conda activate f_env
    ```

3. **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the software:**
    ```bash
    python main.py
    ```

# Usage

## Importing Data

FLIMPA currently accepts  `.std`,  `.ptu`, and  `.tif` file formats for phasor plot analysis. To ensure accurate results, a reference file with a known lifetime (such as a sample of Rhodamine 6G or Erythrosin B) is required to correct for instrumental errors.

The software can be tested using the  `.std` files provided in the  `sample_data` folder. These sample data were used in our publication and involve COS-7 cells stained with SiR-tubulin, treated with 40 µM of Nocodazole. Control data are also included, consisting of images of untreated cells.

There are three different options for importing the data:

-	Import raw data
-	Import raw data and assign experimental conditions (e.g treated vs untreated)
-	Import raw data with manually created masks (currently masks should be created using different software for example FLIMFit)

*Example: Importing Raw Data and Assigning Experimental Conditions*

  ![import](https://github.com/user-attachments/assets/f7042764-3796-4ca1-ad2f-a277d272c078)


Please note that FLIMPA currently only accepts single files and does not support the analysis of time-lapse data.
