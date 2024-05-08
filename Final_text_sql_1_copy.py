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
from modules import *

st.set_page_config(page_title="Text to SQL", page_icon=":bar_chart:", layout="wide")

if 'generated' not in st.session_state:
    st.session_state.generated = False

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

# Open the Google API key and take out the key
with open("google_api_key.txt") as f:
    api_key = f.read().strip()
# Configure the API key
os.environ["GOOGLE_API_KEY"] = api_key
genai.configure(api_key=api_key)

st.markdown(
    "<h1 style='text-align: center; '> Text to SQL </h1> ", unsafe_allow_html=True
)
model = genai.GenerativeModel("gemini-pro")
# Initiate LLM
Settings.llm = Gemini(model="gemini-pro")
Settings.embed_model = GeminiEmbedding(
    model_name="models/embedding-001", api_key=os.environ["GOOGLE_API_KEY"]
)

uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True)

if uploaded_files:

    column_descriptions = generate_column_descriptions(uploaded_files)
    with open(
        r"C:\Users\vishnu.singh\Downloads\text_to_sql\rag_text\column_descriptions.txt",
        "w",
    ) as file:
        file.write(column_descriptions)


# Read document
documents = SimpleDirectoryReader(
    input_dir=r"C:\Users\vishnu.singh\Downloads\text_to_sql\rag_text"
).load_data()

# Using the vetorstoreindex for storing the embeddings
index = VectorStoreIndex.from_documents(documents)
index.as_query_engine(llm=Gemini(model="gemini-pro"))

question = st.text_area("Enter your query here 👇")
response = analyze_query(question, index)
sql_query = generate_query(question, response)


if st.button("Generate SQL Query"):
    st.session_state.generated = True
    st.write("Selected columns:")
    st.write(response.response)
    st.write("Generated SQL Query:")
    st.code(sql_query, language="sql")
    
if st.session_state.generated == True:
    
    # Check if the button is clicked
    if st.button("Generate data"):
        # Execute the SQL query
        mycursor.execute(sql_query)
        columns = [desc[0] for desc in mycursor.description]
        rows = mycursor.fetchall()
        df = pd.DataFrame(rows, columns=columns)
        # Print the table

        df = df.drop_duplicates()
        st.code(sql_query, language="sql")
        st.title("Generated data from the table")
        st.table(df)
    # st.write("Please upload files to generate data.")
st.markdown(
    """
    <div style='bottom: 0px'>
        <strong>Note:</strong>
        <div>1. If you don't have the table then you need to give the table description e.g. table_name, column_names along with your query.</div>
        <div>2. If you have a table, just enter your query.</div>
    </div>
""",
    unsafe_allow_html=True,
)
mydb.commit()
mycursor.close()
mydb.close()
