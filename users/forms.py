from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "type": "text", "placeholder": "Username"}
        )
    )
    password = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "password",
                "placeholder": "Password",
            }
        )
    )


class EmailValidationOnForgotPassword(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"]
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            msg = (
                "Es existiert leider kein registrierter User mit dieser E-Mail-Adresse."
            )
            self.add_error("email", msg)
        return email
