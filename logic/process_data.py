from PyPDF2 import PdfReader
from docx import Document
import streamlit as st


def convert_resume(uploaded_file):
    with st.spinner("Converting resume..."):
        try:
            # Determine the format based on file extension
            file_type = uploaded_file.name.split(".")[-1]

            if file_type == "pdf":
                # For PDFs
                reader = PdfReader(uploaded_file)
                text = ""
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text()

            elif file_type in ["doc", "docx"]:
                # For Word documents
                doc = Document(uploaded_file)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            elif file_type == "txt":
                # For Text files
                text = uploaded_file.read().decode("utf-8")

            else:
                st.error("Unsupported file type!")
                return None

            return text

        except Exception as e:
            st.error(f"Error converting file: {e}")
            return None
