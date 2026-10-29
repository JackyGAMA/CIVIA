"""
run_mvp.py - Lanzador interactivo del MVP de Abstención Electoral INE.
Permite iniciar la interfaz web o realizar consultas en modo consola.
"""

import sys
import os

def print_menu():
    print("="*65)
    print("   SISTEMA DE PREDICCIÓN DE ABSTENCIÓN ELECTORAL INE (MVP)")
    print("="*65)
    print("  [1] Iniciar Servidor Web Interactivo (FastAPI + Dashboard UI)")
    print("  [2] Consultar Estadísticas Generales en Terminal")
    print("  [3] Consultar Sección Electoral Específica")
    print("  [4] Ver Resumen por Estado (32 Entidades)")
    print("  [5] Ver Resumen Municipal")
    print("  [6] Ejecutar Suite de Pruebas Unitarias")
    print("  [0] Salir")
    print("="*65)

def main():
    while True:
        print_menu()
        choice = input(" Seleccione una opción [0-6]: ").strip()
        
        if choice == "1":
            print("\nIniciando servidor web...")
            import app
            app.start_server(open_browser=True)
            break
        elif choice == "2":
            os.system(f'"{sys.executable}" consultar.py --stats')
            input("\nPresione Enter para continuar...")
        elif choice == "3":
            sec = input(" Ingrese el número de sección electoral: ").strip()
            edo = input(" Ingrese la clave de estado (EDOCVE 1-32, o vacío para todas): ").strip()
            cmd = f'"{sys.executable}" consultar.py --seccion {sec}'
            if edo:
                cmd += f' --estado {edo}'
            os.system(cmd)
            input("\nPresione Enter para continuar...")
        elif choice == "4":
            os.system(f'"{sys.executable}" consultar.py --resumen-estado')
            input("\nPresione Enter para continuar...")
        elif choice == "5":
            edo = input(" Ingrese la clave de estado (1-32, o vacío para top nacional): ").strip()
            cmd = f'"{sys.executable}" consultar.py --resumen-municipio'
            if edo:
                cmd += f' --estado {edo}'
            os.system(cmd)
            input("\nPresione Enter para continuar...")
        elif choice == "6":
            os.system(f'"{sys.executable}" test_app.py')
            input("\nPresione Enter para continuar...")
        elif choice == "0":
            print("\nSaliendo del MVP. Hasta pronto.\n")
            break
        else:
            print("\nOpción no válida. Intente de nuevo.\n")

if __name__ == "__main__":
    main()

