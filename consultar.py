"""
consultar.py - Interfaz de línea de comandos (CLI) para consulta rápida del MVP.
Permite consultar predicciones por sección, filtrar por estado y municipio,
y visualizar métricas y resúmenes directamente en la terminal.
"""

import argparse
import sys

# Asegurar codificación utf-8 en consola de Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from data_loader import DataLoader

def main():
    parser = argparse.ArgumentParser(
        description="Consulta de Predicción de Abstención Electoral INE (MVP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python consultar.py --stats
  python consultar.py --seccion 1 --estado 1
  python consultar.py --id 10010001
  python consultar.py --estado 9 --riesgo ALTO --limit 10
  python consultar.py --resumen-estado
  python consultar.py --resumen-municipio --estado 1
        """
    )
    
    parser.add_argument("--stats", action="store_true", help="Muestra estadísticas globales del modelo")
    parser.add_argument("--seccion", type=int, help="Número de sección electoral a buscar")
    parser.add_argument("--id", type=str, help="ID_TERRITORIO o ID_REGISTRO de la sección")
    parser.add_argument("--estado", type=int, help="Clave de estado (EDOCVE: 1 a 32)")
    parser.add_argument("--municipio", type=int, help="Clave de municipio (MPIOCVE)")
    parser.add_argument("--riesgo", choices=["ALTO", "MEDIO", "BAJO"], help="Filtrar por nivel de riesgo")
    parser.add_argument("--resumen-estado", action="store_true", help="Mostrar tabla resumen por estado")
    parser.add_argument("--resumen-municipio", action="store_true", help="Mostrar resumen por municipios")
    parser.add_argument("--limit", type=int, default=15, help="Límite de resultados a mostrar (default: 15)")

    args = parser.parse_args()
    
    dl = DataLoader(".")
    
    # 1. Modo Estadísticas Globales
    if args.stats:
        stats = dl.get_global_stats()
        print("\n" + "="*65)
        print("  SISTEMA PREDICTIVO DE ABSTENCIÓN ELECTORAL INE - MÉTRICAS GLOBALES")
        print("="*65)
        print(f" Total de Secciones Cargadas:   {stats['total_secciones']:,}")
        print(f" Total de Entidades Federativas: {stats['total_estados']}")
        print(f" Total de Municipios:           {stats['total_municipios']:,}")
        print(f" Promedio Nacional Abstención:  {stats['promedio_abstencion']:.2f}%")
        print(f" Rango de Predicción:           [{stats['abstencion_minima']:.2f}% - {stats['abstencion_maxima']:.2f}%]")
        print("-" * 65)
        print(" Distribución por Nivel de Riesgo (Terciles Empíricos):")
        print(f"  🔴 ALTO  (> {stats['umbrales']['q66']*100:.2f}%):    {stats['secciones_alto_riesgo']:,} secciones ({stats['pct_alto_riesgo']}%)")
        print(f"  🟡 MEDIO ({stats['umbrales']['q33']*100:.2f}% - {stats['umbrales']['q66']*100:.2f}%): {stats['secciones_medio_riesgo']:,} secciones")
        print(f"  🟢 BAJO  (< {stats['umbrales']['q33']*100:.2f}%):    {stats['secciones_bajo_riesgo']:,} secciones")
        print("="*65 + "\n")
        return

    # 2. Búsqueda directa por ID o Sección específica
    if args.id or (args.seccion and args.estado):
        if args.id:
            res = dl.get_seccion_detalle(args.id)
        else:
            q = dl.query_secciones(edocve=args.estado, seccion=args.seccion, limit=1)
            res = q['results'][0] if q['results'] else None

        if not res:
            print(f"\n❌ No se encontró ninguna sección con los parámetros indicados.")
            return

        print("\n" + "="*55)
        print(f"  DETALLE DE SECCIÓN ELECTORAL #{res['SECCION']}")
        print("="*55)
        print(f" ID Territorio:        {res['ID_TERRITORIO']}")
        print(f" ID Registro:          {res['ID_REGISTRO']}")
        print(f" Entidad Federativa:   {res['EDONOM']} (Clave: {res['EDOCVE']})")
        print(f" Municipio:            {res['MPIONOM']} (Clave: {res['MPIOCVE']})")
        print(f" Sección:              {res['SECCION']} ({'Urbana' if res['TIPOSEC']=='U' else 'Rural' if res['TIPOSEC']=='R' else 'Mixta'})")
        print(f" Predicción Abstención: {res['PREDICCION_PCT']:.2f}%")
        
        riesgo_badge = "🔴 ALTO" if res['RIESGO'] == 'ALTO' else "🟡 MEDIO" if res['RIESGO'] == 'MEDIO' else "🟢 BAJO"
        print(f" Nivel de Riesgo:      {riesgo_badge}")
        print("="*55 + "\n")
        return

    # 3. Resumen por Estado
    if args.resumen_estado:
        dfe = dl.df_estados
        if dfe is None or dfe.empty:
            print("No se dispone del resumen estatal.")
            return
        print("\n" + "="*85)
        print(f"{'CVE':<4} {'ESTADO':<25} {'ABST. PRED':<12} {'SECCIONES':<10} {'ALTO RIESGO':<12} {'% ALTO':<10}")
        print("="*85)
        for _, r in dfe.sort_values('PROMEDIO_ABSTENCION_PRED', ascending=False).iterrows():
            print(f"{int(r['EDOCVE']):<4} {r['EDONOM']:<25} {r['PROMEDIO_ABSTENCION_PRED']*100:>10.2f}% {int(r['TOTAL_SECCIONES']):>9,} {int(r['SECCIONES_RIESGO_ALTO']):>11,} {r['PORC_SECCIONES_ALTO_RIESGO']:>9.1f}%")
        print("="*85 + "\n")
        return

    # 4. Resumen por Municipio
    if args.resumen_municipio:
        dfm = dl.df_municipios
        if dfm is None or dfm.empty:
            print("No se dispone del resumen municipal.")
            return
        if args.estado:
            dfm = dfm[dfm['EDOCVE'] == args.estado]
            print(f"\n--- Resumen Municipal (Estado {args.estado}) ---")
        else:
            print("\n--- Resumen Municipal (Primeros resultados - use --estado para filtrar) ---")
            
        print("="*90)
        print(f"{'ESTADO':<20} {'MUNICIPIO':<25} {'ABST. PRED':<12} {'SECCIONES':<10} {'% ALTO RIESGO':<15}")
        print("="*90)
        for _, r in dfm.sort_values('PROMEDIO_ABSTENCION_PRED', ascending=False).head(args.limit).iterrows():
            print(f"{r['EDONOM']:<20} {r['MPIONOM']:<25} {r['PROMEDIO_ABSTENCION_PRED']*100:>10.2f}% {int(r['TOTAL_SECCIONES']):>9,} {r['PORC_SECCIONES_ALTO_RIESGO']:>13.1f}%")
        print("="*90 + "\n")
        return

    # 5. Consulta y Filtrado General de Secciones
    data = dl.query_secciones(
        edocve=args.estado,
        mpiocve=args.municipio,
        seccion=args.seccion,
        riesgo=args.riesgo,
        limit=args.limit
    )
    
    total = data['total']
    stats = data['stats']
    results = data['results']
    
    print("\n" + "="*85)
    print(f" RESULTADOS DE BÚSQUEDA ({total:,} secciones coincidentes | Mostrando {len(results)})")
    if stats:
        print(f" Promedio Abstención: {stats.get('promedio_abstencion', 0):.2f}% | "
              f"Alto: {stats.get('alto_riesgo', 0)} | "
              f"Medio: {stats.get('medio_riesgo', 0)} | "
              f"Bajo: {stats.get('bajo_riesgo', 0)}")
    print("="*85)
    print(f"{'ID TERRITORIO':<14} {'ESTADO':<20} {'MUNICIPIO':<20} {'SECC':<6} {'ABSTENCION':<12} {'RIESGO':<8}")
    print("-" * 85)
    
    for r in results:
        r_str = f"🔴 ALTO" if r['RIESGO'] == 'ALTO' else f"🟡 MEDIO" if r['RIESGO'] == 'MEDIO' else f"🟢 BAJO"
        print(f"{r['ID_TERRITORIO']:<14} {r['EDONOM']:<20} {r['MPIONOM'][:19]:<20} {r['SECCION']:<6} {r['PREDICCION_PCT']:>9.2f}%   {r_str:<8}")
    
    print("="*85)
    if total > args.limit:
        print(f" Nota: Se muestran las primeras {args.limit} filas de {total:,}. Use --limit N para ver más.")
    print("")

if __name__ == "__main__":
    main()
