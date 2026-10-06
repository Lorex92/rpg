# Mouse → Frecce

Un piccolo programma per Windows che ti permette di **usare i tasti freccia
con il solo mouse**, come se il mouse fosse un joystick.

## Come funziona

1. Tieni premuto il **tasto sinistro** del mouse in un punto qualsiasi dello schermo.
2. Senza lasciarlo, **sposta il mouse**:

   | Sposti il mouse verso… | Il programma tiene premuto… |
   |------------------------|-----------------------------|
   | l'alto                 | ⬆ Freccia SU                |
   | il basso               | ⬇ Freccia GIÙ               |
   | destra                 | ➡ Freccia DESTRA            |
   | sinistra               | ⬅ Freccia SINISTRA          |

3. Riporti il mouse vicino al punto di partenza → la freccia viene rilasciata.
4. Lasci il tasto sinistro → tutto viene rilasciato.

Un **clic veloce** (premi e rilasci senza spostarti) resta un clic normale,
quindi puoi continuare a usare i menu del gioco.

Mentre tieni premuto, il puntatore resta fermo nel punto in cui hai cliccato
(così non scappa ai bordi dello schermo). Si può disattivare, vedi sotto.

## Installazione (si fa una volta sola)

1. Scarica e installa **AutoHotkey v2** da <https://www.autohotkey.com>
   (bottone "Download", poi "Download v2.0"). Durante l'installazione lascia
   tutte le opzioni come sono.
2. Scarica il file `MouseFrecce.ahk` di questa cartella e mettilo dove vuoi,
   per esempio sul Desktop.

## Uso

1. Fai **doppio clic** su `MouseFrecce.ahk`.
2. Compare una piccola finestra sempre in primo piano con scritto
   **IN FUNZIONE**. Da questo momento il trascinamento con il tasto sinistro
   diventa frecce.
3. Apri il gioco e **clicca una volta sulla finestra del gioco** per dargli il
   focus, poi gioca tenendo premuto e trascinando.
4. **Per mettere in pausa** e tornare a usare il mouse normalmente premi il
   bottone grande **METTI IN PAUSA** nella finestra, oppure premi il **tasto
   centrale del mouse** (la rotellina). La finestra diventa rossa con scritto
   **IN PAUSA**. Lo stesso bottone (ora **RIPRENDI**) o la rotellina lo fanno
   ripartire.
5. Per chiudere il programma premi **Esci dal programma** nella finestra, oppure
   clicca con il destro sull'icona verde "H" in basso a destra vicino
   all'orologio e scegli **Exit**.

Puoi spostare la finestrella trascinandola dalla sua barra del titolo, così
non copre il gioco.

## Impostazioni

Apri `MouseFrecce.ahk` con il **Blocco note** (clic destro → Apri con → Blocco
note). All'inizio del file c'è la sezione **IMPOSTAZIONI**:

| Impostazione        | Cosa fa                                                                                     | Valore iniziale |
|---------------------|---------------------------------------------------------------------------------------------|-----------------|
| `ZonaMorta`         | Di quanti pixel devi spostarti prima che parta una freccia. Più alto = meno sensibile.     | `25`            |
| `Diagonali`         | `true` = muovendoti in diagonale premi due frecce insieme (es. SU + DESTRA).               | `false`         |
| `BloccaCursore`     | `true` = il puntatore resta fermo dove hai cliccato mentre tieni premuto.                   | `true`          |
| `TastoInterruttore` | Tasto del mouse per pausa/riprendi: `"MButton"` centrale, `"RButton"` destro, `""` nessuno. | `"MButton"`   |
| `AttivoAllAvvio`    | `true` = parte già in funzione; `false` = parte in pausa.                                   | `true`          |
| `TastoSu` ecc.      | Quali tasti premere. Per i giochi che usano W A S D scrivi `"w"`, `"s"`, `"a"`, `"d"`.      | frecce          |

Dopo aver cambiato qualcosa salva il file e **riapri** il programma (doppio
clic sul file: la versione vecchia si chiude da sola).

## Se qualcosa non va

- **Le frecce non arrivano al gioco.** Clicca una volta sulla finestra del
  gioco per dargli il focus e riprova. Alcuni giochi hanno bisogno di essere
  avviati e del programma avviato "come amministratore" (clic destro sul file
  → Esegui come amministratore).
- **Il gioco ignora completamente i tasti.** Apri il file con il Blocco note e
  cambia la riga `SendMode "Input"` in `SendMode "Event"`.
- **Parte una freccia anche quando voglio solo cliccare.** Aumenta `ZonaMorta`
  (per esempio `40`).
- **Il tasto centrale del mouse mi serve nel gioco.** Metti
  `TastoInterruttore := ""` e usa solo il bottone nella finestra.
- **La finestrella copre il gioco.** Trascinala altrove dalla barra del titolo.

## Avvio automatico (facoltativo)

Se vuoi che il programma parta da solo quando accendi il computer:
clic destro su `MouseFrecce.ahk` → **Crea collegamento**, poi sposta il
collegamento nella cartella `shell:startup` (scrivi `shell:startup` nella
barra degli indirizzi di Esplora file e premi Invio).
