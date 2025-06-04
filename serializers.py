import datetime
import logging
from django.utils import timezone
from rest_framework import serializers
from django.db import transaction
from rail_sathi.models import RailSathiComplain, RailSathiComplainMedia
from trains.models import TrainDetails

class CustomDateField(serializers.DateField):
    def to_representation(self, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        return super().to_representation(value)


class RailSathiComplainMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RailSathiComplainMedia
        fields = '__all__'
        extra_kwargs = {
            'complain': {'read_only': True}
        }


class RailSathiComplainSerializer(serializers.ModelSerializer):
    complain_date = CustomDateField(format="%Y-%m-%d",
                                    input_formats=["%Y-%m-%d"],
                                    default=timezone.localdate)
    rail_sathi_complain_media_files = RailSathiComplainMediaSerializer(
        many=True, required=False)
    deleted_media_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = RailSathiComplain
        fields = '__all__'

    def get_train_number(self, obj):
        return obj.train.train_no if obj.train else None

    def validate(self, data):
        train = data.get('train', None)
        tn = data.get('train_number')
        tname = data.get('train_name')

        if train:
            if not isinstance(train, TrainDetails):
                raise serializers.ValidationError(
                    "If 'train' is provided, it must be a TrainDetails instance."
                )
            data['train_number'] = train.train_no
            data['train_name'] = train.train_name
        else:
            if not tn or not tname:
                raise serializers.ValidationError(
                    "If no 'train' PK is provided, both 'train_number' and "
                    "'train_name' must be set."
                )
            try:
                train = TrainDetails.objects.get(
                    train_no=tn)
                data['train'] = train
            except TrainDetails.DoesNotExist:
                logging.error(
                    f"Train with number {tn} and name {tname} does not exist. still creating complain."
                )
            
            
        if self.instance is None:
            media_data = data.get('rail_sathi_complain_media_files', [])
            image_count = sum(1 for item in media_data if item.get('media_type') == 'image')
            if image_count > 10:
                raise serializers.ValidationError("A maximum of 10 images is allowed per complain.")
        return data

    def create(self, validated_data):
        media_data = validated_data.pop('rail_sathi_complain_media_files', [])
        complain_instance = RailSathiComplain.objects.create(**validated_data)
        for media in media_data:
            RailSathiComplainMedia.objects.create(
                complain=complain_instance, **media)
        return complain_instance

    def update(self, instance, validated_data):
        media_data = validated_data.pop(
            'rail_sathi_complain_media_files', None)
        deleted_media_ids = validated_data.pop('deleted_media_ids', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            print(attr)
            print(value)
        instance.save()

        with transaction.atomic():
            if deleted_media_ids:
                instance.rail_sathi_complain_media_files.filter(
                    id__in=deleted_media_ids).delete()

            if media_data is not None:
                for media_item in media_data:
                    media_id = media_item.get('id', None)
                    if media_id:
                        try:
                            media_instance = instance.rail_sathi_complain_media_files.get(
                                id=media_id)
                            for key, value in media_item.items():
                                setattr(media_instance, key, value)
                            media_instance.save()
                        except RailSathiComplainMedia.DoesNotExist:
                            RailSathiComplainMedia.objects.create(
                                complain=instance, **media_item)
                    else:
                        RailSathiComplainMedia.objects.create(
                            complain=instance, **media_item)

            total_images = instance.rail_sathi_complain_media_files.filter(
                media_type='image').count()
            if total_images > 10:
                raise serializers.ValidationError(
                    "A maximum of 10 images is allowed per complain.")

        return instance
