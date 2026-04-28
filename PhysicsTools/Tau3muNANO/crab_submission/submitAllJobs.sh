#!/bin/sh
# Usage:
#    submitAllJobs.sh

helpstring="Usage: submitAllJobs.sh [Year] [isMC]"

year=$1
MCflag=$2

if [ -z ${2+x} ]; then
    echo -e ${helpstring}
    return
fi

MCflag=$(echo "$MCflag" | tr '[:upper:]' '[:lower:]')

if [ "$MCflag" != "true" ] && [ "$MCflag" != "false" ]; then
    echo "$helpstring"
    return
fi

declare -a era2022preE=("C" "D-v1" "D-v2" "E")
declare -a era2022postE=("F" "G")
declare -a era2023=("B" "C-v1" "C-v2" "C-v3" "C-v4" "D-v1" "D-v2")
declare -a era2024=("B" "C" "D" "E-v1" "E-v2" "F" "G" "H" "I-v1" "I-v2")
readarray -t MCeras22 < <(jq -r '.["2022"].MC_era[]' Runs.json)
readarray -t MCeras23 < <(jq -r '.["2023"].MC_era[]' Runs.json)
readarray -t MCeras24 < <(jq -r '.["2024"].MC_era[]' Runs.json)

current_dir=$(pwd)

if [ "$MCflag" == "false" ]; then
    type=""
    if [[ "$current_dir" == *"CMSSW_14_"* ]]; then
        if [[ "$year" == "2024" ]]; then
            era=("${era2024[@]}")
        else
            return
        fi
    elif [[ "$current_dir" == *"CMSSW_13_"* ]]; then
        if [[ "$year" == "2022" ]]; then
            era=("${era2022postE[@]}")
        elif [[ "$year" == "2023" ]]; then
            era=("${era2023[@]}")
        else
            return
        fi
    elif [[ "$current_dir" == *"CMSSW_12_"* ]]; then
        if [[ "$year" == "2022" ]]; then
            era=("${era2022preE[@]}")
        else
            return
        fi
    else
        return
    fi
else
    type="MC"
    if [[ "$year" == "2022" ]]; then
        era=("${MCeras22[@]}")
    elif [[ "$year" == "2023" ]]; then
        era=("${MCeras23[@]}")
    else
        era=("${MCeras24[@]}")
    fi
fi

for i in "${era[@]}"; do
    echo -e "\nData $i"
    python3 submit_CRAB.py --year ${year} --${type}era ${i} 
    sleep 1
done
