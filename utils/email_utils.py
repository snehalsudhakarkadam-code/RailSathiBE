import logging
import asyncio
from fastapi_mail import FastMail, MessageSchema
from mail_config import conf
from jinja2 import Template
from typing import Dict, List
import os
from database import get_db_connection, execute_query  # Fixed import

EMAIL_SENDER = conf.MAIL_FROM

def send_plain_mail(subject: str, message: str, from_: str, to: List[str]):
    """Send plain text email"""
    try:
        # Filter valid emails
        valid_emails = [email for email in to if email and not email.startswith("noemail")]
        
        if not valid_emails:
            logging.info("All emails were skipped - no valid recipients.")
            return True

        # Create email message
        email = MessageSchema(
            subject=subject,
            recipients=valid_emails,  # This should be a list, not a string
            body=message,
            subtype="plain"
        )

        # Send email using FastMail
        fm = FastMail(conf)
        
        # Use asyncio to run the async send_message method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fm.send_message(email))
        loop.close()
        
        logging.info(f"Email sent successfully to: {', '.join(valid_emails)}")
        return True
        
    except Exception as e:
        logging.exception(f"Error in send_plain_mail: {repr(e)}")
        return False


def send_passenger_complain_email(complain_details: Dict):
    """Send complaint email to war room users"""
    war_room_user_in_depot = []
    train_depo = complain_details.get('train_depot', '')
    
    try:
        # Query to get war room users
        query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 'war room user'
        """
        
        conn = get_db_connection()
        war_room_users = execute_query(conn, query)
        conn.close()

        if war_room_users:
            for user in war_room_users:
                # Check if user's depot matches train depot
                user_depo = user.get('depo', '')
                if user_depo and train_depo and train_depo in user_depo:
                    war_room_user_in_depot.append(user)
        else:
            logging.info(f"No war room users found for depot {train_depo} in complaint {complain_details['complain_id']}")
            
    except Exception as e:
        logging.error(f"Error fetching war room users: {e}")

    try:
        # Prepare email content
        subject = f"Complaint received for train number: {complain_details['train_no']}"
        pnr_value = complain_details.get('pnr', 'PNR not provided by passenger')
        
        context = {
            "user_phone_number": complain_details.get('user_phone_number', ''),
            "passenger_name": complain_details.get('passenger_name', ''),
            "train_no": complain_details.get('train_no', ''),
            "train_name": complain_details.get('train_name', ''),
            "pnr": pnr_value,
            "berth": complain_details.get('berth', ''),
            "coach": complain_details.get('coach', ''),
            "complain_id": complain_details.get('complain_id', ''),
            "created_at": complain_details.get('created_at', ''),
            "description": complain_details.get('description', ''),
            "train_depo": complain_details.get('train_depo', ''),
            'site_name': 'RailSathi',
        }

        # Load and render template
        template_path = os.path.join("templates", "complaint_creation_email_template.txt")
        
        if not os.path.exists(template_path):
            # Fallback to inline template if file doesn't exist
            template_content = """
                Passenger Complaint Submitted

                A new passenger complaint has been received.

                Complaint ID   : {{ complain_id }}
                Submitted At  : {{ created_at }}

                Passenger Info:
                ---------------
                Name           : {{ passenger_name }}
                Phone Number   : {{ user_phone_number }}

                Travel Details:
                ---------------
                Train Number   : {{ train_no }}
                Train Name     : {{ train_name }}
                Coach          : {{ coach }}
                Berth Number   : {{ berth }}
                PNR            : {{ pnr }}

                Complaint Details:
                ------------------
                Description    : {{ description }}

                Train Depot    : {{ train_depo }}

                You can access this complaint via the portal:
                {{ protocol }}://{{ domain }}/admin/rail_sathi/railsathicomplain/{{ complain_id }}/change/

                Regards,  
                Team RailSathi
            """
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        
        template = Template(template_content)
        message = template.render(context)

        # Send emails to war room users
        emails_sent = 0
        # for user in war_room_user_in_depot:
        if True:
            # email = user.get('email', '')
            email = "harshnmishra01@gmail.com"
            if email and not email.startswith("noemail") and '@' in email:
                try:
                    success = send_plain_mail(subject, message, EMAIL_SENDER, [email])
                    if success:
                        emails_sent += 1
                        logging.info(f"Email sent to {email} for complaint {complain_details['complain_id']}")
                    else:
                        logging.error(f"Failed to send email to {email}")
                except Exception as e:
                    logging.error(f"Error sending email to {email}: {e}")

        # if not war_room_user_in_depot:
        if emails_sent == 0:
        
            # logging.info(f"No war room users found for depot 'train_depo' in complaint {complain_details['complain_id']}")
            logging.info("No email was sent to any user.")
            return {"status": "success", "message": "No war room users found for this depot"}
        
        return {"status": "success", "message": f"Emails sent to {emails_sent} war room users"}
        
    except Exception as e:
        logging.error(f"Error in send_passenger_complain_email: {e}")
        return {"status": "error", "message": str(e)}


def execute_sql_query(sql_query: str):
    """Execute a SELECT query safely"""
    if not sql_query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    conn = get_db_connection()
    try:
        results = execute_query(conn, sql_query)
        return results
    finally:
        conn.close()