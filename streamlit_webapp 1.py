import streamlit as st
import openai
import sql_streamlit_connection as sql_conn
import os
import pandas as pd
from google.cloud import storage
from sqlalchemy import create_engine
from PyPDF2 import PdfReader
from docx import Document
import io
import csv
import toml 

#Using to load configuration from config.toml
config = toml.load('config.toml')

#API from config file
openai.api_key = config['openai']['api_key']

#GCP Object credential
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config['gcp']['credentials_file_path']

#Initialising GCS client.
gcs_client = storage.Client()
 
#Will read the file directly from Google Cloud Storage.
def read_file_from_gcs(gcs_path):
    if not gcs_path or not gcs_path.startswith("gs://"):
        st.error(f"GCS path not valid: {gcs_path}")
        return None
    try:
        bucket_name = gcs_path.split('/')[2]
        file_path_in_gcs = '/'.join(gcs_path.split('/')[3:])
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(file_path_in_gcs)
        file_data = blob.download_as_bytes()
        st.write(f"Reading file from GCS: {gcs_path}")
        return file_data
    except Exception as e:
        st.error(f"Error in reading file from GCS: {e}")
        return None
 
#This function processes the file content depending on the type of file (text, PDF, Word, Excel), and prepares for Openai api.
def process_file(file_data, file_extension):
    try:
        if file_extension == ".txt":
            return file_data.decode('utf-8')
        elif file_extension == ".pdf":
            reader = PdfReader(io.BytesIO(file_data))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        elif file_extension == ".docx":
            doc = Document(io.BytesIO(file_data))
            return '\n'.join([para.text for para in doc.paragraphs])
        elif file_extension == ".xlsx":
            df = pd.read_excel(io.BytesIO(file_data))
            return df.to_string(index=False)
        else:
            st.error("File type not supported")
            return None
    except Exception as e:
        st.error(f"Error in processing the file: {e}")
        return None
 
#This function will send the question along with the file content to OpenAI
def send_question_with_file(question, file_data, file_extension):
    # File type based processing
    file_content = process_file(file_data, file_extension)
    
    # Checking if file is correctly processed
    st.write("Processed File Content:")
    st.write(file_content)
    
    if not file_content:
        st.error("No content found in the file.")
        return None
 
    # Sending the question and file content to openai api
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"{question}\n\nHere is the file content:\n{file_content}"}
            ]
        )
        return response
    except Exception as e:
        st.error(f"Error while calling OpenAI API: {e}")
        return None
 
#Function to decides if to send only the question or both the question and a file to OpenAI api(if a file is available)
def handle_openai_response_with_file(question, gcp_object_path):
    if not gcp_object_path or gcp_object_path.strip() == "":
        st.write("no file for question, Sending only the question to OpenAI.")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        )
        if response:
            openai_response = response['choices'][0]['message']['content'].strip()
            st.write("**Response from OpenAI:**")
            st.write(openai_response)
            return openai_response
        else:
            st.error("No response from OpenAI")
            return None
    else:
        file_data = read_file_from_gcs(gcp_object_path)
        if file_data is None:
            st.error("Cannot read file")
            return None
        file_extension = os.path.splitext(gcp_object_path)[1].lower()
        st.write(f"Extension of file checked: {file_extension}")
        response = send_question_with_file(question, file_data, file_extension)
        if response is not None:
            openai_response = response['choices'][0]['message']['content'].strip()
            st.write("Response from Openai:")
            st.write(openai_response)
            return openai_response
        else:
            st.error("No response from OpenAI.")
            return None
        
# Streamlit app layout
st.title("**OpenAI Based Evaluation Interface for GAIA Dataset Validation**")
 
# Fetch data from GCP SQL using sql_streamlit_connection
data = sql_conn.get_data_from_sql()
 
# Display the data in Streamlit
if not data.empty:
    st.write("**Data fetched successfully:**")
    st.dataframe(data)
else:
    st.write("No data found or error")
 
# Select a row to evaluate
selected_index = st.selectbox("**Select the row to evaluate**", data.index)
 
if selected_index is not None:
    selected_row = data.loc[selected_index]
    st.write(f"Question: {selected_row['question']}")
    st.write(f"**Dependency file:** {selected_row['file_name']}")
    step_choice = st.radio("**Choose Step**", ("Step 1 (Question only)", "Step 2 (Question + Steps)"))
   
    if step_choice == "Step 2 (Question + Steps)":
        st.write("Steps:")
        st.text_area("Steps", selected_row["steps"], height=100)
 
    if st.button(f"Get OpenAI Response and Compare for Row {selected_index + 1}"):
        openai_response = handle_openai_response_with_file(selected_row['question'], selected_row['gcp_object_path'])
       
        if openai_response:
            exact_match = openai_response == selected_row['final_answer']
            contains_match = selected_row['final_answer'] in openai_response
 
            match_result = "Exact Match" if exact_match else "Contains Match" if contains_match else "No Match"
           
            # Save only the required columns to local CSV
            with open('openai_responses.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([selected_row['task_id'], selected_row['question'], selected_row['final_answer'], match_result])
 
            st.write(f"**Comparison Results:** {match_result}")
 
            # Display the content of the CSV
            with open('openai_responses.csv', 'r') as file:
                st.write("**Summary Sheet:**")
                st.text(file.read())        