# biodata_catalyst_stigmatizing_variables
<b>STIGMATIZING VARIABLES</b>
<p>The PIC-SURE Open Access dataset excludes stigmatizing variables from the following categories: Mental health diagnoses/history/treatment; Illicit drug use history/Controlled substances; Sexually transmitted disease diagnoses/history/treatment; Sexual history; Intellectual Achievement/Ability/Educational Attainment; Direct or surrogate identifiers of legal status.</p>
<p>This repo includes scripts that identify stigmatizing variables in the BioData Catalyst PIC-SURE dataset. The repo also hosts the list of stigmatizing variables that are removed from PIC-SURE Open Access each data refresh. </p>
<p>The identification of stigmatizing variables is an evolving process. If you have suggestions, comments, or questions please contact us at https://bdcatalyst.freshdesk.com/support/home


File descriptions

approved_concepts.txt - hpds paths of variables previously flagged as stigmatizing but have been manually approved for open access

conceptsToRemove.txt - hpds paths of all stigmatizing variables removed from Open Access

stigmatizing_terms.csv - terms that when found in a variable's description/id/values will cause it to be flagged as stigmatizing and removed from Open Access
