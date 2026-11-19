from django.db import migrations, models

ESTADOS = ["En preparación", "En tránsito", "Pendiente de entrega", "Entregado"]


def preparar_estados(apps, schema_editor):
    Estado = apps.get_model("envios", "EstadoEnvio")
    Envio = apps.get_model("envios", "Envio")
    alias = schema_editor.connection.alias
    nuevos = {
        nombre: Estado.objects.using(alias).get_or_create(nombre=nombre)[0]
        for nombre in ESTADOS
    }
    equivalencias = {
        "pendiente": "En preparación",
        "en preparacion": "En preparación",
        "en transito": "En tránsito",
        "pendiente de entrega": "Pendiente de entrega",
        "entregado": "Entregado",
    }
    import unicodedata

    for estado in Estado.objects.using(alias).exclude(nombre__in=ESTADOS):
        clave = "".join(
            c
            for c in unicodedata.normalize("NFD", estado.nombre.strip().lower())
            if unicodedata.category(c) != "Mn"
        )
        if clave not in equivalencias:
            raise RuntimeError("Estado de envío no reconocido: " + estado.nombre)
        Envio.objects.using(alias).filter(estado_id=estado.pk).update(
            estado_id=nuevos[equivalencias[clave]].pk
        )
        estado.delete(using=alias)


class Migration(migrations.Migration):
    dependencies = [("envios", "0001_initial")]
    operations = [
        migrations.RunPython(preparar_estados, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="estadoenvio",
            name="nombre",
            field=models.CharField(
                choices=[(s, s) for s in ESTADOS], max_length=50, unique=True
            ),
        ),
        migrations.AddConstraint(
            model_name="estadoenvio",
            constraint=models.CheckConstraint(
                condition=models.Q(nombre__in=ESTADOS), name="estado_envio_permitido"
            ),
        ),
        migrations.AlterField(
            model_name="envio",
            name="empresa_transporte",
            field=models.CharField("Empresa de transporte", blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="envio",
            name="numero_seguimiento",
            field=models.CharField("Número de seguimiento", blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="envio",
            name="fecha_envio",
            field=models.DateTimeField("Fecha de envío", blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="envio",
            name="fecha_entrega",
            field=models.DateTimeField("Fecha de entrega", blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="envio",
            name="costo_envio",
            field=models.DecimalField(
                "Costo de envío", decimal_places=2, max_digits=12, default=0
            ),
        ),
    ]
