import argparse
import time
import glob
import uproot
from dask.distributed import Client, LocalCluster
from dask_jobqueue.htcondor import HTCondorCluster
import dsPhiPi_analyser as analysis_control
import tau3mu_analyser as analysis_signal
import pandas as pd
import numpy as np

import os
import logging

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)


def run_analysis(year: str, era: str, analysis_type: str, output_dir: str, n_workers: int, isMC: bool, csv_path: str = "file_paths.csv"):
    """
    Runs the analysis by automatically detecting available streams from the CSV manifest.
    """
    print(f"Analysis type: {analysis_type}")
    print(f"Dataset name: {output_dir}")
    print(f"Year: {year} | Era: {era}")

    # 1. Load the file manifest
    try:
        df_all = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: The manifest file '{csv_path}' was not found.")
        return

    # 2. Extract unique streams from the CSV for the selected year and era
    # We filter first to ensure we only get streams that actually have data for this year/era
    initial_mask = (df_all['year'].astype(str) == str(year)) & (df_all['era'] == era)
    available_streams = np.unique(df_all[initial_mask]['stream'])

    if len(available_streams) == 0:
        print(f"No data found in manifest for Year {year} and Era {era}.")
        return

    print(f"Detected streams in CSV: {available_streams}")

    # 3. Loop over the detected streams
    for stream in available_streams:
        print(f"\n" + "="*60)
        print(f"STARTING PROCESSING FOR STREAM: {stream}")
        print("="*60)

        # 4. Filter data for the specific stream
        if isMC:
            base_fileout = f"{analysis_type}_{output_dir}_isMC"
        else:
            mask = (
                (df_all['year'].astype(str) == str(year)) & 
                (df_all['era'] == era) & 
                (df_all['stream'] == int(stream))
            )
            base_fileout = f"{analysis_type}_{output_dir}_{year}_{era}_{stream}"

        df_filtered = df_all[mask]

        # 5. Iterate over the groups for this specific stream
        # Using .groupby('group') handles the smart division automatically
        for group_id, group_data in df_filtered.groupby('group'):
            num_files = len(group_data)
            print(f"\n--- Stream {stream} | Group: {group_id} ({num_files} files) ---")
            
            filelist = group_data['path'].tolist()
            files = [f"{f}:Events" for f in filelist]
            
            current_fileout = f"{base_fileout}_group{group_id}"

            # 6. Initialize Dask processing
            try:
                events = uproot.dask(files, open_files=False)
                events = events.repartition(npartitions=n_workers).persist()
                print(f"Dask initialized with {n_workers} partitions.")

                # 7. Execute specific Analysis modules
                if analysis_type == "control":
                    print(f"Running DsPhiPi analysis -> {current_fileout}")
                    analysis_control.Analysis_DsPhiPi(events, output_dir, current_fileout, era, isMC)
                elif analysis_type == "signal":
                    print(f"Running Tau3Mu analysis -> {current_fileout}")
                    analysis_signal.Analysis_Tau3Mu(events, output_dir, current_fileout, era, isMC)
                    
                else:
                    print(f"Error: Unsupported analysis type '{analysis_type}'.")
                    return 

            except Exception as e:
                print(f"An error occurred in Stream {stream}, Group {group_id}: {e}")
                continue

    print("\n" + "="*60)
    print("Full analysis pipeline finished for all detected streams.")
    print("="*60)


def main():
    start = time.time()
    parser = argparse.ArgumentParser(
        prog='Analysis runner for signal channel (tau → 3μ) or control channel (Ds→ϕπ)',
        description='Run analysis on tau → 3μ/ Ds → ϕπ',
        epilog='Example usage: python3 run_analysis_dask_dsPhiPi.py -e B -t control --isMC -o {} -w 70'
    )
    parser.add_argument('-y', '--year', required=True, help='Data-taking year (e.g., 2024, 2025, etc.)')
    parser.add_argument('-e', '--era', required=True, help='Data-taking era (e.g., B, C, D, E-v1, etc.)')
    parser.add_argument('-t', '--type', required=True, choices=['control', 'signal'], help='Type of analysis')
    parser.add_argument('--isMC', action='store_true', help='Analyze Monte Carlo if present, otherwise analyze data')
    parser.add_argument('-o', '--output', required=True, help='Prefix for the output directory or file')
    parser.add_argument('-w', '--n_workers', required=True, type=int, help='Number of Dask workers to use, e.g. 100')

    args = parser.parse_args()
    
    print("Setting up HTCondor Dask cluster...")

    cluster = LocalCluster(
        silence_logs=logging.DEBUG,
    )
    client = Client(cluster, asynchronous=False)

    client.get_versions(check=True)
    
    print(f"Dashboard disponibile al link: {cluster.dashboard_link}")

    file_summary = f"filePaths_{args.type}_{'MC' if args.isMC else 'Data'}_{args.year}_era{args.era}.csv"

    run_analysis(args.year,args.era, args.type, args.output, args.n_workers, isMC = args.isMC, csv_path=file_summary)

    print("Cleaning up client and cluster...")
    client.close()
    cluster.close()
    
    stop = time.time()
    proc_time = stop - start
    print(f"{proc_time:.1f}s is total processing time with {args.n_workers} workers")



if __name__ == "__main__":
    main()
