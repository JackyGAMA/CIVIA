# CIVIA - Sistema de Inteligencia Predictiva de Abstención Electoral (INE)

CIVIA es una plataforma analítica y de visualización geoespacial diseñada para la planeación y focalización territorial de esfuerzos institucionales contra el abstencionismo electoral en México. 

El sistema abarca las **70,751 secciones electorales** de las **32 entidades federativas** y los **2,477 municipios** del país, combinando modelos predictivos de Machine Learning, agregación demográfica etaria y simulación prospectiva de escenarios de intervención preventiva.

---

## Requisitos Previos

- **Python**: Versión 3.9 o superior (Python 3.10, 3.11 o 3.12 recomendadas).
- **Git**: Para clonar el repositorio.
- **Navegador Web**: Chrome, Edge, Firefox, Safari o cualquier navegador moderno.

---

## Guía Rápida de Activación Local (3 Pasos)

### 1. Clonar el repositorio
Abre una terminal o consola de comandos y ejecuta:
```bash
git clone https://github.com/JackyGAMA/CIVIA.git
cd CIVIA
```

### 2. Crear entorno virtual e instalar dependencias

#### En Windows (PowerShell o CMD):
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### En macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Iniciar el servidor
```bash
python app.py
```

El servidor iniciará en:
- **Aplicación Web**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Documentación Interactiva Swagger API**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

*(En Windows también puedes hacer doble clic directamente sobre `run_mvp.bat` para iniciar el servidor sin escribir comandos).*

---

## Métodos Alternativos de Ejecución

### Opción A: Menú Interactivo en Consola
Para un menú guiado por consola con selección de modos:
```bash
python run_mvp.py
```

### Opción B: Consultas Rápidas por Terminal (CLI)
Para consultar predicciones y métricas específicas al instante sin abrir el navegador:
```bash
# Ver métricas nacionales globales y cuantiles de riesgo
python consultar.py --stats

# Consultar una sección electoral específica (ej. Sección 1 de Aguascalientes)
python consultar.py --seccion 1 --estado 1

# Consultar por clave ID_TERRITORIO directa
python consultar.py --id 10010001

# Filtrar secciones por estado y nivel de riesgo
python consultar.py --estado 9 --riesgo ALTO --limit 10

# Ver resumen estatal comparativo de las 32 entidades
python consultar.py --resumen-estado

# Ver resumen municipal
python consultar.py --resumen-municipio --estado 1
```

### Opción C: Modo Autónomo Offline (Sin Servidor)
Doble clic en el archivo `mvp_offline.html` en cualquier navegador web. Permite cargar y explorar el archivo `salidas_finales_abstencion.csv` directamente en memoria local sin requerir Python activo.

---

## Funcionalidades Principales

### 1. Modo de Exploración Histórica
- **Selector de Años (2009 - 2024)**: Permite contrastar resultados históricos observados del INE (2018, 2021) frente a la base calibrada 2024 del modelo ML.
- **Métricas Dinámicas**: Tasa promedio nacional de abstención y distribución en los tres terciles de riesgo:
  - **Bajo Riesgo**: Abstención < 42.31% (Tercil inferior q33)
  - **Riesgo Medio**: Abstención entre 42.31% y 50.99% (Tercil medio)
  - **Alto Riesgo**: Abstención > 50.99% (Tercil superior q66)
- **Filtros Territoriales**: Por Entidad Federativa, Municipio, Nivel de Riesgo y búsqueda seccional.
- **Exportación CSV**: Descarga directa de los datos filtrados en pantalla.

### 2. Modo de Predicción y Proyección Futura
- **Horizonte Prospectivo**: Factores de ajuste calibrados para elecciones intermedias federales (2027: +4.2% diferencial inercial) y presidenciales (2030: +0.8%).
- **Módulo de Escenarios Conectado al Mapa**:
  - **Escenario A (Sin Intervención / Base)**: Visualización inercial de la trayectoria estadística esperada.
  - **Escenario B (Con Intervención Institucional)**: Simulación preventiva de mitigación focalizada (-3.5 pp en alto riesgo, -2.0 pp en riesgo medio, -1.0 pp en bajo riesgo y bono rural de +0.5 pp). Muestra cómo 10 entidades federativas mejoran favorablemente su categoría de riesgo en el mapa.
  - **Impacto Estimado (Diferencial Preventivo)**: Modo comparativo con escala cromática de mitigación (verde oscuro >= 3.0 pp, teal 2.0 - 2.9 pp, esmeralda consolidación), cuantificando las 10,179 secciones electorales mitigadas.

### 3. Ficha Técnica Seccional con Perfil Demográfico
Al hacer clic en "Ficha" sobre cualquier sección de la tabla, se abre una ventana modal que incluye:
- Nivel de riesgo y comparativa porcentual frente a la media nacional (46.77%).
- **Perfil Etario Real**: Edad promedio estimada de la sección, grupo de edad predominante y distribución del padrón por cohortes:
  - 18 a 24 años
  - 25 a 34 años
  - 35 a 44 años
  - 45 a 59 años
  - 60 años y más
- **Recomendaciones Preventivas**: Sugerencias operativas contextualizadas para brigadas territoriales del INE según el perfil etario y geográfico de la sección.

---

## Verificación de Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias que valida la integridad de los datos, los umbrales de riesgo, las proyecciones y los endpoints:

```bash
python -m unittest test_app.py
```
Resultado esperado: `Ran 8 tests ... OK`.

---

## Estructura del Proyecto

```text
CIVIA/
├── app.py                             # Servidor web FastAPI con endpoints REST y lógica de escenarios
├── data_loader.py                     # Motor de carga, consultas en memoria y perfiles demográficos
├── requirements.txt                   # Dependencias de Python requeridas
├── test_app.py                        # Suite de pruebas unitarias automatizadas
├── run_mvp.bat                        # Acceso directo para ejecución en Windows
├── run_mvp.py                         # Lanzador con menú interactivo por consola
├── consultar.py                       # Herramienta CLI de consulta rápida
├── mvp_offline.html                   # Interfaz autónoma offline para navegador
├── README.md                          # Guía de instalación y documentación del sistema
├── geo/
│   └── estados_mexico.geojson         # Capa vectorial de las 32 entidades federativas
├── templates/
│   └── index.html                     # Interfaz web interactiva (Leaflet, TailwindCSS)
├── salidas_finales_abstencion.parquet # Dataset optimizado con 70,751 predicciones seccionales
├── salidas_finales_abstencion.csv     # Dataset seccional en formato CSV
├── resumen_demografia_seccional.csv   # Resumen de edades y cohortes poblacionales por sección
├── resumen_estado_abstencion.csv      # Agregación estatal de abstención
├── resumen_municipio_abstencion.csv   # Agregación municipal (2,477 municipios)
└── predicciones_2024.csv              # Predicciones calibradas ciclo 2024
```

---

## Licencia y Uso Institucional

Desarrollado con fines de inteligencia electoral territorial y planificación cívica institucional.
