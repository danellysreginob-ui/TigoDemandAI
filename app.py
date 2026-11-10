
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "registros.json"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8001))


def leer_registros():
    """Lee el historial existente sin borrarlo ni reemplazarlo."""
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError(
            "registros.json contiene datos que no se pueden leer. "
            "Haz una copia del archivo antes de corregirlo."
        ) from error

    if not isinstance(datos, list):
        raise ValueError("El contenido de registros.json debe ser una lista.")

    return datos


def guardar_registros(registros):
    """Guarda el historial completo, incluyendo los registros anteriores."""
    temporal = DATA_FILE.with_suffix(".json.tmp")
    with temporal.open("w", encoding="utf-8") as archivo:
        json.dump(registros, archivo, ensure_ascii=False, indent=2)
    temporal.replace(DATA_FILE)


class TigoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def responder_json(self, codigo, contenido):
        cuerpo = json.dumps(contenido, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        ruta = urlsplit(self.path).path

        if ruta == "/api/registros":
            try:
                self.responder_json(200, leer_registros())
            except (ValueError, OSError) as error:
                self.responder_json(500, {"error": str(error)})
            return

        if ruta == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        ruta = urlsplit(self.path).path

        if ruta != "/api/registros":
            self.responder_json(404, {"error": "Ruta no encontrada."})
            return

        try:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud <= 0 or longitud > 100_000:
                self.responder_json(400, {"error": "El tamaño de la solicitud no es válido."})
                return

            entrada = json.loads(self.rfile.read(longitud).decode("utf-8"))

            fecha = str(entrada.get("fecha", "")).strip()
            hora = str(entrada.get("hora", "")).strip()
            clientes = int(entrada.get("clientes", 0))
            minutos = float(entrada.get("minutos", 0))

            datetime.strptime(fecha, "%Y-%m-%d")
            datetime.strptime(hora, "%H:%M")

            if clientes < 1 or clientes > 10000:
                raise ValueError("La cantidad de clientes debe ser mayor que cero.")
            if minutos <= 0 or minutos > 1440:
                raise ValueError("Los minutos por cliente deben ser mayores que cero.")

            nuevo = {
                "fecha": fecha,
                "hora": hora,
                "clientes": clientes,
                "minutos": minutos
            }

            registros = leer_registros()
            registros.append(nuevo)
            guardar_registros(registros)
            self.responder_json(201, {
                "mensaje": "Registro guardado correctamente.",
                "registro": nuevo,
                "total_registros": len(registros)
            })

        except (json.JSONDecodeError, UnicodeDecodeError):
            self.responder_json(400, {"error": "Los datos enviados no tienen un formato válido."})
        except (ValueError, TypeError, OSError) as error:
            self.responder_json(400, {"error": str(error)})

    def log_message(self, formato, *args):
        # Mantiene la consola más limpia sin ocultar errores de la aplicación.
        super().log_message(formato, *args)


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, PORT), TigoHandler)
    print("=" * 56)
    print("TigoDemandAI está en ejecución.")
    print(f"Abre en el navegador: http://{HOST}:{PORT}")
    print("No cierres esta ventana mientras uses la aplicación.")
    print("Presiona Ctrl+C para detener el servidor.")
    print("=" * 56)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
