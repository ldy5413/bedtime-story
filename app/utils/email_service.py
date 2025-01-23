import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import random
import string

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def send_verification_email(to_email, verification_code):
    """Send verification email to user"""
    try:
        # Get email configuration from app config
        smtp_server = current_app.config['SMTP_SERVER']
        smtp_port = current_app.config['SMTP_PORT']
        smtp_username = current_app.config['SMTP_USERNAME']
        smtp_password = current_app.config['SMTP_PASSWORD']
        sender_email = current_app.config['SENDER_EMAIL']

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = "Email Verification - Bedtime Story Generator"

        # Create HTML body
        html = f"""
        <html>
            <body>
                <h2>Welcome to Bedtime Story Generator!</h2>
                <p>Thank you for registering. Please use the following verification code to complete your registration:</p>
                <h1 style="color: #3498db;">{verification_code}</h1>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't request this verification, please ignore this email.</p>
            </body>
        </html>
        """
        
        message.attach(MIMEText(html, "html"))

        # Create SMTP session
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)

        return True
    except Exception as e:
        current_app.logger.error(f"Error sending verification email: {str(e)}")
        return False 