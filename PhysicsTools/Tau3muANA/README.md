Here is a professional and clear `README.md` for your framework.

---

# HF Tau3Mu Analysis Framework

This framework is designed for analyzing customized **NANOAOD ntuples** for Heavy Flavor (HF) studies, specifically targeting the $B \to \tau(\to 3\mu)\nu$ and $D_s \to \phi(\to \mu\mu)\pi$ channels.

## 📁 Repository Structure

* **`tau3mu_analysis_runner.py`**: The main entry point. It manages the Dask cluster initialization and distributes the workload.
* **`tau3mu_analyser.py`**: Contains the logic and selection cuts for the 3-muon ($3\mu$) final state.
* **`dsPhiPi_analyser.py`**: Contains the logic and selection cuts for the 2-muon + 1-track ($2\mu + 1\text{tr}$) final state.
* **`requirements.txt`**: List of required Python packages (Uproot, Awkward, Dask, etc.).

---

## 🛠 Setup Instructions

To avoid conflicts with the CMSSW environment, it is highly recommended to use a **Python Virtual Environment**.

1.  **Initialize CMSSW (if needed):**
    ```bash
    cmsenv
    ```

2.  **Create and activate the virtual environment:**
    ```bash
    python3 -m venv my_dask_env
    source my_dask_env/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

> **Note:** If you are running on a cluster, ensure that `PYTHONPATH` is correctly managed to prioritize the virtual environment over system libraries.

---

## 🚀 Running the Analysis

Use the `tau3mu_analysis_runner.py` script to launch the processing. The script requires several arguments to define the dataset and output.

### Command Syntax:
```bash
python3 tau3mu_analysis_runner.py -e <era> -s <stream> -t <type> -o <output_dir> -w <n_workers>
```

### Arguments:
| Flag | Description | Examples |
| :--- | :--- | :--- |
| `-e` | Data-taking Era | `2022`, `2023`, `2024` |
| `-s` | Trigger Stream | `ParkingDoubleMuonLowMass`, `ParkingLLP` |
| `-t` | Analysis Type | `data_signal`, `data_control`, `MC` |
| `-o` | Output Directory | `output_v1`, `test_results` |
| `-w` | Number of Workers | `4`, `8`, `16` (Dask parallelization) |

### Example Command:
```bash
python3 tau3mu_analysis_runner.py -e 2022 -s ParkingDoubleMuonLowMass -t data_signal -o my_analysis_results -w 8
```

---

## 📊 Output
The framework produces:
1.  **ROOT Ntuples**: Processed events saved in the specified output directory.
2.  **Cutflow**: A `cutflow.root` file containing an absolute-count histogram of events passing each selection step.
3.  **Dask Report**: A `dask-report.html` file to monitor performance and resource usage.

---
