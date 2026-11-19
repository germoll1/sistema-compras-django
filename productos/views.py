from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Categoria


@login_required
def inicio(request):
    return redirect("listado_categorias")


@login_required
def listado_categorias(request):
    return render(
        request,
        "productos/categoria.html",
        {"categorias": Categoria.objects.order_by("nombre")},
    )


@login_required
def listado_productos(request):
    productos = (
        Producto.objects.filter(activo=True)
        .select_related("categoria")
        .order_by("nombre")
    )
    categoria = None
    if request.GET.get("categoria"):
        categoria = get_object_or_404(Categoria, pk=request.GET["categoria"])
        productos = productos.filter(categoria=categoria)
    return render(
        request,
        "productos/listado.html",
        {"productos": productos, "categoria": categoria},
    )
