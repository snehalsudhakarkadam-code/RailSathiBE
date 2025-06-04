from django.contrib import admin
from rail_sathi.models import RailSathiComplain, RailSathiComplainMedia

class RailSathiComplainAdmin(admin.ModelAdmin):
    list_display = (
        'complain_id',
        'pnr_number',
        'is_pnr_validated',
        'name',
        'mobile_number',
        'complain_type',
        'complain_description',
        'complain_date',
        'complain_status',
        'train',
        'coach',
        'berth_no',
        'created_at',
        'created_by',
        'updated_at',
        'updated_by'
    )
    search_fields = (
        'pnr_number',
        'name',
        'mobile_number',
        'train__train_number',
        'created_by__username'
    )
    list_filter = ('complain_date', 'complain_status', 'created_at', 'updated_at')
    ordering = ('-created_at',)

class RailSathiComplainMediaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'complain',
        'media_type',
        'media_url',
        'created_at',
        'created_by',
        'updated_at',
        'updated_by'
    )
    search_fields = (
        'complain__pnr_number',
        'complain__train__train_number',
        'media_type'
    )
    list_filter = ('media_type', 'created_at')
    ordering = ('-created_at',)

admin.site.register(RailSathiComplain, RailSathiComplainAdmin)
admin.site.register(RailSathiComplainMedia, RailSathiComplainMediaAdmin)
