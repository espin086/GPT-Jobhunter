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