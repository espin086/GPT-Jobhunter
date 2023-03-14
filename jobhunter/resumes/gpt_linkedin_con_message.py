from openai_models import generate_completion


def write_connection_message(company, title):
    my_prompt = f"""
    Write a maximum 50 character linkedin message to a person 
    who works at{company} about the {title}. 
    
    Mention that your 
    interest, skills,and background look like a perfect fit. 
    Let them know that you have applied to the job and
    ask them how to get the your resume more visibility?
    Thank them. Sign it JJ Espinoza

    Make it professional and engaging.
    """

    response = generate_completion("text-davinci-002", my_prompt, 0.7, 300)
    return response

def recruiter_message(company, title):
    print('-'*70)
    print(f"JOBHUNTER: message for people at: {company} for the {title} position")
    print('-'*70)
    message = write_connection_message( 
    company=company, 
    title=title)
    print(message)

if __name__ == "__main__":
    recruiter_message(company="Acme Company", title="Willie Coyote")


