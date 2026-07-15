# HF Tau3Mu Analysis Framework

This framework is designed for analyzing customized **NANOAOD ntuples** for Heavy Flavor (HF) studies, specifically targeting the HF $\tau(\to 3\mu)$ and $D_s \to \phi(\to \mu\mu)\pi$ channels.

## 📁 Repository Structure

* **`tau3mu_analysis_runner.py`**: The main entry point. It manages the Dask cluster initialization and distributes the workload.
* **`tau3mu_analyser.py`** (preliminary): Contains the logic and selection cuts for the 3-muon ($3\mu$) final state.
* **`dsPhiPi_analyser.py`**: Contains the logic and selection cuts for the $2\mu + 1\text{tr}$ final state.
* **`file_finder.py`**: A pre-processing utility script that scans storage directories, filters by year/era, and maps file paths into an optimized CSV grouped into chunks of 100 files for better job distribution.
* **`requirements.txt`**: List of required Python packages (Uproot, Awkward, Dask, etc.).

---

## 🛠 Setup Instructions

To avoid conflicts with the CMSSW environment, it is highly recommended to use a **Python Virtual Environment**.

1. **Create and activate the virtual environment:**
```bash
python3 -m venv my_dask_env
source my_dask_env/bin/activate

```


2. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt

```
---

## 📅 Pre-processing: File Mapping & Grouping

Before running the core analysis, you should generate a dataset mapping file using `file_finder.py`:
```bash
python3 file_finder.py --year <year> --type <type> [--isMC] [--era <era>]

```
This script automatically divides files into **balanced groups of 100** (with custom tail thresholds) to prevent job skew and ensure an efficient workload distribution across HTCondor/Dask workers.
Before running the script please provide in the `patterns` dictionary the exact directory where the files are saved.

### Arguments:

| Flag | Description | Choices / Examples |
| --- | --- | --- |
| `--year` | The data-taking year (**Required**) | `2024`, `2025` |
| `--type` | Dataset analysis category (**Required**) | `signal`, `control` |
| `--isMC` | Flag to enable Monte Carlo path matching | *Omit for Collision Data* |
| `--era` | Limits the scan to a single specific era (Optional) | `B`, `C-v1`, `D`, ... |


---

## 🚀 Running the Analysis

Use the `tau3mu_analysis_runner.py` script to launch the processing. The script requires several arguments to define the dataset and output.

### Command Syntax:

```bash
python3 tau3mu_analysis_runner.py -e <era> -s <stream> -t <type> -o <output_dir> -w <n_workers>

```

### Arguments:

| Flag | Description | Examples |
| --- | --- | --- |
| `-e` | Data-taking Era | `B`, `C`, `D` |
| `-t` | Analysis Type | `data_signal`, `data_control`, `MC` |
| `-o` | Output Directory | `output_v1`, `test_results` |
| `-w` | Number of Workers | `4`, `8`, `16` (Dask parallelization) |

### Example Command:

```bash
python3 tau3mu_analysis_runner.py -y 2025 -e B -t control -o trial-for-git -w 100
```

### Monitoring with Dask Dashboard
When running the code, Dask will print the local link of the real-time monitoring dashboard in your terminal (e.g., http://127.0.0.1:8787/status).

To access and visualize the dashboard securely from your local browser, set up an SSH Tunnel by running the following command in a new terminal window on your local machine:

```bash
ssh -L 8787:[dask_worker_node]:8787 [your_username]@[remote_cluster_frontend]
```

Replace [dask_worker_node] with the specific hostname/IP where the Dask master scheduler is running, and [your_username]@[remote_cluster_frontend] with your remote cluster login credentials.

Once the tunnel is active, open your browser and navigate to:
http://localhost:8787
---

## 📊 Output

The framework produces:

1. **ROOT Ntuples**: Processed events saved in the specified output directory.
2. **Cutflow**: A `cutflow.root` file containing an absolute-count histogram of events passing each selection step.
3. **Dask Report**: A `dask-report.html` file to monitor performance and resource usage.

---