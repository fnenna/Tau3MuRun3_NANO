import glob
import argparse
import pandas as pd
import numpy as np  # Fornp.arange

patterns = {
    "signal": {
        True:  {"2024": "/path/to/mc/signal/2024/*", "2025": "/path/to/mc/signal/2025/*"},
        False: {"2024": "/path/to/data/signal/2024/{era}/{stream}/*", "2025": "/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass0/SkimTau3mu_2025eraB_stream0_Mini_v4/260717_*/00*/tau3mu_output_Data_*.root"}
    },
    "control": {
        True:  {"2024": "/path/to/mc/control/2024/*", "2025": "/path/to/mc/control/2025/*"},
        False: {"2024": "/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimDsPhiPi_2024era{era}_stream{stream}_Mini_v4/260602_*/00*/dsphipi_output_Data_*.root",
                "2025": "/lustre/cms/store/user/fnenna/ParkingDoubleMuonLowMass{stream}/SkimDsPhiPi_2025era{era}_stream{stream}_Mini_v4/260714*/00*/dsphipi_output_Data_*.root"}
    }
}

parser = argparse.ArgumentParser(
    description="Create a csv files with the paths of the files to be processed for a given year and era."
)

parser.add_argument("--year", type=str, required=True, choices=["2024", "2025"], help="The year to process (2024 or 2025)")
parser.add_argument("--type", type=str, required=True, choices=["signal", "control"], help="The type of data to process (signal or control)")
parser.add_argument("--isMC", action="store_true", help="Flag to indicate if the data is Monte Carlo")
parser.add_argument("--era", type=str, default=None, help="The specific era to process (optional, e.g., B, C, D...)")
args = parser.parse_args()

eras_dic = {
    "2024": ["B", "C", "D", "E-v1", "E-v2", "F", "G", "H", "I-v1", "I-v2"],
    "2025": ["B", "C-v1", "C-v2", "D", "E", "F-v1", "F-v2", "G"]
}

if args.era:
    if args.era in eras_dic[args.year]:
        eras_to_process = [args.era]
    else:
        parser.error(f"Era '{args.era}' is not valid for year {args.year}. Choose from: {eras_dic[args.year]}")
else:
    eras_to_process = eras_dic[args.year]

streams = np.arange(0, 8) 
chunk_size = 100 
threshold = 20 

data_list = []
year = args.year

for era in eras_to_process:
    for stream in streams:
        raw_pattern = patterns[args.type][args.isMC][args.year]
        pattern = raw_pattern.format(era=era, stream=stream)
        files = sorted(glob.glob(pattern))
        total_files = len(files)
        
        if total_files == 0:
            continue

        for i, file_path in enumerate(files):
            group_id = i // chunk_size
            num_groups = total_files // chunk_size
            remainder = total_files % chunk_size
            
            if remainder <= threshold and num_groups > 0:
                if group_id >= num_groups:
                    group_id = num_groups - 1
            
            data_list.append({
                "year": year,
                "era": era,
                "stream": stream,
                "group": group_id,
                "path": file_path
            })

df = pd.DataFrame(data_list)
if args.era:
    output_name = f"filePaths_{args.type}_{'MC' if args.isMC else 'Data'}_{args.year}_era{args.era}.csv"
else:
    output_name = f"filePaths_{args.type}_{'MC' if args.isMC else 'Data'}_{args.year}.csv"
df.to_csv(output_name, index=False)

if not df.empty:
    summary = df.groupby(['year', 'era', 'stream', 'group']).size().reset_index(name='file_count')
    print("Grouping synthesis:")
    print(summary)