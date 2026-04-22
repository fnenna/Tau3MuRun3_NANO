import argparse
import time
import glob
import uproot
from dask.distributed import Client, LocalCluster
from dask_jobqueue.htcondor import HTCondorCluster
import dsPhiPi_analyser as analysis_control
import tau3mu_analyser as analysis_signal

import os
import logging

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

def run_analysis(era: str, stream: str, analysis_type: str, dataset_name: str, n_workers: int):
    print(f"Analysis type: {analysis_type}")
    print(f"Dataset name: {dataset_name}")
    print(f"Era: {era}")
    print(f"Stream: {stream}")


    print("Starting control channel analysis on data...")

    pattern = f"/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimDsPhiPi_2024era{era}_stream*_Mini_v4/*/00*/Tree_PhiPi_*.root"
    #pattern = f'/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimTau3mu_2024era{era}_stream*_Mini_v4/*/00*/TreeData_*.root'
    #pattern = f'/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass0/SkimTau3mu_2024eraB_stream*_Mini_v4/*/00*/TreeData_*.root'
    #pattern = f'/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass0/SkimTau3mu_2024eraB_stream0_Mini_v4/*/0000/TreeData_1.root'

    #pattern = f"/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass*/SkimDsPhiPi_2024era{era}_stream0_Mini_v4/*/00*/Tree_PhiPi_*.root"



    #files = {f: "Tree3Mu/ntuple;1" for f in filelist}
    if analysis_type == "data_control":
        #pattern = f"/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimDsPhiPi_2024era{era}_stream*_Mini_v4/*/00*/Tree_PhiPi_*.root"
        #filelist = glob.glob(pattern)
        #if not filelist:
        #    print(f"No ROOT files found with pattern:\n{pattern}")
        #    return
        #files = [f"{f}:Tree3Mu/ntuple" for f in filelist]
        file = "/eos/home-f/fnenna/tau3mu_run3/CMSSW_15_0_0/src/PhysicsTools/Tau3muNANO/test/nano_2mu1trk_testData.root:Events"

    elif analysis_type == "data_signal":
        #pattern = f'/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimTau3mu_2024era{era}_stream*_Mini_v4/*/00*/TreeData_*.root'
        #filelist = glob.glob(pattern)
        #if not filelist:
        #    print(f"No ROOT files found with pattern:\n{pattern}")
        #    return
        #files = [f"{f}:TreeMakerBkg/ntuple" for f in filelist]
        file = "/eos/home-f/fnenna/tau3mu_run3/CMSSW_15_0_0/src/PhysicsTools/Tau3muNANO/test/tau3mu_test_outputMC.root:Events"
    else:
        print("Unsupported analysis type. Currently only 'data_control' is implemented.")


    #events = uproot.dask(files, open_files=False)
    events = uproot.dask(file, open_files=False)
    events = events.repartition(npartitions=n_workers).persist() #Riduci da 978 a 100

    #print(f"{len(filelist)} files loaded. Repartitioning with {n_workers} workers.")


    fileout = f"{analysis_type}_{dataset_name}_{era}_{stream}"
    if analysis_type == "data_control":
        analysis_control.Analysis_DsPhiPi(events, dataset_name, fileout, era, stream)
    elif analysis_type == "data_signal":
        analysis_signal.Analysis_Tau3Mu(events, dataset_name, fileout, era, stream)
    else:
        print("Unsupported analysis type. Currently only 'data_control' is implemented.")


def main():
    start = time.time()
    parser = argparse.ArgumentParser(
        prog='DsPhiPiAnalysis',
        description='Run analysis on tau → 3μ control channel (Ds→ϕπ)',
        epilog='Example usage: python3 run_analysis_dask_dsPhiPi.py -e B -t data_control -o DsPhiPi -c 1 -w 70 -j 20'
    )
    parser.add_argument('-e', '--era', required=True, help='Data-taking era (e.g., B, C, D, E-v1, etc.)')
    parser.add_argument('-s', '--stream', required=True, help='Data-taking era (e.g., 0-7)')
    parser.add_argument('-t', '--type', required=True, choices=['data_control', 'data_signal'], help='Type of analysis')
    parser.add_argument('-o', '--output', required=True, help='Prefix for the output directory or file')
    #parser.add_argument('-c', '--n_cores', required=True, type=int, help='Number of Dask workers to use')
    parser.add_argument('-w', '--n_workers', required=True, type=int, help='Number of Dask workers to use, e.g. 100')
    #parser.add_argument('-j', '--max_number_of_jobs', required=True, type=int, help='Maximum number of HTCondor jobs')

    args = parser.parse_args()
    
    print("Setting up HTCondor Dask cluster...")

    cluster = LocalCluster(
        silence_logs=logging.DEBUG,
    )
    client = Client(cluster, asynchronous=False)

    client.get_versions(check=True)
    
    print(f"Dashboard disponibile al link: {cluster.dashboard_link}")

    run_analysis(args.era, args.stream, args.type, args.output, args.n_workers)

    print("Cleaning up client and cluster...")
    client.close()
    cluster.close()
    
    stop = time.time()
    proc_time = stop - start
    #print(f"{proc_time:.1f}s is total processing time with {args.n_cores} cores, {args.n_workers} workers and {args.max_number_of_jobs} jobs")
    print(f"{proc_time:.1f}s is total processing time with {args.n_workers} workers")



if __name__ == "__main__":
    main()
