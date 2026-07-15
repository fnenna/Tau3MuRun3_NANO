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

## Project Status and Contributions

> **Current Status:** The analysis framework has been finalized and validated for the control channel ($D_s \to \phi\pi$). Whereas, the signal channel (HF $\tau \to 3\mu$) is currently **ongoing**. 
>
> **Contributions:** We highly welcome and encourage any feedback, bug reports, or pull requests to help optimize the framework and finalize the signal channel. Feel free to open an issue or submit a contribution!