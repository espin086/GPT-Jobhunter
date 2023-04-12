import json
import os
import pandas as pd
import sqlite3

import jobhunter.utils.database

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

def update_database(df, db_file, table_name, key_column):

    # Connect to the SQLite database
    conn = sqlite3.connect(db_file)

    # Check for duplicates
    duplicates_query = f"SELECT {key_column} FROM {table_name}"
    duplicates = pd.read_sql(duplicates_query, conn)

    # Use the pandas `merge()` function to find rows that are not already in the SQLite database
    new_data = pd.merge(df, duplicates, on=key_column, how='left', indicator=True)
    new_data = new_data[new_data['_merge'] == 'left_only'].drop('_merge', axis=1)

    # Append the new data to the SQLite database
    new_data.to_sql(table_name, conn, if_exists='append', index=False)

    # Close the connection to the SQLite database
    conn.close()

def delete_local_json(directory):
    # Loop through all the files in the directory
    for filename in os.listdir(directory):
        # Create the full file path by joining the directory and filename
        file_path = os.path.join(directory, filename)
        
        # Check if the file is a file (not a directory) and if so, delete it
        if os.path.isfile(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    df = clean_data()
    update_database(df=df, db_file="../../data/jobhunter.db", table_name="jobs", key_column="job_url")
    delete_local_json(directory="../../data/temp/")

