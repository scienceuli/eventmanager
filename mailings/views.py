import os
from django.http import HttpResponse
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def view_emails(request):
    email_dir = settings.EMAIL_FILE_PATH
    if not os.path.exists(email_dir):
        return HttpResponse("<h2>Keine Emails gefunden.</h2>")

    emails = []

    for filename in sorted(os.listdir(email_dir), reverse=True):  # Show latest first
        filepath = os.path.join(email_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            email_content = f.read()

        emails.append({"filename": filename, "content": email_content})

    return render(request, "admin/sent_emails.html", {"emails": emails})
