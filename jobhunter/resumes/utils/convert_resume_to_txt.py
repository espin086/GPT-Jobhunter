import PyPDF2
import docx
import os
import argparse


FILE_PATH='/Users/jjespinoza/Documents/jobhunter'

def convert_to_txt(filepath, output_dir):
    """Converts a pdf or word file to plain text format and saves it in a different location.

    Args:
        filepath (str): The file path of the input file.
        output_dir (str): The directory path where the output file will be saved.

    Returns:
        str: The file path of the output file.
    """
    # Get the file extension
    file_ext = filepath.split('.')[-1]

    # Convert pdf to plain text
    if file_ext == 'pdf':
        with open(filepath, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ''
            for page in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page].extract_text()

    # Convert word document to plain text
    elif file_ext in ['doc', 'docx']:
        doc = docx.Document(filepath)
        text = ''
        for para in doc.paragraphs:
            text += para.text + '\n'

    # Save the plain text to a file in the output directory
    os.makedirs(output_dir, exist_ok=True)
    output_filepath = os.path.join(output_dir, 'resume.txt')
    with open(output_filepath, 'w', encoding='utf-8') as txt_file:
        txt_file.write(text)

    return output_filepath


if __name__ == "__main__": 
    filepath = input("Enter the filepath of the resume (including the file extension): ")
    output_filepath = convert_to_txt(filepath, f'{FILE_PATH}/jobhunter/resumes')
    print(f"The plain text file is saved at {output_filepath}")
