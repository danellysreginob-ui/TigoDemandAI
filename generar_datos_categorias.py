"""
Genera 90 días de datos SINTÉTICOS por tipo de atención y entrena un modelo.
No modifica la tabla original "registros" ni el modelo general existente.
"""
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import random
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error

CARPETA = Path(__file__).resolve().parent
BD = CARPETA / "TigoDemandAI.db"
CSV = CARPETA / "datos_categorias_sinteticos.csv"
ARCHIVO_MODELO = CARPETA / "modelo_categorias.joblib"
CATEGORIAS = ["dispositivos", "quejas", "planes", "otros"]
random.seed(42)

def generar_datos():
    hoy = date.today()
    inicio = hoy - timedelta(days=89)
    filas = []
    for n in range(90):
        fecha = inicio + timedelta(days=n)
        finde = fecha.weekday() >= 5
        for hora in range(9, 21):
            if finde:
                intensidad = {9:.55,10:.80,11:.90,12:.75,13:.60,14:.55,
                              15:.60,16:.65,17:.70,18:.75,19:.60,20:.40}[hora]
                base = 22
            else:
                intensidad = {9:.55,10:.65,11:.70,12:.65,13:.80,14:1.0,
                              15:1.0,16:.85,17:.75,18:.90,19:.85,20:.55}[hora]
                base = 34
            total = max(4, int(random.gauss(base * intensidad, max(2, base * intensidad * .13))))
            if finde and hora in (10, 11, 12):
                pesos = [.43, .12, .28, .17]
            elif hora in (14, 15):
                pesos = [.18, .22, .43, .17]
            elif hora in (18, 19):
                pesos = [.20, .30, .32, .18]
            else:
                pesos = [.25, .20, .35, .20]
            pesos = [max(.05, p + random.uniform(-.035, .035)) for p in pesos]
            suma = sum(pesos)
            pesos = [p / suma for p in pesos]
            cantidades = [int(total * p) for p in pesos]
            cantidades[0] += total - sum(cantidades)
            filas.append({
                "fecha": fecha.isoformat(), "hora": f"{hora:02d}:00",
                "dia_semana": fecha.weekday(), "fin_semana": int(finde),
                "mes": fecha.month, "dia_mes": fecha.day, "hora_num": hora,
                "clientes": total, "dispositivos": cantidades[0],
                "quejas": cantidades[1], "planes": cantidades[2],
                "otros": cantidades[3]
            })
    return pd.DataFrame(filas)

def main():
    if not BD.exists():
        raise FileNotFoundError("No encuentro TigoDemandAI.db. Guarda este script dentro de la carpeta TigoDemandAI.")
    df = generar_datos()
    df.to_csv(CSV, index=False, encoding="utf-8-sig")
    with sqlite3.connect(BD) as con:
        df.to_sql("registros_categorias_sinteticos", con, if_exists="replace", index=False)

    columnas = ["dia_semana", "fin_semana", "mes", "dia_mes", "hora_num"]
    X, y = df[columnas], df[CATEGORIAS]
    corte = int(len(df) * .8)
    modelo = MultiOutputRegressor(RandomForestRegressor(
        n_estimators=180, max_depth=14, min_samples_leaf=2,
        random_state=42, n_jobs=-1
    ))
    modelo.fit(X.iloc[:corte], y.iloc[:corte])
    error = mean_absolute_error(y.iloc[corte:], modelo.predict(X.iloc[corte:]))
    joblib.dump({
        "modelo": modelo, "columnas": columnas, "categorias": CATEGORIAS,
        "nota": "Entrenado exclusivamente con datos sintéticos para un proyecto académico."
    }, ARCHIVO_MODELO)
    print("\nPROCESO TERMINADO")
    print(f"Registros generados: {len(df)} (90 días, 12 horarios por día)")
    print(f"Error medio de prueba: {error:.2f} clientes por categoría")
    print("CSV: datos_categorias_sinteticos.csv")
    print("Tabla nueva: registros_categorias_sinteticos")
    print("Modelo: modelo_categorias.joblib")
    print("La tabla original 'registros' y modelo_demanda.joblib NO fueron modificados.")

if __name__ == "__main__":
    main()
