## ⚙️ Environment Setup

Follow these instructions to recreate the workspace on a standard CMS environment (e.g., LXPLUS).

```bash
# Create the software area
cmsrel CMSSW_15_1_X
cd CMSSW_15_1_X/src
cmsenv

# Initialize the repository and download the code
git clone https://github.com/fnenna/Tau3MuRun3_NANO .

# Compile the code
scram b -j 8
```
---