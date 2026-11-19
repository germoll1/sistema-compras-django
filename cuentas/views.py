from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required

from .forms import RegistroUsuarioForm

from .models import Perfil


@login_not_required
def registro(request):

    if request.method == "POST":

        formulario = RegistroUsuarioForm(request.POST)

        if formulario.is_valid():

            usuario = formulario.save()

            Perfil.objects.get_or_create(usuario=usuario)

            login(request, usuario)

            return redirect("inicio")

    else:

        formulario = RegistroUsuarioForm()

    contexto = {"formulario": formulario}

    return render(request, "cuentas/registro.html", contexto)


from django.contrib import messages
from django.contrib.auth.views import LoginView


class TiendaLoginView(LoginView):
    template_name = "cuentas/login.html"
    redirect_authenticated_user = True

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "form-control"
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Bienvenido a nuestra tienda virtual")
        return response
