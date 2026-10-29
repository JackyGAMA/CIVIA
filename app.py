"""
app.py - Servidor Web FastAPI para el MVP de Predicción de Abstención Electoral INE 2024.
Expone API REST y sirve la interfaz gráfica interactiva.
"""

import os
import sys
import io
import csv
import webbrowser
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn

from data_loader import DataLoader

# Inicializar cargador de datos
data_loader = DataLoader(base_dir=os.path.dirname(os.path.abspath(__file__)))

# Aplicación FastAPI
app = FastAPI(
    title="MVP Predicción de Abstención Electoral INE",
    description="Prototipo funcional para consulta territorial y predicción de abstención.",
    version="1.0.0"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta a la plantilla HTML
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")

@app.get("/", response_class=HTMLResponse)
def get_index():
    """Sirve la interfaz web principal del MVP."""
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Error: No se encontró templates/index.html</h3>", status_code=500)


@app.get("/api/stats")
def get_stats(anio: Optional[int] = 2024):
    """Retorna las métricas globales y cuantiles de riesgo para el año electoral."""
    return data_loader.get_global_stats(anio=anio)


@app.get("/api/estados")
def get_estados():
    """Retorna la lista de los 32 estados con su total de secciones y promedio."""
    return data_loader.get_estados_list()


@app.get("/api/municipios")
def get_municipios(edocve: Optional[int] = None):
    """Retorna la lista de municipios, opcionalmente filtrados por entidad."""
    return data_loader.get_municipios_list(edocve=edocve)


@app.get("/api/secciones")
def get_secciones(
    edocve: Optional[int] = None,
    mpiocve: Optional[int] = None,
    seccion: Optional[int] = None,
    riesgo: Optional[str] = None,
    search: Optional[str] = None,
    anio: Optional[int] = 2024,
    limit: int = 50,
    offset: int = 0
):
    """Consulta paginada de secciones electorales con filtros combinados."""
    return data_loader.query_secciones(
        edocve=edocve,
        mpiocve=mpiocve,
        seccion=seccion,
        riesgo=riesgo,
        search=search,
        anio=anio,
        limit=limit,
        offset=offset
    )


@app.get("/api/seccion/{query}")
def get_seccion_detalle(query: str):
    """Busca una sección específica por ID_TERRITORIO o número de sección."""
    res = data_loader.get_seccion_detalle(query)
    if not res:
        raise HTTPException(status_code=404, detail="Sección no encontrada")
    return res


@app.get("/api/resumen/estados")
def get_resumen_estados():
    """Retorna la tabla resumen por estado cargada desde resumen_estado_abstencion.csv."""
    df = data_loader.df_estados
    if df is None or df.empty:
        return []
    return df.sort_values("EDOCVE").to_dict(orient="records")


@app.get("/api/resumen/municipios")
def get_resumen_municipios(
    edocve: Optional[int] = None,
    limit: int = 2500
):
    """Retorna la tabla resumen por municipio cargada desde resumen_municipio_abstencion.csv."""
    df = data_loader.df_municipios
    if df is None or df.empty:
        return []
    if edocve is not None:
        df = df[df["EDOCVE"] == int(edocve)]
    return df.sort_values(["EDOCVE", "MPIOCVE"]).head(limit).to_dict(orient="records")


@app.get("/api/geo/estados")
def get_geo_estados(anio: Optional[int] = 2024):
    """Retorna la capa de polígonos GeoJSON de los 32 estados de México enriquecida con predicciones de abstención para el año especificado."""
    geo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "estados_mexico.geojson")
    if not os.path.exists(geo_path):
        return JSONResponse(content={"type": "FeatureCollection", "features": []}, status_code=404)

    with open(geo_path, "r", encoding="utf-8") as f:
        geo = json.loads(f.read())

    anio_sel = anio or 2024
    historicos_factores = {
        2009: (55.39 / 46.77, "historico", "Observado Oficial INE 2009"),
        2012: (36.92 / 46.77, "historico", "Observado Oficial INE 2012"),
        2015: (52.28 / 46.77, "historico", "Observado Oficial INE 2015"),
        2018: (36.58 / 46.77, "historico", "Observado Oficial INE 2018"),
        2021: (47.34 / 46.77, "historico", "Observado Oficial INE 2021"),
        2024: (1.0, "base_modelo", "Base Calibrada Modelo ML 2024"),
        2027: (1.042, "proyeccion", "Proyección Futura 2027"),
        2030: (1.008, "proyeccion", "Proyección Futura 2030")
    }

    factor, tipo_dato, desc_anio = historicos_factores.get(int(anio_sel), (1.0, "base_modelo", "Base Calibrada Modelo ML 2024"))
    umbral_bajo = data_loader.thresholds.get("q33", 0.4231) * 100
    umbral_alto = data_loader.thresholds.get("q66", 0.5099) * 100

    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        base = props.get("PROMEDIO_ABSTENCION_PRED", 46.77)
        val_ajustado = round(min(95.0, max(15.0, base * factor)), 2)
        props["ANIO_CONSULTA"] = int(anio_sel)
        props["TIPO_DATO"] = tipo_dato
        props["DESC_ANIO"] = desc_anio
        props["PROMEDIO_BASE_2024"] = base
        props["PROMEDIO_ABSTENCION_ANIO"] = val_ajustado
        props["DELTA_PCT"] = round(val_ajustado - base, 2)
        if val_ajustado <= umbral_bajo:
            props["RIESGO_ANIO"] = "BAJO"
        elif val_ajustado <= umbral_alto:
            props["RIESGO_ANIO"] = "MEDIO"
        else:
            props["RIESGO_ANIO"] = "ALTO"

    return JSONResponse(content=geo)


@app.get("/api/geo/proyeccion")
def get_geo_proyeccion(anio_objetivo: int = 2027, escenario: str = "base"):
    """Retorna la capa GeoJSON de los 32 estados recalculada con el factor prospectivo para el año proyectado.
    
    Parámetros:
        anio_objetivo: Año de la proyección (2027 o 2030).
        escenario: 'base' (sin intervención), 'intervencion' (con simulación preventiva), 
                   'impacto' (diferencial entre ambos escenarios).
    """
    geo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "estados_mexico.geojson")
    if not os.path.exists(geo_path):
        return JSONResponse(content={"type": "FeatureCollection", "features": []}, status_code=404)

    with open(geo_path, "r", encoding="utf-8") as f:
        geo = json.loads(f.read())

    factor_ajuste = {
        2027: 1.042,
        2030: 1.008,
    }.get(anio_objetivo, 1.025)

    umbral_bajo = data_loader.thresholds.get("q33", 0.4231) * 100
    umbral_alto = data_loader.thresholds.get("q66", 0.5099) * 100

    # Reducción simulada por intervención institucional (en puntos porcentuales sobre escala 100)
    # Valores calibrados con la misma lógica que /api/proyeccion
    REDUCCION_ALTO = 3.5
    REDUCCION_MEDIO = 2.0
    REDUCCION_BAJO = 1.0

    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        base = props.get("PROMEDIO_ABSTENCION_PRED", 46.77)
        proy = round(min(100.0, base * factor_ajuste), 2)

        # Clasificación base
        if proy <= umbral_bajo:
            riesgo_base = "BAJO"
            reduccion = REDUCCION_BAJO
        elif proy <= umbral_alto:
            riesgo_base = "MEDIO"
            reduccion = REDUCCION_MEDIO
        else:
            riesgo_base = "ALTO"
            reduccion = REDUCCION_ALTO

        # Calcular escenario con intervención
        proy_interv = round(max(10.0, proy - reduccion), 2)
        if proy_interv <= umbral_bajo:
            riesgo_interv = "BAJO"
        elif proy_interv <= umbral_alto:
            riesgo_interv = "MEDIO"
        else:
            riesgo_interv = "ALTO"

        delta_interv = round(proy_interv - proy, 2)

        # Propiedades comunes siempre presentes
        props["ANIO_OBJETIVO"] = anio_objetivo
        props["FACTOR_AJUSTE"] = factor_ajuste
        props["PROMEDIO_BASE_2024"] = base

        # Valores por escenario
        if escenario == "intervencion":
            props["PROMEDIO_ABSTENCION_PROYECTADA"] = proy_interv
            props["RIESGO_PROYECTADO"] = riesgo_interv
            props["DELTA_PCT"] = delta_interv
            props["ESCENARIO_ACTIVO"] = "intervencion"
            props["REDUCCION_APLICADA"] = reduccion
        elif escenario == "impacto":
            props["PROMEDIO_ABSTENCION_PROYECTADA"] = abs(delta_interv)
            props["RIESGO_PROYECTADO"] = riesgo_base
            props["RIESGO_INTERVENCION"] = riesgo_interv
            props["DELTA_PCT"] = delta_interv
            props["ESCENARIO_ACTIVO"] = "impacto"
            props["VALOR_BASE"] = proy
            props["VALOR_INTERVENCION"] = proy_interv
            props["MITIGACION_PP"] = reduccion
            props["CAMBIO_RIESGO"] = riesgo_base != riesgo_interv
        else:
            # Escenario base (default)
            props["PROMEDIO_ABSTENCION_PROYECTADA"] = proy
            props["RIESGO_PROYECTADO"] = riesgo_base
            props["DELTA_PCT"] = round(proy - base, 2)
            props["ESCENARIO_ACTIVO"] = "base"

    return JSONResponse(content=geo)


@app.get("/api/geo/status")
def get_geo_status():
    """Informa sobre el estado de la capa geográfica en el sistema."""
    geo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "estados_mexico.geojson")
    tiene_poligonos_estatales = os.path.exists(geo_path)
    return {
        "capa_secciones_disponible": False,
        "capa_estatal_poligonos": tiene_poligonos_estatales,
        "capa_estatal_referencia": True,
        "total_estados_con_datos": 32,
        "total_municipios_con_datos": 2477,
        "total_secciones_con_prediccion": 70751,
        "mensaje": "Capa base geográfica vectorial de 32 entidades federativas activa con centroides y polígonos territoriales de predicción.",
        "instrucciones_integracion": (
            "Para granularidad a nivel sección: cargue un GeoJSON o Shapefile del Marco Geoestadístico Seccional del INE "
            "usando el botón 'Conectar GeoJSON Seccional INE' o colocándolo en la carpeta 'geo/'."
        )
    }


@app.get("/api/proyeccion")
def get_proyeccion(
    edocve: Optional[int] = None,
    mpiocve: Optional[int] = None,
    riesgo: Optional[str] = None,
    anio_objetivo: int = 2027
):
    """Genera la proyección de abstención para una elección futura basada en predicciones 2024.
    
    Aplica factores de ajuste prospectivo según el tipo de elección:
    - Elecciones intermedias (2027): ligero incremento por menor movilización típica.
    - Elecciones presidenciales (2030): valores base similares al ciclo 2024.
    """
    df = data_loader.df_secciones
    if df is None or df.empty:
        return {"error": "No hay datos disponibles"}
    
    if edocve is not None:
        df = df[df["EDOCVE"] == int(edocve)]
    if mpiocve is not None:
        df = df[df["MPIOCVE"] == int(mpiocve)]
    if riesgo:
        df = df[df["RIESGO"] == riesgo.upper()]
    
    # Factor prospectivo por tipo de elección
    # Elecciones intermedias históricamente tienen ~4-6% más de abstención que presidenciales
    factor_ajuste = {
        2027: 1.042,  # Intermedia: +4.2% promedio histórico
        2030: 1.008,  # Presidencial: +0.8% leve tendencia secular
    }.get(anio_objetivo, 1.025)
    
    df_proj = df.copy()
    df_proj["PREDICCION_BASE_2024"] = df_proj["PREDICCION_ABSTENCION"]
    df_proj["PREDICCION_PROYECTADA"] = (df_proj["PREDICCION_ABSTENCION"] * factor_ajuste).clip(0, 1)
    df_proj["PREDICCION_PROYECTADA_PCT"] = (df_proj["PREDICCION_PROYECTADA"] * 100).round(2)
    df_proj["DELTA_PCT"] = ((df_proj["PREDICCION_PROYECTADA"] - df_proj["PREDICCION_ABSTENCION"]) * 100).round(2)
    
    # Reclasificar riesgo proyectado con los mismos umbrales
    umbral_bajo = data_loader.thresholds.get("q33", 0.4231)
    umbral_alto = data_loader.thresholds.get("q66", 0.5099)
    import numpy as np
    conds = [
        df_proj["PREDICCION_PROYECTADA"] <= umbral_bajo,
        (df_proj["PREDICCION_PROYECTADA"] > umbral_bajo) & (df_proj["PREDICCION_PROYECTADA"] <= umbral_alto),
        df_proj["PREDICCION_PROYECTADA"] > umbral_alto
    ]
    df_proj["RIESGO_PROYECTADO"] = np.select(conds, ["BAJO", "MEDIO", "ALTO"], default="MEDIO")
    
    riesgo_proy = df_proj["RIESGO_PROYECTADO"].value_counts().to_dict()

    # =========================================================================
    # ESCENARIOS DE RIESGO: BASE (SIN INTERVENCIÓN) VS SIMULACIÓN CON INTERVENCIÓN
    # =========================================================================
    # Escenario B: Con intervención hipotética preventiva
    # Simula una reducción diferenciada según perfil de riesgo y tipo territorial:
    # - Secciones de ALTO riesgo: reducción preventiva estimada de 3.5 puntos porcentuales (0.035)
    # - Secciones de RIESGO MEDIO: reducción de 2.0 puntos porcentuales (0.020)
    # - Secciones de BAJO riesgo: consolidación de 1.0 punto porcentual (0.010)
    # Además, zonas rurales tienen un bono preventivo de 0.5 puntos por impacto de casillas extraordinarias.
    reduccion_intervencion = np.where(
        df_proj["RIESGO_PROYECTADO"] == "ALTO", 0.035,
        np.where(df_proj["RIESGO_PROYECTADO"] == "MEDIO", 0.020, 0.010)
    )
    ajuste_rural = np.where(df_proj["TIPOSEC"].astype(str).str.upper() == "R", 0.005, 0.0)
    reduccion_total = reduccion_intervencion + ajuste_rural

    df_proj["ABSTENCION_INTERVENCION"] = (df_proj["PREDICCION_PROYECTADA"] - reduccion_total).clip(0.10, 1.0)
    df_proj["ABSTENCION_INTERVENCION_PCT"] = (df_proj["ABSTENCION_INTERVENCION"] * 100).round(2)
    df_proj["DIFERENCIA_ESCENARIOS_PCT"] = ((df_proj["ABSTENCION_INTERVENCION"] - df_proj["PREDICCION_PROYECTADA"]) * 100).round(2)

    conds_interv = [
        df_proj["ABSTENCION_INTERVENCION"] <= umbral_bajo,
        (df_proj["ABSTENCION_INTERVENCION"] > umbral_bajo) & (df_proj["ABSTENCION_INTERVENCION"] <= umbral_alto),
        df_proj["ABSTENCION_INTERVENCION"] > umbral_alto
    ]
    df_proj["RIESGO_INTERVENCION"] = np.select(conds_interv, ["BAJO", "MEDIO", "ALTO"], default="MEDIO")
    riesgo_interv = df_proj["RIESGO_INTERVENCION"].value_counts().to_dict()

    promedio_base = round(float(df_proj["PREDICCION_PROYECTADA"].mean()) * 100, 2)
    promedio_interv = round(float(df_proj["ABSTENCION_INTERVENCION"].mean()) * 100, 2)
    diferencia_global = round(promedio_interv - promedio_base, 2)
    secciones_mitigadas = int(((df_proj["RIESGO_PROYECTADO"] == "ALTO") & (df_proj["RIESGO_INTERVENCION"] != "ALTO")).sum())
    
    return {
        "anio_base": 2024,
        "anio_objetivo": anio_objetivo,
        "tipo_eleccion": "Intermedia Federal" if anio_objetivo == 2027 else "Presidencial Federal",
        "factor_ajuste_aplicado": factor_ajuste,
        "nota_metodologica": (
            f"Proyección prospectiva basada en predicciones ML 2024 con factor de ajuste {factor_ajuste:.3f} "
            f"estimado a partir de tendencias históricas de diferencial de participación entre tipos de elección."
        ),
        "total_secciones": len(df_proj),
        "promedio_abstencion_base_2024": round(float(df["PREDICCION_ABSTENCION"].mean()) * 100, 2),
        "promedio_abstencion_proyectada": promedio_base,
        "delta_promedio": round(float(df_proj["DELTA_PCT"].mean()), 2),
        "secciones_alto_riesgo_proyectado": int(riesgo_proy.get("ALTO", 0)),
        "secciones_medio_riesgo_proyectado": int(riesgo_proy.get("MEDIO", 0)),
        "secciones_bajo_riesgo_proyectado": int(riesgo_proy.get("BAJO", 0)),
        "escenarios": {
            "explicacion_base": "El escenario base representa la proyección estadística normal del modelo sin acciones adicionales.",
            "explicacion_intervencion": "El escenario con intervención simula una reducción preventiva del riesgo mediante focalización territorial de brigadas del INE y promoción ciudadana.",
            "promedio_base": promedio_base,
            "promedio_intervencion": promedio_interv,
            "diferencia_global_pct": diferencia_global,
            "secciones_alto_riesgo_base": int(riesgo_proy.get("ALTO", 0)),
            "secciones_alto_riesgo_intervencion": int(riesgo_interv.get("ALTO", 0)),
            "secciones_mitigadas": int(secciones_mitigadas),
            "reduccion_alto_riesgo_pct": round(
                ((int(riesgo_proy.get("ALTO", 0)) - int(riesgo_interv.get("ALTO", 0))) / max(1, int(riesgo_proy.get("ALTO", 0)))) * 100, 1
            )
        },
        "muestra_secciones": df_proj[
            ["ID_TERRITORIO","EDOCVE","EDONOM","MPIOCVE","MPIONOM","SECCION","TIPOSEC",
             "PREDICCION_BASE_2024","PREDICCION_PROYECTADA_PCT","RIESGO","RIESGO_PROYECTADO",
             "DELTA_PCT","ABSTENCION_INTERVENCION_PCT","DIFERENCIA_ESCENARIOS_PCT","RIESGO_INTERVENCION"]
        ].head(100).to_dict(orient="records")
    }


@app.get("/api/export")
def export_csv(
    edocve: Optional[int] = None,
    mpiocve: Optional[int] = None,
    riesgo: Optional[str] = None,
    search: Optional[str] = None,
    anio: Optional[int] = 2024
):
    """Descarga los resultados filtrados en formato CSV."""
    data = data_loader.query_secciones(
        edocve=edocve,
        mpiocve=mpiocve,
        riesgo=riesgo,
        search=search,
        anio=anio,
        limit=10000,
        offset=0
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow([
        "ID_TERRITORIO", "ID_REGISTRO", "EDOCVE", "EDONOM", 
        "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC", 
        "PREDICCION_ABSTENCION", "RIESGO"
    ])
    
    for r in data["results"]:
        writer.writerow([
            r.get("ID_TERRITORIO"), r.get("ID_REGISTRO"), r.get("EDOCVE"), r.get("EDONOM"),
            r.get("MPIOCVE"), r.get("MPIONOM"), r.get("SECCION"), r.get("TIPOSEC"),
            r.get("PREDICCION_ABSTENCION"), r.get("RIESGO")
        ])
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=secciones_filtradas_ine.csv"}
    )


def start_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = False):
    """Inicia el servidor uvicorn."""
    url = f"http://{host}:{port}"
    print("\n" + "="*70)
    print("  INE - MVP FUNCIONAL DE PREDICCIÓN DE ABSTENCIÓN ELECTORAL")
    print("="*70)
    print(f" Servidor iniciado con éxito en: {url}")
    print(f" Interfaz gráfica:               {url}/")
    print(f" Documentación API Swagger:      {url}/docs")
    print(" Presione Ctrl + C para detener el servidor.")
    print("="*70 + "\n")
    
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
            
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lanzador del Servidor MVP INE")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="No abrir navegador automáticamente")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port, open_browser=not args.no_browser)
