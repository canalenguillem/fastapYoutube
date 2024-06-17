import time
from pprint import pprint
import requests
from bs4 import BeautifulSoup


class TtsMp3:
    def __init__(self) -> None:
        self.headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_4_9) AppleWebKit/534.29 (KHTML, like Gecko) Chrome/49.0.1273.301 Safari/603"
        }
        self.voces = {}

    def _get_voces(self):
        s = {
            "voces": {},
            "res": None,
        }

        print("Obteniendo voces disponibles")
        url = "https://ttsmp3.com"
        try:
            req = requests.get(url, headers=self.headers)
            if not req.ok:
                s["res"] = f"Error: {req.status_code} {req.reason}"
                return s
            else:
                soup = BeautifulSoup(req.text, "html.parser")
                opciones = soup.find(id="sprachwahl").find_all("option")
                for x in opciones:
                    voz = x.attrs.get("value")
                    idioma = x.text.split("/")[0].strip()
                    if not idioma in s["voces"]:
                        s["voces"][idioma] = []
                    s["voces"][idioma].append(voz)
        except Exception as e:
            s["res"] = f'ERROR: {e}'
            return s
        self.voces = s["voces"]
        s["res"] = "OK"
        pprint(self.voces, sort_dicts=False)
        return s

    def tts(self, texto, voz="Lucia", archivo_salida=None):
        s = {
            "texto": texto,
            "voz": voz,
            "archivo_salida": archivo_salida,
            "tiempo": None,
            "res": None
        }

        # Si no tenemos todavía las voces
        if not self.voces:
            res = self._get_voces()
            if res["res"] != "OK":
                s["res"] = res["res"]
                return s

        voz_disponible = False
        for idioma, datos in self.voces.items():
            for v in datos:
                if v == voz:
                    voz_disponible = True
                    break
            if voz_disponible:
                break
        if not voz_disponible:
            s["res"] = f"ERROR: la voz {voz} no está disponible"
            return s
        inicio = time.time()

        if not archivo_salida:
            s["archivo_salida"] = f"{voz}.mp3"

        # Realizamos petición
        url = "https://ttsmp3.com/makemp3_new.php"
        data = {
            "msg": texto,
            "lang": voz,
            "source": "ttsmp3"
        }
        try:
            req = requests.post(url, headers=self.headers, data=data)
            pprint(req.json(), sort_dicts=False)
            if not req.ok:
                s["res"] = f"ERROR: {req.status_code} {req.reason}"
                return s
            if req.json().get("Error"):
                s["res"] = req.json()["Error"]
                return s

        except Exception as e:
            s["res"] = f"ERROR: {e}"
            return s

        # Si todo ha ido bien descargamos el audio
        url = req.json()["URL"]
        print(f"Descargado: {url}")
        try:
            req = requests.get(url, headers=self.headers)
            if not req.ok:
                s["res"] = f"ERROR al descargar mp3: {req.status_code} {req.reason}"
                return s
            else:
                print(f"Guardando: {s['archivo_salida']}")
                with open(s["archivo_salida"], "wb") as f:
                    f.write(req.content)
                s["audio"] = req.content
        except Exception as e:
            s["res"] = f"ERROR: {e}"
            return s

        s["tiempo"] = time.time() - inicio
        s["res"] = "OK"
        return s
