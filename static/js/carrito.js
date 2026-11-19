document.querySelectorAll('.btn-agregar').forEach(boton => {
    boton.addEventListener('click', async () => {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const estado = document.getElementById('estado-carrito');
        boton.disabled = true;
        document.getElementById('resultado-carrito').hidden = false;
        try {
            const respuesta = await fetch(boton.dataset.url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': token
                },
                credentials: 'same-origin'
            });
            if (respuesta.redirected) {
                window.location.assign(respuesta.url);
                return;
            }
            const datos = await respuesta.json();
            estado.textContent = respuesta.ok ? `${datos.producto}: ${datos.cantidad} en tu carrito.` : (datos.error || 'No se pudo agregar el producto.');
        } catch {
            estado.textContent = 'No se pudo conectar. Intentá nuevamente.';
        } finally {
            boton.disabled = false;
        }
    });
});
