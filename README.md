<div align="center">
  <img src="https://github.com/user-attachments/assets/5ec8fe13-b097-4274-88fb-25c60c28637c" alt="icon_filimpa" width="550" height="300">
</div>


# Project background

<p align="center">
  <strong> ** Please use our latest version </strong> 
  <a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.3">
    FLIMPA (v1.3) </a> **
</p>

**FLIMPA** is an open-source software designed for the phasor plot analysis of raw Time-Correlated Single Photon Counting (TCSPC) Fluorescence Lifetime Imaging Microscopy (FLIM) data.
Developed in Python, it offers an intuitive graphical user interface (GUI) for the analysis and visualisation of FLIM data.

To run the software, please download the executable (<a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.3" title=".exe" download>.exe</a>) file. Currently, the .exe file runs only on Windows computers.

> **FLIMPA: An accessible software for Fluorescence Lifetime Imaging Microscopy Phasor Analysis**          
> Sofia Kapsiani, Nino F Läubli, Edward N. Ward, Mona Shehata, Clemens F. Kaminski, Gabriele S. Kaminski Schierle    
> <a href="https://www.ceb-mng.org/" target="_blank">Molecular Neuroscience Group</a> and <a href="https://laser.ceb.cam.ac.uk/" target="_blank">Laser Analytics Group</a> (University of Cambridge)
> 
[[`FLIMPA (1.2)`](https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.3)] [[`user manual`](https://docs.google.com/presentation/d/1QhVxaMxtbJyqJu0Qqq47dlyh1Fq_08x5p-t_djGUT-Y/edit?usp=sharing)] [[`bioRxiv`](https://www.biorxiv.org/content/10.1101/2024.09.13.612802v1)]  [[`bibtex`](#bibtex-citation)]


##  Features

- Phasor plot generation and analysis
- Table of mean fluorescence lifetime values per image
- ROI selection 
- Gallery plotting of fluorescence lifetime and intensity maps
- Violin plot visualisation


  ![overview](https://github.com/user-attachments/assets/60722b16-39ea-4dcd-b472-00ec8990f616)



# Installation

FLIMPA can be easily run on Windows using the <a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.3" title=".exe" download>.exe</a> file. Alternatively, you can clone the GitHub repository and run the software following these steps:

1. **Download the repository**
    ```bash
    git clone https://github.com/SofiaKapsiani/FLIMPA.git
    cd FLIMPA
    ```

2. **Create and activate a virtual environment**
    ```bash
    conda create --name flimpa_env python=3.11 -y
    conda activate flimpa_env
    ```

3. **Install the required packages**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the software**
    ```bash
    python main.py
    ```

# Usage

For detailed information please refer to our <a href="https://docs.google.com/presentation/d/1QhVxaMxtbJyqJu0Qqq47dlyh1Fq_08x5p-t_djGUT-Y/edit?usp=sharing" target="_blank">online user manual</a>.

## Importing Data

FLIMPA currently accepts  `.sdt`,  `.ptu`, and  `.tif` file formats for phasor plot analysis. To ensure accurate results, a reference file with a known lifetime (such as a sample of Rhodamine 6G or Erythrosin B) is required to correct for instrumental errors.

For best results, we recommend using files with spatial dimensions up to 512 × 512. 
Files with spatial dimensions exceeding 1000 × 1000 can be analysed but may cause memory allocation errors in Python and significantly reduce analysis speed.

> *Importing `.tif` files*<br>
>
> Please ensure that your `.tif` data is in the format `(time, x, y)`. When loading your data, you will be prompted to enter the ```bin width``` (in nanoseconds), which is essential for accurate analysis.
>
> If the exact bin width is unknown, FLIMPA provides an **estimate** option, calculated as:<br>
> ```(1 / (Instrument Frequency (in Hz) * Number of Bins)) * 10^9 ```<br>
> However, this estimate may be inaccurate depending on your data acquisition settings.


The software can be tested using the  `.sdt` files provided in the  `sample_data` folder. These sample data were used in our publication and involve COS-7 cells stained with SiR-tubulin, treated with 40 µM of Nocodazole. Control data are also included, consisting of images of untreated cells.

There are three different options for importing the data:

-	Import raw data
-	Import raw data and assign experimental conditions (e.g treated vs untreated)
-	Import raw data with manually created masks (currently masks should be created using different software for example FLIMFit)

*Example: Importing Raw Data and Assigning Experimental Conditions*

  ![import](https://github.com/user-attachments/assets/f7042764-3796-4ca1-ad2f-a277d272c078)


Please note that FLIMPA currently only accepts single files and does not support the analysis of time-lapse data.

## Running Phasor Plot Analysis

To run the phasor plot analysis, the following parameters need to be specified:

- `Laser Frequency` (in MHz)
- Upload a `Reference File`
- `Reference File Lifetime` (in ns)
- `Number of Time Bins` (*default*: 3x3)
- `Minimum Photon Count Threshold` (*optional*, at least 100 p.c. per pixel recommended)
- `Maximum Photon Count Threshold` (*optional*)

Note: The reference file is shown only to confirm it was loaded correctly and will not be analyzed. Please do not load sample data with the same name as the reference file.

*Example: Importing Reference file, setting minimum photon counts threshold and running the analysis*

![loading_ref](https://github.com/user-attachments/assets/4436669d-2a9b-48b6-8c64-c5b7a4d1bf50)


## Phasor Plot Visualisation 
FLIMPA enables to visualisation of phasor plots from single images and combined plots from multiple samples.  Additionally three different phasor visualisation options: `scatter` plots, `histograms` and `contour` maps.

![scatter](https://github.com/user-attachments/assets/4f108cd6-a10c-4551-bd65-6d9abb356efd)

## Saving Data

FLIMPA also allows users to export all generated data. This includes:

- **Lifetime and Intensity Maps:** Exported as `.png` and raw `.tif` files.
- **Gallery Visualisations:** Lifetime and intensity galleries exported as `.png` files.
- **Phasor Plots and Violin Plots:** Saved with a transparent background.
- **Statistical Data:** A `.csv` file containing the mean fluorescence lifetime per image can be exported for further statistical analysis.


![save-73](https://github.com/user-attachments/assets/7747372c-e5de-40ae-8f2b-1ba320f0418a)


# Citation

*If you found **FLIMPA** helpful for your data analysis, please consider citing our work!* 😊
<a name="bibtex-citation"></a>
```
@article{Kapsiani2024.09.13.612802,
	author = {Kapsiani, Sofia and L{\"a}ubli, Nino F and Ward, Edward N and Shehata, Mona and Kaminski, Clemens F and Kaminski Schierle, Gabriele S},
	title = {FLIMPA: A versatile software for Fluorescence Lifetime Imaging Microscopy Phasor Analysis},
	elocation-id = {2024.09.13.612802},
	year = {2024},
	doi = {10.1101/2024.09.13.612802},
	URL = {https://www.biorxiv.org/content/early/2024/09/19/2024.09.13.612802},
	eprint = {https://www.biorxiv.org/content/early/2024/09/19/2024.09.13.612802.full.pdf},
	journal = {bioRxiv}
}
```
