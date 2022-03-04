# flywheel-tableau-metadata
This repo is for scripts relating to pulling scan metadata from Flywheel and uploading to Tableau.

## `fw_tabulate_scans.py` 
Queries Flywheel to generate a csv of nifti files and associated metadata across a given project. 

### Usage:

### To run on bblrepo1:
1. Login to bblrepo1
2. `module load python/3.9 DEV/fw-16.2.0`
3. Make sure Flywheel CLI credentials are set:
   - To check login status: `fw status`
   - To login: `fw login <API KEY>`
4. Navigate to this repo on bblrepo1: `cd /data/secure/lab/flywheel-tableau-metadata`
5. Run `python get_flywheel_metadata.py -p <PROJECT LABEL>`
   - Add -o <path> flag to specify different output dir than CWD
   - Ad -d <date> flag to only query for scans created/uploaded on or after the given date.
  
  
  ### Examples:
  To grab all scans from the GRMPY project:
  ```
  python fw_tabulate_scans.py -p GRMPY_822831 -o ./data
  ```
  To grab all scans created on or after 11/1/2020 from the GRMPY project:
  ```
  python fw_tabulate_scans.py -p GRMPY_822831 -o ./data -t 2020-11-01  
  ```
  


