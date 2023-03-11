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
            os.system(f"python3 ../jobhunter/run_linkedin_bot.py")
            print("JOBHUNTER: Slaving away to find you the perfect job... take a coffee break, we'll be done in 21 mins!")
            time.sleep(60)
            print("JOBHUNTER: We're using our top secret AI tech to match you with your dream job...hope you're ready to impress your future boss!")
            time.sleep(120)
            print("JOBHUNTER: We'll even figure out how to get you paid what you deserve...because let's face it, you're worth it!")
            time.sleep(780)
            print("JOBHUNTER: Just a heads up, we're putting the final touches on your job matches... only 5 more minutes to go! Better start stretching those fingers for all the job applications you'll be filling out soon ;)")
            time.sleep(300)
            print("JOBHUNTER: Ta-da! We've worked our magic and found you some amazing job matches. Hit enter 3 and let's check them out!")

            os.system(f"python3 ../jobhunter/utils/database.py")
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