import streamlit as st
import sqlite3
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from data.data_access import init_db


# initialize database
init_db()


# Database functions
def add_applicant(
    first_name,
    last_name,
    email,
    phone_number,
    resume_path,
    preferred_job_title,
    preferred_location,
):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO applicants (first_name, last_name, email, phone_number, resume_path, preferred_job_title, preferred_location) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            first_name,
            last_name,
            email,
            phone_number,
            resume_path,
            preferred_job_title,
            preferred_location,
        ),
    )
    conn.commit()
    conn.close()


def get_all_applicants():
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute("SELECT * FROM applicants")
    data = c.fetchall()
    conn.close()
    return data


def update_applicant(id, **kwargs):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f"UPDATE applicants SET {key} = ? WHERE id = ?", (value, id))
    conn.commit()
    conn.close()


def delete_applicant(id):
    conn = sqlite3.connect("data/job_search.db")
    c = conn.cursor()
    c.execute("DELETE FROM applicants WHERE id = ?", (id,))
    conn.commit()
    conn.close()


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


def add_applicants_page():
    # Add Applicant Section
    st.subheader("Add Applicant")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")
    phone_number = st.text_input("Phone Number")
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF, Word, or TXT)", type=["pdf", "docx", "txt"]
    )
    preferred_job_title = st.text_input("Preferred Job Title")
    preferred_location = st.text_input("Preferred Location")

    if st.button("Add Applicant"):
        if uploaded_file is not None:
            resume_path = convert_resume(uploaded_file)
            add_applicant(
                first_name,
                last_name,
                email,
                phone_number,
                resume_path,
                preferred_job_title,
                preferred_location,
            )
            st.success("Added to database!")

    # Update and Delete Section
    # Update and Delete Section
    st.subheader("Update/Delete Applicant")

    applicant_list = get_all_applicants()
    applicant_names = ["Select"] + [f"{a[1]} {a[2]}" for a in applicant_list]
    selected_applicant_name = st.selectbox("Select Applicant", applicant_names)

    if selected_applicant_name != "Select":
        selected_applicant = [
            a for a in applicant_list if f"{a[1]} {a[2]}" == selected_applicant_name
        ][0]

        updated_first_name = st.text_input(
            "First Name", selected_applicant[1], key="updated_first_name"
        )
        updated_last_name = st.text_input(
            "Last Name", selected_applicant[2], key="updated_last_name"
        )
        updated_email = st.text_input(
            "Email", selected_applicant[3], key="updated_email"
        )
        updated_phone_number = st.text_input(
            "Phone Number", selected_applicant[4], key="updated_phone_number"
        )
        updated_preferred_job_title = st.text_input(
            "Preferred Job Title",
            selected_applicant[6],
            key="updated_preferred_job_title",
        )
        updated_preferred_location = st.text_input(
            "Preferred Location",
            selected_applicant[7],
            key="updated_preferred_location",
        )

        if st.button("Update Applicant"):
            update_applicant(
                selected_applicant[0],
                first_name=updated_first_name,
                last_name=updated_last_name,
                email=updated_email,
                phone_number=updated_phone_number,
                preferred_job_title=updated_preferred_job_title,
                preferred_location=updated_preferred_location,
            )
            st.success("Updated in database!")

        if st.button("Delete Applicant"):
            delete_applicant(selected_applicant[0])
            st.success("Deleted from database!")

    # Display all applicants
    st.subheader("All Applicants")
    applicants = get_all_applicants()

    # Convert the applicants data to a Pandas DataFrame
    df_applicants = pd.DataFrame(
        applicants,
        columns=[
            "ID",
            "First Name",
            "Last Name",
            "Email",
            "Phone Number",
            "Resume Text",
            "Preferred Job Title",
            "Preferred Location",
        ],
    )

    # Display the dataframe in Streamlit
    st.write(df_applicants)


def recommended_job_titles_page():
    st.title("Recommended Job Titles")
    # Here, you can add your logic to display recommended job titles


def find_best_jobs_with_ai_page():
    st.title("Find Best Jobs with AI")
    # Here, you can add your logic to find the best jobs using AI


# Main function to display pages based on menu choice
def main():
    # Streamlit app
    st.title("JobHunter")
    # Create the menu
    menu = ["Add Applicant", "Recommended Job Titles", "Find Best Jobs with AI"]
    choice = st.sidebar.radio("Menu", menu)

    # Display the selected page with the corresponding function
    if choice == "Add Applicant":
        add_applicants_page()
    elif choice == "Recommended Job Titles":
        recommended_job_titles_page()
    elif choice == "Find Best Jobs with AI":
        find_best_jobs_with_ai_page()


# Run the main function
if __name__ == "__main__":
    main()
