import re
import pandas as pd

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

def manual_check(final_vars, ex_vars=None):
    print("Continue to review of", len(final_vars), 'variables?')
    status = input("y/n: ")
    if status == "y":
        stig_vars_df = go_through_df(final_vars)
    else:
        stig_vars_df = None
        
    if ex_vars is not None:
        print("Would you like to review the excluded variables?")
        ex_var_review = input('Type "yes" or "no": \n')
        if ex_var_review == 'yes':
            ex_vars_df = go_through_df(ex_vars)
    else:
        ex_vars_df = None
        
    return stig_vars_df, ex_vars_df

def go_through_df(var_list):
    df = pd.DataFrame(var_list, columns=['full name'])
    df['simple name'] = ''
    df['stigmatizing'] = ''
    total = len(var_list)
    
    for i in range(df.shape[0]):
        simple_var = df['full name'][i].strip('\\').split('\\')[-1]
        df['simple name'][i] = simple_var
        print("Is the following variable stigmatizing?\t", i, "of", total)
        print("\n>>>>", simple_var, "<<<<\n")
        status = input('Type "yes" or "no". To display full variable, type "more": \n')
        if status == 'back':
            i = i-1
            simple_var = df['full name'][i].strip('\\').split('\\')[-1]
            df['simple name'][i] = simple_var
            print("Is the following variable stigmatizing?")
            print("\n>>>>", simple_var, "<<<<\n")
            status = input('Type "yes" or "no". To display full variable, type "more": \n')
        if status == 'more':
            print('\n>>>>', df['full name'][i], '<<<<\n')
            status = input('Type "yes" or "no": \n')
        df['stigmatizing'][i] = status
        
    return df