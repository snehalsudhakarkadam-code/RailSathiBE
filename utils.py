import os
import io
import logging
import uuid
from datetime import datetime
from django.db import connection
from django.http import JsonResponse
from google.cloud import storage
from PIL import Image
from moviepy.editor import VideoFileClip
from django.conf import settings
from urllib.parse import unquote
from django.utils.text import get_valid_filename
from rail_sathi.models import RailSathiComplainMedia
from train_api.settings import DOMAIN, EMAIL_SENDER
from user_onboarding.models import Assign_Permission
from django.template.loader import render_to_string
from django.core.mail import EmailMessage


GCS_BUCKET_NAME = "sanchalak-media-bucket1"


def check_permission(user):
    assign = Assign_Permission.objects.filter(user=user).first()
    if assign or user.user_type.name == "railway admin" or user.user_type.name == "s2 admin":
        return True
    else:
        return False


def sanitize_timestamp(raw_timestamp):
    decoded = unquote(raw_timestamp)
    return get_valid_filename(decoded).replace(":", "_")


def process_media_file_upload(file_content, file_format, complain_id, media_type):
    try:
        created_at = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
        unique_id = str(uuid.uuid4())[:5]
        full_file_name = f"rail_sathi_complain_{complain_id}_{sanitize_timestamp(created_at)}_{unique_id}.{file_format}"

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = None

        if media_type == "image":
            file_stream = io.BytesIO(file_content)
            original_image = Image.open(file_stream)
            if original_image.mode == 'RGBA':
                original_image = original_image.convert('RGB')
            new_file = io.BytesIO()
            original_image.save(new_file, format='JPEG')
            new_file.seek(0)
            key = f"rail_sathi_complain_images/{full_file_name}"
            blob = bucket.blob(key)
            blob.upload_from_file(new_file, content_type='image/jpeg')
            logging.info(
                f"rail_sathi_complain_images Image uploaded: {full_file_name}")

        elif media_type == "video":
            try:
                temp_file_path = os.path.join(
                    settings.MEDIA_ROOT, 'temp_files', full_file_name)
                compressed_file_path = os.path.join(
                    settings.MEDIA_ROOT, 'temp_files', f"compressed_{full_file_name}")
                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(file_content)
                clip = VideoFileClip(temp_file_path)
                target_bitrate = '5000k'
                try:
                    clip.write_videofile(
                        compressed_file_path, codec='libx264', bitrate=target_bitrate)
                    clip.close()
                except Exception as e:
                    logging.error(f"Error compressing video: {e}")
                key = f"rail_sathi_complain_videos/{full_file_name}"
                blob = bucket.blob(key)
                with open(compressed_file_path, 'rb') as temp_file:
                    blob.upload_from_file(temp_file, content_type='video/mp4')
                logging.info(
                    f"rail_sathi_complain_videos Video uploaded: {full_file_name}")
            except Exception as e:
                logging.error(f'Error while storing video: {repr(e)}')
            finally:
                if os.path.exists(compressed_file_path):
                    os.remove(compressed_file_path)
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        if blob:
            try:
                url = blob.public_url
                logging.info(f"Uploaded file URL: {url}")
                return url
            except Exception as e:
                logging.error(f"Failed to get public URL: {e}")
                return None
        else:
            logging.error("Upload failed (blob is None)")
            return None
    except Exception as e:
        logging.error(f"Error processing media file: {e}")
        raise e


def upload_file_thread(file_obj, complain_id, user):
    try:
        file_content = file_obj.read()
        filename = file_obj.name
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()

        content_type = file_obj.content_type
        if content_type.startswith("image"):
            media_type = "image"
        elif content_type.startswith("video"):
            media_type = "video"
        else:
            logging.error(f"Unsupported media type for file: {filename}")
            return

        uploaded_url = process_media_file_upload(
            file_content, ext, complain_id, media_type)
        if uploaded_url:
            RailSathiComplainMedia.objects.create(
                complain_id=complain_id,
                media_type=media_type,
                media_url=uploaded_url,
                created_by=user,
            )
            logging.info(
                f"File uploaded and media record created for complaint {complain_id}: {uploaded_url}")
        else:
            logging.error(
                f"File upload failed for complaint {complain_id}: {filename}")
    except Exception as e:
        logging.error(f"Error in upload_file_thread for file {filename}: {e}")


def send_passenger_complain_email(compalin_details):
    war_room_user_in_depot = []
    train_depo = compalin_details['train_depo']
    try:
        query = "SELECT u.* FROM user_onboarding_user U JOIN user_onboarding_roles ut ON u.user_type_id = ut.id WHERE ut.name NOT IN  ('OBHS','EHK','CA'); "
        war_room_users = execute_sql_query(query)

        if war_room_users:
            for u in war_room_users:
                if u['depo']:
                    if (train_depo) in u['depo']:
                        war_room_user_in_depot.append(u)
        else:
            print("No war room users found")
            logging.info(
                f"No war room users found for depot {train_depo} in complain {compalin_details['complain_id']}")
    except Exception as e:
        print(f"Error fetching war room users: {e}")

    try:
        subject = f"Complain recieved for train number : {compalin_details['train_no']}"
        pnr_value = compalin_details.get('pnr')
        if not pnr_value:
            pnr_display = 'pnr is not filled by passenger'
        else :
            pnr_display = pnr_value
        context = {
            "user_phone_number": compalin_details['user_phone_number'],
            "passenger_name": compalin_details['passenger_name'],
            "train_no": compalin_details['train_no'],
            "train_name": compalin_details['train_name'],
            "pnr": pnr_display,
            "berth": compalin_details['berth'],
            "coach": compalin_details['coach'],
            "complain_id": compalin_details['complain_id'],
            "created_at": compalin_details['created_at'],
            "description": compalin_details['description'],
            'domain': 'ro.suvidhaen.com',
            'site_name': 'Website',
            'protocol': 'https',
        }

        message = render_to_string("email/ro_complain_submit.txt", context)

        for user in war_room_user_in_depot:
            if user['email']:
                if user['email'].startswith('noemail'):
                    logging.info(f"Skipping email: {user['email']}")
                    continue
                else:
                    send_plain_mail(subject, message, EMAIL_SENDER,
                                    [user['email']])
                    logging.info(
                        f"Sending email to {user['email']} for complain {compalin_details['complain_id']}")

        if not war_room_user_in_depot:
            logging.info(
                f"No war room users found for depot {train_depo} in complain {compalin_details['complain_id']}")
            return JsonResponse({"status": "success", "message": "No war room users found"})
    except Exception as e:
        logging.error(f"Error sending email: {e}")


def send_plain_mail(subject, message, from_, to):
    try:
        if isinstance(to, str):
            to = [to]
        elif not isinstance(to, list):
            raise ValueError(
                "Expected 'to' to be a string or a list of strings")

        valid_emails = []
        for email in to:
            if email.startswith('noemail'):
                logging.info(f"Skipping email: {email}")
            else:
                valid_emails.append(email)

        if not valid_emails:
            logging.info("All emails were skipped.")
            return True

        email = EmailMessage(subject, message, from_, valid_emails)
        email.content_subtype = "plain"
        logging.info(f" Sending mail to : {', '.join(email.to)}")
        email.send()
        logging.info("Mail sent successfully ")
        return True

    except Exception as e:
        logging.exception(f"An error occurred in send_txt_mail: {repr(e)}")
        return False


def execute_sql_query(sql_query):
    if not sql_query.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
