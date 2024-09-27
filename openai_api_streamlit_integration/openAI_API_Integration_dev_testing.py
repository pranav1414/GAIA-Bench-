#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import openai
import os
import pandas as pd
import PyPDF2
from docx import Document
import json
from PyPDF2 import PdfReader

# Set your OpenAI API key
openai.api_key = ' I have removed hard coded key'

# Function to transcribe audio using Whisper API
def transcribe_audio(file_path):
    audio_file = open(file_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript['text']

# Function to extract text from a .txt file
def extract_text(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# Function to extract text from a PDF file
def extract_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to extract text from a Word (.docx) file
def extract_docx(file_path):
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# Function to extract text from an Excel (.xlsx) file
def extract_excel(file_path):
    df = pd.read_excel(file_path)
    return df.to_string(index=False)

# Function to determine the type of file and extract/transcribe its content
def process_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.mp3' or file_extension == '.wav':
        return transcribe_audio(file_path)
    elif file_extension == '.txt':
        return extract_text(file_path)
    elif file_extension == '.pdf':
        return extract_pdf(file_path)
    elif file_extension == '.docx':
        return extract_docx(file_path)
    elif file_extension == '.xlsx':
        return extract_excel(file_path)
    else:
        return "Unsupported file type."

# Function to send a question with file content to OpenAI Chat API
def send_question_with_file(question, file_path):
    # Process the file based on its type
    file_content = process_file(file_path)
    
    # Send the question along with the file content to OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": f"{question}\n\nHere is the file content:\n{file_content}"}
        ]
    )
    
    return response

# Example usage
question =""" """
file_path = ""


# Call the function and get the response
response = send_question_with_file(question, file_path)

# Print the response from OpenAI
print(response['choices'][0]['message']['content'].strip())

