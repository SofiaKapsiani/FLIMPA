<div align="center">
  <img src="https://github.com/user-attachments/assets/73dee1af-b5dc-4211-b0ce-ba623fe0bdad" alt="icon_filimpa"  width=70% height=70%>
</div>


# Project background

<p align="center">
  <strong> ** Please use our latest version </strong> 
  <a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.4">
    FLIMPA (v1.4) </a> **
</p>

**FLIMPA** is an open-source software designed for the phasor plot analysis of raw Time-Correlated Single Photon Counting (TCSPC) Fluorescence Lifetime Imaging Microscopy (FLIM) data.
<br>
To run the software, please download the executable (<a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.4" title=".exe" download>.exe</a>) file. Currently, the .exe file runs only on Windows computers.

> **FLIMPA: A Versatile Software for Fluorescence Lifetime Imaging Microscopy Phasor Analysis**, published in *Analytical Chemistry*          
> Sofia Kapsiani, Nino F Läubli, Edward N. Ward, Mona Shehata, Clemens F. Kaminski, Gabriele S. Kaminski Schierle    
> <a href="https://www.ceb-mng.org/" target="_blank">Molecular Neuroscience Group</a> and <a href="https://laser.ceb.cam.ac.uk/" target="_blank">Laser Analytics Group</a> (University of Cambridge)
> 
[[`FLIMPA (1.4)`](https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.4)] [[`paper`](https://pubs.acs.org/doi/10.1021/acs.analchem.5c00495)] [`user manual (PowerPoint)`](https://docs.google.com/presentation/d/1rq5PuOyjQz3sg_ERyIjXMgyj1betNweTIrD1v64-u7o/edit?usp=sharing)] [[`user manual (PDF)`](https://pubs.acs.org/doi/suppl/10.1021/acs.analchem.5c00495/suppl_file/ac5c00495_si_002.pdf)] [[`citation`](#bibtex-citation)]


##  Features

<div align="center">
  <img src="https://github.com/user-attachments/assets/48a6a9b8-3d79-4cb2-a910-56432db24f60" alt="flimpa_abstract_figure"  width=80% height=80%>
</div>

<br>

- Phasor plot generation and analysis
- Fluorescence lifetime and intensity map visualisation (individual per image)
- ROI selection 
- Gallery plots of fluorescence lifetime and intensity maps
- Violin plot analysis
- Table of mean fluorescence lifetime values per image


# Installation

FLIMPA can be easily run on Windows using the <a href="https://github.com/SofiaKapsiani/FLIMPA/releases/tag/v1.4" title=".exe" download>.exe</a> file. Alternatively, you can clone the GitHub repository and run the software following these steps:

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

For detailed information please refer to our online user manuals (<a href="https://docs.google.com/presentation/d/1rq5PuOyjQz3sg_ERyIjXMgyj1betNweTIrD1v64-u7o/edit?usp=sharing" target="_blank">PowerPoint</a> & <a href="https://pubs.acs.org/doi/suppl/10.1021/acs.analchem.5c00495/suppl_file/ac5c00495_si_002.pdf" target="_blank">PDF</a>).


![intro_v1 4](https://github.com/user-attachments/assets/81cd375b-d5af-4eec-931f-b3ca2f0ef38e)


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

**For more information on handling `.ptu` files, please refer to slides 5 and 6 of the <a href="https://docs.google.com/presentation/d/1rq5PuOyjQz3sg_ERyIjXMgyj1betNweTIrD1v64-u7o/edit?usp=sharing" target="_blank">online user manual</a>.**

The software can be tested using the  `.sdt` files provided in the  `sample_data` folder. These sample data were used in our publication and involve COS-7 cells stained with SiR-tubulin, treated with 40 µM of Nocodazole. Control data are also included, consisting of images of untreated cells.

There are three different options for importing the data:

-	Import raw data
-	Import raw data and assign experimental conditions (e.g treated vs untreated)
-	Import raw data with manually created masks (currently masks should be created using different software for example FLIMFit)

*Example: Importing Raw Data and Assigning Experimental Conditions*

![condition_assignment_v1 4](https://github.com/user-attachments/assets/b7576e13-c74f-40dd-b6f4-d93d88231342)


Please note that FLIMPA currently only accepts single files and does not support the analysis of time-lapse data.

## Running Phasor Plot Analysis

To run the phasor plot analysis, the following parameters need to be specified:

- `Laser Frequency` (in MHz)
- Upload a `Reference File`
- `Reference File Lifetime` (in ns)
- `Number of Time Bins` (*default*: 3x3)
- `Minimum Photon Count Threshold` (*optional*, at least 100 p.c. per pixel recommended)
- `Maximum Photon Count Threshold` (*optional*)
- `Baseline correction` (selecting `True` will remove constant DC noise from the fluorescence decay curve, improving Fourier Transform analysis)
- `% time bins (baseline corr.)` (*default*: 3.5%, percentage of the initial time bins used for baseline correction)

Warning: If the true fluorescent signal is present in the initial time bins (due to issues like excessive .ptu file time binning or microscope settings), performing `Baseline correction` correction will subtract signal along with the noise, leading to inaccurate results. To ensure proper use of `Baseline correction` and `% time bins (baseline corr.)` please refer to slide 11 of our <a href="https://docs.google.com/presentation/d/1rq5PuOyjQz3sg_ERyIjXMgyj1betNweTIrD1v64-u7o/edit?usp=sharing" target="_blank">online user manual</a>. 

*Example: Importing Reference file, setting minimum photon counts threshold and running the analysis*


![reference_upload_v1 4](https://github.com/user-attachments/assets/205d32d9-488d-4cbb-94b9-ccad854419be)


## Phasor Plot Visualisation 
FLIMPA enables to visualisation of phasor plots from single images and combined plots from multiple samples.  Additionally three different phasor visualisation options: `scatter` plots, `histograms` and `contour` maps.

![plot_options_v1 4](https://github.com/user-attachments/assets/b51e1d2f-f068-4ec5-bab9-1d6389661ea6)


## Saving Data

FLIMPA also allows users to export all generated data. This includes:

- **Lifetime and Intensity Maps:** Exported as `.png` and raw `.tif` files.
- **Gallery Visualisations:** Lifetime and intensity galleries exported as `.png` files.
- **Phasor Plots and Violin Plots:** Saved with a transparent background.
- **Statistical Data:** A `.csv` file containing the mean fluorescence lifetime per image can be exported for further statistical analysis.


<img width="1644" height="951" alt="save_data-42" src="https://github.com/user-attachments/assets/17e8f17e-5780-4461-9d7c-c76dc6100ff9" />

# Citation

*If you found **FLIMPA** helpful for your data analysis, please consider citing our work!* 😊
<a name="bibtex-citation"></a>
```
@article{kapsiani2025flimpa,
  title={FLIMPA: A versatile software for Fluorescence Lifetime Imaging Microscopy Phasor Analysis},
  author={Kapsiani, Sofia and Läubli, Nino F and Ward, Edward N and Shehata, Mona and Kaminski, Clemens F and Kaminski Schierle, Gabriele S},
  journal={Analytical Chemistry},
  year={2025},
  publisher={ACS Publications}
}
```
