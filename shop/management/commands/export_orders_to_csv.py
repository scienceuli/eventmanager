import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from shop.models import Order  # Replace YourModel with your actual model


class Command(BaseCommand):
    help = "Export query results to CSV file"

    def add_arguments(self, parser):
        # Define the command line arguments
        parser.add_argument(
            "date", type=str, help="Specify the date in YYYY-MM-DD format"
        )

    def handle(self, *args, **kwargs):
        date_str = kwargs["date"]
        try:
            # Parse the date string to a datetime object
            specified_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            self.stderr.write(self.style.ERROR("Invalid date format. Use YYYY-MM-DD"))
            return

        # Your query goes here
        queryset = Order.objects.filter(mail_sent_date__date=specified_date)
        # CSV file path
        csv_file_path = "orders_sent.csv"

        # Writing the CSV file
        with open(csv_file_path, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)

            # Write header row if needed
            csv_writer.writerow(
                [
                    "Rechnungsnr",
                    "Vorname",
                    "Nachname",
                    "Email",
                    "Bezahltyp",
                    "angelegt am",
                    "Rechnungsdatum",
                    "Rechnung verschickt",
                ]
            )

            # Write data rows
            for item in queryset:
                csv_writer.writerow(
                    [
                        item.get_order_number,
                        item.firstname,
                        item.lastname,
                        item.email,
                        item.payment_type,
                        item.date_created,
                        item.payment_date,
                        item.mail_sent_date,
                    ]
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully exported data to {csv_file_path}")
        )
