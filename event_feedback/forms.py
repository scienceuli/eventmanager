from django import forms

class SurveyForm(forms.Form):
    consent = forms.BooleanField(required=True)
    final_comment = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, survey=None, **kwargs):
        super().__init__(*args, **kwargs)

        for question in survey.categories.all().prefetch_related("questions"):
            for q in question.questions.all():
                self.fields[f"rating_{q.id}"] = forms.ChoiceField(
                    choices=[(i, i) for i in range(1, 6)],
                    widget=forms.RadioSelect,
                    label=q.text
                )
                self.fields[f"comment_{q.id}"] = forms.CharField(
                    widget=forms.Textarea,
                    required=False,
                    label="Comment"
                )
