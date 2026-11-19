# Sistema de compras Django

Proyecto académico de tienda de electrónica con Django y MariaDB, preparado para ejecutarse en localhost.

## Funciones

- Registro, inicio de sesión y navegación por categorías.
- Carrito privado por usuario y eliminación de productos.
- Checkout con dirección de entrega y validación de stock.
- Pedidos e historial de pagos accesibles únicamente por su propietario.
- Transferencia de demostración y configuración de Checkout Pro de Mercado Pago.
- Administración de pedidos y confirmación de transferencias desde Django Admin.
- Bootstrap incorporado al CSS local; el diseño no depende de un CDN.

## Ejecutar localmente

Requisitos: Python 3.13 y MariaDB compatible con Django 6.1.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `.env` con una clave privada de Django y la configuración de una base MariaDB local existente. Puede generarse una clave con:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

El nombre de la base, el usuario, la contraseña y el puerto deben coincidir con la instalación local. El puerto de ejemplo es 3307; adaptarlo si MariaDB usa otro. El usuario de MariaDB necesita permisos sobre esa base; para ejecutar las pruebas también debe poder crear y eliminar su base temporal de pruebas.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abrir http://127.0.0.1:8000/. Crear categorías y productos desde `/admin/`. El repositorio no incluye usuarios, contraseñas ni una copia de la base del autor.

Si PowerShell no permite activar el entorno, se puede usar directamente `.\.venv\Scripts\python.exe` en lugar de `python`, sin cambiar políticas del sistema.

## Credenciales y pagos

`.env` es privado y Git lo ignora. `.env.example` documenta las variables sin claves reales. Django lo carga automáticamente con `python-dotenv`; las variables del sistema tienen prioridad. No incluir respaldos de MariaDB, archivos con usuarios ni credenciales de Mercado Pago en commits.

Para Mercado Pago se requieren `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET` y `PUBLIC_BASE_URL` con HTTPS público, además de su dominio en `DJANGO_ALLOWED_HOSTS`. Registrar Webhooks de pagos en `/pagos/mercadopago/notificaciones/`. La prueba del flujo externo requiere credenciales de prueba y una URL HTTPS accesible; localhost solo no recibe notificaciones públicas.

El regreso del navegador no confirma un pago. El servidor valida la firma de la notificación y contrasta el pago mediante la API. Sin configurar Mercado Pago puede utilizarse transferencia. El alias y el correo incluidos son ficticios: no transferir dinero real.

El administrador confirma transferencias desde Pagos, después de revisar el comprobante. El stock se descuenta al confirmar el pedido; no hay liberación automática de stock de pedidos abandonados ni reintegros automáticos.

## Validación

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
```

Las pruebas usan una base temporal independiente. El proyecto está configurado para desarrollo académico local, no para un despliegue público de producción. Publicar el código en GitHub no publica la tienda ni su base de datos.
