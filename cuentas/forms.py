from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class RegistroUsuarioForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs["class"] = "form-control"

    email = forms.EmailField(required=True, label="Correo electrónico")

    first_name = forms.CharField(max_length=150, required=True, label="Nombre")

    last_name = forms.CharField(max_length=150, required=True, label="Apellido")

    class Meta:
        model = Usuario
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")

        return email
