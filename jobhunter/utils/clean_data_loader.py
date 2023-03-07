import json
import os
import pandas as pd


def load_to_pandas():

    # Set the directory path where the JSON files are located
    directory_path = '../../data/temp/'

    # Create an empty list to store the data
    data_list = []

    # Loop through the files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            # Open the JSON file and load the data
            with open(os.path.join(directory_path, filename), 'r') as json_file:
                data = json.load(json_file)
            
            # Replace the salary array with the maximum value
            if data.get('salary'):
                data['salary'] = max(data['salary'], default=0)
            else:
                data['salary'] = 0

            # Drop the email key
            data.pop('email', None)

            # Append the updated data to the list
            data_list.append(data)

    # Create a pandas dataframe from the list of data
    df = pd.DataFrame(data_list)
    return df

def drop_columns(df, columns_to_drop):
    """
    Drops columns from a pandas DataFrame.
    
    Args:
        df (pandas.DataFrame): The DataFrame to modify.
        columns_to_drop (list): A list of column names to drop.
    
    Returns:
        pandas.DataFrame: The modified DataFrame with columns dropped.
    """
    return df.drop(columns_to_drop, axis=1)

def rename_columns(df):
    df = df.rename(columns={
        'linkedin_job_url_cleaned': 'job_url',
        'linkedin_company_url_cleaned': 'company_url',
        'job_title': 'title',
        'job_location': 'location',
        'posted_date': 'date',
        'normalized_company_name': 'company_name',
        'job_description': 'description',
        'resume_similarity': 'resume_sim',
        'salary': 'salary_max'
    })
    return df

def clean_data():
    df = load_to_pandas()
    df = drop_columns(df, ['job_url', 'company_name', 'company_url', 'emails'])
    df = rename_columns(df)
    df = df.drop_duplicates()
    # Convert all text values in the dataframe to lowercase
    df = df.apply(lambda x: x.str.lower() if x.dtype == 'object' else x)
    df['resume_sim'] = df['resume_sim'].round(3)
    # convert the float column to an integer column
    df['salary_max'] = df['salary_max'].astype(int)
    return df

if __name__ == "__main__":
    df = clean_data()
    print(df.columns())

