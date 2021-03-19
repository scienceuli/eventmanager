from django.core.exceptions import ValidationError

def csv_content_validator(csv_file):
    csv_file_content = csv_file.read() 