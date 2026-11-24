# biodata_catalyst_stigmatizing_variables
<b>STIGMATIZING VARIABLES</b>
<p>The PIC-SURE Open Access dataset excludes stigmatizing variables from the following categories:</p>
<ul>
  <li>Mental Health Diagnoses/History/Treatment</li>
  <li>Illicit Drug Use History</li>
  <li>Sexually Transmitted Disease Diagnoses/History/Treatment</li>
  <li>Sexual History</li>
  <li>Intellectual Achievement/Ability/Educational Attainment</li>
  <li>Direct or Surrogate Identifiers of Legal Status</li>
  <li>Stigmatizing Identifiers</li>
</ul>

<p>This repo includes scripts that identify stigmatizing variables in the BioData Catalyst PIC-SURE dataset. The repo also hosts the list of stigmatizing variables that are removed from PIC-SURE Open Access each data refresh. </p>
<p>The identification of stigmatizing variables is an evolving process. If you have suggestions, comments, or questions please contact us at https://bdcatalyst.freshdesk.com/support/home


File descriptions

approved_concepts.txt - hpds paths of variables previously flagged as stigmatizing but have been manually approved for open access

conceptsToRemove.txt - hpds paths of all stigmatizing variables removed from Open Access

stigmatizing_terms.csv - terms that when found in a variable's description/id/values will cause it to be flagged as stigmatizing and removed from Open Access

manual_tracking.csv - a list of variable concept paths that have been manually reviewed, and the decision made for each of them

FOR QA: the postrun_qa.py script contains the section labeled "Keyword sets". Terms updated in this fields will reflect the filtering
