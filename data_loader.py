"""
data_loader.py - Módulo de carga y procesamiento de datos para el MVP de Abstención Electoral INE.
Carga resultados de predicción, resúmenes estatales y municipales, asegurando resiliencia y validación.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

class DataLoader:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.df_secciones: Optional[pd.DataFrame] = None
        self.df_estados: Optional[pd.DataFrame] = None
        self.df_municipios: Optional[pd.DataFrame] = None
        self.df_demografia: Optional[pd.DataFrame] = None
        self.thresholds: Dict[str, float] = {}
        self.load_data()

    def load_data(self):
        """Carga los datasets principales con fallback automático entre parquet y csv."""
        print("[DataLoader] Iniciando carga de datos...")
        
        # 1. Cargar salidas finales de predicción por sección
        self.df_secciones = self._load_secciones()
        
        # 2. Cargar resumen por estado
        self.df_estados = self._load_resumen_estado()
        
        # 3. Cargar resumen por municipio
        self.df_municipios = self._load_resumen_municipio()

        # 4. Cargar resumen demográfico por sección (edad y grupos etarios)
        self.df_demografia = self._load_demografia()
        
        # 5. Validar columnas y calcular umbrales de riesgo
        self._ensure_columns()
        self._document_and_validate_risk()
        
        print(f"[DataLoader] Carga exitosa: {len(self.df_secciones):,} secciones cargadas.")

    def _load_demografia(self) -> pd.DataFrame:
        csv_path = os.path.join(self.base_dir, "resumen_demografia_seccional.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, dtype={"ID_TERRITORIO": str})
            print(f"[DataLoader] Resumen demográfico cargado: {len(df)} secciones.")
            return df
        print("[DataLoader] Advertencia: resumen_demografia_seccional.csv no encontrado.")
        return pd.DataFrame()

    def _load_secciones(self) -> pd.DataFrame:
        parquet_path = os.path.join(self.base_dir, "salidas_finales_abstencion.parquet")
        csv_path = os.path.join(self.base_dir, "salidas_finales_abstencion.csv")
        
        # Intentar cargar Parquet si existe y el motor está disponible
        if os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                print(f"[DataLoader] Cargado exitosamente desde Parquet: {parquet_path}")
                return df
            except Exception as e:
                print(f"[DataLoader] No se pudo leer Parquet ({e}). Intentando con CSV de respaldo...")
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            print(f"[DataLoader] Cargado exitosamente desde CSV: {csv_path}")
            return df
            
        raise FileNotFoundError(f"No se encontró ni {parquet_path} ni {csv_path}")

    def _load_resumen_estado(self) -> pd.DataFrame:
        csv_path = os.path.join(self.base_dir, "resumen_estado_abstencion.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            print(f"[DataLoader] Resumen estado cargado: {len(df)} entidades.")
            return df
        print("[DataLoader] Advertencia: resumen_estado_abstencion.csv no encontrado.")
        return pd.DataFrame()

    def _load_resumen_municipio(self) -> pd.DataFrame:
        csv_path = os.path.join(self.base_dir, "resumen_municipio_abstencion.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            print(f"[DataLoader] Resumen municipio cargado: {len(df)} municipios.")
            return df
        print("[DataLoader] Advertencia: resumen_municipio_abstencion.csv no encontrado.")
        return pd.DataFrame()

    def _ensure_columns(self):
        """Reconstruye columnas faltantes si no vienen en el archivo usando ID_TERRITORIO."""
        df = self.df_secciones
        if df is None:
            return
            
        # Asegurar tipo numérico en predicción
        if 'PREDICCION_ABSTENCION' in df.columns:
            df['PREDICCION_ABSTENCION'] = pd.to_numeric(df['PREDICCION_ABSTENCION'], errors='coerce')
        
        # Si falta EDOCVE o SECCION, reconstruir desde ID_TERRITORIO o ID_REGISTRO
        if 'ID_TERRITORIO' in df.columns:
            id_str = df['ID_TERRITORIO'].astype(str).str.zfill(9) # e.g. 010010001
            if 'EDOCVE' not in df.columns:
                df['EDOCVE'] = id_str.str[0:2].astype(int)
            if 'MPIOCVE' not in df.columns:
                df['MPIOCVE'] = id_str.str[2:5].astype(int)
            if 'SECCION' not in df.columns:
                df['SECCION'] = id_str.str[5:9].astype(int)
                
        # Si falta EDONOM o MPIONOM, cruzar con resúmenes si están disponibles
        if 'EDONOM' not in df.columns and self.df_estados is not None and not self.df_estados.empty:
            map_edo = dict(zip(self.df_estados['EDOCVE'], self.df_estados['EDONOM']))
            df['EDONOM'] = df['EDOCVE'].map(map_edo)

        if 'MPIONOM' not in df.columns and self.df_municipios is not None and not self.df_municipios.empty:
            map_mpio = dict(zip(zip(self.df_municipios['EDOCVE'], self.df_municipios['MPIOCVE']), self.df_municipios['MPIONOM']))
            df['MPIONOM'] = df.apply(lambda r: map_mpio.get((r['EDOCVE'], r['MPIOCVE']), f"Municipio {r['MPIOCVE']}"), axis=1)

        # Si falta TIPOSEC, asignar 'U' por defecto
        if 'TIPOSEC' not in df.columns:
            df['TIPOSEC'] = 'U'

        # Normalizar tipos de ID_TERRITORIO y SECCION a int para compatibilidad con CSV y tests
        if 'ID_TERRITORIO' in df.columns:
            df['ID_TERRITORIO'] = pd.to_numeric(df['ID_TERRITORIO'], errors='coerce').fillna(0).astype(int)
        if 'SECCION' in df.columns:
            df['SECCION'] = pd.to_numeric(df['SECCION'], errors='coerce').fillna(0).astype(int)

        self.df_secciones = df

    def _document_and_validate_risk(self):
        """Valida la clasificación de riesgo por terciles (cuantiles 33.3% y 66.7%)."""
        df = self.df_secciones
        if df is None or 'PREDICCION_ABSTENCION' not in df.columns:
            return
            
        # Calcular cuantiles sobre el universo nacional
        q33 = float(df['PREDICCION_ABSTENCION'].quantile(1/3))
        q66 = float(df['PREDICCION_ABSTENCION'].quantile(2/3))
        
        self.thresholds = {
            "q33": round(q33, 4),
            "q66": round(q66, 4),
            "min": round(float(df['PREDICCION_ABSTENCION'].min()), 4),
            "max": round(float(df['PREDICCION_ABSTENCION'].max()), 4),
            "mean": round(float(df['PREDICCION_ABSTENCION'].mean()), 4),
            "method": "Terciles empíricos sobre las 70,751 secciones nacionales"
        }
        
        # Si la columna RIESGO no existe, generarla
        if 'RIESGO' not in df.columns or df['RIESGO'].isnull().any():
            print("[DataLoader] Asignando categoría de RIESGO basada en cuantiles...")
            conditions = [
                df['PREDICCION_ABSTENCION'] <= q33,
                (df['PREDICCION_ABSTENCION'] > q33) & (df['PREDICCION_ABSTENCION'] <= q66),
                df['PREDICCION_ABSTENCION'] > q66
            ]
            choices = ['BAJO', 'MEDIO', 'ALTO']
            df['RIESGO'] = np.select(conditions, choices, default='MEDIO')
            # Normalizar tipos de ID_TERRITORIO y SECCION a int para compatibilidad con CSV y tests
        if 'ID_TERRITORIO' in df.columns:
            df['ID_TERRITORIO'] = pd.to_numeric(df['ID_TERRITORIO'], errors='coerce').fillna(0).astype(int)
        if 'SECCION' in df.columns:
            df['SECCION'] = pd.to_numeric(df['SECCION'], errors='coerce').fillna(0).astype(int)

        self.df_secciones = df

    def get_global_stats(self, anio: Optional[int] = 2024) -> Dict[str, Any]:
        """Obtiene métricas globales del dataset con contexto de año electoral real e histórico."""
        df = self.df_secciones
        if df is None or df.empty:
            return {}

        anio_sel = anio or 2024

        # Factores y datos históricos observados oficiales INE (Participación nacional observada:
        # 2009: 44.61% part -> 55.39% abstencion (Intermedia)
        # 2012: 63.08% part -> 36.92% abstencion (Presidencial)
        # 2015: 47.72% part -> 52.28% abstencion (Intermedia)
        # 2018: 63.42% part -> 36.58% abstencion (Presidencial)
        # 2021: 52.66% part -> 47.34% abstencion (Intermedia)
        # 2024: 61.04% part -> 38.96% abstencion obs / 46.77% base modelo predicha
        # 2027: ~48.73% proyectada (Intermedia futura)
        # 2030: ~47.14% proyectada (Presidencial futura)
        historicos_info = {
            2009: {"promedio": 55.39, "tipo": "Intermedia Federal (Observado Oficial INE)", "factor": 55.39 / 46.77, "modo": "historico"},
            2012: {"promedio": 36.92, "tipo": "Presidencial Federal (Observado Oficial INE)", "factor": 36.92 / 46.77, "modo": "historico"},
            2015: {"promedio": 52.28, "tipo": "Intermedia Federal (Observado Oficial INE)", "factor": 52.28 / 46.77, "modo": "historico"},
            2018: {"promedio": 36.58, "tipo": "Presidencial Federal (Observado Oficial INE)", "factor": 36.58 / 46.77, "modo": "historico"},
            2021: {"promedio": 47.34, "tipo": "Intermedia Federal (Observado Oficial INE)", "factor": 47.34 / 46.77, "modo": "historico"},
            2024: {"promedio": 46.77, "tipo": "Presidencial Federal (Base Calibrada Modelo ML)", "factor": 1.0, "modo": "base_modelo"},
            2027: {"promedio": 48.73, "tipo": "Intermedia Federal (Proyección Futura Prospectiva)", "factor": 1.042, "modo": "proyeccion"},
            2030: {"promedio": 47.14, "tipo": "Presidencial Federal (Proyección Futura Prospectiva)", "factor": 1.008, "modo": "proyeccion"}
        }

        info_anio = historicos_info.get(anio_sel, historicos_info[2024])
        factor = info_anio["factor"]
        promedio_final = info_anio["promedio"]

        # Recalcular conteo de riesgos según el año
        # Si el promedio general sube, las secciones de alto riesgo aumentan
        # Si baja (ej. 2012 o 2018), bajo riesgo aumenta significativamente
        if factor == 1.0 and 'RIESGO' in df.columns:
            risk_counts = df['RIESGO'].value_counts().to_dict()
            alto = int(risk_counts.get("ALTO", 0))
            medio = int(risk_counts.get("MEDIO", 0))
            bajo = int(risk_counts.get("BAJO", 0))
            vals_sim = df['PREDICCION_ABSTENCION']
        else:
            vals_sim = (df['PREDICCION_ABSTENCION'] * factor).clip(0.15, 0.85)
            q33 = self.thresholds.get("q33", 0.4231)
            q66 = self.thresholds.get("q66", 0.5099)
            alto = int((vals_sim > q66).sum())
            medio = int(((vals_sim > q33) & (vals_sim <= q66)).sum())
            bajo = int((vals_sim <= q33).sum())

        return {
            "anio_activo": anio_sel,
            "anio_solicitado": anio_sel,
            "tipo_proceso": info_anio["tipo"],
            "modo_dato": info_anio["modo"],
            "factor_ajuste": round(factor, 4),
            "anios_historicos_base": [2009, 2012, 2015, 2018, 2021],
            "anio_modelo_calibrado": 2024,
            "anios_prospectivos": [2027, 2030],
            "anios_disponibles": [2009, 2012, 2015, 2018, 2021, 2024, 2027, 2030],
            "total_secciones": len(df),
            "total_estados": int(df['EDOCVE'].nunique()),
            "total_municipios": int(df.groupby(['EDOCVE', 'MPIOCVE']).ngroups),
            "promedio_abstencion": promedio_final,
            "abstencion_minima": round(float(vals_sim.min()) * 100, 2),
            "abstencion_maxima": round(float(vals_sim.max()) * 100, 2),
            "secciones_alto_riesgo": alto,
            "secciones_medio_riesgo": medio,
            "secciones_bajo_riesgo": bajo,
            "pct_alto_riesgo": round((alto / len(df)) * 100, 2),
            "umbrales": self.thresholds
        }

    def get_estados_list(self):
        """Retorna la lista de estados ordenada con total de secciones."""
        df = self.df_secciones
        if df is None:
            return []
        estados = df.groupby(['EDOCVE', 'EDONOM']).agg(
            total_secciones=('SECCION', 'count'),
            promedio_abstencion=('PREDICCION_ABSTENCION', 'mean')
        ).reset_index().sort_values('EDOCVE')
        
        estados['promedio_abstencion'] = (estados['promedio_abstencion'] * 100).round(2)
        return estados.to_dict(orient='records')

    def get_municipios_list(self, edocve: Optional[int] = None):
        """Retorna municipios, opcionalmente filtrados por estado."""
        df = self.df_secciones
        if df is None:
            return []
        if edocve is not None:
            df = df[df['EDOCVE'] == int(edocve)]
            
        mpios = df.groupby(['EDOCVE', 'EDONOM', 'MPIOCVE', 'MPIONOM']).agg(
            total_secciones=('SECCION', 'count'),
            promedio_abstencion=('PREDICCION_ABSTENCION', 'mean')
        ).reset_index().sort_values(['EDOCVE', 'MPIOCVE'])
        
        mpios['promedio_abstencion'] = (mpios['promedio_abstencion'] * 100).round(2)
        return mpios.to_dict(orient='records')

    def query_secciones(self, 
                        edocve: Optional[int] = None, 
                        mpiocve: Optional[int] = None, 
                        seccion: Optional[int] = None, 
                        riesgo: Optional[str] = None,
                        search: Optional[str] = None,
                        anio: Optional[int] = 2024,
                        limit: int = 50, 
                        offset: int = 0) -> Dict[str, Any]:
        """Filtra secciones según los parámetros especificados con paginación y contexto de año."""
        df = self.df_secciones
        if df is None or df.empty:
            return {"total": 0, "results": []}

        # Filtrar por año si el dataset contiene múltiples años o por columna ANIO
        if anio is not None and 'ANIO' in df.columns:
            if anio in df['ANIO'].values:
                df = df[df['ANIO'] == int(anio)]

        # Aplicar filtros
        if edocve is not None and edocve > 0:
            df = df[df['EDOCVE'] == int(edocve)]
        if mpiocve is not None and mpiocve > 0:
            df = df[df['MPIOCVE'] == int(mpiocve)]
        if seccion is not None and seccion > 0:
            df = df[df['SECCION'] == int(seccion)]
        if riesgo and riesgo.upper() in ['ALTO', 'MEDIO', 'BAJO']:
            df = df[df['RIESGO'] == riesgo.upper()]
        if search and search.strip():
            s = search.strip().lower()
            # Búsqueda en sección o municipio
            df = df[
                df['SECCION'].astype(str).str.contains(s) | 
                df['MPIONOM'].astype(str).str.lower().str.contains(s) |
                df['EDONOM'].astype(str).str.lower().str.contains(s) |
                df['ID_TERRITORIO'].astype(str).str.contains(s)
            ]

        # Si el año solicitado es un año histórico o proyectado, aplicar el factor de abstención
        # para reflejar las condiciones observadas/proyectadas reales de ese ciclo electoral
        historicos_factores = {
            2009: 55.39 / 46.77,
            2012: 36.92 / 46.77,
            2015: 52.28 / 46.77,
            2018: 36.58 / 46.77,
            2021: 47.34 / 46.77,
            2024: 1.0,
            2027: 1.042,
            2030: 1.008
        }
        factor_anio = historicos_factores.get(int(anio) if anio else 2024, 1.0)

        # Aplicar factor si difiere de 1.0 para que la tabla y métricas muestren el valor del año
        df_view = df.copy()
        if factor_anio != 1.0:
            df_view['PREDICCION_ABSTENCION'] = (df_view['PREDICCION_ABSTENCION'] * factor_anio).clip(0.12, 0.92)
            q33 = self.thresholds.get("q33", 0.4231)
            q66 = self.thresholds.get("q66", 0.5099)
            conds = [
                df_view['PREDICCION_ABSTENCION'] <= q33,
                (df_view['PREDICCION_ABSTENCION'] > q33) & (df_view['PREDICCION_ABSTENCION'] <= q66),
                df_view['PREDICCION_ABSTENCION'] > q66
            ]
            df_view['RIESGO'] = np.select(conds, ['BAJO', 'MEDIO', 'ALTO'], default='MEDIO')

        # Si se filtró por riesgo y el año alteró los riesgos, filtrar con df_view
        if riesgo and riesgo.upper() in ['ALTO', 'MEDIO', 'BAJO']:
            df_view = df_view[df_view['RIESGO'] == riesgo.upper()]

        total_match = len(df_view)
        
        # Resumen del subconjunto filtrado
        subset_stats = {}
        if total_match > 0:
            subset_stats = {
                "total": total_match,
                "promedio_abstencion": round(float(df_view['PREDICCION_ABSTENCION'].mean()) * 100, 2),
                "alto_riesgo": int((df_view['RIESGO'] == 'ALTO').sum()),
                "medio_riesgo": int((df_view['RIESGO'] == 'MEDIO').sum()),
                "bajo_riesgo": int((df_view['RIESGO'] == 'BAJO').sum()),
            }

        # Paginación
        paginated_df = df_view.iloc[offset:offset+limit].copy()
        
        # Formatear columnas para visualización clara
        paginated_df['PREDICCION_PCT'] = (paginated_df['PREDICCION_ABSTENCION'] * 100).round(2)
        
        return {
            "total": total_match,
            "limit": limit,
            "offset": offset,
            "anio_activo": int(anio) if anio else 2024,
            "anio_solicitado": anio or 2024,
            "factor_aplicado": round(factor_anio, 4),
            "stats": subset_stats,
            "results": paginated_df.to_dict(orient='records')
        }

    def get_seccion_detalle(self, query: str) -> Optional[Dict[str, Any]]:
        """Busca una sección específica por ID_TERRITORIO, ID_REGISTRO o número de sección."""
        df = self.df_secciones
        if df is None:
            return None
            
        q = str(query).strip()
        match = None
        
        # Intentar por ID_REGISTRO
        if 'ID_REGISTRO' in df.columns:
            m = df[df['ID_REGISTRO'] == q]
            if not m.empty:
                match = m.iloc[0]
                
        # Intentar por ID_TERRITORIO (str o int)
        if match is None:
            m = df[df['ID_TERRITORIO'].astype(str) == q.zfill(9)]
            if not m.empty:
                match = m.iloc[0]
            elif q.isdigit():
                m = df[df['ID_TERRITORIO'].astype(str) == q]
                if not m.empty:
                    match = m.iloc[0]
                
        # Intentar por SECCION (primer match o exacto como str o int)
        if match is None:
            m = df[df['SECCION'].astype(str) == q]
            if not m.empty:
                match = m.iloc[0]
            elif q.isdigit():
                m = df[df['SECCION'].astype(str) == str(int(q))]
                if not m.empty:
                    match = m.iloc[0]

        if match is not None:
            res = match.to_dict()
            res['PREDICCION_PCT'] = round(float(res['PREDICCION_ABSTENCION']) * 100, 2)
            
            # Enriquecer con información demográfica de edad
            id_terr = str(res.get('ID_TERRITORIO', '')).zfill(9)
            res['DEMOGRAFIA'] = None
            if self.df_demografia is not None and not self.df_demografia.empty:
                d_match = self.df_demografia[self.df_demografia['ID_TERRITORIO'] == id_terr]
                if not d_match.empty:
                    demo_row = d_match.iloc[0].to_dict()
                    
                    # Generar recomendaciones breves basadas en perfil etario, riesgo y tipo de sección
                    riesgo = str(res.get('RIESGO', 'MEDIO')).upper()
                    tiposec = str(res.get('TIPOSEC', 'U')).upper()
                    grupo_pred = str(demo_row.get('GRUPO_PREDOMINANTE', ''))
                    perfil_macro = str(demo_row.get('PERFIL_MACRO', ''))

                    recs = []
                    # Recomendaciones por perfil etario
                    if perfil_macro == 'JOVENES' or grupo_pred in ['18-24', '25-34']:
                        recs.append("Reforzar mensajes institucionales en plataformas digitales y redes sociales con contenido breve, directo y visual.")
                        recs.append("Desplegar brigadas móviles de orientación y promoción en nodos comunitarios, universitarios o de alta concentración juvenil.")
                    elif perfil_macro == 'MAYORES' or grupo_pred == '60+':
                        recs.append("Asegurar señalización visible, accesibilidad física para personas mayores y módulos de atención prioritaria en casillas.")
                        recs.append("Difundir información impresa y clara mediante asambleas vecinales o perifoneo local sobre ubicación exacta de casillas.")
                    else: # ADULTOS o 35-44 / 45-59
                        recs.append("Fortalecer información territorial y vecinal sobre horarios de votación y documentación requerida.")
                        recs.append("Canalizar recordatorios de participación ciudadana mediante liderazgos comunitarios y medios locales.")

                    # Recomendación contextual adicional por riesgo o tipo de sección
                    if riesgo == 'ALTO':
                        recs.append("Priorizar esta sección con presencia anticipada de personal del INE y supervisión de rutas de acceso.")
                    elif tiposec == 'R':
                        recs.append("Monitorear tiempos de traslado y facilitar casillas extraordinarias o transporte hacia centros de votación.")
                    else:
                        recs.append("Mantener módulos informativos en zonas céntricas y mercados para resolver dudas de ubicación seccional.")

                    demo_row['RECOMENDACIONES'] = recs[:3]
                    res['DEMOGRAFIA'] = demo_row

            return res
        return None

