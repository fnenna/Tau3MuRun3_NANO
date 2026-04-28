import subprocess, json, time, os, argparse

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--year", required=True, type=str, help="Year of the dataset")
    argparser.add_argument("--era", type=str, default=None, help="Era of the dataset")
    argparser.add_argument("--MCera", type=str, default=None, help="Era of the dataset")
    args = argparser.parse_args()
    
    year = args.year
    era = args.era
    MCera = args.MCera
    
    if (MCera==None) and (era==None):
        exit()

    with open("Runs.json", "r") as file:
        data = json.load(file)[year]

    # --- CASO DATA (isMC = False) ---
    if era != None:
        era_index = data["Eras"].index(era) if era in data["Eras"] else None
        if era_index == None:
            print(f"WARNING: {era} is not in the list of eras. Please check.")
            exit()
            
        globaltag = data["GTs"][era_index]
        golden_json = data["golden_json"][era_index]

        with open(f"datasets/datasets_{year}_{era}.txt", "r") as filetxt:
            righe = [riga.strip() for riga in filetxt]

        command = f"""
        directory="$PWD";
        # Puntiamo alla cartella 'test' dove hai i file test_DsPhiPi_cfg.py
        pathtoskimfile="$directory/../test"; 
        mkdir -p "{year}_era{era}"; 
        echo "Data {year} - era {era} is selected"; 
        
        path_cfg="$directory/{year}_era{era}/PatAndTree_cfg.py";
        
        # Copiamo il tuo file di test specifico
        cp "$pathtoskimfile/test_DsPhiPi_cfg.py" "$path_cfg";
        
        # Sostituiamo il Global Tag (adattato al tuo placeholder nel file di test)
        # Se nel tuo file hai '140X_dataRun3_v4', sostituiamo quello
        sed -i "s#140X_dataRun3_v4#{globaltag}#g" "$path_cfg";
        
        # FORZIAMO isMC = False nel file cfg per sicurezza
        sed -i "s#options.register('isMC', True#options.register('isMC', False#g" "$path_cfg";

        cp templates/report.sh "{year}_era{era}/report.sh";
        cp templates/status.sh "{year}_era{era}/status.sh";
        cp templates/resubmit.sh "{year}_era{era}/resubmit.sh";
        cd "{year}_era{era}";
        sed -i "s#YEAR#{year}#g" *.sh;
        sed -i "s#ERANAME#{era}#g" *.sh;
        cd ..;
        cp templates/submit.sh "{year}_era{era}/submit.sh";
        """
        subprocess.run(command, shell=True, check=True)

        for i, dataset in enumerate(righe):
            command = f"""
            directory="$PWD";
            path="$directory/{year}_era{era}/PatAndTree_cfg.py";
            cp templates/CRAB_template.py "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#YEAR#{year}#g" "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#ERANAME#{era}#g" "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#NUMBER#{i}#g" "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#DATASET_NAME#{dataset}#g" "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#FILE_TO_SUBMIT_PATH#$path#g" "{year}_era{era}/CRAB_stream_{i}.py";
            sed -i "s#GOLDEN_JSON_PATH#{golden_json}#g" "{year}_era{era}/CRAB_stream_{i}.py";
            cd "{year}_era{era}";
            crab submit -c "CRAB_stream_{i}.py";
            cd ..;
            echo "Stream {i} submitted!";
            sleep 1;
            """
            subprocess.run(command, shell=True, check=True) 

    # --- CASO MC (isMC = True) ---
    elif MCera != None:
        era_index = data["MC_era"].index(MCera) if MCera in data["MC_era"] else None
        if era_index == None:
            print(f"WARNING: {MCera} is not in the list of MC_eras. Please check.")
            exit()
            
        MC_input_type = data["MC_input_type"][era_index]
        globaltag = data["MC_GTs"][era_index]
        MC_datasets = data["MC_datasets"][era_index]

        command = f"""
        directory="$PWD";
        pathtoskimfile="$directory/../test";
        mkdir -p "{year}_{MCera}"; 
        echo "MC {year} - {MCera} is selected"; 
        path_cfg="$directory/{year}_{MCera}/PatAndTree_cfg.py";
        cp "$pathtoskimfile/test_DsPhiPi_cfg.py" "$path_cfg";
        
        # Sostituiamo il Global Tag MC
        sed -i "s#140X_mcRun3_2024_realistic_v26#{globaltag}#g" "$path_cfg";
        
        # FORZIAMO isMC = True
        sed -i "s#options.register('isMC', False#options.register('isMC', True#g" "$path_cfg";

        cp templates/CRAB_template_MC.py "{year}_{MCera}/CRAB_MC.py";
        sed -i "s#YEAR#{year}#g" "{year}_{MCera}/CRAB_MC.py";
        sed -i "s#ERANAME#{MCera}#g" "{year}_{MCera}/CRAB_MC.py";
        sed -i "s#DATASET_NAME#{MC_datasets}#g" "{year}_{MCera}/CRAB_MC.py";
        sed -i "s#FILE_TO_SUBMIT_PATH#$path_cfg#g" "{year}_{MCera}/CRAB_MC.py";
        sed -i "s#INPUT_TYPE#{MC_input_type}#g" "{year}_{MCera}/CRAB_MC.py";
        
        cd "{year}_{MCera}";
        # crab submit -c "CRAB_MC.py"; # Decommenta quando sei pronto
        cd ..;
        echo "{MCera} submitted!";
        """
        subprocess.run(command, shell=True, check=True)