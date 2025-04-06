"""
Email utility functions for MedicineAI
"""
import os
import smtplib
import random
import string
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Gmail SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USERNAME = "dorktech007@gmail.com"
SMTP_PASSWORD = "cpyy-mhhv-cvch-fmeb"

logger = logging.getLogger(__name__)

def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(recipient_email, otp):
    """
    Send OTP via email using Gmail SMTP
    
    Args:
        recipient_email (str): Recipient's email address
        otp (str): The OTP to send
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "MedicineAI - Your OTP for Login"
        message["From"] = SMTP_USERNAME
        message["To"] = recipient_email
        
        # Create HTML content with OTP
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #173430; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .otp-box {{ background-color: #f5f5f5; padding: 15px; font-size: 24px; font-weight: bold; 
                           text-align: center; margin: 20px 0; letter-spacing: 5px; }}
                .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>MedicineAI</h1>
                </div>
                <div class="content">
                    <h2>Your One-Time Password (OTP)</h2>
                    <p>Hello,</p>
                    <p>Your OTP for logging into MedicineAI is:</p>
                    <div class="otp-box">{otp}</div>
                    <p>This OTP is valid for 10 minutes. Please do not share this with anyone.</p>
                    <p>If you did not request this OTP, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 MedicineAI. All rights reserved.</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML content
        part = MIMEText(html, "html")
        message.attach(part)
        
        # Connect to SMTP server and send email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, message.as_string())
            
        logger.info(f"OTP email sent to {recipient_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send OTP email: {str(e)}")
        return False