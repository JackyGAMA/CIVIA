# INE - MVP Funcional de Predicción de Abstención Electoral 2024

Este proyecto implementa el **MVP funcional** para la consulta, exploración y focalización de predicciones de abstención electoral a nivel sección, municipio y estado en México.

---

## 🚀 Formas de Ejecutar el MVP

El MVP está diseñado para operar de manera inmediata a través de múltiples modalidades según su flujo de trabajo:

### 1. Interfaz Web Interactiva Completa (Recomendada)
Inicia el servidor local FastAPI y abre la aplicación en su navegador:
```bash
python app.py
```
O simplemente haga doble clic en Windows sobre:
```text
run_mvp.bat
```
La aplicación estará disponible en: **`http://127.0.0.1:8000`**

### 2. Menú Interactivo en Consola
```bash
python run_mvp.py
```

### 3. Consultas Rápidas por Línea de Comandos (CLI)
Para verificar predicciones de forma instantánea sin abrir el navegador:
```bash
# Ver métricas globales y cuantiles de riesgo
python consultar.py --stats

# Consultar una sección electoral específica (ej. Sección 1 de Aguascalientes)
python consultar.py --seccion 1 --estado 1

# Consultar por ID_TERRITORIO directo
python consultar.py --id 10010001

# Filtrar secciones por estado y nivel de riesgo
python consultar.py --estado 9 --riesgo ALTO --limit 10

# Ver resumen estatal comparativo (32 estados)
python consultar.py --resumen-estado

# Ver resumen municipal
python consultar.py --resumen-municipio --estado 1
```

### 4. Modo Autónomo Offline (Sin Servidor)
Doble clic en el archivo `mvp_offline.html` en su navegador para cargar y consultar `salidas_finales_abstencion.csv` de manera directa mediante FileReader en memoria.

---

## 📊 1. Carga de Datos y Fuentes Principales
El sistema integra de forma nativa los archivos generados por el pipeline predictivo:
- **`salidas_finales_abstencion.parquet`** / **`salidas_finales_abstencion.csv`**: Universo completo de **70,751 secciones electorales**, incluyendo:
  - `ID_TERRITORIO`, `ID_REGISTRO`, `EDOCVE`, `EDONOM`, `MPIOCVE`, `MPIONOM`, `SECCION`, `TIPOSEC`, `PREDICCION_ABSTENCION`, `RIESGO`.
- **`resumen_estado_abstencion.csv`**: 32 entidades federativas con promedios y conteos por riesgo.
- **`resumen_municipio_abstencion.csv`**: 2,477 municipios con promedios y porcentaje de alto riesgo.

*Mecanismo de resiliencia:* `data_loader.py` intenta leer primero el archivo Parquet; si el motor no se encuentra disponible en el entorno de ejecución, conmuta automáticamente a CSV sin pérdida de rendimiento (carga en ~0.15 segundos). Asimismo, si alguna columna territorial faltase, se reconstruye directamente a partir de la estructura posicional del `ID_TERRITORIO`.

---

## 🎯 2. Clasificación de Riesgo de Abstención
El modelo clasifica las secciones electorales según los **terciles empíricos (cuantiles 33.33% y 66.67%)** calculados sobre el universo nacional de predicciones:

| Nivel de Riesgo | Rango de Abstención Proyectada | Secciones Nacionales | % del Total | Interpretación Operativa |
| :--- | :---: | :---: | :---: | :--- |
| 🟢 **BAJO** | `< 42.31%` `[27.82% - 42.31%]` | 23,584 | 33.33% | Zonas con alta participación esperada. |
| 🟡 **MEDIO** | `42.31% - 50.99%` | 23,583 | 33.33% | Zonas con participación intermedia o volátil. |
| 🔴 **ALTO** | `> 50.99%` `[50.99% - 69.33%]` | 23,584 | 33.33% | Zonas críticas con abstención proyectada prioritaria. |

- **Abstención promedio nacional proyectada:** **46.77%**

---

## 🗺️ 3. Estado de la Capa Geográfica
- **Diagnóstico del Repositorio:** El repositorio actual incluye los datos tabulares y cuantitativos seccionales, pero **no contiene la cartografía vectorial seccional** (archivos GeoJSON o Shapefiles con polígonos de sección electoral del Marco Geoestadístico INE).
- **Solución implementada en el MVP:**
  1. **Mapa base interactivo nacional** (Leaflet + OpenStreetMap) con los centroides georreferenciados de las **32 entidades federativas**, coloreados por su nivel de riesgo y dimensionados por número de secciones.
  2. **Banner explícito de advertencia:** Se indica con total claridad al usuario que la capa de polígonos de sección está pendiente de integración.
  3. **Conector GeoJSON Dinámico:** Se incorporó un botón y función de carga local en la pestaña *Módulo Cartográfico*. Tan pronto como el equipo disponga del archivo vectorial (ej. `secciones_mexico.geojson`), el usuario puede seleccionarlo o arrastrarlo a la pantalla y el visualizador pintará automáticamente los polígonos seccionales sobre el mapa.

---

## 📋 4. Resultados Mínimos Incluidos en el MVP

1. **Total de secciones cargadas:** 70,751 secciones verificadas y activas.
2. **Predicción y riesgo por sección:** Consulta por ID o número con barra de progreso, porcentaje y comparativa contra el promedio nacional.
3. **Filtros combinados:** Selección dinámica de Estado, Municipio, Nivel de Riesgo y buscador por texto/número.
4. **Tabla de secciones filtradas:** Con paginación, cálculo reactivo de métricas del subconjunto y botón de exportación a CSV.
5. **Resumen por Estado:** Tabla detallada de las 32 entidades con promedio de abstención y porcentaje de alto riesgo.
6. **Resumen por Municipio:** Tabla de los 2,477 municipios filtrables por entidad federativa.

---

## 🧪 5. Pruebas Unitarias
Para validar que todos los componentes, filtros y APIs operen con integridad:
```bash
python test_app.py
```
Resultado: **8 pruebas ejecutadas exitosamente (100% OK)** en < 0.1 segundos.

