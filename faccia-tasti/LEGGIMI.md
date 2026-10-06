# Faccia → Tasti

Un programma per Windows che **guarda il tuo viso con la webcam** e, quando
fai una certa espressione, **preme un tasto della tastiera** (o un clic del
mouse) a tua scelta. Tutto si configura con il mouse dalla finestra del
programma, senza toccare la tastiera.

## Espressioni riconosciute

| Espressione                | Esempio di uso                 |
|----------------------------|--------------------------------|
| Bocca aperta               | Spazio (salta)                 |
| Sorriso                    | Invio                          |
| Sopracciglia alzate        | Freccia su                     |
| Sopracciglia abbassate     | Freccia giù                    |
| Labbra in avanti (bacio)   | Lettera E (interagisci)        |
| Guance gonfie              | Shift (corri)                  |
| Occhiolino sinistro        | Clic sinistro mouse            |
| Occhiolino destro          | Clic destro mouse              |
| Entrambi gli occhi chiusi  | Esc                            |
| Bocca spostata a sinistra  | Freccia sinistra               |
| Bocca spostata a destra    | Freccia destra                 |
| Naso arricciato            | Tab                            |
| Testa girata a sinistra    | Freccia sinistra               |
| Testa girata a destra      | Freccia destra                 |
| Testa alzata               | Freccia su                     |
| Testa abbassata            | Freccia giù                    |

Per ogni espressione scegli:

- **Tasto da premere**: frecce, Spazio, Invio, Esc, Tab, Shift, Ctrl, Alt,
  lettere, numeri, F1–F12, clic sinistro o destro del mouse. "Nessuno" =
  l'espressione non fa niente.
- **Come**: *Tieni premuto* (il tasto resta premuto finché tieni
  l'espressione, come tenere premuta una freccia) oppure *Premi una volta*
  (un colpo solo ogni volta che fai l'espressione).
- **Soglia**: quanto deve essere marcata l'espressione per scattare.
  Trascina il cursore verso sinistra per renderla più sensibile, verso destra
  per renderla meno sensibile.

Le scelte si salvano da sole nel file `impostazioni.json`.

## Installazione (si fa una volta sola)

1. Installa **Python 3.12** da <https://www.python.org/downloads/>.
   Nella prima schermata dell'installazione **metti la spunta su
   "Add python.exe to PATH"** (in basso), poi "Install Now".
2. Scarica questa cartella `faccia-tasti` sul computer (per esempio sul
   Desktop). Ti servono questi file:
   `FacciaTasti.py`, `requirements.txt`, `installa.bat`, `avvia.bat`.
3. Fai **doppio clic su `installa.bat`**. Si apre una finestra nera che
   scarica le librerie necessarie: ci vogliono alcuni minuti. Alla fine
   scrive "Installazione completata". Premi un tasto qualsiasi o chiudi la
   finestra.

## Uso

1. Fai **doppio clic su `avvia.bat`**. La prima volta il programma scarica da
   solo il modello per il riconoscimento del viso (circa 4 MB).
2. Si apre la finestra con l'anteprima della webcam a sinistra e la lista
   delle espressioni a destra. Mettiti davanti alla webcam **guardando
   dritto** per i primi secondi: il programma impara la posizione neutra
   della tua testa.
3. Prova a fare le espressioni e guarda le barre nella colonna "Quanto la
   vedo": quando un'espressione è attiva il suo nome diventa verde.
4. Per ogni espressione che vuoi usare scegli il tasto nel menu a tendina.
5. Clicca sulla finestra del gioco per dargli il focus e gioca.
6. **Pausa**: il bottone grande **METTI IN PAUSA** blocca tutto (non preme
   più niente), **RIPRENDI** fa ripartire. Utile quando parli o mangi.
7. **Esci dal programma** chiude tutto.

La finestra resta sempre in primo piano; puoi spostarla dalla barra del
titolo per non coprire il gioco.

## Consigli

- Le espressioni **del viso** (bocca, sorriso, sopracciglia, occhiolino) sono
  le più affidabili. Quelle con la testa funzionano, ma **se muovi il mouse
  con la testa (per esempio con Talon)** lasciale su "Nessuno", altrimenti
  ogni movimento del puntatore premerebbe un tasto.
- Se un'espressione scatta da sola, sposta la sua soglia verso destra.
  Se invece non scatta mai, spostala verso sinistra.
- Serve una buona luce sul viso, meglio davanti che dietro (una finestra alle
  spalle rende il viso scuro).
- Se hai più webcam, cambia il numero nella casella "Webcam numero" e premi
  "Riavvia webcam".
- Se la posizione della testa sembra sballata, premi "Ricalibra posizione
  testa" mentre guardi dritto.

## Se qualcosa non va

- **`installa.bat` dice che Python non c'è.** Reinstalla Python e assicurati
  di mettere la spunta su "Add python.exe to PATH".
- **Il gioco ignora i tasti.** Alcuni giochi vanno avviati prima del
  programma, oppure serve avviare `avvia.bat` con clic destro → "Esegui come
  amministratore".
- **"Webcam 0 non trovata".** Prova con 1 o 2 nella casella "Webcam numero" e
  premi "Riavvia webcam". Controlla anche che un altro programma (per
  esempio una videochiamata) non stia già usando la webcam.
- **Un tasto resta premuto.** Premi "METTI IN PAUSA": rilascia tutto.

## Privacy

Le immagini della webcam vengono elaborate solo sul tuo computer e non
vengono salvate né inviate da nessuna parte. L'unico collegamento a internet
è il download iniziale del modello di riconoscimento.
