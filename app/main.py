import streamlit as st
import pandas as pd
import openai

from data.data_access import (
    init_db,
    add_applicant,
    get_all_applicants,
    update_applicant,
    delete_applicant,
)
from logic.process_data import convert_resume
from logic.gpt import generate_completion

# initialize database
init_db()


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
    st.subheader("Recommended Job Titles")

    # Fetch and list applicants
    applicant_list = get_all_applicants()
    applicant_names = ["Select"] + [f"{a[1]} {a[2]}" for a in applicant_list]
    selected_applicant_name = st.selectbox("Select Applicant", applicant_names)

    if selected_applicant_name != "Select":
        selected_applicant = [
            a for a in applicant_list if f"{a[1]} {a[2]}" == selected_applicant_name
        ][0]

        # Fetch the resume text for the selected applicant
        resume_text = selected_applicant[5]

        # Truncate or otherwise reduce the size of the resume text
        max_resume_length = 1000  # This is an arbitrary number; adjust as needed
        if len(resume_text.split()) > max_resume_length:
            resume_text = " ".join(resume_text.split()[:max_resume_length]) + "..."

        if st.button("Get Recommended Job Titles"):
            # Make the API call
            prompt = f"Based on the following resume give me the top 5 new job titles for this person (not on resume), provide a brief description for each job and rank them by highest to lowest salary, provide a salary range Low-High for reach role: {resume_text}"
            response = generate_completion("text-davinci-003", prompt, 0.5, 2400)
            st.write(response)


def find_best_jobs_with_ai_page():
    st.subheader("Find Best Jobs with AI")
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
