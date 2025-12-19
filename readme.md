# 🎬 Gestor de Clientes y Proyectos de Video

Este proyecto es básicamente mi **salvavidas mental** para no perder la cabeza gestionando clientes, vídeos y estados de pago.  
Porque tener 50 carpetas, 200 vídeos y recordar quién pagó qué… es para gente con memoria de elefante 🐘

Este gestor centraliza **clientes, proyectos de video, estados, referencias y subidas a plataformas** en una sola app bonita que no te hace querer lanzar el monitor por la ventana 😅

---

## 🧠 ¿Qué hace exactamente? (versión sin tecnicismos)

Es un **panel de control** para gestionar todos tus clientes y sus vídeos:

- Creas clientes
- Añades vídeos a cada cliente
- Asignas estados (pendiente, revisión, pagado, terminado)
- Ves miniaturas de los vídeos
- Subes directamente a **YouTube** y **Google Drive**
- Mantienes referencias y archivos organizados automáticamente

Todo desde una sola interfaz.  
Sin Excel. Sin caos. Sin perder archivos.

---

## ✨ Lo que lo hace especial

📋 **Gestión de clientes centralizada**  
Crea clientes y el sistema genera automáticamente toda la estructura de carpetas:
- Archivos
- Imágenes
- Sonido
- Música
- Locución
- Transcripción  

Todo ordenado sin pensar demasiado 🧠

---

🎬 **Estados inteligentes para cada vídeo**  
Cada vídeo puede estar en:
- Pendiente
- En revisión
- Pagado
- Terminado  

Cambias el estado desde un combo box y el sistema se reorganiza solo.  
Si marcas *Terminado*, mueve todo a la sección de hechos automáticamente 🔄

---

🖼️ **Miniaturas automáticas en tiempo real**  
Extrae miniaturas usando **FFmpeg** y te muestra previews sin abrir los vídeos.  
Menos clics = más productividad 💰

---

🚀 **Subida directa a YouTube**  
Seleccionas un vídeo y lo subes como *oculto* directamente desde la app usando la **YouTube API**.  
Nada de exportar, subir manualmente y esperar eternamente.

---

☁️ **Sincronización con Google Drive**  
Sube vídeos a Drive con un clic y genera enlaces compartibles automáticamente.  
Perfecto para enviar a clientes sin esfuerzo 🔗

---

📌 **Referencias por proyecto**  
Cada vídeo tiene su carpeta de referencias para:
- Inspiración
- Referencias visuales
- Notas  

Todo centralizado y fácil de encontrar 📸

---

⏱️ **Pomodoro Timer integrado**  
Timer de productividad:
- 25 minutos trabajo
- 5 minutos descanso  

Con alarma incluida.  
Porque trabajar sin pausas es para masoquistas 🍅

---

## 🎭 Cómo funciona (la magia detrás del telón)

La app está desarrollada en **Python con PyQt6**, usando threads para que nada se congele mientras se procesan vídeos o se suben archivos pesados.

### Flujo de trabajo

1️⃣ **Crear cliente**  
Introduces un nombre y el sistema crea automáticamente toda la estructura de carpetas, numerando los proyectos.

2️⃣ **Agregar vídeos**  
Seleccionas un cliente y creas un nuevo vídeo.  
Se generan todas las subcarpetas necesarias y puedes empezar a trabajar de inmediato 🎬

3️⃣ **Cambiar estados**  
Desde un combo box cambias el estado del vídeo.  
El sistema actualiza todo automáticamente según el estado seleccionado.

4️⃣ **Ver contenido**  
Accedes a todas las versiones del vídeo (con marca de agua, sin marca, etc.)  
Cada versión tiene botones para reproducir o subir a plataformas 🎞️

5️⃣ **Subir a plataformas**  
Con un clic subes el vídeo a:
- YouTube (oculto)
- Google Drive (con enlace compartible)  

La API se encarga de todo 🚀

---

## 🛠️ Stack técnico

- 🐍 **Python** – base del proyecto, simple y potente  
- 🎨 **PyQt6** – interfaz moderna y profesional  
- 📹 **FFmpeg** – extracción automática de miniaturas  
- 🚀 **YouTube API** – subida directa de vídeos  
- ☁️ **Google Drive API** – sincronización y enlaces compartibles  
- ⚙️ **Threading** – procesos en segundo plano sin congelar la UI  
- 📊 **JSON** – persistencia de estados y datos de proyectos  

---

## 👥 ¿Para quién es este gestor?

✅ **Productores de vídeo**  
Gestiona múltiples clientes y proyectos sin caos 🎬

✅ **Editores freelance**  
Control total de estados, pagos y entregas en un solo lugar

✅ **Agencias de contenido**  
Varios clientes, varios proyectos, todo separado y ordenado 🤝

✅ **YouTubers y creadores**  
Gestiona vídeos, referencias y subidas sin perder tiempo ⏱️

✅ **Equipos de producción**  
Todos ven el estado de los proyectos y trabajan sincronizados 🤖

---