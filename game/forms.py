from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class':'w-full px-3 py-2 rounded-lg bg-gray-800 text-gray-200'
    }))

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tailwind classes on inputs:
        for fld in self.fields.values():
            fld.widget.attrs.update({
                'class': 'w-full px-3 py-2 rounded-lg bg-gray-800 text-gray-200'
            })
