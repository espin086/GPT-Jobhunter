import os

def menu():
    while True:
        print("╔══════════════════════════════╗")
        print("║         Job Hunter           ║")
        print("║     Find Your Dream Job      ║")
        print("╠══════════════════════════════╣")
        print("║    1. Search Jobs            ║")
        print("║    2. Upload Resume          ║")
        print("║    3. View Saved Jobs        ║")
        print("║    q. Quit                   ║")
        print("╚══════════════════════════════╝")

        choice = input("Enter your choice: ")

        if choice == '1':
            # Do search jobs
            pass
        elif choice == '2':
            # Do upload resume
            file_path = input("Enter the path to your resume file: ")
            if os.path.exists(file_path):
                os.system(f"python3 ../jobhunter/utils/file_converter.py {file_path}")
                os.system(f"python3 ../jobhunter/utils/job_title_generator.py --resume_file /Users/jjespinoza/Documents/jobhunter/jobhunter/resumes/resume.txt ")
            else:
                print("Invalid file path. Please try again.")





            pass
        elif choice == '3':
            # Do view saved jobs
            pass
        elif choice == 'q':
            print("Exiting program...")
            break
        else:
            print("Invalid choice. Please try again.")

menu()