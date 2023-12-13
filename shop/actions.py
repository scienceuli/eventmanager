import csv
from datetime import datetime, date
from django.http import HttpResponse
from django.core.files.base import ContentFile


def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f"attachment; filename={opts.verbose_name}_{datetime.today().strftime('%Y-%m-%d')}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = content_disposition
    writer = csv.writer(response)
    fields = [
        field
        for field in opts.get_fields()
        if not field.many_to_many and not field.one_to_many
    ]
    # Write a first row with header information
    writer.writerow([field.verbose_name for field in fields])
    # Write data rows
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime):
                value = value.strftime("%d.%m.%Y")
            data_row.append(value)
        writer.writerow(data_row)
    return response


def download_invoices_as_zipfile(modeladmin, request, queryset):
    zipfile_name = f"rechnungen:{date.now()}"
    temp_file = ContentFile(b"", name=zipfile_name)
