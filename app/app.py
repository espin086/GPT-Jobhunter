import os
import re
import time

def menu():
    while True:
        print("╔════════════════════════════════╗")
        print("║            Job Hunter          ║")
        print("║        Job hunt, simplified!   ║")
        print("╠════════════════════════════════╣")
        print("║    0. Let's get Started!       ║")
        print("║    1. Show off Your Resume!    ║")
        print("║    2. Hunt for Those Jobs!     ║")
        print("║    3. Dig into your top picks! ║")
        print("║    4. Recruiters, at top picks!║")
        print("║    q. Quit, But Why?           ║")
        print("╚════════════════════════════════╝")

        choice = input("Enter your choice: ")

        if choice == '0':
            os.system(f"python3 ../jobhunter/utils/envconfig.py")
        
        elif choice == '1':
            # Do upload resume
            file_path = input("Enter the path to your resume file: ")
            if os.path.exists(file_path):
                os.system(f"python3 ../jobhunter/utils/file_converter.py {file_path}")
                os.system(f"python3 ../jobhunter/utils/job_title_generator.py --resume_file /Users/jjespinoza/Documents/jobhunter/jobhunter/resumes/resume.txt ")
            else:
                print("Invalid file path. Please try again.")
            pass

        elif choice == '2':
            os.system(f"python3 ../jobhunter/utils/database.py")
            os.system(f"python3 ../jobhunter/run_linkedin_bot.py")
            os.system(f"python3 ../jobhunter/utils/clean_data_loader.py")
            print("INFO: all done! Checkout your matching jobs by pressing entering 3!")
            pass
        
        elif choice == '3':
            # Do view saved jobs
            os.system(f"python3 ../jobhunter/utils/get_latest_jobs.py")
            pass

        elif choice == '4':
            # Open up linkedin search for recruiters for top pics
            os.system(f"python3 ../jobhunter/utils/linkedin_recruiter_outreach.py")
            pass


        elif choice == 'q':
            print("Exiting program...")
            break
        else:
            print("Invalid choice. Please try again.")

menu()