# fw_tabulate_scans.py
#
# Query flywheel to gather csv of available nifti files and associated 
# metadata across a given project.
#
# Author:   Katja Zoner
# Updated:  08/17/2021      

import os
import pytz
import flywheel
import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import date, time, datetime


def get_project(projectLabel):
    '''Given project label return Flywheel project object.'''

    # Get client
    fw = flywheel.Client()
    assert fw, "Your Flywheel CLI credentials aren't set!"

    # Get project object
    project = fw.projects.find_first('label="{}"'.format(projectLabel))
    assert project, f"Project {projectLabel} not found!"
    
    return project


def get_file_data(f, acq):
    '''Given a Flywheel file object, extract and return fileId, seriesNum, and timestamp.'''

    # Get Flywheel fileId to use as unique identifier
    fileId = f.id

    # Try to get series number (sometimes field isn't present.) 
    try:
        seriesNum = f.info['SeriesNumber']
    # Set to None if field isn't present
    except:
        seriesNum = np.NaN 
        
    # Try to get timestamp (sometimes DateTime field isn't present.) 
    try:
        timestamp = f.info['AcquisitionDateTime']
    except KeyError:
        try: 
            timestamp = datetime.combine(acq.timestamp.date(), time.fromisoformat(f.info['AcquisitionTime']))
        except:
            try:
                timestamp = f.info['AcquisitionDate']
            # Set to None if field isn't present
            except:
                timestamp = pd.NaT
    
    return fileId, seriesNum, timestamp


def get_all_metadata_for(project):
    """ 
    Query Flywheel to create a dictionary of all nifti files available in project.
    
    Arguments:
        project - Flywheel project object
        
    Returns: info dict, where:
        info[fileId] = [subId, sesId, acqLabel, filename, seriesNum, timestamp, created]
    """

    # Create info dict with entries for each nifti.
    info = {}

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

                    # Loop through nifti files in acquisition
                    for f in acq.files:
                        if f.type == 'nifti':
   
                            # Get other metadata fields from file
                            fileId, seriesNum, timestamp = get_file_data(f, acq)
                            
                            # Add the folowing metadata to study info dict: fileID --> [subId, sesId, acqLabel, fileName, seriesNum, timestamp]
                            info[fileId] = [sub.label, ses.label, acq.label, f.name, seriesNum, timestamp, f.created.replace(tzinfo=None)]

                    # Update progress bar upon completion of each acq
                    pbar.update(1)

    # Return project info dict
    return info


def get_recent_metadata_for(project, date):
    """ 
    Query Flywheel to create a dictionary of nifti files created/updated on or after given date in project.
    
    Arguments:
        project - Flywheel project object
        date    - datetime.date object
         
    Returns: info dict, where:
        info[fileId] = [subId, sesId, acqLabel, filename, seriesNum, timestamp, created]
    """

    # Get client
    fw = flywheel.Client()

    # Query Flywheel for acquisitions from project containing nifti's created on or after min_date
    query = f'project.label == {project.label} AND ' \
                    f'file.type == nifti AND ' \
                    f'file.created >= {date}'

    results = fw.search({'structured_query': query, 'return_type': 'acquisition'}, size=10000)
    assert results, f"No nifti files created on or after {date} were found in {project.label}! Exiting."

    # Create info dict with entries for each nifti.
    info = {}

    # Loop through each result, get subid and sesid related to acquisition, and extract metadata from relevant files.
    for res in tqdm(results, desc=f"Acquisitions processed", unit="acquisitions", position=0):

        # Get subject and session label
        subid = res.subject.code
        sesid = res.session.label

        # Get acquisition object
        acqid = res.acquisition.id
        acq = fw.get_acquisition(acqid)
        acq.reload()

        # Loop through relevant files in acquisition
        for f in acq.files:
            if f.type=='nifti' and f.created >= datetime(date.year, date.month, date.day, tzinfo=pytz.UTC):
                
                # Get other metadata fields from file
                fileId, seriesNum, timestamp = get_file_data(f, acq)
               
                # Add the folowing metadata to study info dict: fileID --> [subId, sesId, acqLabel, fileName, seriesNum, timestamp]
                info[fileId] = [subid, sesid, acq.label, f.name, seriesNum, timestamp, f.created.replace(tzinfo=None)]
    
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
                        help='path to output directory',
                        default='')

    parser.add_argument('-t', '--date',
                        help='isoformat date "YYYY-MM-DD" -- if supplied, Flywheel is queried only for scans updated on or after given date',
                        default='')

    args = parser.parse_args()
    
    ###############################################################################

    # Use FW client to get project object
    project = get_project(args.project)

    # If date argument was supplied, query Flywheel project for scans created/updated on or after date
    if args.date:

        # Try to cast date argument to datetime.date type
        min_date = datetime.fromisoformat(args.date).date()

        # Build info dict containing metadata on all scans in FW project
        print(f"Gathering metadata from Flywheel project '{project.label}' for scans created on or after '{min_date}'...")
        info = get_recent_metadata_for(project, min_date)      
    
    # Else query for all scans in Flywheel project.
    else:
        
        min_date = None

        # Build info dict containing metadata on all scans in FW project
        print(f"Gathering all scan metadata from Flywheel project '{project.label}'...")
        info = get_all_metadata_for(project)

    # Convert info dict to pandas dataframe and rename columns
    df = pd.DataFrame.from_dict(info, orient='index').reset_index()
    df.columns=['FlywheelFileId','SubjectId', 'SessionId', 'AcqLabel', 'Filename', 'SeriesNumber','Timestamp', 'Created']
    
    # Export dataframe to csv
    filename = f"FlywheelDump_{project.label}_{min_date if min_date else 'all_scans'}_to_{date.today()}.csv"
    fullpath = os.path.join(args.output, filename)
    os.makedirs(args.output, exist_ok = True)
    df.to_csv(fullpath, index=False)

if __name__== "__main__":
    main()
q