import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import NewsletterSubscription, EmailTemplate
from .forms import EmailTemplateForm


def unsubscribe(request, email):
    try:
        subscription = NewsletterSubscription.objects.get(email=email)
        subscription.delete()
        messages.success(request, "Du hast dich von Newsletter abgemeldet.")
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, "E-Mail nicht gefunden.")
    return redirect("home")  # Redirect to a page after unsubscribing


def subscribe(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        email = post_data.get("email", None)
        newsletter_subscription = NewsletterSubscription()
        newsletter_subscription.email = email
        newsletter_subscription.save()
        # send a confirmation mail
        subject = "Newsletter Anmeldung VFLL Fortbildungen"
        message = "Hallo, vielen Dank für das Interessen an unserem Newsletter. Bitte nicht auf diese Mail antworten."
        email_from = settings.NEWSLETTER_EMAIL_FROM
        recipient_list = [
            email,
        ]
        send_mail(subject, message, email_from, recipient_list)
        res = JsonResponse({"msg": "Danke! Newsletter-Anmeldung war erfolgreich!"})
        return res
    return render(request, "index.html")


def validate_email(request):
    email = request.POST.get("email", None)
    if email is None:
        res = JsonResponse({"msg": "E-Mail-Adresse ist notwendig."})
    elif NewsletterSubscription.objects.get(email=email):
        res = JsonResponse({"msg": "Diese E-Mail-Adresse ist bereits registriert."})
    elif not re.match(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", email):
        res = JsonResponse({"msg": "Ungültige E-Mail-Adresse"})
    else:
        res = JsonResponse({"msg": ""})
    return res

@login_required
def create_newsletter(request):
    context = {}
    form = EmailTemplateForm(request.POST or None) 

    if request.method == "POST":
        if form.is_valid():
            form.instance.created_by = request.user
            form.save()
            return redirect("newsletter:newsletter-list")
        
    context['form']= form     
    return render(request, "simple_newsletter/edit_newsletter.html", context)

@login_required
def newsletter_list(request):
    newsletters = EmailTemplate.objects.all()
    context = {
        "newsletters": newsletters
    }
    return render(request, "simple_newsletter/newsletter_list.html", context)

@login_required
def send_newsletter(request, pk):
    obj = EmailTemplate.objects.get(pk=pk)
    obj = get_object_or_404(EmailTemplate, pk=pk)

    subject = obj.subject
    print('obj body:', obj.body)

    if obj.use_mjml and not obj.sent_at:
        html_message = render_to_string(
            "simple_newsletter/email_template.html",
            {
                "body": obj.body,
            },
        )
    else:
        html_message = obj.body
            
    plain_message = strip_tags(html_message)

    recipients = [subscriber.email for subscriber in obj.recipients.all()]
    if not recipients:
        recipients = [
            subscriber.email
            for subscriber in NewsletterSubscription.objects.all()
        ]
    from_email = settings.NEWSLETTER_EMAIL_FROM

    send_mail(
        subject,
        plain_message,
        from_email,
        recipients,
        fail_silently=False,
        html_message=html_message,
    )

    obj.sent_at = obj.created_at
    obj.save()

    return redirect("newsletter:newsletter-list")

ALL_RECIPIENTS_ID = "__all__"


@login_required
def edit_newsletter(request, pk):
    obj = EmailTemplate.objects.get(pk=pk)

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=obj)
        if form.is_valid():
            nl_instance = form.save(commit=False)
            nl_instance.save()  
            recipients = form.cleaned_data['recipients']
            
            nl_instance.recipients.set(recipients)

            return redirect("newsletter:newsletter-list")
    else:
        form = EmailTemplateForm(instance=obj)

        
    context = {
        "obj": obj,
        "form": form
    }
    return render(request, "simple_newsletter/edit_newsletter.html", context)

@login_required
def copy_newsletter(request, pk):
    original = get_object_or_404(EmailTemplate, pk=pk)

    if original:
        new_template = EmailTemplate.objects.get(pk=pk)
        new_template.pk = None
        new_template.subject += " (Koipe)"
        new_template.title += " (Koipe)"
        new_template.created_by = request.user
        new_template.sent_at = None
        new_template.save()

        messages.success(request, "Newsletter wurde kopiert.")
        
        return redirect("newsletter:edit-newsletter", pk=new_template.pk)
    
    messages.error(request, "Newsletter konnte nicht kopiert werden.")

    return redirect("newsletter:newsletter-list")

@login_required
def delete_newsletter(request, pk):
    obj = get_object_or_404(EmailTemplate, pk=pk)

    obj.status = 'c'
    obj.save()

    newsletters = EmailTemplate.objects.filter(status='a').order_by('created_at').reverse()
    return render(request, 'simple_newsletter/_newsletter_table.html', {'newsletters': newsletters})

@login_required
def preview_newsletter(request, pk):
    template = get_object_or_404(EmailTemplate, pk=pk)

    if template.use_mjml:
        html = render_to_string(
            "simple_newsletter/email_template.html",
            {
                "body": template.body,
            },
        )
    else:
        html = template.body  # fallback if not using MJML

    return HttpResponse(html)

    
    
    
        
