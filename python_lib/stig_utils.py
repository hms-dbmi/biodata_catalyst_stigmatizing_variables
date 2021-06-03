import re
import pandas as pd
import os.path
from os import path
from IPython.display import clear_output

def check_simplified_name(varlist, multiindex_df, exclude_vars=[]):
    stig_var_list = []
    excluded_var_list = []
    for i in range(1, len(multiindex_df["simplified_name"])):
        for var in varlist:
            if re.search(var, multiindex_df['simplified_name'][i], re.IGNORECASE):
                for ex in exclude_vars:
                    if multiindex_df['simplified_name'][i].lower() == ex:
                        if multiindex_df['simplified_name'][i] not in excluded_var_list:
                            excluded_var_list.append(multiindex_df['name'][i])
                if multiindex_df['name'][i] not in excluded_var_list:
                    if multiindex_df['name'][i] not in stig_var_list:
                        stig_var_list.append(multiindex_df['name'][i])
    return stig_var_list, excluded_var_list

def regex_filter_out(stig_vars, terms_to_filter):
    filter_out = []
    for i in stig_vars:
        simple_var = i.strip('\\').split('\\')[-1]
        for term in terms_to_filter:
            if re.search(term, simple_var, re.IGNORECASE):
                filter_out.append(i)
    list_difference = [item for item in stig_vars if item not in filter_out]
    return list_difference

def manual_check(final_vars, out_file, ex_vars=None):
    while path.exists(out_file):
        print("Output file already exists. Would you like rename the output file or exit?")
        res = input("Type 'r' to rename or 'e' for exit:\n")
        if res == 'r':
            out_file = input("Type new output file:\n")
        elif res == 'e':
            return None
    print("Continue to review of", len(final_vars), 'variables?')
    status = input("y/n: ")
    if status == "y":
        stig_vars_df = go_through_df(final_vars)
        stig_vars_df.to_csv(out_file, sep='\t')
        print("\n \nSTIGMATIZING VARIABLE RESULTS SAVED TO:\t", out_file)
    else:
        stig_vars_df = None
        
    if ex_vars is not None:
        print("Would you like to review the excluded variables?")
        ex_var_review = input('Type "yes" or "no": \n')
        if ex_var_review == 'yes':
            ex_vars_df = go_through_df(ex_vars)
            ex_out_file = out_file.replace('.tsv', '_excluded.tsv')
            ex_vars_df.to_csv(ex_out_file, sep='\t')
            print("\n \nEXCLUDED VARIABLE RESULTS SAVED TO:\t", ex_out_file)
    else:
        ex_vars_df = None
    
    print("Clear cell output and display pandas dataframe?")
    clear = input('Type "y" or "n": \n')
    if clear == 'y':
        clear_output()
    #print('\n \n \n \nFINAL OUTPUT:\n')
    display(stig_vars_df)
    return stig_vars_df, ex_vars_df

def go_through_df(var_list):
    df = pd.DataFrame(var_list, columns=['full name'])
    df['simple name'] = ''
    df['stigmatizing'] = ''
    total = len(var_list)
    stigs = []
    nonstigs = []
    
    for i in range(df.shape[0]):
        if df['full name'][i].strip('\\').split('\\')[-1].lower() in stigs:
            df['simple name'][i] = df['full name'][i].strip('\\').split('\\')[-1]
            df['stigmatizing'][i] = 'y'
            print("Already identified >", df['full name'][i].strip('\\').split('\\')[-1], "<, recording result", i+1, "of", total)
            continue
        elif df['full name'][i].strip('\\').split('\\')[-1].lower() in nonstigs:
            df['simple name'][i] = df['full name'][i].strip('\\').split('\\')[-1]
            df['stigmatizing'][i] = 'n'
            print("Already identified >", df['full name'][i].strip('\\').split('\\')[-1], "<, recording result", i+1, "of", total)
            continue
        
        result = info_loop(i, df, total)
        if len(result) == 1:
            result = info_loop(i-1, df, total)
            df['simple name'][i-1] = result[1]
            df['stigmatizing'][i-1] = result[0]
            result = info_loop(i, df, total)
        df['simple name'][i] = result[1]
        df['stigmatizing'][i] = result[0]
        if result[1] not in stigs and result[1] not in nonstigs:
            if result[0] == 'y':
                stigs.append(result[1].lower())
            elif result[0] == 'n':
                nonstigs.append(result[1].lower())
            
        #simple_var = df['full name'][i].strip('\\').split('\\')[-1]
        #df['simple name'][i] = simple_var
        #print("Is the following variable stigmatizing?")
        #print("\n>>>>", simple_var, "<<<<\n")
        #status = input('Type "yes" or "no". To display full variable, type "more": \n')
        #if status == 'back':
        #    i = i-1
        #    simple_var = df['full name'][i].strip('\\').split('\\')[-1]
        #    df['simple name'][i] = simple_var
        #    print("Is the following variable stigmatizing?")
        #    print("\n>>>>", simple_var, "<<<<\n")
        #    status = input('Type "yes" or "no". To display full variable, type "more": \n')
        #    i = i+1
        #    
        #if status == 'more':
        #    print('\n>>>>', df['full name'][i], '<<<<\n')
        #    status = input('Type "yes" or "no": \n')
        #df['stigmatizing'][i] = status
        
    return df

def info_loop(i, df, total):
    print("Is the following variable stigmatizing? ", i+1, "of", total)
    simple_var = df['full name'][i].strip('\\').split('\\')[-1]
    print("\n>>>>", simple_var, "<<<<\n")
    status = input('Type "y" or "n". To display full variable, type "more":\n')
    if status == 'back':
        return [status]
    if status == 'more':
        print('\n>>>>', df['full name'][i], '<<<<\n')
        status = input('Type "y" or "n": \n')
    return [status, simple_var]
    
    
def validate_stig_vars(fullVariableDict, input_file, output_file):
    while path.exists(output_file):
        print("Output file already exists. Would you like rename the output file or exit?")
        res = input("Type 'r' to rename or 'e' for exit:\n")
        if res == 'r':
            output_file = input("Type new output file:\n")
        elif res == 'e':
            return None
    stigvars = pd.read_csv(input_file, header=None, sep='\t')
    stigvarlist = [i for i in stigvars[0]]
    need_removal = []
    for i in fullVariableDict:
        if i in stigvarlist:
            print("Stigmatizing variable\n>>>>", i, "<<<<\nfound in Open Access")
            need_removal.append(i)
    if len(need_removal)==0:
        print("No stigmatizing variables found in Open Access. Passed validation test.")
        need_removal = None
    else:
        print(len(need_removal), "stigmatizing variables found in Open Access.")
        print("Saving variables to be removed to:", output_file)
        
    return need_removal