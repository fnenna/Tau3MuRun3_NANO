#!/bin/bash

# Define the eras for each year
declare -a era2025=("C-v1" "C-v2" "D" "E" "F-v1" "F-v2" "G")
declare -a era2024=("B" "C" "D" "E-v1" "E-v2" "F" "G" "H" "I-v1" "I-v2")

# Check if the user provided the year as an argument
if [ -z "$1" ]; then
    echo "Error: Please specify the year (2024 or 2025)"
    echo "Usage: $0 <year>"
    exit 1
fi

YEAR=$1

# Dynamically reference the correct array based on input
if [ "$YEAR" == "2025" ]; then
    selected_era=("${era2025[@]}")
elif [ "$YEAR" == "2024" ]; then
    selected_era=("${era2024[@]}")
else
    echo "Error: Invalid year $YEAR. Choose 2024 or 2025."
    exit 1
fi

# First loop using the selected year and array
for i in "${selected_era[@]}"; do
    echo -e "\nData $i"
    cd ${YEAR}_era${i}
    source resubmit.sh
    sleep 1
    cd ..
done