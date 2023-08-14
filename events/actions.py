from openpyxl import Workbook
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.db.models import Q
from datetime import datetime, date
from .export_excel import ExportExcelAction
from openpyxl.styles import Font
from unidecode import unidecode

from .utils import convert_data_date, convert_boolean_field


def style_output_file(file):
    black_font = Font(color="000000", bold=True)
    for cell in file["1:1"]:
        cell.font = black_font

    for column_cells in file.columns:
        length = max(len((cell.value)) for cell in column_cells if cell.value)
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
        "check",
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
                is_admin_field and not field == "check"
            ):  # check is also admin_field, but we need model field
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
