# 🏭 Goodyear - Plataforma de Control 5S / WPO

Plataforma web corporativa para el registro, seguimiento y auditoría de **5S / WPO** (*Work Place Organization*) en la entrega de turno a nivel de planta en Goodyear.

---

## 🚀 Funcionalidades Principales

- 📱 **Formulario Móvil Guiado**:
  - Registro por área de la planta (`ASRS`, `Banbury`, `Confección`, `Curado`, `Inspección Final`, `Almacén`, `Mantenimiento`, `General`).
  - Identificación dual con **Usuario LDAP** (ej. `ACXXXXX`) y **Nombre Completo del Operador**.
  - **Fecha y hora inalterables**: Estampadas automáticamente por el servidor Python para garantizar la trazabilidad real.
  - Evaluación de puntos clave 5S / WPO (Escritorio limpio, Piso limpio, Mueble de repuestos ordenado, Sin repuestos fuera de lugar).
  - Captura y subida de evidencia fotográfica desde la cámara o galería del teléfono.
- 🖼️ **Optimización de Multimedia (Pillow)**:
  - Redimensión y compresión automática de fotografías en el backend a máx 1280px y formato JPEG optimizado (reduce el peso de fotos de 8MB a ~200KB sin pérdida perceptible).
  - Corrección automática de orientación EXIF.
  - **Limpieza de disco**: Eliminación automática de archivos físicos al borrar una inspección.
- 📊 **Dashboard Analítico e Interactivo (Chart.js)**:
  - **KPI de Cumplimiento Global (% OK)** y conteo de puntos aprobados vs evaluados.
  - Gráficos interactivos de cumplimiento por turno y desglose de aprobaciones por punto de inspección.
  - Historial completo con tarjetas de estado, comentarios y miniaturas.
  - **Visor Lightbox en pantalla completa** para inspección detallada de evidencias fotográficas sin salir del dashboard.
- 📥 **Exportación de Datos (CSV / Excel)**:
  - Descarga directa de reportes consolidados en formato CSV (`/exportar-csv`) optimizados para Excel o auditorías de planta.
- 🔐 **Autenticación Corporativa LDAP**:
  - Integración vía API REST con el directorio activo de la planta (`/api/login-ldap/`).
  - Permisos diferenciados: Borrado autorizado exclusivo para el usuario administrador (`AC17157`).

---

## 🧰 Stack Tecnológico

- **Backend**: Python 3.9+ / Flask
- **Procesamiento de Imágenes**: Pillow (`PIL`)
- **Base de Datos**: SQLite3 (con gestión de context manager y auto-migración)
- **Frontend**: HTML5, CSS3 moderno (Variables CSS, Grid, Flexbox, Glassmorphism), JavaScript ES6+
- **Visualización de Datos**: Chart.js v4

---

## 📁 Estructura del Proyecto

```text
wpo_inspecciones/
├── app.py                  # Servidor principal Flask, rutas, lógica de compresión y autenticación
├── database.py             # Modelo de base de datos, consultas SQL, métricas 5S/WPO y exportación
├── requirements.txt        # Dependencias Python (Flask, Pillow, requests)
├── .gitignore              # Excluye BD, imágenes subidas y logs
├── static/
│   ├── style.css           # Estilos corporativos Goodyear (Azul #003399, Amarillo #FFD200)
│   ├── img/goodyear.svg    # Logotipo oficial Goodyear
│   └── fotos/              # Directorio de fotos comprimidas
└── templates/
    ├── _header.html        # Barra superior, navegación y modal de login LDAP
    ├── formulario.html     # Formulario de inspección adaptado a dispositivos móviles
    ├── dashboard.html      # Dashboard analítico con Chart.js y visor Lightbox
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

Para acceder desde teléfonos móviles o colectores de datos en la misma red Wi-Fi de la planta, utiliza la IP local del equipo: `http://<IP-DE-TU-SERVIDOR>:5000/`

---

## 🗺️ Mapa de Rutas de la Aplicación

| Ruta | Método | Descripción |
| :--- | :--- | :--- |
| `/` | GET | Redirige al Dashboard principal |
| `/inspeccion` | GET / POST | Formulario móvil de entrega de turno 5S / WPO |
| `/dashboard` | GET | Dashboard analítico, KPIs y tabla de historial |
| `/exportar-csv` | GET | Descarga de reporte acumulado en CSV |
| `/login` | POST | Autenticación de usuario contra el servicio LDAP corporativo |
| `/logout` | POST | Cierre de sesión de usuario |
| `/borrar/<id>` | POST | Borrado seguro de registro y fotos (Exclusivo `AC17157`) |

---

## ⚙️ Variables de Entorno (Opcional)

Puedes configurar las siguientes variables de entorno para entornos de producción:

```bash
export SECRET_KEY="tu-clave-secreta-de-produccion"
export LDAP_API="http://10.107.194.110:8080/api/login-ldap/"
```

---

## 📌 Desarrollo

Desarrollado para la **Jefatura de Mantenimiento e Ingeniería de Automatización – Goodyear Chile**.
