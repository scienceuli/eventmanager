import csv
from openpyxl import Workbook
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q
from datetime import datetime, date
from .export_excel import ExportExcelAction
from openpyxl.styles import Font
from unidecode import unidecode
from django.contrib import messages


from .utils import convert_data_date, convert_boolean_field

from .models import Event, EventMember


def style_output_file(file):
    black_font = Font(color="000000", bold=True)
    for cell in file["1:1"]:
        cell.font = black_font

    for column_cells in file.columns:
        if len(column_cells) > 0:
            length = max(
                len((cell.value))
                for cell in column_cells
                if cell.value and len(cell.value) > 0
            )
            length += 2
            file.column_dimensions[column_cells[0].column_letter].width = length

    return file


def export_as_xls(self, request, queryset):
    if not request.user.is_staff:
        raise PermissionDenied
    opts = self.model._meta
    # field_names = self.list_display
    field_names = [
        "lastname",
        "firstname",
        "street",
        "address_line",
        "company",
        "postcode",
        "country",
        "city",
        "phone",
        "email",
        "vfll",
        "agree",
        "date_created",
        "mail_to_admin",
    ]

    file_name = unidecode(opts.verbose_name)
    blank_line = []
    wb = Workbook()
    ws = wb.active
    ws.append(ExportExcelAction.generate_header(self, self.model, field_names))

    for obj in queryset:
        row = []
        for field in field_names:
            is_admin_field = hasattr(self, field)
            if (
                is_admin_field and not field == "agree"
            ):  # agree is also admin_field, but we need model field
                value = getattr(self, field)(obj)
            else:
                value = getattr(obj, field)
                if isinstance(value, datetime) or isinstance(value, date):
                    value = convert_data_date(value)
                elif isinstance(value, bool):
                    value = convert_boolean_field(value)
            row.append(str(value))
        ws.append(row)

    ws = style_output_file(ws)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={file_name}.xlsx"
    wb.save(response)
    return response


export_as_xls.short_description = "Export > Excel"


def import_from_csv(self, request, queryset):
    print(queryset)


def copy_member_instances(modeladmin, request, queryset):
    print("request.post:", request.POST)
    if "apply" in request.POST:

        event_id = request.POST.get("event")
        new_event = Event.objects.get(id=event_id)
        for obj in queryset:
            print(
                list(
                    EventMember.objects.filter(event=new_event).values_list(
                        "email", flat=True
                    )
                )
            )
            if obj.email not in list(
                EventMember.objects.filter(event=new_event).values_list(
                    "email", flat=True
                )
            ):
                obj.pk = None  # This will create a new instance
                obj.name = None
                obj.event = new_event  # Set the new event instance
                obj.save()
                modeladmin.message_user(
                    request, f"TN mit E-Mail {obj.email} wurde kopiert"
                )
            else:
                modeladmin.message_user(
                    request,
                    f"TN mit E-Mail {obj.email} gibt es bereits in {new_event}",
                )

        return HttpResponseRedirect(request.get_full_path())

    return render(
        request,
        "admin/copy_member_instances.html",
        context={
            "objects": queryset,
            "events": Event.objects.all(),
        },
    )


copy_member_instances.short_description = (
    "Ausgewählte TN kopieren und anderem Event zuordnen"
)


def export_members_to_csv(modeladmin, request, queryset):
    """
    Admin action to export selected members to a CSV file.

    """
    if not request.user.is_staff:
        raise PermissionDenied

    # filename
    today = date.today()
    filename = f"members_{today}.csv"

    # Define the response with CSV headers
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Dynamically get field names from the request, or use default fields
    fields_to_export = [
        "email",
        "firstname",
        "lastname",
        "email",
    ]

    # Write the header row
    # writer.writerow(fields_to_export)
    header_list = ["username", "firstname", "lastname", "email", "course1", "role1"]
    writer.writerow(header_list)

    # for course1 take event label = short name, role1 = 'student'

    # Write data rows
    for member in queryset:
        row = [getattr(member, field) for field in fields_to_export]
        writer.writerow(row)

    return response


export_members_to_csv.short_description = "Export > CSV (Vorname, Nachname, Email)"
