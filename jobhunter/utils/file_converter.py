import PyPDF2
import docx

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
    output_filepath = f"{output_dir}/{filepath.split('/')[-1].split('.')[0]}.txt"
    with open(output_filepath, 'w', encoding='utf-8') as txt_file:
        txt_file.write(text)

    return output_filepath




input_filepath = '/Users/jjespinoza/Downloads/test_resume.pdf'
output_dir = '../resumes'
output_filepath = convert_to_txt(input_filepath, output_dir)
print(f"The plain text file is saved at {output_filepath}")
