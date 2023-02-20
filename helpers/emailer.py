"""A module for sending job application emails.
This module contains functions for building and sending an email for a job application. The email is sent through a Gmail account, and the credentials for the account are retrieved from environment variables EMAIL and EMAIL_PASSWORD. A blind carbon copy (BCC) is also sent to bump@go.rebump.cc.
The module contains the following functions:
send_email(email, subject, body): Sends an email to a recipient with a given subject and body.
build_email(name, role, company, link): Builds an email body for a job application.
build_subject(name, role, company): Builds an email subject for a job application.
main(name, email, role, company, link): Sends an email for a job application using the provided recipient information and job details.
"""
import logging
import os
from email.message import EmailMessage
import ssl
import smtplib
import argparse


logging.basicConfig(level=logging.INFO)



def send_email(email, subject, body):
	"""Sends an email to a recipient with a given subject and body.
    This function uses the smtplib library to send an email through a Gmail account. The email account 
    credentials are retrieved from environment variables EMAIL and EMAIL_PASSWORD. A blind carbon copy 
    (BCC) is also sent to bump@go.rebump.cc.
    Args:
        email (str): The email address of the recipient.
        subject (str): The subject of the email.
        body (str): The body of the email.
    Returns:
        None
    """
	email_sender = os.environ.get('EMAIL')
	email_password = os.environ.get('EMAIL_PASSWORD')
	email_receiver = email
	email_bcc = "bump@go.rebump.cc"
	
	em = EmailMessage()
	em['From'] = email_sender
	em['To'] = email_receiver
	em['Bcc'] = email_bcc
	em['Subject'] = subject
	em.set_content(body)
	
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
		try:
			smtp.login(email_sender, email_password)
			smtp.sendmail(email_sender, email_receiver, em.as_string())
			logging.info(f"Email sent to {email_receiver} with subject: {subject}")
		except Exception as e:
			logging.error(f"Error sending email to {email_receiver}: {e}")
			
	return None
	


def build_email(name, role, company, link):
	
	"""Builds an email body for a job application.
    
    This function takes in the recipient's name, the job role, the company name, and a link to the job listing.
    It then builds a formatted email body with the provided information, including a greeting, a brief 
    description of the job, and a call to action to schedule an interview.
    Args:
        name (str): The recipient's name.
        role (str): The job role being applied for.
        company (str): The name of the company the job is with.
        link (str): The link to the job listing.
    Returns:
        str: The email body as a string.
    """
	
	body = """
{0},
I recently came across a role at {2} that I feel would be a perfect fit for me. Here is the link: {3}. I would like to schedule some time to speak with you about this role. Please find my resume attached for your review and schedule a time with me using the links below.
- My Resume: https://drive.google.com/file/d/1gQhwJXHcom1m1nYXJaoFHPhTp6RCdi66/view
- Schedule a Call: https://calendly.com/jj-espinoza-la/interview-jj-espinoza
Please let me know if you have any issues with the link or if there are any other materials you would like me to provide. I look forward to hearing from you soon.
Best regards,
JJ Espinoza
	""".format(name, role, company, link)
	return body
	
def build_subject(name, role, company):
	"""Builds an email subject for a job application.
    
    This function takes in the recipient's name, the job role, and the company name.
    It then builds an email subject using the provided information.
    Args:
        name (str): The recipient's name.
        role (str): The job role being applied for.
        company (str): The name of the company the job is with.
    Returns:
        str: The email subject as a string.
    """
	
	
	subject = "{0}, I love the {1} role at {2}. Let's set up a call?".format(name, role, company)
	return subject



def main(name, email, role, company, link):
	"""Sends an email for a job application.
    
    This function takes in the recipient's name, email, the job role, the company name, and the link to the job posting.
    It then calls the build_subject and build_email functions to construct the subject and body of the email.
    Finally, it calls the send_email function to send the email.
    
    Args:
        name (str): The recipient's name.
        email (str): The recipient's email address.
        role (str): The job role being applied for.
        company (str): The name of the company the job is with.
        link (str): The link to the job posting.
        
    Returns:
        None
    """
	subject = build_subject(name=name, role=role, company=company)
	body = build_email(name=name, role=role, company = company, link = link)
	send_email(email=email, subject=subject, body=body)
	return None
	
	
if __name__ == "__main__":
	
	parser = argparse.ArgumentParser(description="Emails a recruiter about a job role I want to interview about")
	parser.add_argument('name', metavar='name', type=str, help='enter name of recruiter')
	parser.add_argument('email', metavar='email', type=str, help='enter email of recruiter')
	parser.add_argument('role', metavar='role', type=str, help='role you are interested in')
	parser.add_argument('company', metavar='company', type=str, help='name of company')
	parser.add_argument('link', metavar='link', type=str, help='link to job posting')
	
	args = parser.parse_args()
	
	main(name=args.name, email=args.email, role=args.role, company=args.company, link=args.link)
