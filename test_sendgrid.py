#!/usr/bin/env python
"""
Test SendGrid email configuration
Run this locally to test if SendGrid credentials work
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_sendgrid():
    """Test SendGrid SMTP connection and send a test email"""
    
    # Get configuration from environment
    email_host = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
    email_port = int(os.environ.get('EMAIL_PORT', '587'))
    email_user = os.environ.get('EMAIL_HOST_USER', 'apikey')
    email_password = os.environ.get('EMAIL_HOST_PASSWORD', '')
    from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'test@example.com')
    
    print("=" * 60)
    print("SendGrid Configuration Test")
    print("=" * 60)
    print(f"EMAIL_HOST: {email_host}")
    print(f"EMAIL_PORT: {email_port}")
    print(f"EMAIL_HOST_USER: {email_user}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * 10}...{email_password[-10:] if email_password else 'NOT SET'}")
    print(f"DEFAULT_FROM_EMAIL: {from_email}")
    print("=" * 60)
    
    if not email_password:
        print("❌ ERROR: EMAIL_HOST_PASSWORD not set!")
        print("   Add your SendGrid API key to .env file:")
        print("   EMAIL_HOST_PASSWORD=SG.your_api_key_here")
        return False
    
    if email_user != 'apikey':
        print("❌ ERROR: EMAIL_HOST_USER should be 'apikey'")
        print(f"   Current value: {email_user}")
        return False
    
    # Test SMTP connection
    print("\n🔄 Testing SMTP connection...")
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        # Connect to SendGrid
        server = smtplib.SMTP(email_host, email_port, timeout=10)
        server.starttls()
        
        print("✅ Connected to SendGrid SMTP server")
        
        # Authenticate
        print("🔄 Authenticating...")
        server.login(email_user, email_password)
        print("✅ Authentication successful!")
        
        # Send test email
        test_email = input("\nEnter email address to send test to (or press Enter to skip): ").strip()
        
        if test_email:
            print(f"🔄 Sending test email to {test_email}...")
            
            msg = MIMEText("This is a test email from FinTrack. If you received this, SendGrid is configured correctly!")
            msg['Subject'] = 'FinTrack SendGrid Test'
            msg['From'] = from_email
            msg['To'] = test_email
            
            server.send_message(msg)
            print(f"✅ Test email sent successfully to {test_email}!")
            print("   Check your inbox (and spam folder)")
        
        server.quit()
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("   Check your SendGrid API key is correct")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    test_sendgrid()
