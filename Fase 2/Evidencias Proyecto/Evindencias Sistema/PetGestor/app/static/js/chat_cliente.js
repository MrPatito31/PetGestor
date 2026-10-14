let convId = null;

function agregarMensaje(texto, origen) {
    const box = document.getElementById('chat-box');
    const div = document.createElement('div');
    div.classList.add('chat-bubble', origen);
    const etiqueta = origen === 'cliente' ? 'Usted'
        : origen === 'sistema' ? 'Asistente'
            : 'Administrador';
    div.innerHTML = `<small style="color:#666;">${etiqueta}</small><br>${texto}`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

async function iniciarChat() {
    const nombre = document.getElementById('nombre-input').value.trim();
    if (!nombre) { alert('Por favor ingrese su nombre.'); return; }
    const res = await fetch('/chat/iniciar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, asunto: 'Consulta general' })
    });
    const data = await res.json();
    convId = data.conversacion_id;
    document.getElementById('inicio-form').style.display = 'none';
    document.getElementById('mensaje-form').style.display = 'flex';
    agregarMensaje('Bienvenido al canal de atención de PetGestor. ¿En qué podemos orientarle hoy?', 'sistema');
}

async function enviarMensaje() {
    const input = document.getElementById('mensaje-input');
    const texto = input.value.trim();
    if (!texto || !convId) return;
    agregarMensaje(texto, 'cliente');
    input.value = '';
    const res = await fetch(`/chat/${convId}/enviar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: texto })
    });
    const data = await res.json();
    if (data.respuesta_automatica) {
        agregarMensaje(data.respuesta_automatica, 'sistema');
    } else if (data.mensaje_espera) {
        agregarMensaje(data.mensaje_espera, 'sistema');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('mensaje-input')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') enviarMensaje();
    });
});
