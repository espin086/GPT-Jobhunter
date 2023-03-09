import os


# ask user for the value to set for the variable
print("INFO: you will need to create an OpenAI API Key to use this tool: https://openai.com/blog/openai-api")
ORGANIZATION = input("Enter your OPENAI_ORGANIZATION: ")
KEY = input("Enter your API KEY: ")


# export the environment variable in Bash
os.system(f"export OPENAI_ORGANIZATION={ORGANIZATION}")
os.system(f"export OPENAI_API_KEY={KEY}")