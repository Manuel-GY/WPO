# 🏭 Goodyear - Plataforma de Control 5S / WPO

Plataforma web corporativa para el registro, seguimiento y auditoría de **5S / WPO** (*Work Place Organization*) en la entrega de turno a nivel de planta en Goodyear.

---

## 🚀 Funcionalidades Principales

- 📱 **Formulario Móvil y Colectores Industriales (Datalogic Falcon X4 / ZTBrowser)**:
  - Compatible con lectores portátiles de código de barras / QR de planta y navegadores de colector industrial.
  - **Detección de Ubicación por QR Escaneado**: Al escanear un QR de área (ej. `Carros`, `Zona Tambores`, `Taller`, `Mezzanina`, `ASRS`), el formulario abre seleccionando automáticamente la zona escaneada.
- 🔲 **Catálogo Generador de QRs por Área (`/qrs`)**:
  - Vista de catálogo imprimible con códigos QR preconfigurados para **Carros**, **Zona Tambores**, **Taller**, **Mezzanina**, **ASRS**, **Banbury**, **Confección**, **Curado**, **Almacén**, **Mantenimiento**.
- 👤 **Identificación LDAP Corporativa**:
  - Validación con **Usuario LDAP** (ej. `ACXXXXX`) y **Contraseña**, obteniendo automáticamente el **Nombre Completo oficial** de la persona desde la API de la planta.
- 🕒 **Fecha y hora inalterables**: Estampadas automáticamente por el servidor Python para garantizar la trazabilidad real.
- 🖼️ **Optimización de Multimedia (Pillow)**:
  - Redimensión y compresión automática de fotografías en el backend a máx 1280px y formato JPEG optimizado.
- 📊 **Dashboard Analítico e Interactivo (Chart.js)**:
  - **KPI de Cumplimiento Global (% OK)** y conteo de puntos aprobados vs evaluados.
  - Gráficos interactivos de cumplimiento por turno y desglose por área.
- 📥 **Exportación de Datos (CSV / Excel)**:
  - Descarga directa de reportes consolidados en formato CSV (`/exportar-csv`).

---

## 🧰 Stack Tecnológico

- **Backend**: Python 3.9+ / Flask
- **Procesamiento de Imágenes**: Pillow (`PIL`)
- **Generador de QR**: Python `qrcode`
- **Base de Datos**: SQLite3 (con gestión de context manager y auto-migración)
- **Frontend**: HTML5, CSS3 moderno (Variables CSS, Grid, Flexbox, Glassmorphism), JavaScript ES6+
- **Visualización de Datos**: Chart.js v4

---

## 📁 Estructura del Proyecto

```text
wpo_inspecciones/
├── app.py                  # Servidor principal Flask, rutas, lógica de compresión y autenticación
├── database.py             # Modelo de base de datos, consultas SQL, métricas 5S/WPO y exportación
├── requirements.txt        # Dependencias Python (Flask, Pillow, qrcode, requests)
├── .gitignore              # Excluye BD, imágenes subidas y logs
├── static/
│   ├── style.css           # Estilos corporativos Goodyear (Azul #003399, Amarillo #FFD200)
│   ├── img/goodyear.svg    # Logotipo oficial Goodyear
│   └── fotos/              # Directorio de fotos comprimidas
└── templates/
    ├── _header.html        # Barra superior, navegación y modal de login LDAP
    ├── formulario.html     # Formulario de inspección adaptado a móviles y colectores industriales
    ├── dashboard.html      # Dashboard analítico con Chart.js y visor Lightbox
    ├── qrs.html            # Catálogo imprimible de carteles QR para áreas
    └── exito.html          # Redirección directa al Dashboard
```

---

## 🛠️ Instalación y Ejecución

### 1. Clonar el repositorio e instalar dependencias

```bash
git clone https://github.com/Manuel-GY/WPO.git
cd WPO
pip install -r requirements.txt
```

### 2. Ejecutar la aplicación

```bash
python app.py
```

La aplicación se ejecutará por defecto en `http://127.0.0.1:5000/`.

Para acceder desde colectores **Datalogic Falcon X4** o celulares en la red Wi-Fi de la planta, utiliza la IP local del equipo: `http://<IP-DE-TU-SERVIDOR>:5000/`

---

## 🗺️ Mapa de Rutas de la Aplicación

| Ruta | Método | Descripción |
| :--- | :--- | :--- |
| `/` | GET | Redirige al Dashboard principal |
| `/inspeccion` | GET / POST | Formulario móvil (soporta `?area=Zona%20Tambores`, `?area=Carros`, etc.) |
| `/dashboard` | GET | Dashboard analítico, KPIs y tabla de historial |
| `/qrs` | GET | Catálogo de carteles imprimibles de código QR por área |
| `/qr-img` | GET | Generador dinámico del PNG del QR (`?area=Carros`) |
| `/exportar-csv` | GET | Descarga de reporte acumulado en CSV |
| `/login` | POST | Autenticación de usuario contra el servicio LDAP corporativo |
| `/logout` | POST | Cierre de sesión de usuario |
| `/borrar/<id>` | POST | Borrado seguro de registro y fotos (Exclusivo `AC17157`) |

---

## 📌 Desarrollo

Desarrollado para la **Jefatura de Mantenimiento e Ingeniería de Automatización – Goodyear Chile**.
