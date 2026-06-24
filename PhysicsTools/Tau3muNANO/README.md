# Tau3Mu NanoAOD Analysis Workspace

This workspace is dedicated to the production of **custom NanoAOD** for the \tau \to 3\mu$ decay analysis for the HF channel. It includes C++ plugins for Level-1 (L1) trigger bit extraction and specific configurations for vertex fitting and Tau3Mu candidate selection.

## ⚙️ Environment Setup

Follow these instructions to recreate the workspace on a standard CMS environment (e.g., LXPLUS).

```bash
# Create the software area
cmsrel CMSSW_15_0_X
cd CMSSW_15_0_X/src
cmsenv

# Initialize the repository and download the code
git clone https://github.com/fnenna/Tau3MuRun3_NANO .

# Compile the code
scram b -j 8
```
---

## Testing Production

If you want to test the config file and produce the NanoAOD output from a small sample:

1.  Ensure you have a valid grid proxy (`voms-proxy-init`).
2.  Run the job:
    ```bash
    cmsRun PhysicsTools/Tau3muNANO/test/run_{analysis_type}_cfg.py isMC=True/False
    ```
    analysis_type = ["Tau3Mu", "DsPhiPi"]
---

## Running Production

The main informations on data and MC samples are stored in the `Runs.json` file and in files in the `datasets` folder.
### How to add new years (or modify existing ones)
1. Apply your changes in `Runs.json`;
2. If your changes affect data (not required if changes are only in MC), run `getDatset.py` to download information from DAS (as in the example below);
    - `voms-proxy-init -voms cms -rfc`
    - `python3 getDatset.py --year 2025` 

<p>&nbsp;</p>

### Submit all era in a year:
```
submitAllJobs.sh [Year] [MCflag]
```
* `[year]` = `2022`,  `2023` or `2024`: `[MCflag]` = `true or false`

### Run ntuplizer on a full dataset:
```
cd CrabSubmission
source submit_CRAB.sh [era] [year] 
```

<p>&nbsp;</p>
