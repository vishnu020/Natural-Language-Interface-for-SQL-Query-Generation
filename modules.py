import google.generativeai as genai
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from prettytable import PrettyTable
import os
import streamlit as st
import pandas as pd
import sqlparse
import mysql.connector

with open("google_api_key.txt") as f:
    api_key = f.read().strip()
# Configure the API key
os.environ["GOOGLE_API_KEY"] = api_key
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-pro")

user = "root"
password = "ind123"
host = "localhost"
database = "skema"
PORT = 3306

# connecting the sql database
mydb = mysql.connector.connect(
    host=host, user=user, password=password, database=database
)
# initlise the cursor
mycursor = mydb.cursor()

def generate_column_descriptions(uploaded_files):
    column_descriptions = ""
    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split(".")[0]
        df = pd.read_csv(uploaded_file,encoding='latin-1')
        create_table_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join([f'{col} VARCHAR(255)' for col in df.columns])})"
        try:
            mycursor.execute(create_table_query)
        except mysql.connector.Error as err:
            print(f"Error creating table: {err}")

        # Insert data into the table
        for index, row in df.iterrows():
            values = tuple(row)
            insert_query = f"INSERT INTO `{table_name}` VALUES ({', '.join(['%s' for _ in range(len(values))])})"
            try:
                mycursor.execute(insert_query, values)
            except mysql.connector.Error as err:
                print(f"Error inserting data: {err}")
        


        columns = df.columns.tolist()
        column_descriptions += (
            f"There is the description of the columns of the table: {table_name}. "
        )
        prompt = """You are tasked with providing information about the columns in the dataset. 
                    Whenever you receive a column name, describe it succinctly in two lines, 
                    providing only relevant details about the columns present in the dataset.
                    Ensure there is a space between each column description.

                    Example 1:
                    {
                    "Column_name": CustomerName
                    "Description": Name of the customer as provided during registration.
                    "Data_type": String
                    }

                    Example 2:
                    {
                    "Column_name": City
                    "Description": City of the customer
                    "Data_type": Varchar
                    }
                    Note: Strictly follow the given response example format. 
                    Here are the columns of the provided table :
                    """
        final_prompt = prompt + str(columns)
        response = model.generate_content([final_prompt])
        response = response.text
        column_descriptions += (
            f"Please go through the description of each column to further understand in detail "
            f"about the use of each column: {response}\n"
        )
    return column_descriptions


def analyze_query(query, index):
    """
    Analyzes an SQL query to identify which columns from the respective tables would be required to generate it.
    Args:
        query (str): The SQL query to be analyzed.
    Returns:
        str: A summary of the identified columns from the respective tables, along with the reasoning for their selection.
    """

    prompt_msg = f"""
    Consider yourself an expert in SQL language. 
    Based on the following query, identify which columns from the respective tables would be required to generate a SQL query.

    {query} 

    Provide the column name along with the table name from which the columns are coming, and give the proper reasoning why these columns are selected.
    """
    query_engine = index.as_query_engine(response_mode="tree_summarize")
    response = query_engine.query(prompt_msg)
    return response

def generate_query(question, context):
    """
    Generates an SQL query based on the given question and context using a generative model.
    Args:
        question (str): The question specifying the desired SQL query.
        context (str): The context containing information about the columns and table names required for creating the SQL query.
    Returns:
        str: The generated SQL query, without ``` in the beginning or end and without the word "SQL" in the output.
    """

    prompt = f"""You are an advanced language model tasked with understanding and generating SQL queries based 
    on a given {context}. This context contains the information of the columns and the table name which are required for creating the
    SQL query specified in the {question}.The name of the database is {database}.

    Example 1: Give the count of customers who receive their product by economy class?

    SQL query:
    SELECT COUNT(*) AS EconomyClassCustomers
    FROM {database}.sql_case_study_data
    WHERE Ship_Mode = 'economy'

    Example 2: Name the customer from the country Sweden who receives paper as a shipment?

    SQL query:
    SELECT Customer_Name 
    FROM {database}.sql_case_study_data 
    WHERE Country = "Sweden" AND Sub_Category = "Paper"

    Note:Dont forget to add database name befor the table name 

    Also, the SQL code should not have ``` in the beginning or end and "SQL" should not be present in the output.
    """

    response = model.generate_content([question, prompt])
    response1 = response.text.replace("sql", "")
    response1 = response1.replace("```", "")
    return response1