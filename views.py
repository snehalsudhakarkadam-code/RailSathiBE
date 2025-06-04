import logging
import threading
from datetime import datetime
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from rail_sathi.models import RailSathiComplain
from rail_sathi.serializers import RailSathiComplainSerializer
from rail_sathi.utils import check_permission, send_passenger_complain_email, upload_file_thread
from trains.models import TrainDetails


@method_decorator(ratelimit(key='ip', rate='50/m', block=True), name='dispatch')
class RailSathiAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        url_name = request.resolver_match.url_name

        if url_name == "get-rail-sathi-complain-by-id":
            complain_id = kwargs.get('complain_id')
            complain = get_object_or_404(RailSathiComplain, pk=complain_id)
            serializer = RailSathiComplainSerializer(
                complain, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif url_name == "get-rail-sathi-complain-by-date":
            date_str = kwargs.get('date')
            try:
                complain_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            complains = RailSathiComplain.objects.filter(
                complain_date=complain_date)
            serializer = RailSathiComplainSerializer(
                complains, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid GET endpoint."},
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        if not check_permission(request.user):
            return Response(
                {"message": "Permission Denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        serializer = RailSathiComplainSerializer(
            data=data, context={'request': request})
        if serializer.is_valid():
            complaint_instance = serializer.save(created_by=request.user)
            complain_id = complaint_instance.complain_id

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, request.user))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})
            return Response(updated_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        if not check_permission(request.user):
            return Response(
                {"message": "Permission Denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        complain_id = kwargs.get('complain_id')
        complaint_instance = get_object_or_404(
            RailSathiComplain, pk=complain_id)

        if complaint_instance.complain_status == "completed" and \
           getattr(request.user, 'user_type', None) and request.user.user_type.name.lower() != "railway admin":
            return Response(
                {"error": "Completed complaint cannot be updated by non-railway admin users."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RailSathiComplainSerializer(
            complaint_instance, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, request.user))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})
            return Response(updated_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        if not check_permission(request.user):
            return Response(
                {"message": "Permission Denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        complain_id = kwargs.get('complain_id')
        complaint_instance = get_object_or_404(
            RailSathiComplain, pk=complain_id)

        if complaint_instance.complain_status == "completed" and \
           getattr(request.user, 'user_type', None) and request.user.user_type.name.lower() != "railway admin":
            return Response(
                {"error": "Completed complaint cannot be updated by non-railway admin users."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RailSathiComplainSerializer(
            complaint_instance, data=request.data, partial=False, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, request.user))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})
            return Response(updated_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        url_name = request.resolver_match.url_name
        if not check_permission(request.user):
            return Response(
                {"message": "Permission Denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        if url_name == "delete-rail-sathi-complain":
            complain_id = kwargs.get('complain_id')
            complaint_instance = get_object_or_404(
                RailSathiComplain, pk=complain_id)

            if complaint_instance.complain_status == "completed" and \
                    getattr(request.user, 'user_type', None) and request.user.user_type.name.lower() != "railway admin":
                return Response(
                    {"error": "Completed complaint cannot be updated by non-railway admin users."},
                    status=status.HTTP_403_FORBIDDEN
                )

            complaint_instance.delete()
            return Response({"message": "Complaint deleted successfully"},
                            status=status.HTTP_204_NO_CONTENT)
        elif url_name == "delete-image-rail-sathi-complain":
            complain_id = kwargs.get('complain_id')
            complaint_instance = get_object_or_404(
                RailSathiComplain, pk=complain_id)

            if complaint_instance.complain_status == "completed" and \
                    getattr(request.user, 'user_type', None) and request.user.user_type.name.lower() != "railway admin":
                return Response(
                    {"error": "Completed complaint cannot be updated by non-railway admin users."},
                    status=status.HTTP_403_FORBIDDEN
                )
            deleted_media_ids = request.data.get("deleted_media_ids", [])
            print(deleted_media_ids, 'deleted_media_ids')
            if not deleted_media_ids:
                return Response({"error": "No media IDs provided for deletion."},
                                status=status.HTTP_400_BAD_REQUEST)
            deleted_count, _ = complaint_instance.rail_sathi_complain_media_files.filter(
                id__in=deleted_media_ids).delete()
            if deleted_count == 0:
                return Response({"error": "No matching media files found for deletion."},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": f"{deleted_count} media file(s) deleted successfully."},
                            status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid DELETE endpoint."},
                            status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='50/m', block=True), name='dispatch')
class RoRailSathiAPI(APIView):

    def get(self, request, *args, **kwargs):
        url_name = request.resolver_match.url_name

        if url_name == "ro-get-rail-sathi-complain-by-id":
            complain_id = kwargs.get('complain_id')
            complain = get_object_or_404(RailSathiComplain, pk=complain_id)
            serializer = RailSathiComplainSerializer(
                complain, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif url_name == "ro-get-rail-sathi-complain-by-date":
            date_str = kwargs.get('date')
            mobile_number = request.GET.get('mobile_number')
            try:
                complain_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            complains = RailSathiComplain.objects.filter(
                complain_date=complain_date, mobile_number=mobile_number)
            serializer = RailSathiComplainSerializer(
                complains, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid GET endpoint."},
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = RailSathiComplainSerializer(
            data=data, context={'request': request})
        if serializer.is_valid():
            complaint_instance = serializer.save(created_by=data['name'])
            complain_id = complaint_instance.complain_id

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, data['name']))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})

            def _send_email(complaint_inst, complaint_id):
                try:
                    logging.info(
                        f"Email thread started for complaint {complaint_id}")
                    print(
                        f"Starting email thread for complaint {complaint_id}")

                    train_depo = ''
                    if complaint_inst.train:
                        train_number = complaint_inst.train.train_no
                        train_name = complaint_inst.train.train_name
                        train_depo = complaint_inst.train.Depot
                    else:
                        train_number = complaint_inst.train_number
                        train_name = complaint_inst.train_name
                        train_depo = TrainDetails.objects.filter(
                            train_no=train_number).first().Depot if train_number else ''


                    details = {
                        'train_no': train_number,
                        'train_name': train_name,
                        'user_phone_number': complaint_inst.mobile_number,
                        'passenger_name': complaint_inst.name,
                        'pnr': complaint_inst.pnr_number,
                        'berth': complaint_inst.berth_no,
                        'coach': complaint_inst.coach,
                        'complain_id': complaint_id,
                        'created_at': complaint_inst.created_at,
                        'description': complaint_inst.complain_description,
                        'train_depo': train_depo,
                    }
                    logging.info(
                        f"Sending email for complaint {complaint_id} to war room users")
                    send_passenger_complain_email(details)
                    logging.info(
                        f"Email sent successfully for complaint {complaint_id}")
                except Exception as e:
                    logging.error(
                        f"Email thread failure for complaint {complaint_id}: {str(e)}")

            try:
                email_thread = threading.Thread(
                    target=_send_email,
                    args=(complaint_instance, complain_id),
                    name=f"EmailThread-{complain_id}"
                )
                email_thread.daemon = True
                logging.info(
                    f"Starting email thread for complaint {complain_id}")
                email_thread.start()
                logging.info(
                    f"Email thread started with name {email_thread.name}")
            except Exception as e:
                logging.error(f"Failed to create email thread: {str(e)}")

            return Response(updated_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        complain_id = kwargs.get('complain_id')
        complaint_instance = get_object_or_404(
            RailSathiComplain, pk=complain_id)

        if complaint_instance.created_by == request.data['name'] and complaint_instance.complain_status != "completed" and complaint_instance.mobile_number == request.data['mobile_number']:
            return Response(
                {"error": "Only user who created the complaint can update it."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RailSathiComplainSerializer(
            complaint_instance, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.data['name'])

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, request.data['name']))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})
            return Response(updated_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        complain_id = kwargs.get('complain_id')
        complaint_instance = get_object_or_404(
            RailSathiComplain, pk=complain_id)

        if complaint_instance.created_by == request.data['name'] and complaint_instance.complain_status != "completed" and complaint_instance.mobile_number == request.data['mobile_number']:
            return Response(
                {"error": "Only user who created the complaint can update it."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RailSathiComplainSerializer(
            complaint_instance, data=request.data, partial=False, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.data['name'])

            threads = []
            files = request.FILES.getlist('rail_sathi_complain_media_files')
            for file_obj in files:
                t = threading.Thread(target=upload_file_thread, args=(
                    file_obj, complain_id, request.data['name']))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            complaint_instance.refresh_from_db()
            updated_serializer = RailSathiComplainSerializer(
                complaint_instance, context={'request': request})
            return Response(updated_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        url_name = request.resolver_match.url_name

        if url_name == "ro-delete-rail-sathi-complain":
            complain_id = kwargs.get('complain_id')
            complaint_instance = get_object_or_404(
                RailSathiComplain, pk=complain_id)

            if complaint_instance.created_by == request.data['name'] and complaint_instance.complain_status != "completed" and complaint_instance.mobile_number == request.data['mobile_number']:
                return Response(
                    {"error": "Only user who created the complaint can update it."},
                    status=status.HTTP_403_FORBIDDEN
                )

            complaint_instance.delete()
            return Response({"message": "Complaint deleted successfully"},
                            status=status.HTTP_204_NO_CONTENT)
        elif url_name == "ro-delete-image-rail-sathi-complain":
            complain_id = kwargs.get('complain_id')
            complaint_instance = get_object_or_404(
                RailSathiComplain, pk=complain_id)

            if complaint_instance.created_by == request.data['name'] and complaint_instance.complain_status != "completed" and complaint_instance.mobile_number == request.data['mobile_number']:
                return Response(
                    {"error": "Only user who created the complaint can update it."},
                    status=status.HTTP_403_FORBIDDEN
                )
            deleted_media_ids = request.data.get("deleted_media_ids", [])

            if not deleted_media_ids:
                return Response({"error": "No media IDs provided for deletion."},
                                status=status.HTTP_400_BAD_REQUEST)
            deleted_count, _ = complaint_instance.rail_sathi_complain_media_files.filter(
                id__in=deleted_media_ids).delete()
            if deleted_count == 0:
                return Response({"error": "No matching media files found for deletion."},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": f"{deleted_count} media file(s) deleted successfully."},
                            status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid DELETE endpoint."},
                            status=status.HTTP_400_BAD_REQUEST)
