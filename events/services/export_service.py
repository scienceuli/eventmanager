import csv
from datetime import date, datetime

import pandas as pd
from django.db.models import Count, Q
from django.http import HttpResponse
from openpyxl import Workbook

from events.actions import style_output_file
from events.export_excel import ExportExcelAction
from events.models import Event, EventMember
from events.parameters import has_vote_transfer
from events.utils.utils import convert_boolean_field, convert_data_date


class ExportService:
    def export_members_csv(self, event_label):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{event_label}_TN_{date.today()}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Vorname", "Nachname", "E-Mail", "Datum", "Mitgliedschaft"])

        members = EventMember.objects.filter(event__label=event_label).values_list(
            "firstname",
            "lastname",
            "email",
            "date_created",
            "member_type",
        )

        for member in members:
            member = list(member)
            member[3] = member[3].strftime("%d.%m.%y %H:%M")
            writer.writerow(member)

        return response

    def export_mv_members_csv(self, event_label, filters=None):
        filters = filters or {}

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="teilnehmer_{date.today()}.csv"'
        )

        writer = csv.writer(response)
        header = ["Vorname", "Nachname", "E-Mail", "Status", "Datum", "Mitgliedschaft"]

        if has_vote_transfer.get(event_label, None):
            header.extend(
                ["Stimmübertragung", "Check Stimmübertragung", "Einverständnis MV"]
            )
        writer.writerow(header)

        members_mv = EventMember.objects.filter(event__label=event_label)

        if filters.get("firstname"):
            members_mv = members_mv.filter(firstname__icontains=filters["firstname"])
        if filters.get("lastname"):
            members_mv = members_mv.filter(lastname__icontains=filters["lastname"])
        if filters.get("email"):
            members_mv = members_mv.filter(email__icontains=filters["email"])
        if filters.get("vote_transfer_yes"):
            members_mv = members_mv.exclude(vote_transfer__exact="")
        if filters.get("vote_transfer_no"):
            members_mv = members_mv.filter(vote_transfer__exact="")

        base_fields = [
            "firstname",
            "lastname",
            "email",
            "attend_status",
            "date_created",
            "member_type",
        ]

        if has_vote_transfer.get(event_label, None):
            extra_fields = ["vote_transfer", "vote_transfer_check", "agree"]
            members_mv = members_mv.values_list(*(base_fields + extra_fields))
        else:
            members_mv = members_mv.values_list(*base_fields)

        for member in members_mv:
            member = list(member)
            member[4] = member[4].strftime("%d.%m.%y %H:%M")
            writer.writerow(member)

        return response

    def export_ft_members_csv(self, event_label="ffl_mv_2024"):
        response = HttpResponse(content_type="text/csv")
        today = datetime.today().strftime("%Y-%m-%d")
        response["Content-Disposition"] = (
            f"attachment; filename='members_ft_{today}.csv'"
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Vorname",
                "Nachname",
                "E-Mail",
                "Adresszusatz",
                "Straße",
                "PLZ",
                "Ort",
                "Tel.",
                "Anmeldedatum",
                "Workshop",
                "WS-Alternative",
                "MV",
                "Mittagessen",
                "Führung",
                "Netzwerkabend",
                "Yoga",
                "Feier",
                "Essenswunsch",
                "Mitgliedschaft",
                "kein Mitglied",
                "Bemerkung",
            ]
        )

        members_ft = EventMember.objects.filter(event__label=event_label)

        for member in members_ft:
            values = list(member.data.values())
            writer.writerow(values)

        return response

    def export_ft_members_xls(self, event_label="ffl_mv_2026"):
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        today = datetime.today().strftime("%Y-%m-%d")
        output_name = f"members_ft_{today}.xlsx"
        response["Content-Disposition"] = f"attachment; filename={output_name}"

        ftm = EventMember.objects.filter(event__label=event_label).values(
            "lastname",
            "firstname",
            "email",
            "address_line",
            "street",
            "postcode",
            "city",
            "data",
        )

        result = [
            {
                "lastname": item["lastname"],
                "firstname": item["firstname"],
                "email": item["email"],
                "address_line": item["address_line"],
                "street": item["street"],
                "postcode": item["postcode"],
                "city": item["city"],
                **item["data"],
            }
            for item in ftm
        ]

        df = pd.DataFrame(result)
        df = df[
            [
                "lastname",
                "firstname",
                "email",
                "address_line",
                "street",
                "postcode",
                "city",
                "takes_part_in_mv",
                "ws2026",
                "tour",
                "dinner_one",
                "dinner_two",
                "food_preferences",
                "food_remarks",
                "memberships",
                "remarks",
            ]
        ]
        df.columns = [
            "Nachname",
            "Vorname",
            "E-Mail",
            "Adresszusatz",
            "Strasse",
            "PLZ",
            "Stadt",
            "Teilnahme MV",
            "WS",
            "Rahmenprogramm",
            "Abendessen Fr",
            "Abendessen Sa",
            "Essenswuensche",
            "Essen Bem.",
            "Mitgliedschaften",
            "Bem.",
        ]
        df.to_excel(response)

        return response

    def export_moodle_participants(self, event):
        participants = event.members.all().filter(attend_status="registered")
        today = date.today()
        filename = f"members_{event.label}_{today}.csv"

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            ["username", "firstname", "lastname", "email", "course1", "role1"]
        )

        fields_to_export = ["email", "firstname", "lastname", "email"]

        for member in participants:
            row = [getattr(member, field) for field in fields_to_export]
            row.append(event.label)
            row.append("student")
            writer.writerow(row)

        return response

    def export_participants_xls(self, event, version):
        from events.admin import EventMemberAdmin

        if version == "controlling":
            field_names = [
                "lastname",
                "firstname",
                "academic",
                "company",
                "street",
                "postcode",
                "city",
                "phone",
                "email",
                "get_memberships_boolean",
                "get_no_memberships_boolean",
                "date_created",
                "get_order_nr",
                "get_order_price",
                "get_payment_receipt",
            ]
            file_name = f"Controlling_{event.label}_{datetime.now().date()}"
            sheet_title = "Controlling"
        elif version == "participants":
            field_names = [
                "lastname",
                "firstname",
                "academic",
                "phone",
                "email",
            ]
            file_name = f"TeilnehmerInnen_{event.label}_{datetime.now().date()}"
            sheet_title = "TeilnehmerInnen"

        blank_line = []
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_title

        ws.append(
            ExportExcelAction.generate_header(
                EventMemberAdmin, EventMember, field_names
            )
        )

        qs_event_members = event.members.all()
        qs_event_members_registered = qs_event_members.filter(
            Q(attend_status="registered")
        ).annotate(vfll_true=Count("vfll", filter=Q(vfll=True)))
        admin_cls = EventMemberAdmin

        self._iterate_members(ws, qs_event_members_registered, admin_cls, field_names)

        if version == "controlling":
            qs_event_members_waiting = qs_event_members.filter(
                Q(attend_status="waiting")
            )
            ws.append(blank_line)
            ws.append(["", "Warteliste"])
            self._iterate_members(ws, qs_event_members_waiting, admin_cls, field_names)

            ws.append(blank_line)
            ws.append(["", "Referentinnen"])
            for speaker in event.speaker.all():
                ws.append(["", speaker.last_name, speaker.first_name, speaker.email])

            ws.append(blank_line)
            ws.append(["", "Veranstaltungsdaten"])
            ws.append(["", "Veranstaltungstitel:", event.name])
            ws.append(["", "Veranstaltungsformat:", event.eventformat.name])
            ws.append(
                [
                    "",
                    "Termin:",
                    (
                        datetime.strftime(event.first_day, "%d.%m.%Y")
                        if event.first_day
                        else ""
                    ),
                ]
            )
            ws.append(["", "Ort:", event.location.title])
            ws.append(
                [
                    "",
                    "Veranstalter:",
                    event.organizer.name if event.organizer else "",
                ]
            )

        ws = style_output_file(ws)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f"attachment; filename={file_name}.xlsx"
        wb.save(response)
        return response

    def _iterate_members(self, ws, queryset, admin_cls, field_names):
        from django.contrib import admin

        model_class = EventMember
        admin_cls_instance = admin_cls(model_class, admin.site)
        counter = 1
        for obj in queryset:
            row = [str(counter)]
            for field in field_names:
                is_admin_field = hasattr(admin_cls, field)
                if is_admin_field and not field == "agree":
                    method = getattr(admin_cls_instance, field)
                    value = method(obj)
                    if isinstance(value, bool):
                        value = convert_boolean_field(value)
                else:
                    value = getattr(obj, field)
                    if isinstance(value, datetime) or isinstance(value, date):
                        value = convert_data_date(value)
                    elif isinstance(value, bool):
                        value = convert_boolean_field(value)
                    elif value is None:
                        value = ""

                row.append(str(value))

            ws.append(row)
            counter += 1
