#!/bin/bash


# Configuration
TEMPLATE="progs/README.namelist"
ODIR="regcm5-nml"

TABLE="configure-domain_201108.tbl"
EXPNM="201108"

TABLE="configure-domain_201408.tbl"
EXPNM="201408"

TABLE="configure-domain_201508.tbl"
EXPNM="201508"

# Check if files exist
if [[ ! -f "$TEMPLATE" || ! -f "$TABLE" ]]; then
    echo "Error: Template or Table file not found."
    exit 1
fi

# 1. Get a list of all unique domains (handles "d01,d02" format)
# This splits the first column by commas and gathers unique entries
DOMAINS=$(awk 'NR>1 { split($1, a, ","); for (i in a) print a[i] }' "$TABLE" | sort -u)

for DOM in $DOMAINS; do
    NEW_FILE=$ODIR/"nml.${EXPNM}.${DOM}.in"
    echo "Processing $NEW_FILE ..."
    
    # Copy the template to start fresh for this domain
    cp "$TEMPLATE" "$NEW_FILE"
    
    # 2. Extract parameters where the first column contains the current domain
    # Example: if DOM is "d01", this matches "d01" AND "d01,d02"
    awk -v d="$DOM" 'NR>1 {
        split($1, arr, ",");
        found = 0;
        for (i in arr) {
            if (arr[i] == d) found = 1;
        }
        if (found) print $2, $3;
    }' "$TABLE" | while read -r PARAM VALUE; do
        
        # 3. Use sed to replace the value
        # This handles strings with quotes, numbers, and booleans
        # It looks for: parameter_name = old_value
        # and preserves everything after the value (commas, comments)
        sed -i -E "s|^([[:blank:]]*$PARAM[[:blank:]]*=[[:blank:]]*)[^,!/]*|\1$VALUE |" "$NEW_FILE"
        
    done
done

echo "Success! Namelists generated."
