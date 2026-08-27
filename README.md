# WPO - Inspección de Entrega de Turno ASRS

Plataforma web para realizar inspecciones de **WPO** (Work Place Organization) en la entrega de turno del sistema **ASRS** de Goodyear.

## 🚀 Funcionalidades

- **Código QR dinámico**: Genera un QR que apunta al formulario de inspección. Se escanea con el celular para registrar la inspección desde cualquier dispositivo en la red.
- **Formulario móvil**: Registro de:
  - Nombre del operador
  - Turno (A / B / C / D)
  - Fecha
  - Puntos de inspección (escritorio limpio, piso limpio, mueble de repuestos ordenado, sin repuestos en mesón o piso)
  - Comentarios / observaciones
  - **Registro fotográfico** desde la cámara o galería del celular
- **Dashboard de estadísticas**:
  - Total de inspecciones
  - Inspecciones del mes
  - Distribución por turno
  - Historial con fotos y detalle de cada punto
- **Login LDAP corporativo**: Autenticación contra el directorio de la planta vía la API de backend existente.
- **Borrado autorizado**: Solo el usuario autorizado (`AC17157`) puede eliminar inspecciones de prueba.

## 🧰 Tecnologías

- **Backend**: Python + Flask
- **Base de datos**: SQLite (archivo `inspecciones.db`)
- **QR**: Librería `qrcode`
- **Autenticación**: Integración con la API LDAP de la planta (`/api/login-ldap/`)

## 📁 Estructura

```
├── app.py                  # Backend Flask (rutas, QR, login LDAP, upload de fotos)
├── database.py             # Modelo y consultas SQLite
├── requirements.txt        # Dependencias
├── static/
│   ├── style.css           # Estilos premium
│   ├── img/goodyear.svg    # Logo oficial Goodyear
│   └── fotos/              # Imágenes subidas por los operadores
└── templates/
    ├── _header.html        # Barra superior con logo y navegación
    ├── home.html           # Página del QR
    ├── formulario.html     # Formulario de inspección
    ├── dashboard.html      # Estadísticas e historial
    └── exito.html          # Confirmación de registro
```

## 💻 Ejecución en local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar la aplicación
python app.py
```

Abrir en el navegador: `http://127.0.0.1:5000/`

Para acceder desde el celular (misma red Wi-Fi): usar la IP local del equipo, p. ej. `http://<ip-de-tu-pc>:5000/`

> La página principal redirige al **Dashboard**. El **QR** está en `http://<servidor>/qr`.
> El **formulario** (lo que escanean los operarios) está en `http://<servidor>/inspeccion`.

## 🔐 Configuración del login LDAP

La autenticación se realiza contra la API LDAP de la planta:

```python
# app.py
LDAP_API = os.environ.get("LDAP_API", "http://10.107.194.110:8080/api/login-ldap/")
BORRADO_AUTORIZADO = "ac17157"   # Único usuario autorizado para borrar
```

## 📌 Notas

- El registro fotográfico se guarda en `static/fotos/` (excluido del control de versiones).
- La base de datos (`inspecciones.db`) se crea automáticamente al arrancar y no se sube al repositorio.
- Desarrollado para **Mantenimiento e Ingeniería de Automatización – Goodyear**.
