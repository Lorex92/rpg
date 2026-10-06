# -*- coding: utf-8 -*-
"""
FACCIA -> TASTI   (versione 2.0)

Un solo programma con due funzioni, entrambe configurabili con il mouse:

 1. ESPRESSIONI DEL VISO -> TASTI
    Guarda il viso con la webcam e, quando fai un'espressione, preme un tasto
    della tastiera (o un clic del mouse) a tua scelta.

 2. MOUSE -> FRECCE   (solo Windows)
    Tieni premuto il tasto sinistro del mouse e sposta il puntatore: in alto
    tiene premuta FRECCIA SU, in basso GIU', a destra DESTRA, a sinistra
    SINISTRA. Un clic veloce resta un clic normale.

Richiede Python 3 e le librerie di requirements.txt (installa.bat).
Istruzioni complete in LEGGIMI.md
"""

import json
import os
import sys
import threading
import time
import urllib.request

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_IMPOSTAZIONI = os.path.join(CARTELLA, "impostazioni.json")
FILE_MODELLO = os.path.join(CARTELLA, "face_landmarker.task")
FILE_ERRORI = os.path.join(CARTELLA, "errori.txt")
URL_MODELLO = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
               "face_landmarker/float16/1/face_landmarker.task")

WINDOWS = os.name == "nt"

# ----------------------------------------------------------------------
#  ESPRESSIONI RICONOSCIUTE
#  (id interno, nome mostrato, soglia iniziale, funzione che calcola 0..1)
#  b = punteggi di MediaPipe (0..1)
# ----------------------------------------------------------------------

def _media(b, *nomi):
    return sum(b.get(n, 0.0) for n in nomi) / len(nomi)

ESPRESSIONI = [
    ("bocca_aperta", "Bocca aperta",               0.40, lambda b: b.get("jawOpen", 0.0)),
    ("sorriso",      "Sorriso",                    0.55, lambda b: _media(b, "mouthSmileLeft", "mouthSmileRight")),
    ("sopracciglia", "Sopracciglia alzate",        0.50, lambda b: b.get("browInnerUp", 0.0)),
    ("accigliato",   "Sopracciglia abbassate",     0.60, lambda b: _media(b, "browDownLeft", "browDownRight")),
    ("guance",       "Guance gonfie",              0.40, lambda b: b.get("cheekPuff", 0.0)),
    ("occhio_sx",    "Occhiolino sinistro",        0.40, lambda b: max(0.0, b.get("eyeBlinkLeft", 0.0) - b.get("eyeBlinkRight", 0.0))),
    ("occhio_dx",    "Occhiolino destro",          0.40, lambda b: max(0.0, b.get("eyeBlinkRight", 0.0) - b.get("eyeBlinkLeft", 0.0))),
    ("occhi_chiusi", "Entrambi gli occhi chiusi",  0.60, lambda b: min(b.get("eyeBlinkLeft", 0.0), b.get("eyeBlinkRight", 0.0))),
    ("bocca_sx",     "Bocca spostata a sinistra",  0.40, lambda b: b.get("mouthLeft", 0.0)),
    ("bocca_dx",     "Bocca spostata a destra",    0.40, lambda b: b.get("mouthRight", 0.0)),
    ("naso",         "Naso arricciato",            0.40, lambda b: _media(b, "noseSneerLeft", "noseSneerRight")),
]

MODALITA = ["Tieni premuto", "Premi una volta"]
AZIONE_PAUSA = "** Pausa / Riprendi **"
DURATA_TAP = 0.08           # secondi di pressione per "Premi una volta"
FOTOGRAMMI_CONFERMA = 2     # fotogrammi di fila prima di attivare/disattivare
ISTERESI = 0.7              # si spegne quando scende sotto soglia * ISTERESI
SCELTE_FPS = [10, 15, 20, 30]

# marchio messo sui clic inviati dal programma, per riconoscerli nel hook
MARCHIO_MIO = 0x46414343

# ----------------------------------------------------------------------
#  TASTI DISPONIBILI   nome mostrato -> (tipo, tasto pynput, nome pydirectinput)
#  tipo: "k" tastiera, "m" mouse, "p" azione interna (pausa)
# ----------------------------------------------------------------------

def _tabella_tasti():
    from pynput.keyboard import Key
    from pynput.mouse import Button
    t = {"Nessuno": None, AZIONE_PAUSA: ("p", None, None)}
    speciali = [
        ("Freccia su", Key.up, "up"), ("Freccia giu'", Key.down, "down"),
        ("Freccia sinistra", Key.left, "left"), ("Freccia destra", Key.right, "right"),
        ("Spazio", Key.space, "space"), ("Invio", Key.enter, "enter"),
        ("Esc", Key.esc, "esc"), ("Tab", Key.tab, "tab"),
        ("Shift", Key.shift, "shift"), ("Ctrl", Key.ctrl, "ctrl"), ("Alt", Key.alt, "alt"),
        ("Backspace", Key.backspace, "backspace"),
    ]
    for nome, k, pdi in speciali:
        t[nome] = ("k", k, pdi)
    t["Clic sinistro mouse"] = ("m", Button.left, None)
    t["Clic destro mouse"] = ("m", Button.right, None)
    for c in "abcdefghijklmnopqrstuvwxyz":
        t["Lettera " + c.upper()] = ("k", c, c)
    for c in "0123456789":
        t["Numero " + c] = ("k", c, c)
    for i in range(1, 13):
        t["F%d" % i] = ("k", getattr(Key, "f%d" % i), "f%d" % i)
    return t


TASTI_FRECCE = ["Freccia su", "Freccia giu'", "Freccia sinistra", "Freccia destra"]


def invia_mouse_win(sinistro, giu):
    """Invia un pulsante del mouse su Windows con il nostro marchio, cosi'
    il hook di Mouse -> Frecce lo lascia passare."""
    import ctypes
    from ctypes import wintypes
    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

    if sinistro:
        flag = 0x0002 if giu else 0x0004     # LEFTDOWN / LEFTUP
    else:
        flag = 0x0008 if giu else 0x0010     # RIGHTDOWN / RIGHTUP
    inp = INPUT(0, MOUSEINPUT(0, 0, 0, flag, 0, MARCHIO_MIO))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


class Tastiera:
    """Preme e rilascia tasti. Su Windows usa pydirectinput se c'e' (meglio
    per i giochi), altrimenti pynput."""

    def __init__(self):
        from pynput.keyboard import Controller as KC
        from pynput.mouse import Controller as MC
        from pynput.mouse import Button
        self.kb = KC()
        self.mouse = MC()
        self.Button = Button
        self.tabella = _tabella_tasti()
        self.pdi = None
        if WINDOWS:
            try:
                import pydirectinput
                pydirectinput.PAUSE = 0
                self.pdi = pydirectinput
            except ImportError:
                pass

    def nomi(self):
        return list(self.tabella.keys())

    def _mouse(self, bottone, giu):
        if WINDOWS:
            try:
                invia_mouse_win(bottone == self.Button.left, giu)
                return
            except Exception:
                pass
        if giu:
            self.mouse.press(bottone)
        else:
            self.mouse.release(bottone)

    def premi(self, nome):
        v = self.tabella.get(nome)
        if not v or v[0] == "p":
            return
        tipo, k, pdi = v
        if tipo == "m":
            self._mouse(k, True)
        elif self.pdi and pdi:
            self.pdi.keyDown(pdi)
        else:
            self.kb.press(k)

    def rilascia(self, nome):
        v = self.tabella.get(nome)
        if not v or v[0] == "p":
            return
        tipo, k, pdi = v
        try:
            if tipo == "m":
                self._mouse(k, False)
            elif self.pdi and pdi:
                self.pdi.keyUp(pdi)
            else:
                self.kb.release(k)
        except Exception:
            pass

    def sblocca_tutto(self):
        """Rilascia OGNI tasto e pulsante conosciuto, premuto o no: serve per
        sbloccare il computer se qualcosa e' rimasto premuto."""
        for nome, v in self.tabella.items():
            if not v or v[0] == "p":
                continue
            tipo, k, pdi = v
            try:
                if tipo == "m":
                    self._mouse(k, False)
                else:
                    self.kb.release(k)
                    if self.pdi and pdi:
                        self.pdi.keyUp(pdi)
            except Exception:
                pass


# ----------------------------------------------------------------------
#  MOTORE VISO: decide quando un'espressione e' "attiva" e preme i tasti
# ----------------------------------------------------------------------

class Motore:
    def __init__(self, tastiera, impostazioni):
        self.tastiera = tastiera
        self.imp = impostazioni
        self.attive = {}          # id -> True se l'espressione e' attiva ora
        self.contatori = {}       # id -> fotogrammi consecutivi sopra/sotto soglia
        self.tenuti = {}          # id -> nome del tasto tenuto premuto
        self.in_pausa = False
        self.chiuso = False       # True durante la chiusura: non preme piu' nulla
        self.al_cambio_pausa = None   # callback (es. per il mouse)

    def aggiorna(self, valori):
        """valori: dict id -> punteggio 0..1 (vuoto = nessuna faccia)."""
        for eid, nome, _soglia_def, _fn in ESPRESSIONI:
            cfg = self.imp["espressioni"][eid]
            soglia = float(cfg["soglia"])
            v = valori.get(eid, 0.0)
            attiva = self.attive.get(eid, False)
            if not attiva:
                sopra = v >= soglia
                self.contatori[eid] = self.contatori.get(eid, 0) + 1 if sopra else 0
                if self.contatori[eid] >= FOTOGRAMMI_CONFERMA:
                    self.contatori[eid] = 0
                    self.attive[eid] = True
                    self._attivata(eid, cfg)
            else:
                sotto = v < soglia * ISTERESI
                self.contatori[eid] = self.contatori.get(eid, 0) + 1 if sotto else 0
                if self.contatori[eid] >= FOTOGRAMMI_CONFERMA:
                    self.contatori[eid] = 0
                    self.attive[eid] = False
                    self._disattivata(eid)

    def _attivata(self, eid, cfg):
        if self.chiuso:
            return
        tasto = cfg["tasto"]
        if tasto == AZIONE_PAUSA:
            # funziona anche quando e' in pausa: e' il modo per riprendere
            self.pausa(not self.in_pausa)
            return
        if self.in_pausa or tasto == "Nessuno":
            return
        if cfg["modalita"] == "Premi una volta":
            self.tastiera.premi(tasto)
            time.sleep(DURATA_TAP)
            self.tastiera.rilascia(tasto)
        else:
            self.tastiera.premi(tasto)
            self.tenuti[eid] = tasto

    def _disattivata(self, eid):
        tasto = self.tenuti.pop(eid, None)
        if tasto:
            self.tastiera.rilascia(tasto)

    def rilascia_tutto(self):
        for eid in list(self.tenuti):
            self._disattivata(eid)

    def pausa(self, valore):
        self.in_pausa = valore
        if valore:
            self.rilascia_tutto()
        if self.al_cambio_pausa:
            try:
                self.al_cambio_pausa(valore)
            except Exception:
                pass

    def chiudi(self):
        self.chiuso = True
        self.rilascia_tutto()
        self.tastiera.sblocca_tutto()


# ----------------------------------------------------------------------
#  MOTORE MOUSE -> FRECCE (logica pura, senza Windows)
# ----------------------------------------------------------------------

class MotoreMouse:
    """Riceve gli eventi del tasto sinistro e del movimento; tiene premute le
    frecce. Metodi: giu(x, y) -> True se il clic va catturato;
    muovi(x, y); su() -> True se va mandato un clic normale."""

    def __init__(self, tastiera, impostazioni):
        self.tastiera = tastiera
        self.imp = impostazioni
        self.in_corso = False      # tasto sinistro catturato e tenuto
        self.in_frecce = False     # il trascinamento e' diventato frecce
        self.start = (0, 0)
        self.tenuti = set()
        self.in_pausa = False

    @property
    def cfg(self):
        return self.imp["mouse"]

    def attivo(self):
        return bool(self.cfg["attivo"]) and not self.in_pausa

    def giu(self, x, y):
        if not self.attivo():
            return False
        self.in_corso = True
        self.in_frecce = False
        self.start = (x, y)
        return True

    def muovi(self, x, y):
        if not self.in_corso:
            return
        dx = x - self.start[0]
        dy = y - self.start[1]
        dist = (dx * dx + dy * dy) ** 0.5
        voluti = set()
        if dist >= float(self.cfg["zona_morta"]):
            self.in_frecce = True
            t = self.cfg["tasti"]
            if self.cfg["diagonali"]:
                soglia = dist * 0.383      # 8 settori da 45 gradi
                if dy <= -soglia:
                    voluti.add(t["su"])
                if dy >= soglia:
                    voluti.add(t["giu"])
                if dx <= -soglia:
                    voluti.add(t["sinistra"])
                if dx >= soglia:
                    voluti.add(t["destra"])
            else:
                if abs(dx) > abs(dy):
                    voluti.add(t["destra"] if dx > 0 else t["sinistra"])
                else:
                    voluti.add(t["giu"] if dy > 0 else t["su"])
        voluti.discard("Nessuno")
        self._applica(voluti)

    def su(self):
        if not self.in_corso:
            return False
        self.in_corso = False
        self._applica(set())
        return not self.in_frecce      # clic normale da mandare

    def _applica(self, voluti):
        for tasto in list(self.tenuti):
            if tasto not in voluti:
                self.tastiera.rilascia(tasto)
                self.tenuti.discard(tasto)
        for tasto in voluti:
            if tasto not in self.tenuti:
                self.tastiera.premi(tasto)
                self.tenuti.add(tasto)

    def rilascia(self):
        self.in_corso = False
        self.in_frecce = False
        self._applica(set())

    def pausa(self, valore):
        self.in_pausa = valore
        if valore:
            self.rilascia()


class HookMouse:
    """Collega MotoreMouse al mouse vero di Windows (hook di basso livello)."""

    def __init__(self, motore_mouse, tastiera):
        self.mm = motore_mouse
        self.tastiera = tastiera
        self.rett = None          # (x, y, larghezza, altezza) della nostra finestra
        self.listener = None
        self.errore = None

    def disponibile(self):
        return WINDOWS

    def sopra_finestra(self, x, y):
        r = self.rett
        return bool(r) and r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]

    def avvia(self):
        if not WINDOWS:
            return
        try:
            from pynput import mouse
        except Exception as e:
            self.errore = str(e)
            return
        WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
        mm = self.mm

        def filtro(msg, data):
            if msg not in (WM_LBUTTONDOWN, WM_LBUTTONUP):
                return True
            if data.dwExtraInfo == MARCHIO_MIO:
                return True                   # e' un clic nostro: passa
            if msg == WM_LBUTTONDOWN:
                if mm.in_corso or self.sopra_finestra(data.pt.x, data.pt.y):
                    return True
                if mm.giu(data.pt.x, data.pt.y):
                    self.listener.suppress_event()
                return True
            # WM_LBUTTONUP
            if mm.in_corso:
                if mm.su():
                    self._clic_normale()
                self.listener.suppress_event()
            return True

        def al_movimento(x, y, *_):
            if mm.in_corso:
                mm.muovi(x, y)

        self.listener = mouse.Listener(on_move=al_movimento, win32_event_filter=filtro)
        self.listener.daemon = True
        self.listener.start()

    def _clic_normale(self):
        try:
            invia_mouse_win(True, True)
            invia_mouse_win(True, False)
        except Exception:
            pass

    def ferma(self):
        self.mm.rilascia()
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass


# ----------------------------------------------------------------------
#  IMPOSTAZIONI (salvate in impostazioni.json)
# ----------------------------------------------------------------------

def impostazioni_predefinite():
    return {
        "webcam": 0,
        "fps": 15,
        "anteprima": True,
        "espressioni": {
            eid: {"tasto": "Nessuno", "modalita": MODALITA[0], "soglia": soglia}
            for eid, _n, soglia, _f in ESPRESSIONI
        },
        "mouse": {
            "attivo": True,
            "zona_morta": 25,
            "diagonali": False,
            "tasti": {"su": "Freccia su", "giu": "Freccia giu'",
                      "sinistra": "Freccia sinistra", "destra": "Freccia destra"},
        },
    }


def carica_impostazioni():
    imp = impostazioni_predefinite()
    try:
        with open(FILE_IMPOSTAZIONI, "r", encoding="utf-8") as f:
            salvate = json.load(f)
        imp["webcam"] = int(salvate.get("webcam", 0))
        imp["fps"] = int(salvate.get("fps", imp["fps"]))
        imp["anteprima"] = bool(salvate.get("anteprima", True))
        for eid, cfg in salvate.get("espressioni", {}).items():
            if eid in imp["espressioni"] and isinstance(cfg, dict):
                imp["espressioni"][eid].update(cfg)
        m = salvate.get("mouse", {})
        if isinstance(m, dict):
            for k in ("attivo", "zona_morta", "diagonali"):
                if k in m:
                    imp["mouse"][k] = m[k]
            if isinstance(m.get("tasti"), dict):
                imp["mouse"]["tasti"].update(m["tasti"])
    except (OSError, ValueError):
        pass
    if imp["fps"] not in SCELTE_FPS:
        imp["fps"] = 15
    return imp


def salva_impostazioni(imp):
    try:
        with open(FILE_IMPOSTAZIONI, "w", encoding="utf-8") as f:
            json.dump(imp, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def scarica_modello(stato=None):
    if os.path.exists(FILE_MODELLO) and os.path.getsize(FILE_MODELLO) > 1_000_000:
        return
    if stato:
        stato("Scarico il modello per il riconoscimento del viso (3,7 MB)...")
    tmp = FILE_MODELLO + ".parziale"
    urllib.request.urlretrieve(URL_MODELLO, tmp)
    os.replace(tmp, FILE_MODELLO)


def alza_priorita():
    """Su Windows chiede al sistema di dare precedenza a questo programma,
    cosi' continua a vedere il viso anche con un gioco pesante aperto."""
    if not WINDOWS:
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00008000)  # ABOVE_NORMAL
    except Exception:
        pass


def proteggi_chiusura(funzione):
    """Qualunque cosa chiuda il programma (X della finestra, chiusura della
    console, spegnimento), prima rilascia tutti i tasti."""
    import atexit
    import signal
    atexit.register(funzione)
    for nome in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, nome, None)
        if sig is not None:
            try:
                signal.signal(sig, lambda *_: (funzione(), os._exit(0)))
            except Exception:
                pass
    if WINDOWS:
        try:
            import ctypes
            HANDLER = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)

            def gestore(evento):
                funzione()
                return 0
            proteggi_chiusura._gestore = HANDLER(gestore)   # evita il garbage collector
            ctypes.windll.kernel32.SetConsoleCtrlHandler(proteggi_chiusura._gestore, 1)
        except Exception:
            pass


# ----------------------------------------------------------------------
#  ELENCO DELLE WEBCAM
# ----------------------------------------------------------------------

MAX_WEBCAM = 6


def elenca_webcam(cv2):
    """Ritorna una lista di (indice, nome). Su Windows prova a leggere i nomi
    veri con pygrabber (stesso ordine di DirectShow usato da OpenCV);
    altrimenti prova ad aprire le webcam una per una."""
    if WINDOWS:
        try:
            from pygrabber.dshow_graph import FilterGraph
            nomi = FilterGraph().get_input_devices()
            if nomi:
                return [(i, n) for i, n in enumerate(nomi)]
        except Exception:
            pass
    trovate = []
    for i in range(MAX_WEBCAM):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if WINDOWS else cv2.VideoCapture(i)
        ok = cap.isOpened()
        cap.release()
        if ok:
            trovate.append((i, "Webcam %d" % i))
    return trovate


# ----------------------------------------------------------------------
#  WEBCAM + RICONOSCIMENTO (gira in un thread separato)
# ----------------------------------------------------------------------

class Riconoscitore(threading.Thread):
    def __init__(self, imp, motore):
        super().__init__(daemon=True)
        self.imp = imp
        self.motore = motore
        self.valori = {}           # ultimi punteggi 0..1 per espressione
        self.anteprima = None      # ultimo fotogramma RGB specchiato (piccolo)
        self.faccia = False
        self.messaggio = "Avvio..."
        self.fps_reali = 0.0
        self.lock = threading.Lock()
        self.fermati = False
        self.riavvia_webcam = False
        self.elenco = None         # [(indice, nome)] delle webcam trovate

    def run(self):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision

        try:
            scarica_modello(self._stato)
        except Exception as e:
            self._stato("ERRORE: non riesco a scaricare il modello. Controlla la connessione.\n%s" % e)
            return

        opzioni = vision.FaceLandmarkerOptions(
            base_options=mpp.BaseOptions(model_asset_path=FILE_MODELLO),
            output_face_blendshapes=True,
            num_faces=1,
            running_mode=vision.RunningMode.VIDEO,
        )
        landmarker = vision.FaceLandmarker.create_from_options(opzioni)

        self._stato("Cerco le webcam collegate...")
        try:
            elenco = elenca_webcam(cv2)
        except Exception:
            elenco = []
        if not elenco:
            elenco = [(i, "Webcam %d" % i) for i in range(3)]
        with self.lock:
            self.elenco = elenco

        cap = None
        t0 = time.monotonic()
        ultimo_ts = 0
        ultimo_elaborato = 0.0
        conta = 0
        conta_t = time.monotonic()

        while not self.fermati:
            if cap is None or self.riavvia_webcam:
                self.riavvia_webcam = False
                if cap is not None:
                    cap.release()
                cap = self._apri_webcam(cv2, int(self.imp["webcam"]))
                if cap is None:
                    # quella salvata non va: provo le altre
                    scelta = int(self.imp["webcam"])
                    for idx, _nome in elenco:
                        if idx == scelta:
                            continue
                        cap = self._apri_webcam(cv2, idx)
                        if cap is not None:
                            self.imp["webcam"] = idx
                            salva_impostazioni(self.imp)
                            break
                if cap is None:
                    self._stato("Nessuna webcam disponibile. Collegane una o chiudi il programma che la sta usando.")
                    time.sleep(2.0)
                    continue
                self._stato("Uso: " + self.nome_webcam(int(self.imp["webcam"])))

            # prendo sempre l'ultimo fotogramma (cosi' non si accumula ritardo)
            # ma lo analizzo solo alla cadenza scelta: meno lavoro per il processore
            if not cap.grab():
                self._stato("La webcam non manda immagini...")
                time.sleep(0.2)
                continue
            adesso = time.monotonic()
            intervallo = 1.0 / max(1, int(self.imp.get("fps", 15)))
            if adesso - ultimo_elaborato < intervallo:
                time.sleep(0.004)
                continue
            ultimo_elaborato = adesso
            ok, frame = cap.retrieve()
            if not ok:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ts = int((adesso - t0) * 1000)
            if ts <= ultimo_ts:
                ts = ultimo_ts + 1
            ultimo_ts = ts
            ris = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)

            valori = {}
            faccia = bool(ris.face_blendshapes)
            if faccia:
                b = {c.category_name: c.score for c in ris.face_blendshapes[0]}
                for eid, _n, _s, fn in ESPRESSIONI:
                    try:
                        valori[eid] = float(fn(b))
                    except Exception:
                        valori[eid] = 0.0

            self.motore.aggiorna(valori)

            conta += 1
            if adesso - conta_t >= 1.0:
                self.fps_reali = conta / (adesso - conta_t)
                conta, conta_t = 0, adesso

            piccolo = None
            if self.imp.get("anteprima", True):
                piccolo = cv2.flip(cv2.resize(rgb, (320, 240)), 1)   # come uno specchio
            with self.lock:
                self.valori = valori
                self.faccia = faccia
                self.anteprima = piccolo

        if cap is not None:
            cap.release()
        try:
            landmarker.close()
        except Exception:
            pass
        self.motore.rilascia_tutto()

    def nome_webcam(self, idx):
        for i, n in (self.elenco or []):
            if i == idx:
                return n
        return "Webcam %d" % idx

    def _apri_webcam(self, cv2, idx):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if WINDOWS else cv2.VideoCapture(idx)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap

    def _stato(self, testo):
        with self.lock:
            self.messaggio = testo


# ----------------------------------------------------------------------
#  FINESTRA
# ----------------------------------------------------------------------

def avvia_finestra():
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk

    imp = carica_impostazioni()
    tastiera = Tastiera()
    tastiera.sblocca_tutto()        # se qualcosa era rimasto premuto, lo libera
    motore = Motore(tastiera, imp)
    mm = MotoreMouse(tastiera, imp)
    hook = HookMouse(mm, tastiera)
    motore.al_cambio_pausa = mm.pausa
    ric = Riconoscitore(imp, motore)
    alza_priorita()

    def spegni_tutto():
        motore.chiudi()
        mm.rilascia()

    proteggi_chiusura(spegni_tutto)

    root = tk.Tk()
    root.title("Faccia -> Tasti")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    stile = ttk.Style()
    try:
        stile.theme_use("vista" if WINDOWS else "clam")
    except tk.TclError:
        pass
    stile.configure("Verde.Horizontal.TProgressbar", background="#2e8b57")
    stile.configure("Grande.TButton", font=("Segoe UI", 13, "bold"), padding=8)

    # ================= colonna sinistra: anteprima e comandi =================
    sinistra = ttk.Frame(root, padding=10)
    sinistra.grid(row=0, column=0, sticky="n")
    riga = [0]

    def prossima():
        riga[0] += 1
        return riga[0]

    video = tk.Label(sinistra, width=320, height=240, bg="black")
    video.grid(row=0, column=0, columnspan=2, pady=(0, 6))

    lbl_stato = ttk.Label(sinistra, text="", wraplength=320, justify="center",
                          font=("Segoe UI", 10))
    lbl_stato.grid(row=prossima(), column=0, columnspan=2, pady=(0, 8))

    lbl_pausa = ttk.Label(sinistra, text="", font=("Segoe UI", 12, "bold"))
    lbl_pausa.grid(row=prossima(), column=0, columnspan=2)

    def aggiorna_pausa():
        if motore.in_pausa:
            lbl_pausa.config(text="IN PAUSA - non preme nulla", foreground="#b00000")
            btn_pausa.config(text=">  RIPRENDI")
        else:
            lbl_pausa.config(text="IN FUNZIONE", foreground="#008000")
            btn_pausa.config(text="II  METTI IN PAUSA")

    stato_pausa = {"v": motore.in_pausa}

    def toggle_pausa():
        motore.pausa(not motore.in_pausa)
        stato_pausa["v"] = motore.in_pausa
        aggiorna_pausa()

    btn_pausa = ttk.Button(sinistra, command=toggle_pausa, style="Grande.TButton")
    btn_pausa.grid(row=prossima(), column=0, columnspan=2, sticky="ew", pady=(4, 10))
    aggiorna_pausa()

    # --- webcam
    ttk.Label(sinistra, text="Webcam da usare:").grid(row=prossima(), column=0, columnspan=2,
                                                        sticky="w", pady=(0, 2))
    var_cam = tk.StringVar(value="Cerco le webcam...")
    cb_cam = ttk.Combobox(sinistra, textvariable=var_cam, state="readonly", width=38)
    cb_cam.grid(row=prossima(), column=0, columnspan=2, sticky="ew")
    voci_cam = {}      # testo mostrato -> indice

    def scelta_cam(*_):
        idx = voci_cam.get(var_cam.get())
        if idx is None or idx == int(imp["webcam"]):
            return
        imp["webcam"] = idx
        salva_impostazioni(imp)
        ric.riavvia_webcam = True

    cb_cam.bind("<<ComboboxSelected>>", scelta_cam)

    def aggiorna_elenco_cam(elenco):
        voci_cam.clear()
        for idx, nome in elenco:
            voci_cam["%s  (n. %d)" % (nome, idx)] = idx
        cb_cam["values"] = list(voci_cam.keys())
        for testo, idx in voci_cam.items():
            if idx == int(imp["webcam"]):
                var_cam.set(testo)
                break
        else:
            var_cam.set("Webcam %d non trovata" % int(imp["webcam"]))

    # --- leggerezza: anteprima e fotogrammi al secondo
    var_ant = tk.BooleanVar(value=bool(imp["anteprima"]))

    def cambia_ant():
        imp["anteprima"] = bool(var_ant.get())
        salva_impostazioni(imp)
        if not imp["anteprima"]:
            video.config(image="")
            foto["img"] = None

    ttk.Checkbutton(sinistra, text="Mostra l'anteprima della webcam (toglila per alleggerire)",
                    variable=var_ant, command=cambia_ant).grid(
        row=prossima(), column=0, columnspan=2, sticky="w", pady=(8, 0))

    riga_fps = ttk.Frame(sinistra)
    riga_fps.grid(row=prossima(), column=0, columnspan=2, sticky="w", pady=(4, 0))
    ttk.Label(riga_fps, text="Analisi del viso al secondo:").pack(side="left")
    var_fps = tk.StringVar(value=str(imp["fps"]))
    cb_fps = ttk.Combobox(riga_fps, textvariable=var_fps, state="readonly", width=4,
                          values=[str(v) for v in SCELTE_FPS])
    cb_fps.pack(side="left", padx=(6, 6))
    lbl_fps = ttk.Label(riga_fps, text="", foreground="#555")
    lbl_fps.pack(side="left")

    def cambia_fps(*_):
        imp["fps"] = int(var_fps.get())
        salva_impostazioni(imp)

    cb_fps.bind("<<ComboboxSelected>>", cambia_fps)
    ttk.Label(sinistra, foreground="#555", wraplength=320, justify="left",
              text="Meno analisi al secondo = programma piu' leggero ma un po' meno pronto. "
                   "10 o 15 vanno bene per la maggior parte dei giochi.").grid(
        row=prossima(), column=0, columnspan=2, sticky="w")

    def sblocca():
        motore.rilascia_tutto()
        mm.rilascia()
        tastiera.sblocca_tutto()

    ttk.Button(sinistra, text="Sblocca tutti i tasti (se qualcosa resta premuto)",
               command=sblocca).grid(row=prossima(), column=0, columnspan=2, sticky="ew", pady=(12, 4))
    ttk.Button(sinistra, text="Esci dal programma",
               command=lambda: chiudi()).grid(row=prossima(), column=0, columnspan=2,
                                              sticky="ew", pady=(4, 0))

    # ================= colonna destra: espressioni =================
    destra = ttk.Frame(root, padding=10)
    destra.grid(row=0, column=1, sticky="n")

    ttk.Label(destra, text="ESPRESSIONI DEL VISO", font=("Segoe UI", 11, "bold")).grid(
        row=0, column=0, columnspan=5, sticky="w", pady=(0, 6))
    intestazioni = ["Espressione", "Quanto la vedo", "Soglia", "Tasto da premere", "Come"]
    for c, testo in enumerate(intestazioni):
        ttk.Label(destra, text=testo, font=("Segoe UI", 9, "bold")).grid(
            row=1, column=c, padx=4, pady=(0, 4), sticky="w")

    barre = {}
    etichette = {}
    nomi_tasti = tastiera.nomi()

    def fai_salvatore(eid, var_tasto, var_mod, var_soglia):
        def salva(*_):
            cfg = imp["espressioni"][eid]
            vecchio = cfg["tasto"]
            cfg["tasto"] = var_tasto.get()
            cfg["modalita"] = var_mod.get()
            cfg["soglia"] = round(float(var_soglia.get()), 2)
            if vecchio != cfg["tasto"] and eid in motore.tenuti:
                motore._disattivata(eid)
            salva_impostazioni(imp)
        return salva

    for r, (eid, nome, _s, _f) in enumerate(ESPRESSIONI, start=2):
        cfg = imp["espressioni"][eid]
        et = ttk.Label(destra, text=nome, width=26)
        et.grid(row=r, column=0, padx=4, pady=2, sticky="w")
        etichette[eid] = et

        barra = ttk.Progressbar(destra, length=120, maximum=100,
                                style="Verde.Horizontal.TProgressbar")
        barra.grid(row=r, column=1, padx=4, pady=2)
        barre[eid] = barra

        var_soglia = tk.DoubleVar(value=float(cfg["soglia"]))
        var_tasto = tk.StringVar(value=cfg["tasto"] if cfg["tasto"] in nomi_tasti else "Nessuno")
        var_mod = tk.StringVar(value=cfg["modalita"] if cfg["modalita"] in MODALITA else MODALITA[0])
        salva = fai_salvatore(eid, var_tasto, var_mod, var_soglia)

        ttk.Scale(destra, from_=0.1, to=0.95, variable=var_soglia, length=110,
                  command=salva).grid(row=r, column=2, padx=4, pady=2)
        cb = ttk.Combobox(destra, values=nomi_tasti, textvariable=var_tasto,
                          state="readonly", width=20)
        cb.grid(row=r, column=3, padx=4, pady=2)
        cb.bind("<<ComboboxSelected>>", salva)
        cm = ttk.Combobox(destra, values=MODALITA, textvariable=var_mod,
                          state="readonly", width=15)
        cm.grid(row=r, column=4, padx=4, pady=2)
        cm.bind("<<ComboboxSelected>>", salva)

    r = len(ESPRESSIONI) + 2
    ttk.Label(destra, foreground="#555", wraplength=640, justify="left",
              text=("Soglia: quanto deve essere forte l'espressione per scattare "
                    "(trascina verso sinistra = piu' sensibile). "
                    "Consiglio: assegna '" + AZIONE_PAUSA + "' a un'espressione per "
                    "fermare e riprendere tutto anche dentro un gioco a schermo intero.")
              ).grid(row=r, column=0, columnspan=5, pady=(8, 0), sticky="w")

    # ================= sezione MOUSE -> FRECCE =================
    r += 1
    ttk.Separator(destra, orient="horizontal").grid(row=r, column=0, columnspan=5,
                                                     sticky="ew", pady=10)
    r += 1
    ttk.Label(destra, text="MOUSE -> FRECCE", font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=5, sticky="w")
    r += 1
    ttk.Label(destra, foreground="#555", wraplength=640, justify="left",
              text=("Tieni premuto il tasto sinistro e sposta il puntatore: in alto tiene "
                    "premuta la freccia su, in basso giu', a destra destra, a sinistra "
                    "sinistra. Torna vicino al punto di partenza per rilasciare. "
                    "Un clic veloce resta un clic normale.")).grid(
        row=r, column=0, columnspan=5, sticky="w", pady=(2, 6))

    cm_cfg = imp["mouse"]
    var_m_attivo = tk.BooleanVar(value=bool(cm_cfg["attivo"]))
    var_m_diag = tk.BooleanVar(value=bool(cm_cfg["diagonali"]))
    var_m_zona = tk.DoubleVar(value=float(cm_cfg["zona_morta"]))
    var_m_tasti = {k: tk.StringVar(value=v if v in nomi_tasti else "Nessuno")
                   for k, v in cm_cfg["tasti"].items()}

    def salva_mouse(*_):
        cm_cfg["attivo"] = bool(var_m_attivo.get())
        cm_cfg["diagonali"] = bool(var_m_diag.get())
        cm_cfg["zona_morta"] = int(round(float(var_m_zona.get())))
        for k, var in var_m_tasti.items():
            cm_cfg["tasti"][k] = var.get()
        if not cm_cfg["attivo"]:
            mm.rilascia()
        else:
            mm._applica(set())      # tasti cambiati: rilascia quelli vecchi
        lbl_zona.config(text="%d px" % cm_cfg["zona_morta"])
        salva_impostazioni(imp)
        aggiorna_stato_mouse()

    r += 1
    chk_attivo = ttk.Checkbutton(destra, text="Attiva Mouse -> Frecce",
                                 variable=var_m_attivo, command=salva_mouse)
    chk_attivo.grid(row=r, column=0, columnspan=2, sticky="w")
    lbl_mouse = ttk.Label(destra, text="", font=("Segoe UI", 10, "bold"))
    lbl_mouse.grid(row=r, column=2, columnspan=3, sticky="w")

    r += 1
    riga_z = ttk.Frame(destra)
    riga_z.grid(row=r, column=0, columnspan=5, sticky="w", pady=(4, 0))
    ttk.Label(riga_z, text="Spostamento minimo prima che parta una freccia:").pack(side="left")
    ttk.Scale(riga_z, from_=10, to=120, variable=var_m_zona, length=140,
              command=salva_mouse).pack(side="left", padx=6)
    lbl_zona = ttk.Label(riga_z, text="%d px" % int(cm_cfg["zona_morta"]), width=7)
    lbl_zona.pack(side="left")
    ttk.Checkbutton(riga_z, text="Diagonali (due frecce insieme)",
                    variable=var_m_diag, command=salva_mouse).pack(side="left", padx=(16, 0))

    r += 1
    riga_t = ttk.Frame(destra)
    riga_t.grid(row=r, column=0, columnspan=5, sticky="w", pady=(6, 0))
    for k, etich in (("su", "In alto:"), ("giu", "In basso:"),
                     ("sinistra", "A sinistra:"), ("destra", "A destra:")):
        ttk.Label(riga_t, text=etich).pack(side="left", padx=(0, 3))
        c = ttk.Combobox(riga_t, values=nomi_tasti, textvariable=var_m_tasti[k],
                         state="readonly", width=16)
        c.pack(side="left", padx=(0, 10))
        c.bind("<<ComboboxSelected>>", salva_mouse)

    def aggiorna_stato_mouse():
        if not hook.disponibile():
            lbl_mouse.config(text="non disponibile (solo Windows)", foreground="#b00000")
            chk_attivo.state(["disabled"])
        elif hook.errore:
            lbl_mouse.config(text="errore: " + hook.errore[:60], foreground="#b00000")
        elif not cm_cfg["attivo"]:
            lbl_mouse.config(text="spento: il mouse funziona normalmente", foreground="#555")
        elif motore.in_pausa:
            lbl_mouse.config(text="in pausa", foreground="#b00000")
        else:
            lbl_mouse.config(text="acceso", foreground="#008000")

    # ================= aggiornamento periodico =================
    foto = {"img": None}
    stato_cam = {"elenco": None, "idx": None}

    def aggiorna():
        if motore.in_pausa != stato_pausa["v"]:      # pausa cambiata dal viso
            stato_pausa["v"] = motore.in_pausa
            aggiorna_pausa()
        aggiorna_stato_mouse()
        try:
            hook.rett = (root.winfo_rootx(), root.winfo_rooty(),
                         root.winfo_width(), root.winfo_height())
        except Exception:
            pass
        with ric.lock:
            valori = dict(ric.valori)
            faccia = ric.faccia
            ant = ric.anteprima
            msg = ric.messaggio
            elenco = ric.elenco
            fps_reali = ric.fps_reali
        if elenco is not None and (elenco != stato_cam["elenco"]
                                   or int(imp["webcam"]) != stato_cam["idx"]):
            stato_cam["elenco"] = elenco
            stato_cam["idx"] = int(imp["webcam"])
            aggiorna_elenco_cam(elenco)
        if ant is not None and imp["anteprima"]:
            foto["img"] = ImageTk.PhotoImage(Image.fromarray(ant))
            video.config(image=foto["img"])
        testo = msg
        if elenco is not None:
            testo += "\n" + ("Viso riconosciuto" if faccia else "Nessun viso in vista")
        lbl_stato.config(text=testo)
        lbl_fps.config(text="(ora: %.0f)" % fps_reali if fps_reali else "")
        for eid, _n, _s, _f in ESPRESSIONI:
            barre[eid]["value"] = int(valori.get(eid, 0.0) * 100)
            attiva = motore.attive.get(eid, False)
            etichette[eid].config(foreground="#008000" if attiva else "black",
                                  font=("Segoe UI", 10, "bold" if attiva else "normal"))
        root.after(100, aggiorna)

    def chiudi():
        motore.chiuso = True
        ric.fermati = True
        hook.ferma()
        motore.rilascia_tutto()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", chiudi)
    ric.start()
    hook.avvia()
    aggiorna_stato_mouse()
    root.after(100, aggiorna)
    root.mainloop()
    motore.chiuso = True
    ric.fermati = True
    hook.ferma()
    ric.join(3.0)
    spegni_tutto()


if __name__ == "__main__":
    senza_console = sys.stdout is None or sys.stderr is None
    if senza_console:
        # avviato con pythonw: niente finestra nera, gli errori vanno su file
        log = open(FILE_ERRORI, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    try:
        avvia_finestra()
    except Exception:
        import traceback
        testo = traceback.format_exc()
        print(testo)
        try:
            import tkinter.messagebox as mb
            mb.showerror("Faccia -> Tasti: errore",
                         "Si e' verificato un errore. I dettagli sono nel file errori.txt "
                         "nella cartella del programma.\n\n" + testo[-800:])
        except Exception:
            pass
        sys.exit(1)
