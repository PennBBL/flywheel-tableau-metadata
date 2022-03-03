# fw_tabulate_scans.py
#
# Query flywheel to gather csv of available nifti files and associated 
# metadata across a given project.
#
# Author:   Katja Zoner
# Updated:  08/17/2021      

import os
import flywheel
import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import date, datetime


def getProject(projectLabel):
    
    # Get client
    fw = flywheel.Client()
    assert fw, "Your Flywheel CLI credentials aren't set!"

    # Get project object
    project = fw.projects.find_first('label="{}"'.format(projectLabel))
    assert project, f"Project {projectLabel} not found!"
    
    return project


def queryFlywheel(project):
    """ 
    Query Flywheel to create a dictionary of nifti files available in project.
    
    Arguments:
        project - Flywheel project object
        
    Returns: info dict, where:
        info[fileId] = [subId, sesId, acqLabel, filename, seriesNum, timestamp]
    """

    # Create info dict with entries for each subject.
    info = dict()

    # Loop through subjects in project
    for sub in tqdm(project.subjects(), desc=f"Subjects processed", unit="subject", position=0):

        count=0
        for ses in sub.sessions():
            for acq in ses.acquisitions():
                count+=1
        
        # Set up internal loop progress bar for sessions/acquisitions/files
        with tqdm(total=count, desc=f"subject {sub.label}", unit="file", leave=False) as pbar:
            
            # Loop through sessions in subject
            for ses in sub.sessions():
                ses = ses.reload()

                # Loop through acquisitions in session
                for acq in ses.acquisitions():
                    acq = acq.reload()

                    # Loop through files in acquisition
                    for f in acq.files:
                        
                        # Skip over non-nifti files
                        if f.type != 'nifti':
                            continue

                        # Get Flywheel fileId to use as unique identifier
                        fileId = f.id

                        # Try to get timestamp (sometimes DateTime field isn't present.) 
                        try:
                            timestamp = f.info['AcquisitionDateTime']
                        except KeyError:
                            try:
                                timestamp = f.info['AcquisitionDate']
                            # Set to None if field isn't present
                            except:
                                timestamp = pd.NaT
                        
                        # Try to get series number (sometimes field isn't present.) 
                        try:
                            seriesNum = f.info['SeriesNumber']
                        # Set to None if field isn't present
                        except:
                            seriesNum = np.NaN      

                        # Add the folowing metadata to study info dict:
                        # fileID: [subId, sesId, acqLabel, fileName, seriesNum, timestamp]
                        info[fileId] = [sub.label, ses.label, acq.label, f.name, seriesNum, timestamp]

                    # Update progress bar upon completion of each acq
                    pbar.update(1)

    # Return project info dict
    return info

def main():

    ###############################################################################
    ############################   Parse arguments     ############################

    parser = argparse.ArgumentParser(
        description='Query Flywheel to generate csv of available nifti files and associated metadata across a given project.')

    parser.add_argument('-p', '--project', required=True,
                        help='project label on Flywheel')

    parser.add_argument('-o', '--output',
                        help='name of output file',
                        default=f'flywheel_scans_{date.today()}.csv')

    parser.add_argument('-d', '--dest',
                        help='path to output directory',
                        default='')

    args = parser.parse_args()
    
    ###############################################################################

    # Use FW client to get project object
    project = getProject(args.project)

    # Build info dict containing metadata on all scans in FW project
    print(f"Gathering metadata from Flywheel project {project.label}...")
    info = queryFlywheel(project)

    # Convert info dict to pandas dataframe and rename columns
    df = pd.DataFrame.from_dict(info, orient='index').reset_index()
    df.columns=['FlywheelFileId','SubjectId', 'SessionId', 'AcqLabel', 'Filename', 'SeriesNumber','Timestamp']
    
    # Export dataframe to csv
    os.makedirs(args.dest, exist_ok = True)
    fullpath = os.path.join(args.dest, args.output)
    df.to_csv(fullpath, index=False)

if __name__== "__main__":
    main()
