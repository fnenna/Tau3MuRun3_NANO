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

## 🚀 Running Production

To process a local or remote file and produce the NanoAOD output:

1.  Ensure you have a valid grid proxy (`voms-proxy-init`).
2.  Run the job:
    ```bash
    cmsRun PhysicsTools/Tau3muNANO/test/run_{analysis_type}_cfg.py
    ```
    analysis_type = ["Tau3Mu", "DsPhiPi"]
---

## 📂 Repository Structure (DA AGGIORNARE CON I VARI CODICI AGGIUNTI)

This repository manages only the custom analysis code, following the standard CMSSW directory hierarchy:

* **`PhysicsTools/Tau3muNANO/plugins/`**: Contains C++ source files:
    * `L1_trigger_table.cc`: Produces a `FlatTable` containing L1 trigger decisions.
* **`PhysicsTools/Tau3muNANO/python/`**: Python configuration fragments (`cff`):
    * Definitions for Muon, Vertex, and Trigger tables.
* **`PhysicsTools/Tau3muNANO/test/`**: Execution scripts:
    * `run_nano_cfg.py`: Full configuration to process MiniAOD files.
---
