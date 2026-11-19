from django import forms
from cuentas.models import Direccion


class CheckoutForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs["class"] = "form-control"

    medio_pago = forms.ChoiceField(
        label="Medio de pago",
        choices=[
            ("transferencia", "Transferencia bancaria"),
            ("mercadopago", "Mercado Pago"),
        ],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Direccion
        fields = [
            "calle",
            "numero",
            "piso",
            "departamento",
            "ciudad",
            "provincia",
            "codigo_postal",
        ]
