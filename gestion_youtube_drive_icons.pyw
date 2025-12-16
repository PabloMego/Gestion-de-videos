import os
import shutil
import json
import subprocess
import datetime
import winsound
import webbrowser
from functools import partial
import traceback
from typing import Dict, List

# Notion sync module is no longer used
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel,
    QLineEdit, QFileDialog, QTabWidget, QScrollArea, QComboBox, QFrame, QMessageBox, 
    QDialog, QListWidgetItem, QSplitter, QToolButton, QGroupBox, QGridLayout, QProgressBar, QCheckBox, QStackedWidget,
    QTextEdit, QSpacerItem, QSizePolicy, QLCDNumber
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QThread, QTime
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPainter, QLinearGradient, QPixmap, QPen, QGuiApplication, QClipboard

# --- ADICIONES: multimedia, sorting natural y Google Drive ---
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QGuiApplication
import re
import tempfile
import time
from googleapiclient.discovery import build as gbuild
from googleapiclient.http import MediaFileUpload as DriveMediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow as DriveInstalledAppFlow
from google.auth.transport.requests import Request as DriveRequest
import pickle as _pickle

# Natural numeric sort for filenames like "01.name", "10.name" so 2 < 10 correctly
def sort_naturally(lst):
    def keyfn(s):
        # try to extract leading number(s)
        m = re.match(r"(\d+)", s)
        if m:
            return (int(m.group(1)), s)
        # fallback: search any number
        m2 = re.search(r"(\d+)", s)
        if m2:
            return (int(m2.group(1)), s)
        return (10**9, s)
    return sorted(list(lst), key=keyfn)

# Helper: extract a thumbnail using ffmpeg (if available). Returns path or None.
def extract_thumbnail(video_path, out_path=None, time_pos="00:00:01"):
    if out_path is None:
        out_path = os.path.join(tempfile.gettempdir(), f"thumb_{int(time.time())}.jpg")
    try:
        # Use ffmpeg if available
        cmd = [
            "ffmpeg", "-y", "-ss", time_pos, "-i", video_path,
            "-vframes", "1", "-q:v", "2", out_path
        ]
        # Usar CREATE_NO_WINDOW para evitar que se muestre la ventana de consola
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        subprocess.run(cmd, 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True,
                      startupinfo=startupinfo)
        if os.path.exists(out_path):
            return out_path
    except Exception:
        pass
    return None

# Google Drive helpers (uses client_secrets file 'client_secret.json')
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
def get_drive_service():
    creds = None
    if os.path.exists("drive_token.pickle"):
        with open("drive_token.pickle", "rb") as f:
            creds = _pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(DriveRequest())
        else:
            flow = DriveInstalledAppFlow.from_client_secrets_file("client_secret.json", DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open("drive_token.pickle", "wb") as f:
            _pickle.dump(creds, f)
    return gbuild("drive", "v3", credentials=creds)

# Configuración
RUTA_CLIENTES = "Clientes"
SUBCARPETAS_VIDEO = [
    "0.archivos","1.imágenes y videos","2.sonido","3.música","4.locución","5.transcripción"
]
ESTADOS_ARCHIVO = "estados.json"

# Estilo Oscuro
DARK_STYLE_SHEET = """
/* --- Estilo General --- */
QWidget {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #202124; /* Fondo principal oscuro */
    color: #e0e0e0; /* Texto principal más suave */
    border: none;
}

/* --- Ventana Principal --- */
QMainWindow, QDialog {
    background-color: #202124;
}

/* --- Paneles y Grupos --- */
QGroupBox {
    background-color: #28292d; /* Fondo de grupo ligeramente más claro */
    border-radius: 8px;
    border: 1px solid #3c4043; /* Borde sutil */
    margin-top: 10px;
    padding: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #bdc1c6; /* Color de título de grupo */
    font-weight: 600;
    font-size: 11px;
}

/* --- Etiqueta Cliente Actual --- */
#clienteActualLabel {
    background-color: #28292d;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #3c4043;
}

/* --- Sidebar --- */
#sidebar {
    background-color: #28292d;
    border-radius: 12px;
    margin: 8px;
    border: 1px solid #3c4043;
}

#sidebar QLabel {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    padding: 15px;
    background: transparent;
}

/* --- Botones --- */
QPushButton {
    background-color: #3c4043; /* Fondo de botón estándar */
    color: #e0e0e0;
    border-radius: 6px;
    padding: 10px 16px;
    font-weight: 600;
    font-size: 11px;
    border: 1px solid #5f6368;
}

QPushButton:hover {
    background-color: #4a4d51; /* Ligeramente más claro al pasar el mouse */
    border-color: #888a8c;
}

QPushButton:pressed {
    background-color: #28292d; /* Más oscuro al presionar */
}

QPushButton:disabled {
    background-color: #3c4043;
    color: #888a8c;
    border-color: #5f6368;
}

/* Botones con Acento (Crear, Terminar) */
#btn_crear, #btn_terminar {
    background-color: #2d7ff9; /* Azul de acento */
    color: white;
    border: none;
}
#btn_crear:hover, #btn_terminar:hover { background-color: #4c9aff; }
#btn_crear:pressed, #btn_terminar:pressed { background-color: #1a6ff9; }

/* Botón YouTube */
#btn_youtube {
    background-color: #ff0000; /* Rojo YouTube */
    color: white;
    border: none;
}
#btn_youtube:hover { background-color: #ff3333; }
#btn_youtube:pressed { background-color: #cc0000; }

/* Botón Drive */
#btn_drive {
    background-color: #0F9D58; /* Verde Drive */
    color: white;
    border: none;
}
#btn_drive:hover { background-color: #16a860; }
#btn_drive:pressed { background-color: #0d8246; }

/* Botón de Eliminar */
#btn_eliminar {
    background-color: #d93025; /* Rojo para acciones destructivas */
    color: white;
    border: none;
}

#btn_eliminar:hover {
    background-color: #e5493f;
}

#btn_eliminar:pressed {
    background-color: #c5221f;
}

/* --- Campos de Texto --- */
QLineEdit, QTextEdit {
    background-color: #28292d;
    border: 1px solid #5f6368;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
}

QLineEdit:focus, QTextEdit:focus {
    border-color: #2d7ff9; /* Borde azul al enfocar */
}

/* --- Lista de Clientes --- */
QListWidget {
    background-color: #28292d;
    border: 1px solid #3c4043;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 12px;
    border-radius: 6px;
}

QListWidget::item:hover {
    background-color: #3c4043;
}

QListWidget::item:selected {
    background-color: #2d7ff9;
    color: white;
}

/* --- Pestañas --- */
QTabWidget::pane {
    border: none;
}

QTabBar::tab {
    background-color: transparent;
    color: #bdc1c6;
    padding: 10px 15px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:hover {
    color: #ffffff;
}

QTabBar::tab:selected {
    color: #2d7ff9;
    border-bottom: 2px solid #2d7ff9;
}

/* Scroll Areas */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #2d2d30;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #5a5a5a;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #6a6a6a;
}

/* ComboBox */
QComboBox {
    background: #3c3c3c;
    border: 2px solid #5a5a5a;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 100px;
    font-weight: 500;
    color: #ffffff;
}

QComboBox:hover {
    border-color: #0e639c;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    border: 2px solid #ffffff;
    width: 6px;
    height: 6px;
    border-top: none;
    border-right: none;
    transform: rotate(-45deg);
}

QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #5a5a5a;
    selection-background-color: #0e639c;
}

/* Tarjetas de video */
.video-card {
    background: #2d2d30;
    border: 2px solid #3e3e42;
    border-radius: 12px;
    margin: 8px;
    padding: 16px;
}

.video-card:hover {
    border-color: #0e639c;
    box-shadow: 0 4px 20px rgba(14, 99, 156, 0.3);
}

/* Estados */
.estado-pendiente {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                               stop:0 #433519, stop:1 #5d4e37);
    border-color: #ca5010;
}

.estado-pagado {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                               stop:0 #0e4b0e, stop:1 #107c10);
    border-color: #16b316;
}

.estado-revision {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                               stop:0 #1a4480, stop:1 #0e639c);
    border-color: #1177bb;
}

.estado-terminado {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                               stop:0 #4c0e4c, stop:1 #6b1a6b);
    border-color: #8b2a8b;
}

/* Group Boxes */
QGroupBox {
    background: #2d2d30;
    border: 2px solid #3e3e42;
    border-radius: 12px;
    font-weight: 600;
    font-size: 13px;
    color: #ffffff;
    margin: 10px 5px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px 0 8px;
    background: #0e639c;
    color: white;
    border-radius: 4px;
}

/* Progress Bar */
QProgressBar {
    background: #3e3e42;
    border: none;
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                               stop:0 #0e639c, stop:1 #1177bb);
    border-radius: 8px;
}

/* Dialogs */
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                               stop:0 #2d2d30, stop:1 #1e1e1e);
    border-radius: 12px;
    color: #ffffff;
}

/* Message Boxes */
QMessageBox {
    background: #2d2d30;
    border-radius: 12px;
    color: #ffffff;
}

QMessageBox QPushButton {
    min-width: 80px;
    margin: 4px;
}

QMessageBox QLabel {
    color: #ffffff;
}
"""

# --- Funciones de gestión (mantienen la funcionalidad original) ---
def cargar_estados(cliente_path):
    path = os.path.join(cliente_path, ESTADOS_ARCHIVO)
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_estados(cliente_path, estados):
    path = os.path.join(cliente_path, ESTADOS_ARCHIVO)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(estados, f, indent=4, ensure_ascii=False)

def crear_cliente(nombre):
    if not os.path.exists(RUTA_CLIENTES):
        os.makedirs(RUTA_CLIENTES)
    carpetas = [c for c in os.listdir(RUTA_CLIENTES) if os.path.isdir(os.path.join(RUTA_CLIENTES,c))]
    numeros = [int(c.split('.')[0]) for c in carpetas if c[0].isdigit()]
    nuevo_num = max(numeros)+1 if numeros else 1
    nombre_carpeta = f"{nuevo_num}.{nombre}"
    ruta_cliente = os.path.join(RUTA_CLIENTES,nombre_carpeta)
    os.makedirs(ruta_cliente)
    os.makedirs(os.path.join(ruta_cliente,"Videos"))
    os.makedirs(os.path.join(ruta_cliente,"Hechos"))
    os.makedirs(os.path.join(ruta_cliente,"Referencias"))  # 👈 NUEVO
    with open(os.path.join(ruta_cliente, ESTADOS_ARCHIVO), "w", encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False)
    return nombre_carpeta


def eliminar_cliente(nombre_cliente):
    ruta = os.path.join(RUTA_CLIENTES, nombre_cliente)
    if os.path.exists(ruta):
        shutil.rmtree(ruta)

def anclar_quick_access(ruta_carpeta):
    """Ancla la carpeta al Acceso rápido de Windows"""
    ruta_carpeta = os.path.abspath(ruta_carpeta)
    ps_script = f"""
    $Path = '{ruta_carpeta}'
    $shell = New-Object -ComObject shell.application
    $folder = $shell.Namespace((Split-Path $Path))
    $item = $folder.ParseName((Split-Path $Path -Leaf))
    try {{ $item.InvokeVerb('desanclar del acceso rápido') }} catch {{ }}
    $item.InvokeVerb('pintar en acceso rápido')
    """
    try:
        # Configurar para ocultar la ventana de consola de PowerShell
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_script], 
                      check=True,
                      startupinfo=startupinfo)
    except Exception as e:
        print("No se pudo anclar al Acceso rápido:", e)

def agregar_video_nuevo(cliente, nombre_video):
    try:
        ruta_cliente = os.path.join(RUTA_CLIENTES, cliente)
        videos_path = os.path.join(ruta_cliente, "Videos")
        numero = len([d for d in os.listdir(videos_path) if os.path.isdir(os.path.join(videos_path, d))]) + 1
        # Asegurarse de que el nombre del cliente no tenga prefijo numérico aquí
        nombre_base_cliente = cliente.split('.', 1)[-1]
        nombre_carpeta = f"{numero:02d}.{nombre_base_cliente}-{nombre_video}"
        ruta_video = os.path.join(videos_path, nombre_carpeta)
        os.makedirs(ruta_video)
        for sub in SUBCARPETAS_VIDEO:
            os.makedirs(os.path.join(ruta_video, sub))
        estados = cargar_estados(ruta_cliente)
        estados[nombre_carpeta] = "Pendiente"
        guardar_estados(ruta_cliente, estados)
        anclar_quick_access(ruta_video)
        return True
    except Exception as e:
        print(f"Error al crear video nuevo: {e}")
        return False

def agregar_video_hecho(cliente, archivos):
    ruta_cliente = os.path.join(RUTA_CLIENTES,cliente)
    hechos_path = os.path.join(ruta_cliente,"Hechos")
    # Solo contar archivos sueltos (no carpetas de proyectos terminados)
    archivos_sueltos = [f for f in os.listdir(hechos_path) if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and os.path.isfile(os.path.join(hechos_path, f))]
    numero = len(archivos_sueltos) + 1
    for archivo in archivos:
        nombre = os.path.basename(archivo)
        nombre_destino = f"{numero}.{nombre}"
        shutil.copy(archivo, os.path.join(hechos_path,nombre_destino))
        numero+=1

def mover_a_terminado(cliente, nombre_video):
    """Busca el video final (sin 'MA') en la carpeta del proyecto, lo mueve a 'Hechos' y archiva la carpeta del proyecto."""
    ruta_cliente = os.path.join(RUTA_CLIENTES, cliente)
    ruta_proyecto_pendiente = os.path.join(ruta_cliente, "Videos", nombre_video)
    hechos_path = os.path.join(ruta_cliente, "Hechos")
    
    if not os.path.exists(ruta_proyecto_pendiente):
        return False

    # 1. Buscar el video final (sin 'MA')
    video_final_path = None
    nombre_video_final = ""
    for root, _, files in os.walk(ruta_proyecto_pendiente):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) and 'ma' not in file.lower():
                video_final_path = os.path.join(root, file)
                nombre_video_final = file
                break
        if video_final_path:
            break

    if not video_final_path:
        QMessageBox.warning(None, "Video no encontrado", f"No se encontró un video final (sin 'MA') en la carpeta '{nombre_video}'.")
        return False

    try:
        # 2. Mover el video final a la carpeta 'Hechos'
        shutil.move(video_final_path, os.path.join(hechos_path, nombre_video_final))

        # 3. Archivar la carpeta del proyecto
        ruta_archivados = os.path.join(hechos_path, ".proyectos_archivados")
        if not os.path.exists(ruta_archivados):
            os.makedirs(ruta_archivados)
        
        shutil.move(ruta_proyecto_pendiente, os.path.join(ruta_archivados, nombre_video))

        # 4. Actualizar el estado del proyecto a 'Terminado'
        estados = cargar_estados(ruta_cliente)
        estados[nombre_video] = "Terminado"
        guardar_estados(ruta_cliente, estados)
        
        return True

    except Exception as e:
        QMessageBox.critical(None, "Error al mover", f"Ocurrió un error al terminar el proyecto: {e}")
        return False

def pasar_a_terminado(cliente, nombre_video, archivos_seleccionados):
    """Mueve videos seleccionados de pendiente a terminado (funcionalidad legacy)"""
    ruta_cliente = os.path.join(RUTA_CLIENTES, cliente)
    ruta_pendiente = os.path.join(ruta_cliente, "Videos", nombre_video)
    hechos_path = os.path.join(ruta_cliente, "Hechos")
    
    # Solo contar archivos sueltos para numeración
    archivos_sueltos = [f for f in os.listdir(hechos_path) if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and os.path.isfile(os.path.join(hechos_path, f))]
    numero = len(archivos_sueltos) + 1
    
    # Copiar archivos seleccionados
    for archivo in archivos_seleccionados:
        origen = os.path.join(ruta_pendiente, archivo)
        if os.path.exists(origen):
            nombre_destino = f"{numero}.{archivo}"
            destino = os.path.join(hechos_path, nombre_destino)
            shutil.copy(origen, destino)
            numero += 1
    
    # Actualizar estado a Terminado
    estados = cargar_estados(ruta_cliente)
    estados[nombre_video] = "Terminado"
    guardar_estados(ruta_cliente, estados)

# --- Thread para subida a YouTube ---

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

class YouTubeUploadThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished_upload = pyqtSignal(bool, str)

    def __init__(self, video_path, title="", description=""):
        super().__init__()
        self.video_path = video_path
        self.title = title or os.path.basename(video_path)
        self.description = description

    def run(self):
        try:
            youtube = get_authenticated_service()

            self.message.emit("⏳ Subiendo a YouTube...")
            self.progress.emit(10)

            media = MediaFileUpload(self.video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": self.title,
                        "description": self.description,
                    },
                    "status": {
                        "privacyStatus": "unlisted"  # 👈 OCULTO
                    }
                },
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.progress.emit(int(status.progress() * 100))

            self.finished_upload.emit(True, f"✅ Video subido como oculto: https://youtu.be/{response['id']}")

        except Exception as e:
            self.finished_upload.emit(False, f"❌ Error en la subida: {str(e)}")


class ModernButton(QPushButton):
    def __init__(self, text, button_type="normal"):
        super().__init__(text)
        self.button_type = button_type
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                margin: 4px 2px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """ if button_type == "verde" else "")
        self.setObjectName(f"btn_{button_type}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class AnimatedFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

class NuevoClienteDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✨ Crear Nuevo Cliente")
        self.setFixedSize(400, 200)
        self.setStyleSheet(DARK_STYLE_SHEET)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Título
        titulo = QLabel("Crear Nuevo Cliente")
        titulo.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            padding: 20px;
            text-align: center;
        """)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Input
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Introduce el nombre del cliente...")
        layout.addWidget(self.input_nombre)

        # Botones
        btn_layout = QHBoxLayout()
        
        btn_cancelar = ModernButton("Cancelar", "eliminar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_aceptar = ModernButton("Crear Cliente", "crear")
        btn_aceptar.clicked.connect(self.aceptar)
        btn_aceptar.setDefault(True)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_aceptar)
        layout.addLayout(btn_layout)

        self.nombre_cliente = None
        self.input_nombre.returnPressed.connect(self.aceptar)

    def aceptar(self):
        texto = self.input_nombre.text().strip()
        if texto:
            self.nombre_cliente = texto
            self.accept()
        else:
            self.input_nombre.setFocus()

class ContenidoVideoDialog(QDialog):
    def __init__(self, ruta_video, cliente=None, nombre_video=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 Contenido del Video")
        self.setGeometry(150, 150, 1000, 700) # Ancho aumentado a 1000 píxeles
        self.setStyleSheet(DARK_STYLE_SHEET)
        self.ruta_video = ruta_video
        self.cliente = cliente
        self.nombre_video = nombre_video
        self.parent_widget = parent

        main_layout = QVBoxLayout(self)

        # --- Título y botones de acceso rápido ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título
        titulo = QLabel(f"📁 {os.path.basename(ruta_video)}")
        titulo.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #ffffff; 
            padding: 10px; 
            background-color: #28292d; 
            border-radius: 8px;
        """)
        header_layout.addWidget(titulo, 1)
        
        # Botones de acceso rápido
        btn_style = """
            QPushButton {
                padding: 8px 12px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-left: 5px;
                color: white;
                background: transparent;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        """
        
        # Botón de Google Drive
        self.btn_drive = QPushButton("🚀 Google Drive")
        self.btn_drive.setStyleSheet(btn_style + """
            QPushButton {
                background-color: #34A853;
            }
            QPushButton:hover {
                background-color: #2D8E4A;
            }
        """)
        self.btn_drive.clicked.connect(lambda: self.abrir_url("https://drive.google.com/drive/u/1/my-drive"))
        header_layout.addWidget(self.btn_drive)
        
        # Botón de YouTube Studio
        self.btn_yt_studio = QPushButton("🎬 YouTube Studio")
        self.btn_yt_studio.setStyleSheet(btn_style + """
            QPushButton {
                background-color: #FF0000;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        self.btn_yt_studio.clicked.connect(lambda: self.abrir_url("https://studio.youtube.com/channel/UCamjR0Sd0JOoNAUcU8FLUSQ/videos/upload?filter=%5B%5D&sort=%7B%22columnType%22%3A%22date%22%2C%22sortOrder%22%3A%22DESCENDING%22%7D"))
        header_layout.addWidget(self.btn_yt_studio)
        
        # Asegurarse de que no haya bordes ni fondos no deseados
        header_widget.setStyleSheet("background: transparent; border: none;")
        header_layout.setSpacing(5)
        
        main_layout.addWidget(header_widget)

        # Crear pestañas principales
        self.tab_widget = QTabWidget()

        # --- Pestaña: Videos del Proyecto ---
        self.tab_videos = QWidget()
        videos_layout = QVBoxLayout(self.tab_videos)

        # Layout para las dos listas de videos
        listas_layout = QHBoxLayout()

        videos_normales_files = [f for f in sort_naturally(os.listdir(ruta_video)) if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and "MA" not in f]
        videos_marca_files = [f for f in sort_naturally(os.listdir(ruta_video)) if f.endswith(('.mp4', '.avi', '.mov', '.mkv')) and "MA" in f]

        self.videos_normales = []
        self.videos_marca = []

        # --- Columna de Videos Normales ---
        normal_group, normal_scroll = self.crear_lista_videos("🎥 Videos Normales", videos_normales_files, self.videos_normales)
        listas_layout.addWidget(normal_group)

        # --- Columna de Videos con Marca de Agua ---
        marca_group, marca_scroll = self.crear_lista_videos("🏷️ Videos con Marca de Agua", videos_marca_files, self.videos_marca)
        listas_layout.addWidget(marca_group)

        videos_layout.addLayout(listas_layout)
        self.tab_widget.addTab(self.tab_videos, "🎥 Videos del Proyecto")

        main_layout.addWidget(self.tab_widget)

        # --- Botones Inferiores ---
        bottom_btn_layout = QHBoxLayout()

        btn_cerrar = ModernButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        bottom_btn_layout.addWidget(btn_cerrar)
        main_layout.addLayout(bottom_btn_layout)

        # No se cargan referencias ya que se eliminó la pestaña

    def crear_lista_videos(self, titulo, archivos, lista_control):
        group = QGroupBox(titulo)
        scroll_layout = QVBoxLayout(group)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not archivos:
            empty_label = QLabel(f"No hay videos en esta categoría")
            empty_label.setStyleSheet("color: #888a8c; font-style: italic; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
        else:
            for f in archivos:
                frame, checkbox = self.crear_fila_video(f)
                layout.addWidget(frame)
                lista_control.append((checkbox, f))

        scroll_area.setWidget(container)
        scroll_layout.addWidget(scroll_area)
        return group, scroll_area

    def crear_fila_video(self, filename):
        # Contenedor principal de la tarjeta
        card = QFrame()
        card.setStyleSheet("""
            QFrame { 
                background-color: #28292d; 
                border: 1px solid #3c4043; 
                border-radius: 8px; 
                padding: 10px; 
            }
            QFrame:hover { border-color: #2d7ff9; }
        """)
        card_layout = QVBoxLayout(card)

        # 1. Miniatura grande arriba
        thumb_label = QLabel()
        thumb_label.setMinimumHeight(180)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_label.setStyleSheet("background-color: #202124; border-radius: 6px;")
        thumb_path = extract_thumbnail(os.path.join(self.ruta_video, filename))
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(300, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            thumb_label.setPixmap(pixmap)
        else:
            thumb_label.setText("🎬")
            thumb_label.setStyleSheet("font-size: 50px; color: #888a8c; background-color: #202124; border-radius: 6px;")
        card_layout.addWidget(thumb_label)

        # 2. Texto del video abajo
        nombre_label = QLabel(filename)
        nombre_label.setToolTip(filename)
        nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nombre_label.setStyleSheet("color: #e0e0e0; font-weight: 600; font-size: 12px; padding: 8px 0;")
        nombre_label.setWordWrap(True)
        card_layout.addWidget(nombre_label)

        # 3. Botones abajo, uno al lado del otro
        button_layout = QHBoxLayout()
        btn_play = ModernButton("▶️ Reproducir")
        btn_youtube = ModernButton("YouTube", "youtube")
        btn_drive = ModernButton("Drive", "drive")

        # Conexiones
        btn_play.clicked.connect(partial(os.startfile, os.path.join(self.ruta_video, filename)))
        btn_youtube.clicked.connect(partial(self.subir_youtube, os.path.join(self.ruta_video, filename), filename))
        btn_drive.clicked.connect(partial(self.subir_drive, os.path.join(self.ruta_video, filename), filename))

        button_layout.addWidget(btn_play)
        button_layout.addWidget(btn_youtube)
        button_layout.addWidget(btn_drive)
        card_layout.addLayout(button_layout)

        # Devolvemos None para el checkbox ya que lo hemos eliminado
        return card, None

    def get_selected_videos(self):
        """Obtiene lista de videos seleccionados"""
        selected = []
        for checkbox, filename in self.videos_normales + self.videos_marca:
            if checkbox.isChecked():
                selected.append(filename)
        return selected

    def _show_preview_for(self, file_path):
        """Mostrar miniatura (si ffmpeg disponible) o reproducir en el pequeño reproductor."""
        # try thumbnail first
        thumb = extract_thumbnail(file_path)
        if thumb and os.path.exists(thumb):
            pix = QPixmap(thumb).scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(pix)
            self.preview_label.setVisible(True)
            try:
                self.video_widget.setVisible(False)
                self.media_player.stop()
            except Exception:
                pass
            return
        # fallback: show tiny playable preview
        try:
            self.preview_label.setVisible(False)
            self.video_widget.setVisible(True)
            self.media_player.setSource(file_path)
            self.media_player.play()
            # stop after a short preview (10s)
            QTimer.singleShot(10000, self.media_player.pause)
        except Exception:
            # as a last resort, set text
            self.preview_label.setText(os.path.basename(file_path))
            self.preview_label.setVisible(True)

    def pasar_seleccionados_terminado(self):
        """Pasa los videos seleccionados a terminados"""
        selected = self.get_selected_videos()
        if not selected:
            QMessageBox.warning(self, "⚠️ Advertencia", "Por favor, selecciona al menos un video.")
            return
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("✅ Confirmar Finalización")
        msg.setText(f"¿Pasar {len(selected)} video(s) a terminados?")
        msg.setInformativeText("Los videos seleccionados se copiarán a la carpeta de terminados.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet(DARK_STYLE_SHEET)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                pasar_a_terminado(self.cliente, self.nombre_video, selected)
                
                # Mostrar éxito
                success_msg = QMessageBox()
                success_msg.setIcon(QMessageBox.Icon.Information)
                success_msg.setWindowTitle("✅ Videos Terminados")
                success_msg.setText(f"Se pasaron {len(selected)} video(s) a terminados correctamente.")
                success_msg.setStyleSheet(DARK_STYLE_SHEET)
                success_msg.exec()
                
                # Actualizar la interfaz principal
                if self.parent_widget and hasattr(self.parent_widget, 'actualizar_videos'):
                    self.parent_widget.actualizar_videos()
                
                self.close()
                
            except Exception as e:
                error_msg = QMessageBox()
                error_msg.setIcon(QMessageBox.Icon.Critical)
                error_msg.setWindowTitle("❌ Error")
                error_msg.setText(f"Error al pasar videos a terminados: {str(e)}")
                error_msg.setStyleSheet(DARK_STYLE_SHEET)
                error_msg.exec()

    def subir_youtube(self, video_path, video_name):
        """Subir video a YouTube"""
        dialog = YouTubeUploadDialog(video_path, video_name, self)
        dialog.exec()

    def subir_drive(self, video_path, video_name):
        """Subir video a Drive"""
        dialog = DriveUploadDialog(video_path, video_name, self)
        dialog.exec()

    def abrir_url(self, url):
        """Abrir URL en el navegador"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, "⚠️ Advertencia", f"No se pudo abrir la URL: {str(e)}")


class ReferenciasProyectoDialog(QDialog):
    """Diálogo para gestionar referencias específicas de un proyecto individual"""

    def __init__(self, ruta_proyecto, nombre_proyecto, parent=None):
        super().__init__(parent)
        self.ruta_proyecto = ruta_proyecto
        self.nombre_proyecto = nombre_proyecto
        self.setWindowTitle(f"📌 Referencias - {nombre_proyecto}")
        self.setGeometry(200, 200, 1200, 800)  # Tamaño similar a la sección de referencias
        self.setStyleSheet(DARK_STYLE_SHEET)

        main_layout = QVBoxLayout(self)

        # Título
        titulo = QLabel(f"📌 Referencias del Proyecto: {nombre_proyecto}")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; padding: 10px; background-color: #28292d; border-radius: 8px;")
        main_layout.addWidget(titulo)

        # Layout principal con scroll
        ref_main_layout = QVBoxLayout()

        # Sección para agregar nueva referencia
        ref_add_group = QGroupBox("➕ Gestión de Referencias")
        ref_add_layout = QHBoxLayout()

        # Botón para agregar referencia
        self.btn_agregar_referencia = ModernButton("➕ Agregar Referencia")
        self.btn_agregar_referencia.clicked.connect(self.agregar_referencia)
        ref_add_layout.addWidget(self.btn_agregar_referencia, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Botón para abrir carpeta de referencias
        self.btn_abrir_carpeta = ModernButton("📂 Abrir Carpeta de Referencias")
        self.btn_abrir_carpeta.clicked.connect(self.abrir_carpeta_referencias)
        ref_add_layout.addWidget(self.btn_abrir_carpeta, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Espaciador para empujar los botones a la izquierda
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        ref_add_layout.addItem(spacer)

        ref_add_group.setLayout(ref_add_layout)
        ref_main_layout.addWidget(ref_add_group)

        # Sección para mostrar referencias existentes
        ref_view_group = QGroupBox("📌 Referencias")
        ref_view_layout = QVBoxLayout(ref_view_group)

        # Contenedor para la cuadrícula de referencias
        self.referencias_grid = QWidget()
        self.grid_referencias = QGridLayout()
        self.grid_referencias.setSpacing(15)
        self.grid_referencias.setContentsMargins(10, 10, 10, 10)
        self.referencias_grid.setLayout(self.grid_referencias)

        # Añadir al layout con scroll
        ref_view_scroll = QScrollArea()
        ref_view_scroll.setWidgetResizable(True)
        ref_view_scroll.setWidget(self.referencias_grid)

        ref_view_layout.addWidget(ref_view_scroll)
        ref_main_layout.addWidget(ref_view_group, 1)  # El 1 hace que ocupe el espacio restante

        main_layout.addLayout(ref_main_layout)

        # Botones inferiores
        bottom_btn_layout = QHBoxLayout()

        btn_cerrar = ModernButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        bottom_btn_layout.addWidget(btn_cerrar)
        main_layout.addLayout(bottom_btn_layout)

        # Cargar referencias existentes
        self.cargar_referencias()

    def abrir_carpeta_referencias(self):
        """Abre la carpeta de referencias del proyecto en el explorador de archivos"""
        ruta_referencias = os.path.join(self.ruta_proyecto, "Referencias")
        
        # Si la carpeta no existe, la creamos
        if not os.path.exists(ruta_referencias):
            try:
                os.makedirs(ruta_referencias)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta de referencias: {str(e)}")
                return
        
        # Abrir la carpeta en el explorador de archivos
        try:
            os.startfile(ruta_referencias)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la carpeta de referencias: {str(e)}")
    
    def agregar_referencia_texto(self):
        """Función eliminada - ya no se usa"""
        pass

    def agregar_referencia(self):
        """Agregar archivos desde el explorador de archivos (igual que la sección de referencias general)"""
        # Mostrar diálogo para seleccionar archivos (mismo filtro que la sección general)
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Archivos multimedia (*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png)")

        if file_dialog.exec():
            archivos = file_dialog.selectedFiles()
            ruta_referencias = os.path.join(self.ruta_proyecto, "Referencias")

            if not os.path.exists(ruta_referencias):
                os.makedirs(ruta_referencias)

            for archivo_origen in archivos:
                nombre_archivo = os.path.basename(archivo_origen)
                archivo_destino = os.path.join(ruta_referencias, nombre_archivo)

                # Si el archivo ya existe, agregar un número al final
                contador = 1
                while os.path.exists(archivo_destino):
                    nombre, extension = os.path.splitext(nombre_archivo)
                    archivo_destino = os.path.join(ruta_referencias, f"{nombre}_{contador}{extension}")
                    contador += 1

                try:
                    shutil.copy2(archivo_origen, archivo_destino)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo copiar el archivo {nombre_archivo}: {str(e)}")

            # Actualizar la vista de referencias
            self.cargar_referencias()

    def cargar_referencias(self):
        """Cargar y mostrar las referencias del proyecto (igual que la sección de referencias general)"""
        # Limpiar referencias existentes
        for i in reversed(range(self.grid_referencias.count())):
            widget = self.grid_referencias.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Cargar archivos desde la carpeta de referencias
        ruta_referencias = os.path.join(self.ruta_proyecto, "Referencias")

        if not os.path.exists(ruta_referencias):
            empty_label = QLabel("No hay referencias para este proyecto")
            empty_label.setStyleSheet("color: #888a8c; font-style: italic; padding: 30px; font-size: 14px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_referencias.addWidget(empty_label, 0, 0, 1, 3)  # Ocupa toda la fila
            return

        # Buscar archivos multimedia (mismo filtro que la sección de referencias general)
        archivos = [f for f in os.listdir(ruta_referencias)
                   if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png'))]

        if not archivos:
            empty_label = QLabel("No hay referencias para este proyecto")
            empty_label.setStyleSheet("color: #888a8c; font-style: italic; padding: 30px; font-size: 14px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_referencias.addWidget(empty_label, 0, 0, 1, 3)  # Ocupa toda la fila
            return

        # Ordenar archivos por fecha de modificación (más recientes primero)
        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(ruta_referencias, x)), reverse=True)

        # Mostrar archivos en grid de 3 columnas (igual que la sección de referencias general)
        row = 0
        col = 0
        max_cols = 3

        for archivo in archivos:
            archivo_path = os.path.join(ruta_referencias, archivo)

            # Crear tarjeta igual que en la sección de referencias general
            ref_frame = self.crear_tarjeta_referencia_general(archivo_path, archivo)
            self.grid_referencias.addWidget(ref_frame, row, col)

            # Avanzar en la cuadrícula
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def crear_tarjeta_referencia_general(self, archivo_path, nombre_archivo):
        """Crear una tarjeta igual que en la sección de referencias general"""
        ref_frame = QFrame()
        ref_frame.setStyleSheet("""
            QFrame {
                background: #28292d;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #2d7ff9; /* Borde azul al pasar el mouse */
            }
        """)

        ref_layout = QVBoxLayout()
        ref_frame.setLayout(ref_layout)

        # Contenedor para la miniatura para un tamaño consistente
        thumb_container = QLabel()
        thumb_container.setMinimumSize(280, 210)
        thumb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_container.setStyleSheet("background: #252526; border-radius: 6px;")

        # Cargar miniatura o imagen
        pixmap = None
        is_video = archivo_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
        if is_video:
            thumb_path = extract_thumbnail(archivo_path)
            if thumb_path and os.path.exists(thumb_path):
                pixmap = QPixmap(thumb_path)
        else:
            pixmap = QPixmap(archivo_path)

        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(280, 210,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            thumb_container.setPixmap(scaled_pixmap)
        else:
            icon_text = "🎬" if is_video else "🖼️"
            thumb_container.setText(icon_text)
            thumb_container.setStyleSheet("font-size: 60px; background: #252526; border-radius: 6px; color: #888a8c;")

        ref_layout.addWidget(thumb_container)

        # Nombre del archivo
        nombre_mostrar = nombre_archivo if len(nombre_archivo) < 35 else nombre_archivo[:32] + "..."
        nombre_label = QLabel(nombre_mostrar)
        nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nombre_label.setToolTip(nombre_archivo)
        nombre_label.setStyleSheet("color: #e0e0e0; margin-top: 10px; font-size: 12px; font-weight: 500;")
        ref_layout.addWidget(nombre_label)

        # Botones de acción (igual que la sección de referencias general)
        btn_layout = QHBoxLayout()

        abrir_texto = "▶️ Reproducir" if is_video else "👁️ Ver"
        btn_abrir = ModernButton(abrir_texto)
        btn_abrir.clicked.connect(partial(os.startfile, archivo_path))

        btn_eliminar = ModernButton("🗑️ Eliminar", "eliminar")
        btn_eliminar.clicked.connect(partial(self.eliminar_referencia_archivo, archivo_path, nombre_archivo))

        btn_layout.addWidget(btn_abrir)
        btn_layout.addWidget(btn_eliminar)
        ref_layout.addLayout(btn_layout)

        return ref_frame

    def eliminar_referencia_archivo(self, archivo_path, nombre_archivo):
        """Eliminar un archivo del proyecto"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de que quieres eliminar la referencia '{nombre_archivo}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                os.remove(archivo_path)
                self.cargar_referencias()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo: {str(e)}")


class DriveUploadThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished_upload = pyqtSignal(bool, str)

    def __init__(self, file_path, name=None):
        super().__init__()
        self.file_path = file_path
        self.name = name or os.path.basename(file_path)

    def run(self):
        try:
            self.message.emit("⏳ Subiendo a Google Drive...")
            self.progress.emit(10)
            drive = get_drive_service()
            file_metadata = {"name": self.name}
            media = DriveMediaFileUpload(self.file_path, resumable=True)
            request = drive.files().create(body=file_metadata, media_body=media, fields="id")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.progress.emit(int(status.progress() * 100))
            file_id = response.get("id")
            # Make it publicly readable
            drive.permissions().create(fileId=file_id, body={"role":"reader","type":"anyone"}).execute()
            link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            self.finished_upload.emit(True, link)
        except Exception as e:
            self.finished_upload.emit(False, f"Error: {str(e)}")

class DriveUploadDialog(QDialog):
    def __init__(self, file_path, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📂 Subir a Google Drive")
        self.setFixedSize(480, 260)
        self.setStyleSheet(DARK_STYLE_SHEET)
        self.file_path = file_path
        self.file_name = file_name

        layout = QVBoxLayout()
        self.setLayout(layout)

        titulo = QLabel(f"📂 Subir: {file_name}")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size:16px; font-weight:bold; color:#ffffff; padding:12px;")
        layout.addWidget(titulo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#ffffff; font-style:italic;")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_subir = ModernButton("📂 Subir a Drive", "youtube")
        self.btn_subir.clicked.connect(self.iniciar_subida)
        btn_layout.addWidget(self.btn_subir)

        self.btn_cancelar = ModernButton("Cancelar", "eliminar")
        self.btn_cancelar.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancelar)

        layout.addLayout(btn_layout)
        self.upload_thread = None

    def iniciar_subida(self):
        self.btn_subir.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.upload_thread = DriveUploadThread(self.file_path, self.file_name)
        self.upload_thread.progress.connect(self.progress_bar.setValue)
        self.upload_thread.message.connect(self.status_label.setText)
        self.upload_thread.finished_upload.connect(self.finalizada)
        self.upload_thread.start()

    def finalizada(self, success, message):
        self.btn_subir.setEnabled(True)
        if success:
            # copy link to clipboard
            try:
                QGuiApplication.clipboard().setText(message)
            except Exception:
                pass
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("✅ Subida Exitosa")
            msg.setText(f"Enlace copiado al portapapeles:\n{message}")
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()
            self.close()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("❌ Error en Subida")
            msg.setText(message)
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()
            self.progress_bar.setVisible(False)
            self.status_label.setText("")
class YouTubeUploadDialog(QDialog):
    def __init__(self, video_path, video_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📤 Subir a YouTube")
        self.setFixedSize(500, 400)
        self.setStyleSheet(DARK_STYLE_SHEET)
        self.video_path = video_path
        self.video_name = video_name
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Título
        titulo = QLabel(f"📤 Subir: {video_name}")
        titulo.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            padding: 15px;
            text-align: center;
        """)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)
        
        # Formulario
        form_group = QGroupBox("📝 Detalles del Video")
        form_layout = QVBoxLayout()
        
        # Título del video
        form_layout.addWidget(QLabel("Título:"))
        self.input_titulo = QLineEdit()
        self.input_titulo.setText(os.path.splitext(video_name)[0])
        form_layout.addWidget(self.input_titulo)
        
        # Descripción
        form_layout.addWidget(QLabel("Descripción:"))
        self.input_descripcion = QTextEdit()
        self.input_descripcion.setMaximumHeight(100)
        self.input_descripcion.setPlainText("Video subido desde el Gestor de Clientes")
        form_layout.addWidget(self.input_descripcion)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Progreso
        self.progress_group = QGroupBox("📊 Progreso de Subida")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #ffffff; font-style: italic;")
        progress_layout.addWidget(self.status_label)
        
        self.progress_group.setLayout(progress_layout)
        layout.addWidget(self.progress_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        self.btn_subir = ModernButton("📤 Subir a YouTube", "youtube")
        self.btn_subir.clicked.connect(self.iniciar_subida)
        btn_layout.addWidget(self.btn_subir)
        
        self.btn_cancelar = ModernButton("Cancelar", "eliminar")
        self.btn_cancelar.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancelar)
        
        layout.addLayout(btn_layout)
        
        self.upload_thread = None
    
    def iniciar_subida(self):
        """Iniciar proceso de subida"""
        titulo = self.input_titulo.text().strip()
        descripcion = self.input_descripcion.toPlainText().strip()
        
        if not titulo:
            QMessageBox.warning(self, "⚠️ Advertencia", "El título no puede estar vacío.")
            return
        
        # Deshabilitar botón y mostrar progreso
        self.btn_subir.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Iniciar thread de subida
        self.upload_thread = YouTubeUploadThread(self.video_path, titulo, descripcion)
        self.upload_thread.progress.connect(self.progress_bar.setValue)
        self.upload_thread.message.connect(self.status_label.setText)
        self.upload_thread.finished_upload.connect(self.subida_finalizada)
        self.upload_thread.start()
    
    def subida_finalizada(self, success, message):
        """Callback cuando termina la subida"""
        self.btn_subir.setEnabled(True)
        
        if success:
            # Extraer el enlace del mensaje
            link_start = message.find('https://')
            if link_start != -1:
                video_link = message[link_start:].strip()
                try:
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setText(video_link)
                    message += "\n\n🔗 El enlace se ha copiado al portapapeles."
                except Exception as e:
                    print(f"Error al copiar al portapapeles: {e}")
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("✅ Subida Exitosa")
            msg.setText(message)
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()
            self.close()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("❌ Error de Subida")
            msg.setText(message)
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()
            self.progress_bar.setVisible(False)
            self.status_label.setText("")

class ClienteManager(QWidget):
    estado_cambiado = pyqtSignal(str, str) # Señal: (nombre_video, nuevo_estado)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Gestión de Clientes y Videos - Versión Pro Dark")
        self.setGeometry(100,100,1700,900)
        self.setStyleSheet(DARK_STYLE_SHEET)
        self.cliente_seleccionado = None
        self.notas_cliente = {}  # Diccionario para almacenar las notas de los clientes

        # Layout principal con splitter
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- SIDEBAR ---
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar.setMinimumHeight(600)
        
        side_layout = QVBoxLayout()
        side_layout.setContentsMargins(15, 15, 15, 15) # Añadir padding general
        side_layout.setSpacing(10) # Añadir espaciado entre widgets
        sidebar.setLayout(side_layout)

        # Título sidebar
        titulo_sidebar = QLabel("👥 CLIENTES")
        titulo_sidebar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(titulo_sidebar)

        # Buscador
        self.input_cliente = QLineEdit()
        self.input_cliente.setPlaceholderText("🔍 Buscar cliente...")
        self.input_cliente.textChanged.connect(self.filtrar_clientes)
        side_layout.addWidget(self.input_cliente)

        # Botones de cliente
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8) # Espaciado entre botones
        
        btn_nuevo = ModernButton("✨ Crear Cliente", "crear")
        btn_nuevo.clicked.connect(self.crear_cliente_ui)
        btn_layout.addWidget(btn_nuevo)
        
        btn_eliminar_cliente = ModernButton("🗑️ Eliminar Cliente", "eliminar")
        btn_eliminar_cliente.clicked.connect(self.eliminar_cliente_ui)
        btn_layout.addWidget(btn_eliminar_cliente)
        
        btn_abrir_cliente = ModernButton("📁 Abrir Carpeta")
        btn_abrir_cliente.clicked.connect(self.abrir_cliente_carpeta_ui)
        btn_layout.addWidget(btn_abrir_cliente)

        # Botón de Inicio
        btn_inicio = ModernButton("🏠 Inicio", "verde")
        btn_inicio.clicked.connect(self.mostrar_resumen_global)
        btn_layout.insertWidget(0, btn_inicio)  # Insertar al principio
        
        side_layout.addLayout(btn_layout)

        # Lista de clientes
        self.list_clientes = QListWidget()
        self.list_clientes.itemClicked.connect(self.seleccionar_cliente)
        side_layout.addWidget(self.list_clientes)

        splitter.addWidget(sidebar)

        # --- PANEL CENTRAL ---
        center_widget = QWidget()
        center_layout = QVBoxLayout()
        center_widget.setLayout(center_layout)

        # --- Contenedor para Paneles Superiores (se oculta en resumen) ---
        self.paneles_superiores = QWidget()
        paneles_layout = QVBoxLayout(self.paneles_superiores)
        paneles_layout.setContentsMargins(0, 0, 0, 0)

        # Área de información del cliente
        info_group = QGroupBox("📊 Cliente Seleccionado")
        info_layout = QHBoxLayout()
        self.label_cliente_actual = QLabel("Ningún cliente seleccionado")
        self.label_cliente_actual.setObjectName("clienteActualLabel")
        info_layout.addWidget(self.label_cliente_actual)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        info_layout.addWidget(self.progress_bar)
        info_group.setLayout(info_layout)
        paneles_layout.addWidget(info_group)

        # Área de acciones
        actions_group = QGroupBox("🎬 Gestión de Videos")
        actions_layout = QHBoxLayout()
        self.input_video = QLineEdit()
        self.input_video.setPlaceholderText("🎭 Nombre del nuevo video...")
        actions_layout.addWidget(self.input_video, 2)
        btn_video_nuevo = ModernButton("➕ Video Nuevo")
        btn_video_nuevo.clicked.connect(self.agregar_video_nuevo_ui)
        actions_layout.addWidget(btn_video_nuevo, 1)
        btn_video_hecho = ModernButton("📤 Video Terminado")
        btn_video_hecho.clicked.connect(self.agregar_video_hecho_ui)
        actions_layout.addWidget(btn_video_hecho, 1)
        actions_group.setLayout(actions_layout)
        paneles_layout.addWidget(actions_group)

        center_layout.addWidget(self.paneles_superiores)

        # Pestañas mejoradas
        self.tabs = QTabWidget()
        
        # Tab Pendientes
        self.tab_pendientes = QWidget()
        self.scroll_pendientes = QScrollArea()
        self.scroll_pendientes.setWidgetResizable(True)
        self.container_pendientes = QWidget()
        self.layout_pendientes = QVBoxLayout()
        self.layout_pendientes.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_pendientes.setLayout(self.layout_pendientes)
        self.scroll_pendientes.setWidget(self.container_pendientes)
        
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(self.scroll_pendientes)
        self.tab_pendientes.setLayout(tab_layout)
        self.tabs.addTab(self.tab_pendientes, "⏳ Pendientes")

        # Tab Hechos (con Grid Layout)
        self.tab_hechos = QWidget()
        hechos_main_layout = QVBoxLayout(self.tab_hechos)

        self.grid_hechos = QGridLayout()
        self.grid_hechos.setSpacing(15)
        self.grid_hechos.setContentsMargins(10, 10, 10, 10)

        container_hechos = QWidget()
        container_hechos.setLayout(self.grid_hechos)

        scroll_hechos = QScrollArea()
        scroll_hechos.setWidgetResizable(True)
        scroll_hechos.setWidget(container_hechos)

        hechos_main_layout.addWidget(scroll_hechos)
        self.tabs.addTab(self.tab_hechos, "✅ Terminados")
        
        # Tab Referencias
        self.tab_referencias = QWidget()
        self.scroll_referencias = QScrollArea()
        self.scroll_referencias.setWidgetResizable(True)
        self.container_referencias = QWidget()
        self.layout_referencias = QVBoxLayout()
        self.layout_referencias.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_referencias.setLayout(self.layout_referencias)
        self.scroll_referencias.setWidget(self.container_referencias)
        
        # Tab Notas
        self.tab_notas = QWidget()
        self.scroll_notas = QScrollArea()
        self.scroll_notas.setWidgetResizable(True)
        self.container_notas = QWidget()
        self.layout_notas = QVBoxLayout()
        self.layout_notas.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_notas.setLayout(self.layout_notas)
        self.scroll_notas.setWidget(self.container_notas)
        
        # Configurar el editor de notas
        self.init_ui_notas()
        
        # Layout principal de referencias
        ref_main_layout = QVBoxLayout()
        
        # Sección para agregar nueva referencia
        ref_add_group = QGroupBox("➕ Gestión de Referencias")
        ref_add_layout = QHBoxLayout()
        
        # Botón para agregar referencia
        self.btn_agregar_referencia = ModernButton("➕ Agregar Referencia")
        self.btn_agregar_referencia.clicked.connect(self.agregar_referencia)
        ref_add_layout.addWidget(self.btn_agregar_referencia, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Botón para abrir carpeta de referencias
        self.btn_abrir_carpeta_referencias = ModernButton("📂 Abrir Carpeta de Referencias")
        self.btn_abrir_carpeta_referencias.clicked.connect(self.abrir_carpeta_referencias)
        ref_add_layout.addWidget(self.btn_abrir_carpeta_referencias, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Espaciador para empujar los botones a la izquierda
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        ref_add_layout.addItem(spacer)
        
        ref_add_group.setLayout(ref_add_layout)
        ref_main_layout.addWidget(ref_add_group)
        
        # Sección para mostrar referencias existentes
        ref_view_group = QGroupBox("📌 Referencias")
        ref_view_layout = QVBoxLayout()
        
        # Contenedor para la cuadrícula de referencias
        self.referencias_grid = QWidget()
        self.grid_referencias = QGridLayout()
        self.grid_referencias.setSpacing(15)
        self.grid_referencias.setContentsMargins(10, 10, 10, 10)
        self.referencias_grid.setLayout(self.grid_referencias)
        
        # Añadir al layout con scroll
        ref_view_scroll = QScrollArea()
        ref_view_scroll.setWidgetResizable(True)
        ref_view_scroll.setWidget(self.referencias_grid)
        
        ref_view_layout.addWidget(ref_view_scroll)
        ref_view_group.setLayout(ref_view_layout)
        ref_main_layout.addWidget(ref_view_group, 1)  # El 1 hace que ocupe el espacio restante
        
        self.tab_referencias.setLayout(ref_main_layout)
        self.tabs.addTab(self.tab_referencias, "📌 Referencias")
        
        # Añadir pestaña de Notas
        self.tabs.addTab(self.tab_notas, "📝 Notas")
        # El Pomodoro ahora se agregará al resumen

        # --- Stack para cambiar entre Resumen y Pestañas de Cliente ---
        self.main_stack = QStackedWidget()

        # Vista 1: Resumen Global (se creará en un método aparte)
        self.resumen_widget = self.crear_vista_resumen()
        self.main_stack.addWidget(self.resumen_widget)

        # Vista 1: Pestañas del Cliente
        self.main_stack.addWidget(self.tabs)

        # Vista 2: Pantalla de Carga
        self.loading_widget = self.crear_vista_carga()
        self.main_stack.addWidget(self.loading_widget)

        center_layout.addWidget(self.main_stack)
        splitter.addWidget(center_widget)

        # Configurar proporciones del splitter
        splitter.setSizes([300, 1000])

        # Conectar la señal personalizada al método que maneja el cambio
        self.estado_cambiado.connect(self.cambiar_estado)

        # Inicializar
        self.actualizar_clientes()
        self.actualizar_videos()
        self.paneles_superiores.setVisible(False) # Oculto al inicio

        

    def actualizar_clientes(self):
        self.list_clientes.clear()
        if not os.path.exists(RUTA_CLIENTES):
            os.makedirs(RUTA_CLIENTES)
            
        clientes = []
        for c in sort_naturally(os.listdir(RUTA_CLIENTES)):
            if os.path.isdir(os.path.join(RUTA_CLIENTES,c)):
                clientes.append(c)
        
        for cliente in clientes:
            item = QListWidgetItem(f"👤 {cliente}")
            item.setData(Qt.ItemDataRole.UserRole, cliente)
            self.list_clientes.addItem(item)

    def filtrar_clientes(self, texto):
        texto = texto.strip().lower()
        self.list_clientes.clear()
        if not os.path.exists(RUTA_CLIENTES):
            return
            
        for c in sort_naturally(os.listdir(RUTA_CLIENTES)):
            if os.path.isdir(os.path.join(RUTA_CLIENTES, c)) and texto in c.lower():
                item = QListWidgetItem(f"👤 {c}")
                item.setData(Qt.ItemDataRole.UserRole, c)
                self.list_clientes.addItem(item)
    
    def mostrar_resumen_global(self):
        self.list_clientes.clearSelection()
        self.seleccionar_cliente(None)
        # Limpiar el editor de notas cuando se muestra el resumen
        self.editor_notas.clear()
        self.editor_notas.setEnabled(False)
        self.btn_guardar_notas.setEnabled(False)
        self.etiqueta_estado.setText("Ningún cliente seleccionado")
        
        # Mostrar el widget de resumen y ocultar los paneles superiores
        self.main_stack.setCurrentWidget(self.resumen_widget)
        self.paneles_superiores.setVisible(False)
        
    def init_ui_notas(self):
        """Inicializa la interfaz de usuario para las notas del cliente"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Título
        titulo = QLabel("Notas del Cliente")
        titulo.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(titulo)
        
        # Editor de notas
        self.editor_notas = QTextEdit()
        self.editor_notas.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                min-height: 300px;
            }
        """)
        main_layout.addWidget(self.editor_notas)
        
        # Botón para guardar
        self.btn_guardar_notas = ModernButton("💾 Guardar Notas")
        self.btn_guardar_notas.clicked.connect(self.guardar_notas_cliente)
        main_layout.addWidget(self.btn_guardar_notas, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Etiqueta de estado
        self.etiqueta_estado = QLabel("")
        self.etiqueta_estado.setStyleSheet("color: #888a8c; font-style: italic;")
        main_layout.addWidget(self.etiqueta_estado)
    
    def cargar_notas_cliente(self, nombre_cliente):
        """Carga las notas del cliente desde el archivo"""
        if not nombre_cliente:
            self.editor_notas.clear()
            self.editor_notas.setEnabled(False)
            self.btn_guardar_notas.setEnabled(False)
            self.etiqueta_estado.setText("Ningún cliente seleccionado")
            return
            
        ruta_notas = os.path.join(RUTA_CLIENTES, nombre_cliente, "notas.txt")
        
        try:
            if os.path.exists(ruta_notas):
                with open(ruta_notas, 'r', encoding='utf-8') as f:
                    self.editor_notas.setPlainText(f.read())
            else:
                self.editor_notas.clear()
                
            self.editor_notas.setEnabled(True)
            self.btn_guardar_notas.setEnabled(True)
            self.etiqueta_estado.setText(f"Notas cargadas para {nombre_cliente}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las notas: {str(e)}")
            self.editor_notas.clear()
    
    def guardar_notas_cliente(self):
        """Guarda las notas del cliente en el archivo"""
        if not self.cliente_seleccionado:
            return
            
        ruta_notas = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "notas.txt")
        
        try:
            with open(ruta_notas, 'w', encoding='utf-8') as f:
                f.write(self.editor_notas.toPlainText())
            
            self.etiqueta_estado.setText("Notas guardadas correctamente")
            
            # Temporizador para borrar el mensaje después de 3 segundos
            QTimer.singleShot(3000, lambda: self.etiqueta_estado.setText(""))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las notas: {str(e)}")
    
    def seleccionar_cliente(self, item):
        if item:
            # Mostrar pantalla de carga
            self.main_stack.setCurrentIndex(2)
            self.paneles_superiores.setVisible(False)
            QApplication.processEvents() # Asegura que se muestre la pantalla de carga

            self.cliente_seleccionado = item.data(Qt.ItemDataRole.UserRole)
            self.label_cliente_actual.setText(f"Cliente: {self.cliente_seleccionado}")
            cliente_path = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
            ref_path = os.path.join(cliente_path, "Referencias")
            if not os.path.exists(ref_path):
                os.makedirs(ref_path)
            
            # Cargar datos
            self.actualizar_videos()
            self.cargar_notas_cliente(self.cliente_seleccionado)
            
            # Mostrar vista del cliente
            self.main_stack.setCurrentIndex(1)
            self.paneles_superiores.setVisible(True)
        else:
            self.cliente_seleccionado = None
            self.label_cliente_actual.setText("Ningún cliente seleccionado")
            self.actualizar_videos()
            self.main_stack.setCurrentIndex(0)
            self.paneles_superiores.setVisible(False)

    def crear_cliente_ui(self):
        dialog = NuevoClienteDialog()
        if dialog.exec():
            nombre = dialog.nombre_cliente
            if nombre:
                if crear_cliente(nombre):
                    # Crear archivo de notas vacío
                    ruta_notas = os.path.join(RUTA_CLIENTES, nombre, "notas.txt")
                    try:
                        with open(ruta_notas, 'w', encoding='utf-8') as f:
                            f.write("")
                    except Exception as e:
                        QMessageBox.warning(self, "Advertencia", 
                                         f"Se creó el cliente pero no se pudo crear el archivo de notas: {str(e)}")
                    
                    self.actualizar_clientes()
                    # Seleccionar el nuevo cliente
                    for i in range(self.list_clientes.count()):
                        if self.list_clientes.item(i).text() == f"👤 {nombre}":
                            self.list_clientes.setCurrentRow(i)
                            break
                            
    def agregar_video_nuevo_ui(self):
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return

        nombre_video = self.input_video.text().strip()
        if not nombre_video:
            QMessageBox.warning(self, "Advertencia", "Por favor, introduce un nombre para el video.")
            return

        # Asegurarnos de que self.cliente_seleccionado tiene el nombre limpio
        cliente_nombre_limpio = self.cliente_seleccionado
        if not cliente_nombre_limpio:
            QMessageBox.warning(self, "Advertencia", "Error interno: no se pudo obtener el nombre del cliente.")
            return

        if agregar_video_nuevo(cliente_nombre_limpio, nombre_video):
            self.input_video.clear()
            self.actualizar_videos()
        else:
            QMessageBox.critical(self, "Error", f"No se pudo crear el video '{nombre_video}'.")

    def agregar_video_hecho_ui(self):
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return

        archivos, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar videos terminados",
            "",
            "Videos (*.mp4 *.avi *.mov *.mkv)"
        )

        if archivos:
            agregar_video_hecho(self.cliente_seleccionado, archivos)
            self.actualizar_videos()
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("✅ Proceso Completado")
            msg.setText(f"Se agregaron {len(archivos)} video(s) terminado(s)")
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()

    def abrir_cliente_carpeta_ui(self):
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return
        
        ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        if os.path.exists(ruta_cliente):
            os.startfile(ruta_cliente)
        else:
            QMessageBox.critical(self, "Error", f"La carpeta para el cliente '{self.cliente_seleccionado}' no fue encontrada.")

    def eliminar_cliente_ui(self):
        if not hasattr(self, 'cliente_seleccionado') or not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return
            
        # Confirmar eliminación
        respuesta = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            f"¿Estás seguro de que quieres eliminar al cliente '{self.cliente_seleccionado}'?\n\n¡Esta acción no se puede deshacer!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                if eliminar_cliente(self.cliente_seleccionado):
                    # Limpiar selección
                    self.cliente_seleccionado = None
                    self.label_cliente_actual.setText("Ningún cliente seleccionado")
                    # Actualizar lista de clientes
                    self.actualizar_clientes()
                    # Limpiar contenido
                    self.actualizar_videos()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el cliente: {str(e)}")
    
    def actualizar_videos(self):
        # Limpiar listas actuales
        for i in reversed(range(self.layout_pendientes.count())): 
            widget = self.layout_pendientes.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        # Limpiar cuadrícula de videos terminados
        if hasattr(self, 'grid_hechos'):
            for i in reversed(range(self.grid_hechos.count())):
                widget = self.grid_hechos.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
                
        # Limpiar referencias
        if hasattr(self, 'grid_referencias'):
            for i in reversed(range(self.grid_referencias.count())): 
                widget = self.grid_referencias.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
        
        # Actualizar referencias si hay un cliente seleccionado
        if hasattr(self, 'cliente_seleccionado') and self.cliente_seleccionado:
            self.actualizar_referencias()

        if not self.cliente_seleccionado:
            self.main_stack.setCurrentIndex(0) # Asegurarse de mostrar el resumen
            self.poblar_resumen_global()
            return

        ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        estados = cargar_estados(ruta_cliente)

        # Videos Pendientes
        videos_path = os.path.join(ruta_cliente, "Videos")
        if os.path.exists(videos_path):
            videos = sort_naturally(os.listdir(videos_path))
            if videos:
                for v in videos:
                    estado = estados.get(v, "Pendiente")
                    card = self.crear_tarjeta_pendiente(v, estado)
                    self.layout_pendientes.addWidget(card)
            else:
                empty_label = QLabel("📝 No hay videos pendientes")
                empty_label.setStyleSheet("""
                    color: #969696;
                    font-style: italic;
                    padding: 30px;
                    text-align: center;
                    font-size: 14px;
                """)
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout_pendientes.addWidget(empty_label)

        # Videos Hechos/Terminados (con cuadrícula)
        hechos_path = os.path.join(ruta_cliente, "Hechos")
        if os.path.exists(hechos_path):
            videos_terminados = [f for f in sort_naturally(os.listdir(hechos_path)) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
            
            # Configuración de la cuadrícula
            max_cols = 3  # Número de columnas fijas
            row, col = 0, 0

            if videos_terminados:
                for video in videos_terminados:
                    video_path = os.path.join(hechos_path, video)
                    card = self.crear_tarjeta_video_terminado(video, video_path)
                    # Asegurar que la tarjeta tenga un tamaño mínimo y máximo
                    card.setMinimumSize(300, 300)  # Tamaño mínimo para mantener consistencia
                    card.setMaximumSize(400, 400)  # Tamaño máximo para evitar que se vean demasiado grandes
                    
                    # Añadir a la cuadrícula
                    self.grid_hechos.addWidget(card, row, col)
                    
                    # Configurar el factor de estiramiento para que las columnas ocupen el mismo espacio
                    self.grid_hechos.setColumnStretch(col, 1)
                    
                    # Mover a la siguiente celda
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                
                # Asegurar que todas las filas tengan la misma altura
                for r in range(row + 1):
                    self.grid_hechos.setRowStretch(r, 1)
                    
                # Asegurar que las columnas tengan el mismo ancho
                self.grid_hechos.setColumnStretch(max_cols - 1, 1)
                
            else:
                # Mostrar mensaje cuando no hay videos
                empty_label = QLabel("🎬 No hay videos terminados")
                empty_label.setStyleSheet("""
                    color: #969696; 
                    font-style: italic; 
                    padding: 30px; 
                    font-size: 14px;
                    qproperty-alignment: AlignCenter;
                """)
                # Asegurar que el mensaje ocupe todo el ancho de la cuadrícula
                self.grid_hechos.addWidget(empty_label, 0, 0, 1, max_cols, Qt.AlignmentFlag.AlignCenter)
                
                # Asegurar que la fila del mensaje ocupe todo el espacio disponible
                self.grid_hechos.setRowStretch(0, 1)
                
                # Asegurar que las columnas tengan el mismo ancho
                for c in range(max_cols):
                    self.grid_hechos.setColumnStretch(c, 1)

    def sincronizar_notion(self):
        """Sincroniza los videos desde Notion y los muestra en la vista de tablero"""
        if NotionSync is None:
            QMessageBox.critical(self, "Error", "El módulo NotionSync no está disponible. Asegúrate de tener configurado el token y la base de datos de Notion.")
            return

        # Deshabilitar el botón y mostrar mensaje de carga
        self.btn_sincronizar_notion.setEnabled(False)
        self.btn_sincronizar_notion.setText("Sincronizando...")
        
        # Limpiar el contenedor de Notion
        for i in reversed(range(self.notion_layout.count())): 
            widget = self.notion_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        try:
            # Obtener los videos de Notion
            notion = NotionSync()
            videos = notion.get_pending_videos()
            
            if not videos:
                label = QLabel("No se encontraron videos en Notion o hubo un error al conectarse.")
                label.setStyleSheet("color: #ffffff; padding: 20px;")
                self.notion_layout.addWidget(label)
                return

            # Crear un layout de tablero horizontal
            board_layout = QHBoxLayout()
            board_layout.setSpacing(15)
            board_layout.setContentsMargins(0, 0, 0, 0)
            
            # Agrupar videos por estado
            videos_por_estado = {}
            for video in videos:
                estado = video.get('status', 'Sin estado')
                if estado not in videos_por_estado:
                    videos_por_estado[estado] = []
                videos_por_estado[estado].append(video)
            
            # Crear una columna para cada estado
            for estado, videos_estado in videos_por_estado.items():
                # Crear columna
                columna = QFrame()
                columna.setObjectName("notionColumn")
                columna.setStyleSheet("""
                    #notionColumn {
                        background-color: #2d2d2d;
                        border-radius: 8px;
                        padding: 10px;
                        min-width: 300px;
                        max-width: 300px;
                    }
                """)
                
                layout_columna = QVBoxLayout(columna)
                layout_columna.setContentsMargins(5, 5, 5, 5)
                
                # Título de la columna con contador
                titulo = QLabel(f"{estado} ({len(videos_estado)})")
                titulo.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        font-weight: bold;
                        font-size: 14px;
                        padding: 8px;
                        background-color: #3d3d3d;
                        border-radius: 4px;
                        margin-bottom: 10px;
                    }
                """)
                layout_columna.addWidget(titulo)
                
                # Contenedor para las tarjetas con scroll
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background: transparent;
                    }
                    QScrollBar:vertical {
                        border: none;
                        background: #3d3d3d;
                        width: 8px;
                        margin: 0px;
                        border-radius: 4px;
                    }
                    QScrollBar::handle:vertical {
                        background: #5e5e5e;
                        min-height: 20px;
                        border-radius: 4px;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        height: 0px;
                    }
                """)
                
                cards_container = QWidget()
                cards_layout = QVBoxLayout(cards_container)
                cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                cards_layout.setSpacing(10)
                cards_layout.setContentsMargins(2, 2, 10, 2)
                
                # Añadir tarjetas a la columna
                for video in videos_estado:
                    card = self.crear_tarjeta_notion(video)
                    if card:
                        cards_layout.addWidget(card)
                
                # Añadir espaciador al final
                cards_layout.addStretch()
                
                scroll.setWidget(cards_container)
                layout_columna.addWidget(scroll)
                
                # Añadir la columna al tablero
                board_layout.addWidget(columna)
            
            # Añadir el tablero a un contenedor con scroll horizontal
            board_container = QWidget()
            board_container.setLayout(board_layout)
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(board_container)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background: transparent;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: #2d2d2d;
                    height: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:horizontal {
                    background: #5e5e5e;
                    min-width: 20px;
                    border-radius: 4px;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
            """)
            
            self.notion_layout.addWidget(scroll_area)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al sincronizar con Notion: {str(e)}")
            print(f"Error en sincronizar_notion: {traceback.format_exc()}")
        finally:
            # Restaurar el botón
            self.btn_sincronizar_notion.setEnabled(True)
            self.btn_sincronizar_notion.setText("🔄 Sincronizar con Notion")
    
    def crear_tarjeta_notion(self, video):
        """Crea una tarjeta para mostrar un video de Notion"""
        try:
            # Crear el frame principal de la tarjeta
            card = QFrame()
            card.setObjectName("notionCard")
            card.setStyleSheet("""
                #notionCard {
                    background-color: #1e1e1e;
                    border: 1px solid #333;
                    border-radius: 6px;
                    padding: 12px;
                    margin: 0;
                    transition: all 0.2s ease;
                }
                #notionCard:hover {
                    background-color: #2d2d2d;
                    border-color: #444;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                }
                QLabel#title {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 8px;
                }
                QLabel#property {
                    color: #b3b3b3;
                    font-size: 12px;
                    margin: 2px 0;
                }
                QPushButton#notionButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    margin-top: 8px;
                }
                QPushButton#notionButton:hover {
                    background-color: #3d3d3d;
                    border-color: #555;
                }
            """)
            
            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(4)
            
            # Título del video
            titulo = QLabel(video.get('title', 'Sin título'))
            titulo.setObjectName("title")
            titulo.setWordWrap(True)
            layout.addWidget(titulo)
            
            # Cliente
            if 'client' in video and video['client']:
                cliente = QLabel(f"👤 {video['client']}")
                cliente.setObjectName("property")
                layout.addWidget(cliente)
            
            # Fecha de última modificación
            if 'last_edited' in video and video['last_edited']:
                fecha = QLabel(f"📅 {video['last_edited']}")
                fecha.setObjectName("property")
                layout.addWidget(fecha)
            
            # Duración (si está disponible)
            if 'duration' in video and video['duration']:
                duracion = QLabel(f"⏱️ {video['duration']}")
                duracion.setObjectName("property")
                layout.addWidget(duracion)
            
            # Botón para abrir en Notion
            if 'notion_url' in video and video['notion_url']:
                btn_notion = QPushButton("Abrir en Notion")
                btn_notion.setObjectName("notionButton")
                btn_notion.clicked.connect(lambda checked, url=video['notion_url']: webbrowser.open(url))
                layout.addWidget(btn_notion)
            
            # URL del video (si está disponible)
            if 'url' in video and video['url']:
                url = QLabel(f"🔗 <a href=\"{video['url']}\" style='color: #64b5f6; text-decoration: none;'>Ver video</a>")
                url.setObjectName("property")
                url.setOpenExternalLinks(True)
                layout.addWidget(url)
            
            return card
            
        except Exception as e:
            print(f"Error al crear tarjeta de Notion: {str(e)}")
            print(traceback.format_exc())
            return None

    def anclar_quick_access(ruta_carpeta):
        """
        Ancla la carpeta al Acceso rápido de Windows usando VBScript.
        
        Args:
            ruta_carpeta (str): Ruta absoluta a la carpeta que se desea anclar.
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        import os
        import subprocess
        import tempfile
        
        # Verificar si la carpeta existe
        if not os.path.exists(ruta_carpeta):
            print(f"Error: La carpeta no existe: {ruta_carpeta}")
            return False
        
        try:
            # Obtener la ruta absoluta
            ruta_absoluta = os.path.abspath(ruta_carpeta).replace('\\', '\\\\')
            
            # Crear un script VBS temporal
            vbs_script = f"""
            On Error Resume Next
            
            ' Crear objeto Shell
            Set shell = CreateObject("Shell.Application")
            
            ' Obtener la carpeta padre y el nombre de la carpeta
            Set fso = CreateObject("Scripting.FileSystemObject")
            folderPath = "{ruta_absoluta}"
            Set folder = fso.GetFolder(folderPath)
            parentPath = fso.GetParentFolderName(folderPath)
            folderName = fso.GetFileName(folderPath)
            
            ' Obtener el objeto de la carpeta
            Set shellFolder = shell.Namespace(parentPath)
            Set folderItem = shellFolder.ParseName(folderName)
            
            ' Verificar si se pudo obtener el objeto de la carpeta
            If folderItem Is Nothing Then
                WScript.Echo "No se pudo encontrar la carpeta: " & folderPath
                WScript.Quit 1
            End If
            
            ' Intentar con el verbo en español
            folderItem.InvokeVerbEx "pintar en acceso rápido"
            
            ' Si falla, intentar con el verbo en inglés
            If Err.Number <> 0 Then
                Err.Clear
                folderItem.InvokeVerbEx "Pin to Quick access"
                If Err.Number <> 0 Then
                    WScript.Echo "No se pudo anclar la carpeta. Asegúrese de que el sistema esté en español o inglés."
                    WScript.Quit 1
                End If
                WScript.Echo "Carpeta anclada correctamente (inglés): " & folderPath
            Else
                WScript.Echo "Carpeta anclada correctamente (español): " & folderPath
            End If
            
            WScript.Quit 0
            """
            
            # Guardar el script VBS temporal
            with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False, mode='w', encoding='utf-8') as f:
                f.write(vbs_script)
                vbs_path = f.name
            
            try:
                # Ejecutar el script VBS
                # Configurar para ocultar la ventana de consola de cscript
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                result = subprocess.run(
                    ['cscript.exe', '//Nologo', '//B', vbs_path],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Verificar el resultado
                if result.returncode == 0:
                    print(f"Carpeta anclada correctamente: {ruta_absoluta}")
                    if result.stdout:
                        print(result.stdout.strip())
                    return True
                else:
                    print(f"Error al anclar la carpeta. Código de salida: {result.returncode}")
                    if result.stderr:
                        print(f"Error: {result.stderr.strip()}")
                    return False
                    
            finally:
                # Eliminar el archivo temporal
                try:
                    os.unlink(vbs_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error inesperado al anclar la carpeta: {str(e)}")
            return False

    def actualizar_referencias(self):
        if not hasattr(self, 'grid_referencias') or not self.cliente_seleccionado:
            return
            
        # Limpiar referencias existentes
        for i in reversed(range(self.grid_referencias.count())): 
            widget = self.grid_referencias.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        cliente_path = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        ref_path = os.path.join(cliente_path, "Referencias")
        
        if not os.path.exists(ref_path):
            os.makedirs(ref_path)
            # Mostrar mensaje cuando no hay referencias
            empty_label = QLabel("📌 No hay referencias disponibles")
            empty_label.setStyleSheet("""
                color: #969696; 
                font-style: italic; 
                padding: 30px; 
                font-size: 14px;
                qproperty-alignment: AlignCenter;
            """)
            self.grid_referencias.addWidget(empty_label, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            return
            
        archivos = [f for f in os.listdir(ref_path) 
                   if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png'))]
        
        if not archivos:
            # Mostrar mensaje cuando no hay archivos de referencia
            empty_label = QLabel("📌 No hay archivos de referencia")
            empty_label.setStyleSheet("""
                color: #969696; 
                font-style: italic; 
                padding: 30px; 
                font-size: 14px;
                qproperty-alignment: AlignCenter;
            """)
            self.grid_referencias.addWidget(empty_label, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            return
        
        # Configuración de la cuadrícula
        max_cols = 3  # Número de columnas en la cuadrícula
        card_width = 300  # Ancho fijo para cada tarjeta
        
        # Ajustar el espaciado y márgenes de la cuadrícula
        self.grid_referencias.setSpacing(15)
        self.grid_referencias.setContentsMargins(10, 10, 10, 10)
        
        row = 0
        col = 0
        
        for archivo in archivos:
            archivo_path = os.path.join(ref_path, archivo)
            
            # Crear contenedor para la tarjeta de referencia
            card_frame = QFrame()
            card_frame.setObjectName("referenceCard")
            card_frame.setStyleSheet('''
                QFrame#referenceCard {
                    background: #28292d;
                    border: 1px solid #3c4043;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 0 5px 15px 5px;
                    min-width: %dpx;
                    max-width: %dpx;
                }
                QFrame#referenceCard:hover {
                    border-color: #2d7ff9;
                    background: #2e2f33;
                }
            ''' % (card_width - 30, card_width - 30))  # Ajustar según el padding
            
            card_frame.setFixedWidth(card_width)
            
            # Layout principal de la tarjeta
            card_layout = QVBoxLayout(card_frame)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(10)
            
            # Contenedor para la miniatura con relación de aspecto 16:9
            thumb_container = QLabel()
            thumb_container.setFixedSize(260, 160)  # Tamaño fijo para mantener consistencia
            thumb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_container.setStyleSheet("""
                QLabel {
                    background: #1e1e1e;
                    border-radius: 4px;
                    border: 1px solid #3c4043;
                }
            """)
            
            # Cargar miniatura o imagen
            is_video = archivo.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
            
            if is_video:
                # Para videos, extraer miniatura
                thumb_path = extract_thumbnail(archivo_path)
                if thumb_path and os.path.exists(thumb_path):
                    pixmap = QPixmap(thumb_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(260, 160, 
                                                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                    Qt.TransformationMode.SmoothTransformation)
                        # Centrar la imagen en el contenedor
                        thumb_container.setPixmap(scaled_pixmap)
                        thumb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                # Para imágenes, cargar directamente
                pixmap = QPixmap(archivo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(260, 160, 
                                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                Qt.TransformationMode.SmoothTransformation)
                    thumb_container.setPixmap(scaled_pixmap)
            
            # Si no se pudo cargar ninguna miniatura, mostrar un ícone
            if not thumb_container.pixmap() or thumb_container.pixmap().isNull():
                icon_text = "🎬" if is_video else "🖼️"
                thumb_container.setText(icon_text)
                thumb_container.setStyleSheet("""
                    QLabel {
                        font-size: 40px;
                        background: #1e1e1e;
                        border-radius: 4px;
                        border: 1px solid #3c4043;
                        color: #8a8a8a;
                    }
                """)
            
            # Hacer que la miniatura sea clickeable
            thumb_container.mousePressEvent = lambda e, path=archivo_path: os.startfile(path)
            
            # Contenedor para la miniatura
            thumb_wrapper = QWidget()
            thumb_layout = QVBoxLayout(thumb_wrapper)
            thumb_layout.setContentsMargins(0, 0, 0, 0)
            thumb_layout.setSpacing(0)
            thumb_layout.addWidget(thumb_container)
            
            card_layout.addWidget(thumb_wrapper)
            
            # Nombre del archivo (con elipsis si es muy largo)
            nombre_mostrar = os.path.splitext(archivo)[0]  # Quitar extensión
            if len(nombre_mostrar) > 25:
                nombre_mostrar = nombre_mostrar[:22] + "..."
                
            nombre_label = QLabel(nombre_mostrar)
            nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nombre_label.setToolTip(archivo)  # Mostrar nombre completo en tooltip
            nombre_label.setStyleSheet('''
                QLabel {
                    color: #e0e0e0;
                    font-size: 13px;
                    font-weight: 500;
                    margin-top: 5px;
                    padding: 0 5px;
                }
            ''')
            
            # Hacer que el nombre sea clickeable
            nombre_label.mousePressEvent = lambda e, path=archivo_path: os.startfile(path)
            
            card_layout.addWidget(nombre_label)
            
            # Botones de acción
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 10, 0, 0)
            btn_layout.setSpacing(10)
            
            # Botón para abrir/ver
            btn_abrir = ModernButton("▶️ Abrir" if is_video else "👁️ Ver")
            btn_abrir.clicked.connect(partial(os.startfile, archivo_path))
            
            # Botón para eliminar
            btn_eliminar = ModernButton("🗑️ Eliminar", "eliminar")
            btn_eliminar.setToolTip("Eliminar referencia")
            btn_eliminar.clicked.connect(partial(self.eliminar_referencia, archivo_path, archivo))
            
            # Añadir botones al layout
            btn_layout.addWidget(btn_abrir)
            btn_layout.addWidget(btn_eliminar)
            
            # Añadir los botones a la tarjeta
            card_layout.addWidget(btn_container)
            
            # Asegurar que la tarjeta tenga un tamaño consistente
            card_frame.setMinimumSize(280, 280)
            card_frame.setMaximumSize(320, 400)
            
            # Añadir a la cuadrícula
            self.grid_referencias.addWidget(card_frame, row, col)
            
            # Configurar el factor de estiramiento para que las columnas ocupen el mismo espacio
            self.grid_referencias.setColumnStretch(col, 1)
            
            # Mover a la siguiente celda
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Asegurar que todas las filas tengan la misma altura
        for r in range(row + 1):
            self.grid_referencias.setRowStretch(r, 1)
            
        # Asegurar que las columnas tengan el mismo ancho
        self.grid_referencias.setColumnStretch(max_cols - 1, 1)

    def abrir_carpeta_referencias_proyecto(self, nombre_proyecto):
        """Abre la carpeta de referencias de un proyecto específico en el explorador de archivos."""
        if not hasattr(self, 'cliente_seleccionado') or not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return
            
        cliente_path = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        proyecto_path = os.path.join(cliente_path, "Videos", nombre_proyecto)
        ref_path = os.path.join(proyecto_path, "Referencias")
        
        # Si la carpeta no existe, la creamos
        if not os.path.exists(ref_path):
            try:
                os.makedirs(ref_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta de referencias: {str(e)}")
                return
        
        # Abrir la carpeta en el explorador de archivos
        try:
            os.startfile(ref_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la carpeta de referencias: {str(e)}")
            
    def abrir_carpeta_referencias(self):
        """Abre la carpeta de referencias del cliente seleccionado en el explorador de archivos."""
        if not hasattr(self, 'cliente_seleccionado') or not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return
            
        cliente_path = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        ref_path = os.path.join(cliente_path, "Referencias")
        
        # Si la carpeta no existe, la creamos
        if not os.path.exists(ref_path):
            try:
                os.makedirs(ref_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta de referencias: {str(e)}")
                return
        
        # Abrir la carpeta en el explorador de archivos
        try:
            os.startfile(ref_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la carpeta de referencias: {str(e)}")

    def agregar_referencia(self):
        if not hasattr(self, 'cliente_seleccionado') or not self.cliente_seleccionado:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un cliente primero.")
            return
            
        # Mostrar diálogo para seleccionar archivos
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Archivos multimedia (*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png)")
        
        if file_dialog.exec():
            archivos = file_dialog.selectedFiles()
            cliente_path = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
            ref_path = os.path.join(cliente_path, "Referencias")
            
            if not os.path.exists(ref_path):
                os.makedirs(ref_path)
                
            for archivo_origen in archivos:
                nombre_archivo = os.path.basename(archivo_origen)
                archivo_destino = os.path.join(ref_path, nombre_archivo)
                
                # Si el archivo ya existe, agregar un número al final
                contador = 1
                while os.path.exists(archivo_destino):
                    nombre, extension = os.path.splitext(nombre_archivo)
                    archivo_destino = os.path.join(ref_path, f"{nombre}_{contador}{extension}")
                    contador += 1
                
                try:
                    shutil.copy2(archivo_origen, archivo_destino)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo copiar el archivo {nombre_archivo}: {str(e)}")
            
            # Actualizar la vista de referencias
            self.actualizar_referencias()
            
    def eliminar_referencia(self, ruta_archivo, nombre_archivo):
        respuesta = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            f"¿Estás seguro de que quieres eliminar la referencia '{nombre_archivo}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                os.remove(ruta_archivo)
                self.actualizar_referencias()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el archivo: {str(e)}")
    
    def crear_tarjeta_video_terminado(self, nombre_video, ruta_video):
        card_frame = QFrame()
        card_frame.setStyleSheet("""
            QFrame {
                background: #28292d;
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #2d7ff9;
            }
        """)
        
        layout = QVBoxLayout(card_frame)

        # Miniatura
        thumb_container = QLabel()
        thumb_container.setMinimumSize(280, 210)
        thumb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_container.setStyleSheet("background: #252526; border-radius: 6px;")

        thumb_path = extract_thumbnail(ruta_video)
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(280, 210, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            thumb_container.setPixmap(pixmap)
        else:
            thumb_container.setText("🎬")
            thumb_container.setStyleSheet("font-size: 60px; background: #252526; border-radius: 6px; color: #8a8a8a;")

        layout.addWidget(thumb_container)

        # Nombre del video
        nombre_label = QLabel(nombre_video if len(nombre_video) < 35 else nombre_video[:32] + "...")
        nombre_label.setToolTip(nombre_video)
        nombre_label.setStyleSheet("color: #e0e0e0; margin-top: 10px; font-size: 12px; font-weight: 500;")
        nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(nombre_label)

        # Botones
        btn_layout = QHBoxLayout()
        btn_reproducir = ModernButton("▶️ Reproducir")
        btn_reproducir.clicked.connect(lambda: os.startfile(ruta_video))
        
        btn_abrir_carpeta = ModernButton("📁 Abrir Carpeta")
        btn_abrir_carpeta.clicked.connect(lambda: os.startfile(os.path.dirname(ruta_video)))

        btn_layout.addWidget(btn_reproducir)
        btn_layout.addWidget(btn_abrir_carpeta)
        layout.addLayout(btn_layout)

        return card_frame

    def crear_vista_resumen(self):
        # Crear widget contenedor principal con pestañas
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Crear el widget de pestañas principal
        self.tabs_principal = QTabWidget()
        self.tabs_principal.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs_principal.setDocumentMode(False)
        
        # --- Pestaña de Resumen ---
        resumen_tab = QWidget()
        resumen_layout = QVBoxLayout(resumen_tab)
        resumen_layout.setContentsMargins(15, 15, 15, 15)
        resumen_layout.setSpacing(15)
        
        # Crear pestañas con mejor diseño
        self.tabs_resumen = QTabWidget()
        self.tabs_resumen.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs_resumen.setDocumentMode(False)  # Desactivar document mode para permitir estilos personalizados
        
        # Estilo mejorado para las pestañas
        self.tabs_resumen.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3c4043;
                border-radius: 8px;
                padding: 0px;
                background: #28292d;
                margin-top: 4px;
            }
            QTabBar::tab {
                background: #2d2f33;
                color: #b0b0b0;
                padding: 10px 24px;
                margin: 0px 2px;
                border: 1px solid #3c4043;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 14px;
                min-width: 180px;
                min-height: 32px;
                transition: all 0.2s ease;
            }
            QTabBar::tab:first {
                margin-left: 8px;
            }
            QTabBar::tab:selected {
                background: #1e88e5;
                color: white;
                font-weight: 600;
                border-color: #1e88e5;
                margin-bottom: -1px;
            }
            QTabBar::tab:!selected {
                margin-top: 4px;
                background: #252629;
                border-bottom: 1px solid #3c4043;
            }
            QTabBar::tab:hover:!selected {
                background: #3c4043;
                color: #ffffff;
            }
            QTabBar::tab:selected {
                border-top: 3px solid #64b5f6;
                padding-top: 8px;
            }
            QTabBar {
                background: transparent;
                border: none;
            }
        """)
        
        # --- Pestaña de Pomodoro ---
        pomodoro_tab = QWidget()
        pomodoro_layout = QVBoxLayout(pomodoro_tab)
        pomodoro_layout.setContentsMargins(10, 10, 10, 10)
        
        # Título del Pomodoro
        pomodoro_titulo = QLabel("🍅 Pomodoro")
        pomodoro_titulo.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            padding-bottom: 15px;
            border-bottom: 1px solid #3c4043;
            margin-bottom: 20px;
        """)
        pomodoro_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pomodoro_layout.addWidget(pomodoro_titulo)
        
        # Añadir el temporizador Pomodoro
        self.pomodoro_timer = PomodoroTimer()
        pomodoro_layout.addWidget(self.pomodoro_timer, 1)
        
        # --- Pestaña de Resumen de Videos ---
        resumen_tab = QWidget()
        resumen_layout = QVBoxLayout(resumen_tab)
        resumen_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título del resumen
        titulo = QLabel("📋 Resumen de Videos Pendientes")
        titulo.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            padding-bottom: 15px;
            border-bottom: 1px solid #3c4043;
            margin-bottom: 15px;
        """)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        resumen_layout.addWidget(titulo)
        
        # Área de desplazamiento para los videos
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2f33;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #5f6368;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.resumen_container = QWidget()
        self.resumen_layout = QVBoxLayout(self.resumen_container)
        self.resumen_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.resumen_layout.setSpacing(12)
        self.resumen_layout.setContentsMargins(5, 5, 15, 5)
        scroll_area.setWidget(self.resumen_container)
        
        resumen_layout.addWidget(scroll_area)
        
        # Añadir pestañas al QTabWidget
        self.tabs_resumen.addTab(resumen_tab, "📋 Resumen de Videos")
        self.tabs_resumen.addTab(pomodoro_tab, "🍅 Pomodoro")
        
        # Seleccionar la pestaña de Resumen por defecto
        self.tabs_resumen.setCurrentIndex(0)
        
        # Añadir las pestañas al layout principal
        main_layout.addWidget(self.tabs_resumen)
        
        return main_widget

    def poblar_resumen_global(self):
        # Limpiar resumen anterior
        for i in reversed(range(self.resumen_layout.count())):
            widget = self.resumen_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        videos_pendientes = []
        if not os.path.exists(RUTA_CLIENTES): return

        for nombre_cliente in sort_naturally(os.listdir(RUTA_CLIENTES)):
            ruta_cliente = os.path.join(RUTA_CLIENTES, nombre_cliente)
            if not os.path.isdir(ruta_cliente): continue

            videos_path = os.path.join(ruta_cliente, "Videos")
            if not os.path.exists(videos_path): continue

            estados = cargar_estados(ruta_cliente)
            for video in sort_naturally(os.listdir(videos_path)):
                if estados.get(video, "Pendiente") != "Terminado":
                    videos_pendientes.append((nombre_cliente, video))

        if not videos_pendientes:
            empty_label = QLabel("¡Felicidades! No hay videos pendientes.")
            empty_label.setStyleSheet("color: #888a8c; font-style: italic; padding: 30px; font-size: 16px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.resumen_layout.addWidget(empty_label)
            return

        for cliente, video in videos_pendientes:
            card = self.crear_tarjeta_resumen(cliente, video)
            self.resumen_layout.addWidget(card)

    def crear_tarjeta_resumen(self, nombre_cliente, nombre_video):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background-color: #28292d; 
                border: 1px solid #3c4043; 
                border-radius: 8px; 
                padding: 12px; 
                margin-bottom: 8px;
            }
            QFrame:hover { border-color: #2d7ff9; }
        """)
        layout = QHBoxLayout(frame)

        # Miniatura
        thumb_label = QLabel()
        thumb_label.setFixedSize(100, 56)
        thumb_label.setStyleSheet("background-color: #202124; border-radius: 4px;")
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_path = os.path.join(RUTA_CLIENTES, nombre_cliente, "Videos", nombre_video)
        thumb_path = extract_thumbnail(video_path)
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(100, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            thumb_label.setPixmap(pixmap)
        else:
            thumb_label.setText("🎬")
            thumb_label.setStyleSheet("font-size: 24px; color: #888a8c;")
        layout.addWidget(thumb_label)

        # Info del video
        info_layout = QVBoxLayout()
        video_label = QLabel(nombre_video)
        video_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e0e0e0;")
        cliente_label = QLabel(nombre_cliente)
        cliente_label.setStyleSheet("font-size: 11px; color: #bdc1c6;")
        info_layout.addWidget(video_label)
        info_layout.addWidget(cliente_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Botón para ir al cliente
        btn_ir = ModernButton("Ir al Cliente")
        btn_ir.clicked.connect(lambda: self.seleccionar_cliente_por_nombre(nombre_cliente))
        layout.addWidget(btn_ir)

        return frame

    def seleccionar_cliente_por_nombre(self, nombre_cliente):
        for i in range(self.list_clientes.count()):
            item = self.list_clientes.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == nombre_cliente:
                self.list_clientes.setCurrentItem(item)
                self.seleccionar_cliente(item)
                break

    def crear_vista_carga(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label = QLabel("Cargando datos del cliente...")
        label.setStyleSheet("font-size: 20px; color: #bdc1c6; font-style: italic;")
        
        layout.addWidget(label)
        return widget

    def cambiar_estado(self, nombre_video, nuevo_estado):
        if not self.cliente_seleccionado:
            return
        try:
            ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
            estados = cargar_estados(ruta_cliente)
            estados[nombre_video] = nuevo_estado
            guardar_estados(ruta_cliente, estados)
            self.actualizar_videos()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cambiar el estado del video: {e}")

    def crear_tarjeta_pendiente(self, nombre, estado):
        frame = AnimatedFrame()
        frame.setFrameShape(QFrame.Shape.Box)

        # Asegurar que estado sea string
        estado = str(estado)

        # Paleta de colores de estado estilo Notion
        estilos_por_estado = {
            "Pendiente": "background-color: #452d1a; border: 1px solid #e67e22;",
            "Pagado":    "background-color: #1a452e; border: 1px solid #2ecc71;",
            "Revisión":  "background-color: #1a3a45; border: 1px solid #3498db;",
            "Terminado": "background-color: #3a1a45; border: 1px solid #9b59b6;"
        }

        # Estilo base + según estado
        estilo_base = """
            border-radius: 12px;
            margin: 8px;
            padding: 16px;
        """
        frame.setStyleSheet(estilo_base + estilos_por_estado.get(estado, ""))

        # --- Resto del contenido ---
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()

        emojis_estado = {"Pendiente": "⏳", "Pagado": "💰", "Revisión": "👁️", "Terminado": "✅"}
        emoji = emojis_estado.get(estado, "📝")

        titulo = QLabel(f"{emoji} {nombre}")
        titulo.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #ffffff;
        """)
        header_layout.addWidget(titulo, 1)

        combo_estado = QComboBox()
        combo_estado.addItems(["Pendiente", "Pagado", "Revisión", "Terminado"])
        combo_estado.setCurrentText(estado)
        combo_estado.currentTextChanged.connect(lambda nuevo_estado, n=nombre: self.estado_cambiado.emit(n, nuevo_estado))
        combo_estado.setStyleSheet("font-weight: 600; min-width: 120px;")
        header_layout.addWidget(combo_estado)

        layout.addLayout(header_layout)

        btn_layout = QHBoxLayout()
        btn_abrir = ModernButton("📁 Abrir")
        btn_abrir.clicked.connect(lambda _, n=nombre: self.abrir_carpeta(n))
        btn_layout.addWidget(btn_abrir)

        btn_ver = ModernButton("👀 Ver Contenido")
        btn_ver.clicked.connect(lambda _, n=nombre: self.abrir_contenido_pendiente(n))
        btn_layout.addWidget(btn_ver)

        btn_referencias = ModernButton("📌 Referencias")
        btn_referencias.clicked.connect(lambda _, n=nombre: self.gestionar_referencias_proyecto(n))
        btn_layout.addWidget(btn_referencias)

        btn_eliminar = ModernButton("🗑️ Eliminar", "eliminar")
        btn_eliminar.clicked.connect(lambda _, n=nombre: self.eliminar_pendiente(n))
        btn_layout.addWidget(btn_eliminar)

        layout.addLayout(btn_layout)
        frame.setLayout(layout)

        return frame

    def crear_tarjeta_proyecto_terminado(self, nombre, estado):
        """Crear tarjeta para proyecto terminado (carpeta completa movida)"""
        frame = AnimatedFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                       stop:0 #4c0e4c, stop:1 #6b1a6b);
            border: 2px solid #8b2a8b;
            border-radius: 12px;
            margin: 8px;
            padding: 16px;
        """)
        
        layout = QVBoxLayout()
        
        # Header de la tarjeta
        header_layout = QHBoxLayout()
        
        titulo = QLabel(f"✅ {nombre}")
        titulo.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #ffffff;
        """)
        header_layout.addWidget(titulo, 1)
        
        # Estado selector (solo visual para proyectos terminados)
        combo = QComboBox()
        combo.addItems(["Terminado"])
        combo.setCurrentText("Terminado")
        combo.setEnabled(False)  # No se puede cambiar
        combo.setStyleSheet("""
            QComboBox {
                font-weight: 600;
                min-width: 120px;
                background: #6b1a6b;
                color: #ffffff;
            }
        """)
        header_layout.addWidget(combo)
        
        layout.addLayout(header_layout)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        btn_abrir = ModernButton("📁 Abrir Carpeta")
        btn_abrir.clicked.connect(lambda _, n=nombre: self.abrir_carpeta_terminado(n))
        btn_layout.addWidget(btn_abrir)
        
        btn_ver = ModernButton("👀 Ver Contenido")
        btn_ver.clicked.connect(lambda _, n=nombre: self.abrir_contenido_terminado(n))
        btn_layout.addWidget(btn_ver)
        
        btn_volver = ModernButton("↩️ Volver a Pendiente")
        btn_volver.clicked.connect(lambda _, n=nombre: self.volver_a_pendiente(n))
        btn_layout.addWidget(btn_volver)
        
        btn_eliminar = ModernButton("🗑️ Eliminar", "eliminar")
        btn_eliminar.clicked.connect(lambda _, n=nombre: self.eliminar_proyecto_terminado(n))
        btn_layout.addWidget(btn_eliminar)
        
        layout.addLayout(btn_layout)
        frame.setLayout(layout)
        
        return frame

    def crear_tarjeta_archivo_suelto(self, nombre, ruta):
        """Crear tarjeta para archivo suelto (funcionalidad legacy)"""
        frame = AnimatedFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setStyleSheet("""
            background: #2d2d30;
            border: 2px solid #3e3e42;
            border-radius: 12px;
            margin: 8px;
            padding: 16px;
        """)
        
        layout = QVBoxLayout()
        
        # Header
        titulo = QLabel(f"🎬 {nombre}")
        titulo.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        """)
        layout.addWidget(titulo)
        
        # Botones - Solo para archivos sueltos
        btn_layout = QHBoxLayout()
        
        btn_ver = ModernButton("▶️ Reproducir")
        btn_ver.clicked.connect(lambda _, r=ruta: self.ver_video_terminado(r))
        btn_layout.addWidget(btn_ver)
        
        btn_eliminar = ModernButton("🗑️ Eliminar", "eliminar")
        btn_eliminar.clicked.connect(lambda _, r=ruta: self.eliminar_hecho(r))
        btn_layout.addWidget(btn_eliminar)
        
        layout.addLayout(btn_layout)
        frame.setLayout(layout)
        
        return frame

    def abrir_carpeta_terminado(self, nombre):
        """Abrir carpeta de proyecto terminado"""
        ruta_terminado = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Hechos", nombre)
        if os.path.exists(ruta_terminado):
            os.startfile(ruta_terminado)

    def abrir_contenido_terminado(self, nombre):
        """Abrir contenido de proyecto terminado"""
        ruta_terminado = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Hechos", nombre)
        if os.path.exists(ruta_terminado):
            dialog = ContenidoVideoDialog(ruta_terminado, None, None, self)  # Sin cliente/nombre para no mostrar "Pasar a Terminado"
            dialog.exec()

    def volver_a_pendiente(self, nombre):
        """Volver proyecto terminado a pendiente"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("↩️ Confirmar Regreso")
        msg.setText(f"¿Volver '{nombre}' a pendientes?")
        msg.setInformativeText("Se moverá la carpeta completa del proyecto de vuelta a pendientes.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet(DARK_STYLE_SHEET)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
                ruta_terminado = os.path.join(ruta_cliente, "Hechos", nombre)
                ruta_pendiente = os.path.join(ruta_cliente, "Videos", nombre)
                
                # Mover carpeta de vuelta
                if os.path.exists(ruta_terminado):
                    shutil.move(ruta_terminado, ruta_pendiente)
                    
                    # Actualizar estado
                    estados = cargar_estados(ruta_cliente)
                    estados[nombre] = "Pendiente"
                    guardar_estados(ruta_cliente, estados)
                    
                    # Mostrar éxito
                    success_msg = QMessageBox()
                    success_msg.setIcon(QMessageBox.Icon.Information)
                    success_msg.setWindowTitle("↩️ Proyecto Restaurado")
                    success_msg.setText(f"El proyecto '{nombre}' se movió a pendientes correctamente.")
                    success_msg.setStyleSheet(DARK_STYLE_SHEET)
                    success_msg.exec()
                    
                    # Actualizar interfaz
                    self.actualizar_videos()
                    
            except Exception as e:
                error_msg = QMessageBox()
                error_msg.setIcon(QMessageBox.Icon.Critical)
                error_msg.setWindowTitle("❌ Error")
                error_msg.setText(f"Error al mover el proyecto: {str(e)}")
                error_msg.setStyleSheet(DARK_STYLE_SHEET)
                error_msg.exec()

    def eliminar_proyecto_terminado(self, nombre):
        """Eliminar proyecto terminado completo"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("⚠️ Confirmar Eliminación")
        msg.setText(f"¿Eliminar el proyecto terminado '{nombre}'?")
        msg.setInformativeText("Se eliminará la carpeta completa con todos sus archivos. Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet(DARK_STYLE_SHEET)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            ruta_terminado = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Hechos", nombre)
            if os.path.exists(ruta_terminado):
                shutil.rmtree(ruta_terminado)
            
            # Eliminar del estado también
            ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
            estados = cargar_estados(ruta_cliente)
            if nombre in estados:
                del estados[nombre]
                guardar_estados(ruta_cliente, estados)
            
            self.actualizar_videos()

    def ver_video_terminado(self, ruta_video):
        """Mostrar contenido de video terminado - solo reproducir"""
        if os.path.exists(ruta_video):
            os.startfile(ruta_video)

    def cambiar_estado(self, nombre, valor):
        if not self.cliente_seleccionado:
            return
            
        ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
        estados = cargar_estados(ruta_cliente)
        
        # Si se marca como terminado, mover la carpeta completa
        if valor == "Terminado":
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("✅ Confirmar Finalización")
            msg.setText(f"¿Marcar '{nombre}' como terminado?")
            msg.setInformativeText("Se moverá la carpeta completa del proyecto a la sección de terminados.")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setStyleSheet(DARK_STYLE_SHEET)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                success = mover_a_terminado(self.cliente_seleccionado, nombre)
                if success:
                    # Mostrar éxito
                    success_msg = QMessageBox()
                    success_msg.setIcon(QMessageBox.Icon.Information)
                    success_msg.setWindowTitle("✅ Video Terminado")
                    success_msg.setText(f"El proyecto '{nombre}' se movió a terminados correctamente.")
                    success_msg.setStyleSheet(DARK_STYLE_SHEET)
                    success_msg.exec()
                    
                    # Actualizar interfaz
                    self.actualizar_videos()
                else:
                    # Mostrar error
                    error_msg = QMessageBox()
                    error_msg.setIcon(QMessageBox.Icon.Critical)
                    error_msg.setWindowTitle("❌ Error")
                    error_msg.setText("Error al mover el proyecto a terminados.")
                    error_msg.setStyleSheet(DARK_STYLE_SHEET)
                    error_msg.exec()
            else:
                # Revertir el combo box si cancela
                self.actualizar_videos()
        else:
            # Para otros estados, solo actualizar
            estados[nombre] = valor
            guardar_estados(ruta_cliente, estados)
            self.actualizar_videos()

    def abrir_carpeta(self, nombre):
        ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Videos", nombre)
        if os.path.exists(ruta_cliente):
            os.startfile(ruta_cliente)

    def abrir_contenido_pendiente(self, nombre):
        ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Videos", nombre)
        if os.path.exists(ruta_cliente):
            dialog = ContenidoVideoDialog(ruta_cliente, self.cliente_seleccionado, nombre, self)
            dialog.exec()

    def eliminar_pendiente(self, nombre):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("⚠️ Confirmar Eliminación")
        msg.setText(f"¿Eliminar el video pendiente '{nombre}'?")
        msg.setInformativeText("Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet(DARK_STYLE_SHEET)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            ruta = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Videos", nombre)
            if os.path.exists(ruta):
                shutil.rmtree(ruta)
            
            # Eliminar del estado también
            ruta_cliente = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado)
            estados = cargar_estados(ruta_cliente)
            if nombre in estados:
                del estados[nombre]
                guardar_estados(ruta_cliente, estados)
            
            self.actualizar_videos()

    def gestionar_referencias_proyecto(self, nombre_proyecto):
        """Abrir diálogo para gestionar referencias específicas de un proyecto"""
        if not self.cliente_seleccionado:
            QMessageBox.warning(self, "⚠️ Advertencia", "Por favor, selecciona un cliente primero.")
            return

        ruta_proyecto = os.path.join(RUTA_CLIENTES, self.cliente_seleccionado, "Videos", nombre_proyecto)
        if not os.path.exists(ruta_proyecto):
            QMessageBox.critical(self, "❌ Error", f"No se encontró el proyecto '{nombre_proyecto}'.")
            return

        # Crear y mostrar el diálogo de referencias del proyecto
        dialog = ReferenciasProyectoDialog(ruta_proyecto, nombre_proyecto, self)
        dialog.exec()

    def sincronizar_notion(self):
        """Sincroniza los videos desde Notion y los muestra en la vista de tablero"""
        if NotionSync is None:
            QMessageBox.critical(self, "Error", "El módulo NotionSync no está disponible. Asegúrate de tener configurado el token y la base de datos de Notion.")
            return

        # Deshabilitar el botón y mostrar mensaje de carga
        self.btn_sincronizar_notion.setEnabled(False)
        self.btn_sincronizar_notion.setText("Sincronizando...")
        
        # Limpiar el contenedor de Notion
        for i in reversed(range(self.notion_layout.count())): 
            widget = self.notion_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        try:
            # Obtener los videos de Notion
            notion = NotionSync()
            videos = notion.get_pending_videos()
            
            if not videos:
                label = QLabel("No se encontraron videos en Notion o hubo un error al conectarse.")
                label.setStyleSheet("color: #ffffff; padding: 20px;")
                self.notion_layout.addWidget(label)
                return

            # Crear un layout de tablero horizontal
            board_layout = QHBoxLayout()
            board_layout.setSpacing(15)
            board_layout.setContentsMargins(0, 0, 0, 0)
            
            # Agrupar videos por estado
            videos_por_estado = {}
            for video in videos:
                estado = video.get('status', 'Sin estado')
                if estado not in videos_por_estado:
                    videos_por_estado[estado] = []
                videos_por_estado[estado].append(video)
            
            # Crear una columna para cada estado
            for estado, videos_estado in videos_por_estado.items():
                # Crear columna
                columna = QFrame()
                columna.setObjectName("notionColumn")
                columna.setStyleSheet("""
                    #notionColumn {
                        background-color: #2d2d2d;
                        border-radius: 8px;
                        padding: 10px;
                        min-width: 300px;
                        max-width: 300px;
                    }
                """)
                
                layout_columna = QVBoxLayout(columna)
                layout_columna.setContentsMargins(5, 5, 5, 5)
                
                # Título de la columna con contador
                titulo = QLabel(f"{estado} ({len(videos_estado)})")
                titulo.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        font-weight: bold;
                        font-size: 14px;
                        padding: 8px;
                        background-color: #3d3d3d;
                        border-radius: 4px;
                        margin-bottom: 10px;
                    }
                """)
                layout_columna.addWidget(titulo)
                
                # Contenedor para las tarjetas con scroll
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background: transparent;
                    }
                    QScrollBar:vertical {
                        border: none;
                        background: #3d3d3d;
                        width: 8px;
                        margin: 0px;
                        border-radius: 4px;
                    }
                    QScrollBar::handle:vertical {
                        background: #5e5e5e;
                        min-height: 20px;
                        border-radius: 4px;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        height: 0px;
                    }
                """)
                
                cards_container = QWidget()
                cards_layout = QVBoxLayout(cards_container)
                cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                cards_layout.setSpacing(10)
                cards_layout.setContentsMargins(2, 2, 10, 2)
                
                # Añadir tarjetas a la columna
                for video in videos_estado:
                    card = self.crear_tarjeta_notion(video)
                    if card:
                        cards_layout.addWidget(card)
                
                # Añadir espaciador al final
                cards_layout.addStretch()
                
                scroll.setWidget(cards_container)
                layout_columna.addWidget(scroll)
                
                # Añadir la columna al tablero
                board_layout.addWidget(columna)
            
            # Añadir el tablero a un contenedor con scroll horizontal
            board_container = QWidget()
            board_container.setLayout(board_layout)
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(board_container)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background: transparent;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: #2d2d2d;
                    height: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:horizontal {
                    background: #5e5e5e;
                    min-width: 20px;
                    border-radius: 4px;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
            """)
            
            self.notion_layout.addWidget(scroll_area)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al sincronizar con Notion: {str(e)}")
            print(f"Error en sincronizar_notion: {traceback.format_exc()}")
        finally:
            # Restaurar el botón
            self.btn_sincronizar_notion.setEnabled(True)
            self.btn_sincronizar_notion.setText("🔄 Sincronizar con Notion")
    
    def crear_tarjeta_notion(self, video):
        """Crea una tarjeta para mostrar un video de Notion"""
        try:
            # Crear el frame principal de la tarjeta
            card = QFrame()
            card.setObjectName("notionCard")
            card.setStyleSheet("""
                #notionCard {
                    background-color: #1e1e1e;
                    border: 1px solid #333;
                    border-radius: 6px;
                    padding: 12px;
                    margin: 0;
                    transition: all 0.2s ease;
                }
                #notionCard:hover {
                    background-color: #2d2d2d;
                    border-color: #444;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                }
                QLabel#title {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 8px;
                }
                QLabel#property {
                    color: #b3b3b3;
                    font-size: 12px;
                    margin: 2px 0;
                }
                QPushButton#notionButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    margin-top: 8px;
                }
                QPushButton#notionButton:hover {
                    background-color: #3d3d3d;
                    border-color: #555;
                }
            """)
            
            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(4)
            
            # Título del video
            titulo = QLabel(video.get('title', 'Sin título'))
            titulo.setObjectName("title")
            titulo.setWordWrap(True)
            layout.addWidget(titulo)
            
            # Cliente
            if 'client' in video and video['client']:
                cliente = QLabel(f"👤 {video['client']}")
                cliente.setObjectName("property")
                layout.addWidget(cliente)
            
            # Fecha de última modificación
            if 'last_edited' in video and video['last_edited']:
                fecha = QLabel(f"📅 {video['last_edited']}")
                fecha.setObjectName("property")
                layout.addWidget(fecha)
            
            # Duración (si está disponible)
            if 'duration' in video and video['duration']:
                duracion = QLabel(f"⏱️ {video['duration']}")
                duracion.setObjectName("property")
                layout.addWidget(duracion)
            
            # Botón para abrir en Notion
            if 'notion_url' in video and video['notion_url']:
                btn_notion = QPushButton("Abrir en Notion")
                btn_notion.setObjectName("notionButton")
                btn_notion.clicked.connect(lambda checked, url=video['notion_url']: webbrowser.open(url))
                layout.addWidget(btn_notion)
            
            # URL del video (si está disponible)
            if 'url' in video and video['url']:
                url = QLabel(f"🔗 <a href=\"{video['url']}\" style='color: #64b5f6; text-decoration: none;'>Ver video</a>")
                url.setObjectName("property")
                url.setOpenExternalLinks(True)
                layout.addWidget(url)
            
            return card
            
        except Exception as e:
            print(f"Error al crear tarjeta de Notion: {str(e)}")
            print(traceback.format_exc())
            return None

# --- Aplicación Principal ---
def main():
    app = QApplication([])
    app.setStyle('Fusion')  # Usar el estilo Fusion para mejor apariencia
    
    # Configurar fuente de la aplicación
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Configurar paleta oscura
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # Crear y mostrar la ventana
    window = ClienteManager()
    
    # Establecer un tamaño mínimo para la ventana principal
    window.setMinimumSize(1600, 700)  # Tamaño mínimo razonable
    
    # Establecer tamaño inicial
    initial_width = 1200
    initial_height = 800
    window.resize(initial_width, initial_height)
    
    # Centrar la ventana usando QScreen
    screen = window.screen().availableGeometry()
    window_rect = window.frameGeometry()
    window_rect.moveCenter(screen.center())
    window.move(window_rect.topLeft())
    window.show()
    
    # Asegurarse de que el diseño se ajuste al redimensionar
    window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    # Agregar etiqueta de versión en la esquina inferior derecha
    version_label = QLabel("Version: 2.0", window)
    version_label.setStyleSheet("""
        color: #888888; 
        font-size: 10px; 
        font-style: italic;
        padding: 2px 8px;
        background-color: rgba(30, 30, 30, 0.7);
        border-radius: 8px;
    """)
    version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
    version_label.setGeometry(window.width() - 120, window.height() - 30, 100, 20)
    
    # Conectar el evento de cambio de tamaño para mantener la etiqueta en su lugar
    def resizeEvent(event):
        version_label.move(window.width() - 120, window.height() - 30)
        
    window.resizeEvent = resizeEvent
    window.show()
    
    app.exec()

class PomodoroTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pomodoro Timer")
        self.setMinimumSize(450, 600)
        
        # Configuración de tiempos (en segundos)
        self.work_time = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.time_left = self.work_time
        self.is_running = False
        self.is_working = True
        
        # Inicializar contadores
        self.pomodoros_completed = 0
        self.short_breaks_completed = 0
        self.long_breaks_completed = 0
        
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Selector de modo
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🍅 Trabajo", "work")
        self.mode_combo.addItem("☕ Descanso Corto", "short_break")
        self.mode_combo.addItem("🌴 Descanso Largo", "long_break")
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border-radius: 4px;
                background-color: #2d2f33;
                color: white;
                border: 1px solid #3c4043;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        layout.addWidget(self.mode_combo)

        # Título
        self.title_label = QLabel("🍅 Tiempo de Trabajo")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                margin: 10px 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Display del tiempo - Estilo moderno mejorado
        self.time_display = QLCDNumber()
        self.time_display.setDigitCount(5)
        self.time_display.setSegmentStyle(QLCDNumber.SegmentStyle.Filled)
        
        # Etiqueta del tiempo con fuente personalizada más grande
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 96px;
                font-weight: 800;
                letter-spacing: 4px;
                margin: 0;
                padding: 10px 0;
                text-shadow: 0 0 10px rgba(76, 175, 80, 0.3);
            }
        """)
        
        # Contenedor del tiempo con efecto de gradiente
        time_container = QWidget()
        time_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1e1e1e, stop: 0.5 #252525, stop: 1 #1e1e1e
                );
                border-radius: 20px;
                border: 1px solid #3c4043;
                margin: 5px;
            }
        """)
        
        time_layout = QVBoxLayout(time_container)
        time_layout.setContentsMargins(0, 20, 0, 20)
        time_layout.addWidget(self.time_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Configurar el layout principal del display
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        display_layout.setContentsMargins(10, 10, 10, 10)
        display_layout.addWidget(time_container)
        display_widget.setMinimumHeight(200)
        display_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 3px solid #2d2f33;
                border-radius: 25px;
                padding: 5px;
            }
        """)
        layout.addWidget(display_widget)

        # Estado actual - Mover justo debajo del reloj
        self.status_label = QLabel("Listo para comenzar")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-size: 13px;
                font-style: italic;
                margin: 0 0 10px 0;
            }
        """)
        layout.addWidget(self.status_label)

        # Controles - Botones modernos
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)  # Espaciado entre botones
        
        # Estilo común para los botones
        button_style = """
            QPushButton {
                background-color: #2d2f33;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: 600;
                min-width: 100px;
                margin: 5px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #3c4043;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                transform: translateY(1px);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }
        """
        
        # Botón de inicio
        self.start_button = QPushButton("▶ INICIAR")
        self.start_button.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botón de pausa
        self.pause_button = QPushButton("⏸ PAUSAR")
        self.pause_button.setStyleSheet(button_style + """
            QPushButton {
                background-color: #FFA000;
                color: white;
            }
            QPushButton:hover {
                background-color: #FFB74D;
            }
            QPushButton:pressed {
                background-color: #F57C00;
            }
        """)
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botón de reinicio
        self.reset_button = QPushButton("🔄 REINICIAR")
        self.reset_button.setStyleSheet(button_style + """
            QPushButton {
                background-color: #5C6BC0;
                color: white;
            }
            QPushButton:hover {
                background-color: #7986CB;
            }
            QPushButton:pressed {
                background-color: #3949AB;
            }
        """)
        self.reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_button.setToolTip("Reiniciar temporizador")
        
        # Añadir botones al layout
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.reset_button)
        
        layout.addLayout(controls_layout)
        
        # Contenedor para las estadísticas
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(10, 0, 10, 10)
        stats_layout.setSpacing(15)
        
        # Estilo común para los contadores
        counter_style = """
            QLabel {
                color: #E0E0E0;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 15px;
                border-radius: 8px;
                background-color: #252525;
                border: 1px solid #3c4043;
                min-width: 180px;
                text-align: center;
            }
        """
        
        # Contador de pomodoros
        self.pomodoro_count = QLabel("🍅 0")
        self.pomodoro_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_count.setStyleSheet(counter_style + """
            QLabel {
                border-left: 4px solid #4CAF50;
            }
        """)
        
        # Contador de descansos cortos
        self.short_break_count = QLabel("☕ 0")
        self.short_break_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.short_break_count.setStyleSheet(counter_style + """
            QLabel {
                border-left: 4px solid #2196F3;
            }
        """)
        
        # Contador de descansos largos
        self.long_break_count = QLabel("🌴 0")
        self.long_break_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.long_break_count.setStyleSheet(counter_style + """
            QLabel {
                border-left: 4px solid #FF9800;
            }
        """)
        
        # Añadir contadores al layout
        stats_layout.addWidget(self.pomodoro_count)
        stats_layout.addWidget(self.short_break_count)
        stats_layout.addWidget(self.long_break_count)
        
        layout.addWidget(stats_container)
        
        # Inicializar contadores
        self.pomodoros_completed = 0
        self.short_breaks_completed = 0
        self.long_breaks_completed = 0
        
        # Añadir espaciador para empujar todo hacia arriba
        layout.addStretch()
        
        # Estilo general del widget
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #3c4043;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px 0;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # Configurar señales
        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(self.reset_timer)

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

    def toggle_timer(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.timer.start(1000)  # Actualizar cada segundo
        self.start_button.setText("⏸ Pausar")
        self.is_running = True

    def pause_timer(self):
        self.timer.stop()
        self.start_button.setText("▶ Continuar")
        self.is_running = False

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.start_button.setText("▶ INICIAR")
        self.time_left = self.work_time if self.is_working else (self.short_break if self.mode_combo.currentData() == "short_break" else self.long_break)
        self.update_display()

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_display()
        else:
            self.timer_complete()

    def update_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        self.time_display.display(f"{minutes:02d}:{seconds:02d}")

    def timer_complete(self):
        self.timer.stop()
        self.is_running = False
        self.start_button.setText("▶ INICIAR")
        
        # Reproducir sonido de alarma
        try:
            # Reproducir sonido del sistema (sonido de alarma de Windows)
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
            # Repetir el sonido 3 veces
            for _ in range(2):
                winsound.Beep(1000, 500)  # Frecuencia 1000Hz, duración 500ms
                QApplication.processEvents()  # Permitir que la interfaz se actualice
                time.sleep(0.2)
        except Exception as e:
            print(f"Error al reproducir sonido: {e}")
            QApplication.beep()  # Fallback al beep básico
            
        # Determinar el siguiente modo
        current_mode = self.mode_combo.currentData()
        
        if current_mode == "work":
            # Después de trabajar, decidir qué tipo de descanso toca
            self.pomodoros_completed += 1
            self.pomodoro_count.setText(f"🍅 {self.pomodoros_completed}")
            
            if self.pomodoros_completed % 4 == 0:
                # Cada 4 pomodoros, descanso largo
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("¡Tiempo de descanso!")
                msg.setText("¡Buen trabajo! Es hora de un descanso largo de 15 minutos.")
                msg.setStyleSheet(DARK_STYLE_SHEET)
                msg.exec()
                self.mode_combo.setCurrentIndex(2)  # Cambiar a descanso largo
            else:
                # Descanso corto normal
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("¡Tiempo de descanso!")
                msg.setText("¡Buen trabajo! Toma un descanso corto de 5 minutos.")
                msg.setStyleSheet(DARK_STYLE_SHEET)
                msg.exec()
                self.mode_combo.setCurrentIndex(1)  # Cambiar a descanso corto
                
        else:
            # Después de un descanso, volver a trabajar
            if current_mode == "short_break":
                self.short_breaks_completed += 1
                self.short_break_count.setText(f"☕ {self.short_breaks_completed}")
            else:  # long_break
                self.long_breaks_completed += 1
                self.long_break_count.setText(f"🌴 {self.long_breaks_completed}")
                
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("¡Hora de trabajar!")
            msg.setText("El descanso ha terminado. ¡Es hora de trabajar!")
            msg.setStyleSheet(DARK_STYLE_SHEET)
            msg.exec()
            self.mode_combo.setCurrentIndex(0)  # Cambiar a modo trabajo
            
        # Cambiar al siguiente modo automáticamente
        
    # Si se desea iniciar automáticamente el siguiente temporizador, descomenta la siguiente línea:
    # self.start_timer()

    def change_mode(self, auto_switch=False):
        # Detener el temporizador actual si está en marcha
        was_running = self.is_running
        if was_running:
            self.timer.stop()
            
        mode = self.mode_combo.currentData()
        
        if mode == "work":
            self.time_left = self.work_time
            self.is_working = True
            self.title_label.setText("🍅 Tiempo de Trabajo")
            self.time_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 72px;
                    font-weight: 700;
                    letter-spacing: 2px;
                    margin: 0;
                    padding: 0;
                }
            """)
        elif mode == "short_break":
            self.time_left = self.short_break
            self.is_working = False
            self.title_label.setText("☕ Descanso Corto")
            self.time_label.setStyleSheet("""
                QLabel {
                    color: #2196F3;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 72px;
                    font-weight: 700;
                    letter-spacing: 2px;
                    margin: 0;
                    padding: 0;
                }
            """)
        else:  # long_break
            self.time_left = self.long_break
            self.is_working = False
            self.title_label.setText("🌴 Descanso Largo")
            self.time_label.setStyleSheet("""
                QLabel {
                    color: #FF9800;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 72px;
                    font-weight: 700;
                    letter-spacing: 2px;
                    margin: 0;
                    padding: 0;
                }
            """)
        
        # Actualizar la pantalla con el nuevo tiempo
        self.update_display()
        
        # Si el temporizador estaba en marcha, lo reiniciamos
        if was_running:
            self.start_timer()


if __name__ == "__main__":
    main()