from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django import forms
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import HttpResponse

from .models import Event, EventMember

signer = TimestampSigner()

class EventQuestion(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=255)
    required = models.BooleanField(default=False)
    QUESTION_TYPES = (
        ('text', 'Text'),
        ('choice', 'Choice'),
        # Add other types if needed
    )
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    choices = models.TextField(blank=True, help_text="Comma-separated choices for choice type.")

class EventAnswer(models.Model):
    participant = models.ForeignKey(EventMember, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(EventQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()


def build_dynamic_answer_form(event, eventmember):
    class DynamicAnswerForm(forms.Form):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for question in event.questions.all():
                initial = ''
                try:
                    initial = eventmember.answers.get(question=question).answer_text
                except EventAnswer.DoesNotExist:
                    pass

                field_kwargs = {
                    'label': question.text,
                    'required': question.required,
                    'initial': initial,
                }
                if question.type == 'choice':
                    choices = [(c.strip(), c.strip()) for c in question.choices.split(',')]
                    self.fields[f'q_{question.id}'] = forms.ChoiceField(choices=choices, **field_kwargs)
                else:
                    self.fields[f'q_{question.id}'] = forms.CharField(**field_kwargs)
    
    return DynamicAnswerForm




def additional_info_view(request, signed_uuid):
    try:
        original_uuid = signer.unsign(signed_uuid, max_age=60*60*24*3)  # valid for 3 days
    except SignatureExpired:
        return HttpResponse("Der Link ist leider abgelaufen")
    except BadSignature:
        return HttpResponse("Ungültiger Link.")

    # Validate token (omitted here for brevity — see previous answer)
    eventmember = get_object_or_404(EventMember, uuid=original_uuid)
    event = eventmember.event

    # 👉 Build the dynamic form class
    DynamicForm = build_dynamic_answer_form(event, eventmember)

    if request.method == 'POST':
        form = DynamicForm(request.POST)
        if form.is_valid():
            # Save answers
            for field_name, value in form.cleaned_data.items():
                question_id = int(field_name.split('_')[1])
                question = EventQuestion.objects.get(pk=question_id)
                EventAnswer.objects.update_or_create(
                    participant=eventmember,
                    question=question,
                    defaults={'answer_text': value}
                )
            return render(request, 'events/additional_info_thank_you.html')
    else:
        form = DynamicForm()

    return render(request, 'events/additional_info_form.html', {
        'form': form,
        'eventmember': eventmember
    })

