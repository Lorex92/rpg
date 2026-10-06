# -*- coding: utf-8 -*-
"""
FACCIA -> TASTI   (versione 1.0)

Apre la webcam, riconosce le espressioni del viso e per ognuna preme un tasto
della tastiera (o un clic del mouse) a tua scelta. Tutto si configura con il
mouse dalla finestra del programma.

Richiede Python 3 e le librerie elencate in requirements.txt
(si installano con installa.bat). Istruzioni complete in LEGGIMI.md
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
URL_MODELLO = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
               "face_landmarker/float16/1/face_landmarker.task")

# ----------------------------------------------------------------------
#  ESPRESSIONI RICONOSCIUTE
#  (id interno, nome mostrato, soglia iniziale, funzione che calcola 0..1)
#  b = punteggi di MediaPipe (0..1),  t = dati sulla posizione della testa
# ----------------------------------------------------------------------

def _media(b, *nomi):
    return sum(b.get(n, 0.0) for n in nomi) / len(nomi)

ESPRESSIONI = [
    ("bocca_aperta",   "Bocca aperta",                    0.40, lambda b, t: b.get("jawOpen", 0.0)),
    ("sorriso",        "Sorriso",                         0.55, lambda b, t: _media(b, "mouthSmileLeft", "mouthSmileRight")),
    ("sopracciglia",   "Sopracciglia alzate",             0.50, lambda b, t: b.get("browInnerUp", 0.0)),
    ("accigliato",     "Sopracciglia abbassate",          0.60, lambda b, t: _media(b, "browDownLeft", "browDownRight")),
    ("bacio",          "Labbra in avanti (bacio)",        0.50, lambda b, t: b.get("mouthPucker", 0.0)),
    ("guance",         "Guance gonfie",                   0.40, lambda b, t: b.get("cheekPuff", 0.0)),
    ("occhio_sx",      "Occhiolino sinistro",             0.40, lambda b, t: max(0.0, b.get("eyeBlinkLeft", 0.0) - b.get("eyeBlinkRight", 0.0))),
    ("occhio_dx",      "Occhiolino destro",               0.40, lambda b, t: max(0.0, b.get("eyeBlinkRight", 0.0) - b.get("eyeBlinkLeft", 0.0))),
    ("occhi_chiusi",   "Entrambi gli occhi chiusi",       0.60, lambda b, t: min(b.get("eyeBlinkLeft", 0.0), b.get("eyeBlinkRight", 0.0))),
    ("bocca_sx",       "Bocca spostata a sinistra",       0.40, lambda b, t: b.get("mouthLeft", 0.0)),
    ("bocca_dx",       "Bocca spostata a destra",         0.40, lambda b, t: b.get("mouthRight", 0.0)),
    ("naso",           "Naso arricciato",                 0.40, lambda b, t: _media(b, "noseSneerLeft", "noseSneerRight")),
    ("testa_sx",       "Testa girata a sinistra",         0.50, lambda b, t: t.get("sx", 0.0)),
    ("testa_dx",       "Testa girata a destra",           0.50, lambda b, t: t.get("dx", 0.0)),
    ("testa_su",       "Testa alzata",                    0.50, lambda b, t: t.get("su", 0.0)),
    ("testa_giu",      "Testa abbassata",                 0.50, lambda b, t: t.get("giu", 0.0)),
]

MODALITA = ["Tieni premuto", "Premi una volta"]
AZIONE_PAUSA = "** Pausa / Riprendi **"
DURATA_TAP = 0.08   # secondi di pressione per "Premi una volta"

# ----------------------------------------------------------------------
#  TASTI DISPONIBILI   nome mostrato -> (tipo, tasto pynput, nome pydirectinput)
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


class Tastiera:
    """Preme e rilascia tasti. Su Windows usa pydirectinput se c'e' (meglio
    per i giochi), altrimenti pynput."""

    def __init__(self):
        from pynput.keyboard import Controller as KC
        from pynput.mouse import Controller as MC
        self.kb = KC()
        self.mouse = MC()
        self.tabella = _tabella_tasti()
        self.pdi = None
        if os.name == "nt":
            try:
                import pydirectinput
                pydirectinput.PAUSE = 0
                self.pdi = pydirectinput
            except ImportError:
                pass

    def nomi(self):
        return list(self.tabella.keys())

    def premi(self, nome):
        v = self.tabella.get(nome)
        if not v or v[0] == "p":
            return
        tipo, k, pdi = v
        if tipo == "m":
            self.mouse.press(k)
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
                self.mouse.release(k)
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
                    self.mouse.release(k)
                else:
                    self.kb.release(k)
                    if self.pdi and pdi:
                        self.pdi.keyUp(pdi)
            except Exception:
                pass


# ----------------------------------------------------------------------
#  MOTORE: decide quando un'espressione e' "attiva" e preme i tasti
# ----------------------------------------------------------------------

FOTOGRAMMI_CONFERMA = 3     # quanti fotogrammi di fila prima di attivare/disattivare
ISTERESI = 0.7              # si spegne quando scende sotto soglia * ISTERESI


class Motore:
    def __init__(self, tastiera, impostazioni):
        self.tastiera = tastiera
        self.imp = impostazioni
        self.attive = {}          # id -> True se l'espressione e' attiva ora
        self.contatori = {}       # id -> fotogrammi consecutivi sopra/sotto soglia
        self.tenuti = {}          # id -> nome del tasto tenuto premuto
        self.in_pausa = False
        self.chiuso = False       # True durante la chiusura: non preme piu' nulla

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

    def chiudi(self):
        self.chiuso = True
        self.rilascia_tutto()
        self.tastiera.sblocca_tutto()

    def pausa(self, valore):
        self.in_pausa = valore
        if valore:
            self.rilascia_tutto()


# ----------------------------------------------------------------------
#  POSIZIONE DELLA TESTA (dai punti del viso)
# ----------------------------------------------------------------------

AMPIEZZA_GIRO = 0.22   # spostamento del naso (in larghezze-viso) che vale 100%
AMPIEZZA_ALTO = 0.16


def misura_testa(punti):
    """Ritorna (rapporto_orizzontale, rapporto_verticale) del naso rispetto al
    centro del viso, in unita' di larghezza del viso."""
    naso = punti[1]
    sin, des = punti[234], punti[454]
    cx, cy = (sin.x + des.x) / 2, (sin.y + des.y) / 2
    larg = max(1e-6, ((sin.x - des.x) ** 2 + (sin.y - des.y) ** 2) ** 0.5)
    return (naso.x - cx) / larg, (naso.y - cy) / larg


def valori_testa(orizz, vert, neutro):
    """Trasforma le misure in 4 punteggi 0..1 (sx, dx, su, giu).
    Nell'immagine NON specchiata il lato destro della persona sta a sinistra:
    girare la testa a destra fa diminuire la x del naso."""
    o = orizz - neutro[0]
    v = vert - neutro[1]
    clip = lambda x: max(0.0, min(1.0, x))
    return {
        "sx": clip(o / AMPIEZZA_GIRO),
        "dx": clip(-o / AMPIEZZA_GIRO),
        "su": clip(-v / AMPIEZZA_ALTO),
        "giu": clip(v / AMPIEZZA_ALTO),
    }


# ----------------------------------------------------------------------
#  IMPOSTAZIONI (salvate in impostazioni.json)
# ----------------------------------------------------------------------

def impostazioni_predefinite():
    return {
        "webcam": 0,
        "neutro_testa": [0.0, 0.12],
        "espressioni": {
            eid: {"tasto": "Nessuno", "modalita": MODALITA[0], "soglia": soglia}
            for eid, _n, soglia, _f in ESPRESSIONI
        },
    }


def carica_impostazioni():
    imp = impostazioni_predefinite()
    try:
        with open(FILE_IMPOSTAZIONI, "r", encoding="utf-8") as f:
            salvate = json.load(f)
        imp["webcam"] = int(salvate.get("webcam", 0))
        imp["neutro_testa"] = list(salvate.get("neutro_testa", imp["neutro_testa"]))
        for eid, cfg in salvate.get("espressioni", {}).items():
            if eid in imp["espressioni"]:
                imp["espressioni"][eid].update(cfg)
    except (OSError, ValueError):
        pass
    return imp


def salva_impostazioni(imp):
    try:
        with open(FILE_IMPOSTAZIONI, "w", encoding="utf-8") as f:
            json.dump(imp, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def alza_priorita():
    """Su Windows chiede al sistema di dare precedenza a questo programma,
    cosi' continua a vedere il viso anche con un gioco pesante aperto."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00008000)  # ABOVE_NORMAL
    except Exception:
        pass


def proteggi_chiusura(motore):
    """Qualunque cosa chiuda il programma (X della finestra, chiusura della
    console, spegnimento), prima rilascia tutti i tasti."""
    import atexit
    import signal
    atexit.register(motore.chiudi)
    for nome in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, nome, None)
        if sig is not None:
            try:
                signal.signal(sig, lambda *_: (motore.chiudi(), os._exit(0)))
            except Exception:
                pass
    if os.name == "nt":
        try:
            import ctypes
            HANDLER = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)

            def gestore(evento):
                motore.chiudi()
                return 0
            proteggi_chiusura._gestore = HANDLER(gestore)   # evita il garbage collector
            ctypes.windll.kernel32.SetConsoleCtrlHandler(proteggi_chiusura._gestore, 1)
        except Exception:
            pass


def scarica_modello(stato=None):
    if os.path.exists(FILE_MODELLO) and os.path.getsize(FILE_MODELLO) > 1_000_000:
        return
    if stato:
        stato("Scarico il modello per il riconoscimento del viso (3,7 MB)...")
    tmp = FILE_MODELLO + ".parziale"
    urllib.request.urlretrieve(URL_MODELLO, tmp)
    os.replace(tmp, FILE_MODELLO)


# ----------------------------------------------------------------------
#  ELENCO DELLE WEBCAM
# ----------------------------------------------------------------------

MAX_WEBCAM = 6


def elenca_webcam(cv2):
    """Ritorna una lista di (indice, nome). Su Windows prova a leggere i nomi
    veri con pygrabber (stesso ordine di DirectShow usato da OpenCV);
    altrimenti prova ad aprire le webcam una per una."""
    if os.name == "nt":
        try:
            from pygrabber.dshow_graph import FilterGraph
            nomi = FilterGraph().get_input_devices()
            if nomi:
                return [(i, n) for i, n in enumerate(nomi)]
        except Exception:
            pass
    trovate = []
    for i in range(MAX_WEBCAM):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(i)
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
        self.lock = threading.Lock()
        self.fermati = False
        self.riavvia_webcam = False
        self.calibra = 0           # fotogrammi di calibrazione testa rimasti
        self._cal_acc = []
        self.elenco = None         # [(indice, nome)] delle webcam trovate

    def richiedi_calibrazione(self):
        self._cal_acc = []
        self.calibra = 30

    def run(self):
        import cv2
        import numpy as np
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
        if not self.imp.get("neutro_testa_calibrato"):
            self.richiedi_calibrazione()

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

            ok, frame = cap.read()
            if not ok:
                self._stato("La webcam non manda immagini...")
                time.sleep(0.2)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ts = int((time.monotonic() - t0) * 1000)
            if ts <= ultimo_ts:
                ts = ultimo_ts + 1
            ultimo_ts = ts
            ris = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)

            valori = {}
            faccia = bool(ris.face_blendshapes)
            if faccia:
                b = {c.category_name: c.score for c in ris.face_blendshapes[0]}
                orizz, vert = misura_testa(ris.face_landmarks[0])
                if self.calibra > 0:
                    self._cal_acc.append((orizz, vert))
                    self.calibra -= 1
                    if self.calibra == 0:
                        n = len(self._cal_acc)
                        self.imp["neutro_testa"] = [
                            sum(a for a, _ in self._cal_acc) / n,
                            sum(v for _, v in self._cal_acc) / n,
                        ]
                        self.imp["neutro_testa_calibrato"] = True
                        salva_impostazioni(self.imp)
                        self._stato("Posizione neutra della testa calibrata")
                t = valori_testa(orizz, vert, self.imp["neutro_testa"])
                for eid, _n, _s, fn in ESPRESSIONI:
                    try:
                        valori[eid] = float(fn(b, t))
                    except Exception:
                        valori[eid] = 0.0

            self.motore.aggiorna(valori)

            piccolo = cv2.resize(rgb, (320, 240))
            piccolo = cv2.flip(piccolo, 1)   # specchiato, come uno specchio
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
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(idx)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
    ric = Riconoscitore(imp, motore)
    alza_priorita()
    proteggi_chiusura(motore)

    root = tk.Tk()
    root.title("Faccia -> Tasti")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    stile = ttk.Style()
    try:
        stile.theme_use("vista" if os.name == "nt" else "clam")
    except tk.TclError:
        pass
    stile.configure("Verde.Horizontal.TProgressbar", background="#2e8b57")
    stile.configure("Grande.TButton", font=("Segoe UI", 13, "bold"), padding=8)

    # ---------- colonna sinistra: anteprima e comandi ----------
    sinistra = ttk.Frame(root, padding=10)
    sinistra.grid(row=0, column=0, sticky="n")

    video = tk.Label(sinistra, width=320, height=240, bg="black")
    video.grid(row=0, column=0, columnspan=2, pady=(0, 6))

    lbl_stato = ttk.Label(sinistra, text="", wraplength=320, justify="center",
                          font=("Segoe UI", 10))
    lbl_stato.grid(row=1, column=0, columnspan=2, pady=(0, 8))

    lbl_pausa = ttk.Label(sinistra, text="", font=("Segoe UI", 12, "bold"))
    lbl_pausa.grid(row=2, column=0, columnspan=2)

    def aggiorna_pausa():
        if motore.in_pausa:
            lbl_pausa.config(text="IN PAUSA - non preme nulla", foreground="#b00000")
            btn_pausa.config(text=">  RIPRENDI")
        else:
            lbl_pausa.config(text="IN FUNZIONE", foreground="#008000")
            btn_pausa.config(text="II  METTI IN PAUSA")

    def toggle_pausa():
        motore.pausa(not motore.in_pausa)
        stato_pausa["v"] = motore.in_pausa
        aggiorna_pausa()

    btn_pausa = ttk.Button(sinistra, command=toggle_pausa, style="Grande.TButton")
    btn_pausa.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 10))
    aggiorna_pausa()

    ttk.Label(sinistra, text="Webcam da usare:").grid(row=4, column=0, columnspan=2,
                                                        sticky="w", pady=(0, 2))
    var_cam = tk.StringVar(value="Cerco le webcam...")
    cb_cam = ttk.Combobox(sinistra, textvariable=var_cam, state="readonly", width=38)
    cb_cam.grid(row=5, column=0, columnspan=2, sticky="ew")
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

    ttk.Button(sinistra, text="Ricalibra posizione testa (guarda dritto)",
               command=ric.richiedi_calibrazione).grid(row=6, column=0, columnspan=2,
                                                        sticky="ew", pady=(10, 4))

    def sblocca():
        motore.rilascia_tutto()
        tastiera.sblocca_tutto()

    ttk.Button(sinistra, text="Sblocca tutti i tasti (se qualcosa resta premuto)",
               command=sblocca).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 4))
    ttk.Button(sinistra, text="Esci dal programma",
               command=lambda: chiudi()).grid(row=8, column=0, columnspan=2,
                                              sticky="ew", pady=(4, 0))

    # ---------- colonna destra: una riga per espressione ----------
    destra = ttk.Frame(root, padding=10)
    destra.grid(row=0, column=1, sticky="n")

    intestazioni = ["Espressione", "Quanto la vedo", "Soglia", "Tasto da premere", "Come"]
    for c, testo in enumerate(intestazioni):
        ttk.Label(destra, text=testo, font=("Segoe UI", 9, "bold")).grid(
            row=0, column=c, padx=4, pady=(0, 4), sticky="w")

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

    for r, (eid, nome, _s, _f) in enumerate(ESPRESSIONI, start=1):
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

    ttk.Label(destra, foreground="#555", wraplength=640, justify="left",
              text=("Soglia: quanto deve essere forte l'espressione per scattare "
                    "(trascina verso sinistra = piu' sensibile). "
                    "Le barre si colorano quando l'espressione e' attiva.\n"
                    "Consiglio: assegna '" + AZIONE_PAUSA + "' a un'espressione, cosi' "
                    "puoi fermare e riprendere il programma anche dentro un gioco a "
                    "schermo intero.")
              ).grid(row=len(ESPRESSIONI) + 1, column=0, columnspan=5, pady=(10, 0), sticky="w")

    # ---------- aggiornamento periodico ----------
    foto = {"img": None}
    stato_cam = {"elenco": None, "idx": None}
    stato_pausa = {"v": motore.in_pausa}

    def aggiorna():
        if motore.in_pausa != stato_pausa["v"]:      # pausa cambiata dal viso
            stato_pausa["v"] = motore.in_pausa
            aggiorna_pausa()
        with ric.lock:
            valori = dict(ric.valori)
            faccia = ric.faccia
            ant = ric.anteprima
            msg = ric.messaggio
            elenco = ric.elenco
        if elenco is not None and (elenco != stato_cam["elenco"]
                                   or int(imp["webcam"]) != stato_cam["idx"]):
            stato_cam["elenco"] = elenco
            stato_cam["idx"] = int(imp["webcam"])
            aggiorna_elenco_cam(elenco)
        if ant is not None:
            img = Image.fromarray(ant)
            foto["img"] = ImageTk.PhotoImage(img)
            video.config(image=foto["img"])
        testo = msg
        if ant is not None:
            testo += "\n" + ("Viso riconosciuto" if faccia else "Nessun viso in vista")
        lbl_stato.config(text=testo)
        for eid, _n, _s, _f in ESPRESSIONI:
            barre[eid]["value"] = int(valori.get(eid, 0.0) * 100)
            attiva = motore.attive.get(eid, False)
            etichette[eid].config(foreground="#008000" if attiva else "black",
                                  font=("Segoe UI", 10, "bold" if attiva else "normal"))
        root.after(66, aggiorna)

    def chiudi():
        motore.chiuso = True
        ric.fermati = True
        motore.rilascia_tutto()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", chiudi)
    ric.start()
    root.after(100, aggiorna)
    root.mainloop()
    motore.chiuso = True
    ric.fermati = True
    ric.join(3.0)
    motore.chiudi()


FILE_ERRORI = os.path.join(CARTELLA, "errori.txt")

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
