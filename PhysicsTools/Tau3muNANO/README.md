# Tau3Mu NanoAOD Analysis Workspace

This workspace is dedicated to the production of **custom NanoAOD** for the $\tau \to 3\mu$ decay analysis for the HF channel.

## Testing Production

If you want to test the config file and produce the NanoAOD output from a small sample:

1.  Ensure you have a valid grid proxy (`voms-proxy-init`):
    ```bash
    voms-proxy-init --voms cms
    ```
2.  Run the job:
    ```bash
    cmsRun PhysicsTools/Tau3muNANO/test/test_{analysis_type}_cfg.py isMC=True/False
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


### Run ntuplizer on a full dataset for one specific year:
```
cd crab_submission
source submit_AllJobs.sh [Year] [isMC]
```
* `[year]` = `2022`,  `2023` or `2024`: `[MCflag]` = `true or false`

Note that `submit_AllJobs.sh` needs to be updated with the list of the eras for the year under analysis, if it has not been added yet.
To check the status of the jobs for the whole eras, you can use the `status.sh` contained in each era directory.
If there are failed jobs you can run:
```
source resubmitAll.sh [Year]
```
NB: for the moment this is written only for data. TO-DO: add MC treatment.

Let's move now to the analysis directory Tau3MuANA!
<p>&nbsp;</p>
