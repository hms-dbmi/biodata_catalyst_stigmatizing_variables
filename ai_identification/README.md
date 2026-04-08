Step 1 : Download the vars.tsv file for the study
Step 2 : Run the python script
    ex : python3 stig_id_ai.py --input vars.tsv --output recover_flagged.tsv --num-columns 6 --no-header
Step 3 : Commit the conceptsToRemove.txt file

The process is completed when the conceptsToRemove.txt file is updated on the main branch



Arguments Available for different inputs -

#######

DEFAULT - Headerless TSV with 6 columns :
    python stig_id_ai.py
        --input recover_vars.tsv 
        --output recover_vars_FLAGGED.tsv 
        --no-header 
        --num-columns 6

Example : 

python3 stig_id_ai.py --input vars.tsv --output recover_flagged.tsv --num-columns 6 --no-header

Additional Options - 

CSV with header :
    python stig_id_ai.py
        --input recover_vars.csv 
        --output recover_vars_FLAGGED.csv

TSV with header :
    python stig_id_ai.py
        --input recover_vars.tsv  
        --output recover_vars_FLAGGED.tsv

Optional gzip output :
    python stig_id_ai.py
        --input recover_vars.tsv 
        --output recover_vars_FLAGGED.tsv.gz 
        --no-header 
        --num-columns 6
