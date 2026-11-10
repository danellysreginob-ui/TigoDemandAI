
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

CARPETA = Path(__file__).resolve().parent

ARCHIVO_MODELO_GENERAL = CARPETA / "modelo_demanda.joblib"
ARCHIVO_MODELO_CATEGORIAS = CARPETA / "modelo_categorias.joblib"

CATEGORIAS = [
    "dispositivos",
    "quejas",
    "planes",
    "otros"
]


def distribuir_clientes(total, cantidades):
    """
    Ajusta las predicciones por categoría para que sumen
    exactamente el total de clientes del modelo general.
    """
    cantidades = [max(0, float(valor)) for valor in cantidades]
    suma = sum(cantidades)

    if total == 0:
        return [0] * len(CATEGORIAS)

    if suma == 0:
        resultado = [0] * len(CATEGORIAS)
        resultado[0] = total
        return resultado

    proporciones = [valor / suma for valor in cantidades]
    resultado = [int(total * proporcion) for proporcion in proporciones]

    diferencia = total - sum(resultado)

    # Repartir los clientes restantes según los mayores decimales.
    decimales = [
        total * proporcion - entero
        for proporcion, entero in zip(proporciones, resultado)
    ]

    orden = sorted(
        range(len(decimales)),
        key=lambda i: decimales[i],
        reverse=True
    )

    for i in range(diferencia):
        resultado[orden[i % len(orden)]] += 1

    return resultado


def predecir(fecha, hora):
    # Validar fecha y hora.
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
    hora_obj = datetime.strptime(hora, "%H:%M")

    # Comprobar que existen los dos modelos.
    if not ARCHIVO_MODELO_GENERAL.exists():
        raise FileNotFoundError(
            "No existe modelo_demanda.joblib. "
            "Ejecuta entrenar_modelo.py."
        )

    if not ARCHIVO_MODELO_CATEGORIAS.exists():
        raise FileNotFoundError(
            "No existe modelo_categorias.joblib. "
            "Ejecuta generar_datos_categorias.py."
        )

    # --------------------------------
    # 1. PREDICCIÓN GENERAL
    # --------------------------------

    modelo_general = joblib.load(ARCHIVO_MODELO_GENERAL)

    datos_generales = pd.DataFrame([{
        "dia_semana": fecha_obj.weekday(),
        "hora_num": hora_obj.hour,
        "mes": fecha_obj.month,
        "dia_mes": fecha_obj.day
    }])

    clientes = max(
        0,
        round(float(modelo_general.predict(datos_generales)[0]))
    )

    if clientes < 25:
        nivel = "Bajo"
    elif clientes < 45:
        nivel = "Medio"
    else:
        nivel = "Alto"

    # --------------------------------
    # 2. PREDICCIÓN POR CATEGORÍAS
    # --------------------------------

    paquete = joblib.load(ARCHIVO_MODELO_CATEGORIAS)

    modelo_categorias = paquete["modelo"]
    columnas = paquete["columnas"]

    datos_categorias = {
        "dia_semana": fecha_obj.weekday(),
        "fin_semana": int(fecha_obj.weekday() >= 5),
        "mes": fecha_obj.month,
        "dia_mes": fecha_obj.day,
        "hora_num": hora_obj.hour
    }

    entrada = pd.DataFrame(
        [[datos_categorias[columna] for columna in columnas]],
        columns=columnas
    )

    predicciones = modelo_categorias.predict(entrada)[0]

    # Ajustar categorías al total general.
    cantidades = distribuir_clientes(clientes, predicciones)

    resultado_categorias = {
        categoria: cantidad
        for categoria, cantidad in zip(CATEGORIAS, cantidades)
    }

    # --------------------------------
    # 3. RESULTADO FINAL
    # --------------------------------

    return {
        "fecha": fecha,
        "hora": hora,
        "clientes_predichos": clientes,
        "nivel_demanda": nivel,
        "categorias_predichas": resultado_categorias
    }


if __name__ == "__main__":
    fecha = input("Fecha (AAAA-MM-DD): ").strip()
    hora = input("Hora (HH:MM): ").strip()

    resultado = predecir(fecha, hora)

    print("\n--- PREDICCIÓN TIGODEMANDAI ---")
    print(f"Fecha: {resultado['fecha']}")
    print(f"Hora: {resultado['hora']}")
    print(f"Clientes estimados: {resultado['clientes_predichos']}")
    print(f"Nivel de demanda: {resultado['nivel_demanda']}")

    print("\n--- PREDICCIÓN POR CATEGORÍAS ---")

    for categoria, cantidad in resultado["categorias_predichas"].items():
        print(f"{categoria.capitalize()}: {cantidad} clientes")

    print(
        "\nTotal por categorías:",
        sum(resultado["categorias_predichas"].values())
    )
