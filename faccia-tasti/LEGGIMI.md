# Faccia → Tasti  (versione 2)

Un solo programma per Windows, tutto configurabile con il mouse, che fa due
cose:

1. **Espressioni del viso → tasti.** Guarda il tuo viso con la webcam e,
   quando fai una certa espressione, preme un tasto della tastiera (o un clic
   del mouse) a tua scelta.
2. **Mouse → frecce.** Tieni premuto il tasto sinistro del mouse e sposta il
   puntatore: in alto tiene premuta Freccia SU, in basso GIÙ, a destra DESTRA,
   a sinistra SINISTRA. Riporti il puntatore vicino al punto di partenza e la
   freccia si rilascia. Un clic veloce resta un clic normale. Funziona anche
   se muovi il puntatore con Talon o con un eye/head tracker.

Il bottone **METTI IN PAUSA** ferma entrambe le funzioni insieme.

## Espressioni riconosciute

| Espressione                | Esempio di uso          |
|----------------------------|-------------------------|
| Bocca aperta               | Spazio (salta)          |
| Sorriso                    | Invio                   |
| Sopracciglia alzate        | Lettera E (interagisci) |
| Sopracciglia abbassate     | Shift (corri)           |
| Guance gonfie              | Pausa / Riprendi        |
| Occhiolino sinistro        | Clic sinistro mouse     |
| Occhiolino destro          | Clic destro mouse       |
| Entrambi gli occhi chiusi  | Esc                     |
| Bocca spostata a sinistra  | Tab                     |
| Bocca spostata a destra    | Lettera Q               |
| Naso arricciato            | F1                      |

Per ogni espressione scegli:

- **Tasto da premere**: frecce, Spazio, Invio, Esc, Tab, Shift, Ctrl, Alt,
  lettere, numeri, F1–F12, clic sinistro o destro del mouse, oppure l'azione
  **`** Pausa / Riprendi **`**. "Nessuno" = l'espressione non fa niente.
- **Come**: *Tieni premuto* (il tasto resta premuto finché tieni
  l'espressione) oppure *Premi una volta* (un colpo solo).
- **Soglia**: quanto deve essere marcata l'espressione per scattare.
  Verso sinistra = più sensibile, verso destra = meno sensibile.

Le scelte si salvano da sole nel file `impostazioni.json`.

## Installazione (si fa una volta sola)

1. Serve **Python** (3.10, 3.11 o 3.12). Se lo hai già, per esempio per
   Stable Diffusion, va bene quello. Altrimenti installalo da
   <https://www.python.org/downloads/> mettendo la spunta su
   **"Add python.exe to PATH"**.
2. Scarica questa cartella `faccia-tasti` sul computer (per esempio sul
   Desktop).
3. Fai **doppio clic su `installa.bat`** e aspetta "Installazione completata".

## Uso

1. Fai **doppio clic su `avvia.bat`**. La prima volta scarica da solo il
   modello per il riconoscimento del viso (circa 4 MB). Si apre direttamente
   la finestra del programma, senza finestre nere.
2. A sinistra vedi la webcam, a destra la lista delle espressioni e, sotto, la
   sezione Mouse → Frecce.
3. Prova le espressioni guardando le barre "Quanto la vedo": quando una è
   attiva il suo nome diventa verde. Scegli i tasti dai menu a tendina.
4. Clicca sulla finestra del gioco per dargli il focus e gioca.
5. **Pausa**: il bottone grande **METTI IN PAUSA** ferma tutto (viso e
   mouse), **RIPRENDI** fa ripartire. Se assegni "** Pausa / Riprendi **" a
   un'espressione puoi farlo anche dentro un gioco a schermo intero.
6. **Esci dal programma** chiude tutto e rilascia ogni tasto.

La finestra resta sempre in primo piano; spostala dalla barra del titolo.

## Mouse → Frecce: impostazioni

- **Attiva Mouse → Frecce**: spegnilo se vuoi usare il mouse normalmente.
- **Spostamento minimo**: di quanti pixel devi spostarti prima che parta una
  freccia. Se ti partono frecce quando vuoi solo cliccare, alzalo.
- **Diagonali**: muovendoti in diagonale premi due frecce insieme.
- **In alto / In basso / A sinistra / A destra**: quali tasti premere. Per i
  giochi che usano W A S D scegli le lettere W, S, A, D.

## Programma più leggero

- Togli la spunta a **"Mostra l'anteprima della webcam"** quando hai finito
  di configurare: risparmia parecchio lavoro.
- **"Analisi del viso al secondo"**: 10 o 15 bastano per giocare; più alto
  = più pronto ma più pesante. Accanto vedi quante analisi fa davvero.
- Chiudi Stable Diffusion e altri programmi pesanti mentre giochi.

## Se qualcosa non va

- **`installa.bat` dice che Python non c'è.** Installa Python con la spunta
  "Add python.exe to PATH".
- **Il programma non si apre.** Guarda nel file `errori.txt` nella cartella e
  incollami quello che c'è scritto.
- **Il gioco ignora i tasti.** Se il gioco è avviato "come amministratore",
  avvia anche `avvia.bat` con clic destro → "Esegui come amministratore".
- **Un tasto o il mouse restano bloccati.** Premi **Sblocca tutti i tasti**
  nella finestra, oppure riavvia il programma: all'avvio rilascia tutto.
- **Nessuna webcam disponibile.** Controlla che sia collegata e che un altro
  programma non la stia usando, poi scegli la webcam dal menu.
- **Mouse → Frecce dice "non disponibile".** Questa funzione esiste solo su
  Windows.

## Privacy

Le immagini della webcam vengono elaborate solo sul tuo computer e non
vengono salvate né inviate da nessuna parte. L'unico collegamento a internet
è il download iniziale del modello di riconoscimento.
