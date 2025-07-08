from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import (AuthenticationForm, PasswordResetForm,
                                       SetPasswordForm, UserCreationForm)

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

class PwdResetForm(PasswordResetForm):

    email = forms.EmailField(max_length=254, widget=forms.TextInput(
        attrs={'class': 'form-control mb-3', 'placeholder': 'Email', 'id': 'form-email'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        u = User.objects.filter(email=email)
        if not u:
            raise forms.ValidationError(
                'Leider gibt es keinen User mit dieser E-Mail.')
        return email
    
class PwdResetConfirmForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='Neues Passwort', widget=forms.PasswordInput(
            attrs={'class': 'form-control mb-3', 'placeholder': 'Neues Passwort', 'id': 'form-newpass'}))
    new_password2 = forms.CharField(
        label='Neues Passwort wiederholen', widget=forms.PasswordInput(
            attrs={'class': 'form-control mb-3', 'placeholder': 'Neues Passwort', 'id': 'form-new-pass2'}))




class EmailValidationOnForgotPassword(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"]
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            msg = (
                "Es existiert leider kein registrierter User mit dieser E-Mail-Adresse."
            )
            self.add_error("email", msg)
        return email

