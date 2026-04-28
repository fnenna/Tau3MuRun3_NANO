import subprocess, json, time, os, argparse, time
# voms-proxy-init -voms cms -rfc

def fetch_DAS(query, year, era, timeout=10, max_retries=3):
    command = "/cvmfs/cms.cern.ch/common/dasgoclient -query='"+ query + f"' > datasets/datasets_{year}_{era}.txt"
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        print(f"Era: {era} - DAS Query Attempt {attempt}")

        try:
            process = subprocess.Popen(command, shell=True)
            start_time = time.time()

            while process.poll() is None:  # Checks if the process is still running
                if time.time() - start_time > timeout:
                    process.terminate()  # Terminates the process
                    print(f"Timeout reached! Aborting the command and retrying...")
                    break
                time.sleep(0.5)  # Reduces CPU load

            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                print(f"Era: {era} - DAS Query Done")
                return stdout  # Command succeeded

            print(f"Error during execution: {stderr}")
        
        except Exception as e:
            print(f"Unexpected error: {e}")

    print(f"All {max_retries} attempts failed.")
    return None

# Esempio di utilizzo
if __name__ == "__main__":
    if not os.path.exists("datasets"):
        os.makedirs("datasets")
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--year", required=True, type=str, help="Year of the dataset")
    args = argparser.parse_args()
    year = args.year
    with open("Runs.json", "r") as file:
        data = json.load(file)[year]
    for i, era in enumerate(data["Eras"]): 
        print("ecco")
        print("dataset=/"+data["database"]+ "/"+ data["Campaign"][i]+"/MINIAOD")
        fetch_DAS("dataset=/"+data["database"]+ "/"+ data["Campaign"][i]+"/MINIAOD", year=year, era=era, timeout=15, max_retries=5)
        with open(f"datasets/datasets_{year}_{era}.txt", "r") as filetxt:
            righe = [riga.strip() for riga in filetxt]
        if len(righe) != 8:
            print(f"WARNING: {era} has more/less than 8 datasets. Please check.")
            time.sleep(3)
        print("")
