import openpyxl
from openpyxl.styles import NamedStyle

from datetime import datetime
from django.http import HttpResponse
from django.db.models import DecimalField, FloatField, IntegerField
from decimal import Decimal


from utilities.pdf import render_to_pdf_directly


def export_to_excel_short(modeladmin, request, queryset):
    response = export_to_excel(modeladmin, request, queryset, short=True)
    return response


def export_to_excel(modeladmin, request, queryset, short=False):
    # decimal_style = NamedStyle(name="decimal_style", number_format="0,00")
    decimal_style = NamedStyle(name="decimal_style", number_format="###0.00")
    wb = openpyxl.Workbook()
    if "decimal_style" not in wb.named_styles:
        wb.add_named_style(decimal_style)
    ws = wb.active
    ws.title = "Rechnungen Export"
    opts = modeladmin.model._meta
    fields_no_export = [
        "uuid",
    ]

    if short:
        fields = [
            "invoice_number",
            "get_full_name_and_events",
            "amount",
            "invoice_date",
        ]
    else:
        fields = [
            field
            for field in opts.get_fields()
            if not field.many_to_many
            and not field.one_to_many
            and field.name not in fields_no_export
        ]

    # Define the header row
    if short:
        headers = [
            "Belegfeld",
            "Buchungstext",
            "Umsatz",
            "Datum",
            "Konto",
            "Gegenkonto",
            "S/H Kennzeichen",
        ]
    else:
        headers = [field.verbose_name for field in fields]
        headers.append("Betrag")
    ws.append(headers)

    # Append data rows
    for obj in queryset:
        data_row = []
        numeric_columns = []
        if short:
            for col_idx, field in enumerate(fields, start=1):
                if hasattr(obj, field):
                    value = getattr(obj, field)
                    # If it's a method, call it
                    value = value() if callable(value) else value
                    # print(
                    #     f"Field: {field}, Value: {value}, Type: {type(value)}"
                    # )  # Debugging line
                    if isinstance(value, datetime):
                        value = value.strftime("%d.%m.%Y")
                    if isinstance(
                        value, (int, float, DecimalField, FloatField, Decimal)
                    ):
                        value = (
                            float(value) if value is not None else 0.00
                        )  # Convert to float
                        numeric_columns.append(col_idx)
                    data_row.append(value)
            data_row.extend(["10000", "8000", "S"])
        else:
            for field in fields:
                value = getattr(obj, field.name)
                if isinstance(value, datetime):
                    value = value.strftime("%d.%m.%Y")
                data_row.append(value)
                data_row.append(obj.get_total_cost())
        ws.append(data_row)
        last_row = ws.max_row
        for col_idx in numeric_columns:
            ws.cell(row=last_row, column=col_idx).style = decimal_style

    filename = f"{opts.verbose_name}_{datetime.today().strftime('%Y-%m-%d')}"
    if short:
        filename = filename + "_kurz"

    # Prepare the response
    content_disposition = f"attachment; filename={filename}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = content_disposition

    wb.save(response)

    return response
