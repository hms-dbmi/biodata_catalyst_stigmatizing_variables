

## Gold standard identification process
1. Extract full RECOVER pediatric data dictionary
2. Provide each data curator with the full RECOVER pediatric data dictonary. Each curator was timeboxed to categorize as many variables as possible within 5 hours. (Round 1)
3. It was not feasible to categorize the entire data dictionary. Round 1 results were collected and all remaining variables in the data dictionary were de-duplicated. 
4. The de-duplicated data dictionary was provided to the curators to categorize the rest of the variables. (Round 2)
5. Round 2 results were collected. Categories were compared across curators. Cases when a single curator categorized the same variable different ways were also flagged. These consolidated results were saved.
6. The consolidated results were reviewed by all curators and a consensus was reached. 
7. Check the final dataset to make sure all disagreements are resolved. 


## Files

### Code
`goldsstandardround2.Rmd` : R code for formatting and consolidating gold standard categorized results from curators.

### CSVs

Full data dictionary
- `recover_pediatric_dataset.csv`

Round 1 results 
- `Gold Standard StigVar Categorization - Simran - RECOVER Pediatric.csv`
- `Gold Standard StigVar Categorization - Emily - RECOVER Pediatric.csv`
- `Gold Standard StigVar Categorization - Alba - RECOVER Pediatric.csv`

De-duplicated data dictionary for review
- `simrantoreview.csv`
- `emilytoreview.csv`
- `albatoreview.csv`

Round 2 results
- `Gold Standard StigVar Categorization - Simran - RECOVER Pediatric Round 2.csv`
- `Gold Standard StigVar Categorization - Emily - RECOVER Pediatric Round 2.csv`
- `Gold Standard StigVar Categorization - Alba - RECOVER Pediatric Round 2.csv`

Consolidated results
- `forgroupreview.csv`

Consolidated results after manual group review
- `group review - forgroupreview`
- `final_goldstandard_variables.csv` (formatted)



