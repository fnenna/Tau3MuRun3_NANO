#!/bin/bash

# Output file
OUTPUT_FILE="lumi_results.txt"
> "$OUTPUT_FILE"  # Clear file at start

# Normtag path
NORMTAG="/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_BRIL.json"

# Loop through each 2024_era* directory
for ERA_DIR in 2024_era*; do
    echo "Searching in $ERA_DIR..."

    # Find all processedLumis.json files under crab_projects
    find "$ERA_DIR/crab_projects/" -type f -path "*/results/processedLumis.json" | while read -r JSON_FILE; do
        echo "  Found $JSON_FILE"

        # Run brilcalc and capture output
        BRIL_OUTPUT=$(brilcalc lumi --normtag "$NORMTAG" -u /fb -i "$JSON_FILE" --hltpath "HLT_DoubleMu3_Trk_Tau3mu_v*")
        # Extract delivered lumi from summary
        DELIVERED=$(echo "$BRIL_OUTPUT" | grep "#Sum delivered" | awk '{print $4}')
        PROCESSED=$(echo "$BRIL_OUTPUT" | grep "#Sum recorded" | awk '{print $4}')


        # Label it by era + crab folder
        LABEL=$(dirname "$JSON_FILE" | sed 's|/results||' | sed 's|crab_projects/||')

        # Append to output file
        echo "$LABEL: delivered = $DELIVERED /fb - recorded = $PROCESSED /fb" >> "$OUTPUT_FILE"
    done
done

echo "Done! Summary saved to $OUTPUT_FILE"
