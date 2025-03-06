import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def send_email(model,email_to,results_file_location1,results_file_location2):
    smtp_port = 587
    smtp_server = "smtp.gmail.com"
    email_from = os.environ.get("GMAILID")

    pswd = os.environ.get("GMAILPASS")

    subject = f"Your {model} simulations are done! Results attached."

    for person in email_to:

        body = f"""
        
        Dear {person},
        
        Thank you for using {model}. Your simulations are now complete. Please find attached the results.
        
        Looking forward to more support.
        
        Regards,
        
        Team {model}
        
        """

        msg= MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = person
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        filename1= results_file_location1

        attachment1 = open(filename1, 'rb')

        attachment_package = MIMEBase('application','octet-stream')
        attachment_package.set_payload((attachment1).read())
        encoders.encode_base64(attachment_package)
        attachment_package.add_header('Content-Disposition',"attachment; filename= " + filename1[33:])
        msg.attach(attachment_package)

        filename2 = results_file_location2

        attachment2 = open(filename2, 'rb')

        attachment_package = MIMEBase('application', 'octet-stream')
        attachment_package.set_payload((attachment2).read())
        encoders.encode_base64(attachment_package)
        attachment_package.add_header('Content-Disposition', "attachment; filename= " + filename2[33:])
        msg.attach(attachment_package)

        text = msg.as_string()

        print("Connecting to server...")
        TIE_server = smtplib.SMTP(smtp_server, smtp_port)
        TIE_server.starttls()
        TIE_server.login(email_from, pswd)
        print("Successfully connected to server")
        print()

        print(f"Sending email to: {person}...")
        TIE_server.sendmail(email_from, person, text)
        print(f"Email sent to: {person}")
        print()

    TIE_server.quit()
