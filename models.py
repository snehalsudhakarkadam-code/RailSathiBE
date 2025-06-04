from django.db import models
from django.utils import timezone 
from trains.models import TrainDetails

class RailSathiComplain(models.Model):
    COMPLAIN_CHOICES = [
        ('cleaning', 'Cleaning Issues'),
        ('linen', 'Linen Issues')
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]
    PNR_VALIDATION_STATUS_CHOICES = [
        ('attempted-success', 'Attempted & Success'),
        ('attempted-failure', 'Attempted & Failure'),
        ('not-attempted', 'Not Attempted'),
    ]
    complain_id = models.AutoField(primary_key=True)
    pnr_number = models.CharField(max_length=20, null=True, blank=True)
    is_pnr_validated = models.CharField(
        max_length=50,
        choices=PNR_VALIDATION_STATUS_CHOICES,
        default='not-attempted',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    complain_type = models.CharField(max_length=20, choices=COMPLAIN_CHOICES, null=True, blank=True)
    complain_description = models.TextField(null=True, blank=True)
    complain_date = models.DateField(null=True, blank=True, default=timezone.now)
    complain_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    train = models.ForeignKey(TrainDetails, on_delete=models.CASCADE, null=True, blank=True)
    train_number = models.CharField(max_length=20, null=True, blank=True)
    train_name = models.CharField(max_length=100, null=True, blank=True)
    coach = models.CharField(max_length=100, null=True, default='', blank=True)
    berth_no = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

class RailSathiComplainMedia(models.Model):
    MEDIA_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    complain = models.ForeignKey(
        RailSathiComplain, 
        related_name='rail_sathi_complain_media_files', 
        on_delete=models.CASCADE
    )
    media_type = models.CharField(max_length=50, null=True, blank=True, choices=MEDIA_CHOICES)
    media_url = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
