from backend.models import User
from django import forms

# Форма для регистрации пользователей
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('last_name', 'first_name', 'username', 'email', 'company', 'position')

    def clean_password2(self):
        "Проверка на совпадение пароля"
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Password don't match.")
        return cd['password2']

# Форма для авторизации пользователей
class LoginForm(forms.Form):
    username = forms.CharField(label='Email')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

