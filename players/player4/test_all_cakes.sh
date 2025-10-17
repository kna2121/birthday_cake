#!/bin/bash

# Find all CSV files in the players directories
all_cakes=$(find cakes/players/player* -name "*.csv")

# Remove empty cakes
all_cakes=$(echo "$all_cakes" | grep -v "empty.csv")

# Add given cakes from TA
all_cakes=$(echo -e "$all_cakes\ncakes/figure_eight.csv\ncakes/horseshoe.csv")

# Count the number of cakes
cake_count=$(echo "$all_cakes" | wc -l)

# Print the results
echo "Found $cake_count cakes"
# echo "$all_cakes" | sort

target_piece_sizes=(20 30 40)

# Run our player on all cakes 
for cake in $all_cakes; do
    echo "Cutting cake: $cake"
    echo "Cake: $cake" >> results_player4.txt

    # Get area of the cake
    output=$(PYTHONPATH=. uv run main.py --import-cake "$cake" --player r --children 10)
    area=$(echo "$output" | grep -Eo 'Area: [0-9]+(\.[0-9]+)?' | awk '{print $2}')
    echo "Area: $area"
    # Cut for all target piece sizes
    for target in "${target_piece_sizes[@]}"; do
        children=$(echo "$area / $target" | bc)
        echo "Target piece size: $target, Children: $children" >> results_player4.txt
        PYTHONPATH=. uv run main.py --import-cake "$cake" --player 4 --children $children  >> results_player4.txt
    done
done