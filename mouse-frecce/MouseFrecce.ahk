; ======================================================================
;  MOUSE -> FRECCE   (versione 1.0)
;
;  Trasforma il trascinamento del mouse in tasti freccia tenuti premuti,
;  come se il mouse fosse un joystick:
;
;    1. tieni premuto il tasto SINISTRO del mouse in un punto qualsiasi
;    2. senza lasciarlo, sposta il mouse:
;         verso l'alto    -> tiene premuto  FRECCIA SU
;         verso il basso  -> tiene premuto  FRECCIA GIU'
;         verso destra    -> tiene premuto  FRECCIA DESTRA
;         verso sinistra  -> tiene premuto  FRECCIA SINISTRA
;    3. riporta il mouse verso il punto di partenza -> rilascia la freccia
;    4. lascia il tasto sinistro -> rilascia tutto
;
;  Un clic normale (premi e rilasci senza spostarti) resta un clic normale,
;  cosi' puoi comunque usare i menu del gioco.
;
;  Richiede AutoHotkey v2  ->  https://www.autohotkey.com
;  Istruzioni complete nel file LEGGIMI.md
; ======================================================================

#Requires AutoHotkey v2.0
#SingleInstance Force
CoordMode "Mouse", "Screen"
SendMode "Input"
SetKeyDelay -1, -1

; ----------------------------------------------------------------------
;  IMPOSTAZIONI  (puoi cambiare i valori qui sotto)
; ----------------------------------------------------------------------

; Quanti pixel devi spostarti dal punto di partenza prima che parta una
; freccia. Piu' alto = meno sensibile. (consigliato tra 15 e 50)
ZonaMorta := 25

; true  = puoi premere due frecce insieme muovendoti in diagonale
;         (es. in alto a destra = SU + DESTRA)
; false = una sola freccia alla volta, quella della direzione prevalente
Diagonali := false

; true  = mentre tieni premuto il puntatore resta fermo dove hai cliccato
;         (come un joystick: non scappa ai bordi dello schermo)
; false = il puntatore si muove normalmente
BloccaCursore := true

; Tasto del mouse che ATTIVA / DISATTIVA il programma al volo.
;   "MButton" = tasto centrale (rotellina premuta)
;   "RButton" = tasto destro
;   ""        = nessuno (si usa solo il bottone nella finestra)
TastoInterruttore := "MButton"

; true = il programma e' gia' attivo appena lo apri
AttivoAllAvvio := true

; Tasti da tenere premuti. Se il gioco usa W A S D al posto delle frecce
; scrivi:  "w"  "s"  "a"  "d"
TastoSu       := "Up"
TastoGiu      := "Down"
TastoSinistra := "Left"
TastoDestra   := "Right"

; ----------------------------------------------------------------------
;  Da qui in giu' non serve modificare nulla
; ----------------------------------------------------------------------

Intervallo := 10      ; ogni quanti millisecondi controlla il mouse
Limite     := 150     ; spostamento massimo "virtuale" con BloccaCursore

Attivo      := false
startX      := 0
startY      := 0
accX        := 0
accY        := 0
inArrowMode := false  ; true quando il trascinamento e' diventato frecce
passaggio   := false  ; true quando il clic e' sulla nostra finestra
premuti     := Map()  ; tasti attualmente tenuti premuti

; ------------------------- finestra di controllo -----------------------

; E0x08000000 = la finestra non si "prende" il focus: il gioco resta attivo
MyGui := Gui("+AlwaysOnTop +ToolWindow +E0x08000000", "Mouse -> Frecce")
MyGui.SetFont("s11", "Segoe UI")
Stato := MyGui.Add("Text", "w260 h50 Center", "")
BtnToggle := MyGui.Add("Button", "w260 h45", "")
BtnToggle.OnEvent("Click", Toggle)
MyGui.SetFont("s9")
Info := MyGui.Add("Text", "w260 Center", "Tieni premuto il sinistro e trascina = frecce`nClic veloce = clic normale")
MyGui.SetFont("s10")
BtnEsci := MyGui.Add("Button", "w260", "Esci dal programma")
BtnEsci.OnEvent("Click", (*) => ExitApp())
MyGui.OnEvent("Close", (*) => ExitApp())
MyGui.Show("x20 y20 NoActivate")

A_IconTip := "Mouse -> Frecce"
A_TrayMenu.Insert("1&", "Attiva / Disattiva", Toggle)
A_TrayMenu.Insert("2&")

if (TastoInterruttore != "")
    Hotkey TastoInterruttore, Toggle

SetAttivo(AttivoAllAvvio)

; ------------------------------ hotkey ---------------------------------

#HotIf Attivo
*LButton:: {
    global startX, startY, accX, accY, inArrowMode, passaggio
    if SopraGui() {
        ; clic sulla nostra finestra: lo lasciamo passare normalmente
        passaggio := true
        Click "Down"
        return
    }
    passaggio := false
    MouseGetPos &startX, &startY
    accX := 0
    accY := 0
    inArrowMode := false
    SetTimer Tick, Intervallo
}

*LButton Up:: {
    global inArrowMode, passaggio
    if passaggio {
        passaggio := false
        Click "Up"
        return
    }
    SetTimer Tick, 0
    RilasciaTutti()
    if !inArrowMode {
        ; non ti sei spostato: era un clic normale, lo mandiamo al gioco
        Click startX " " startY
    }
    inArrowMode := false
}
#HotIf

; ----------------------------- funzioni --------------------------------

Tick() {
    global accX, accY, inArrowMode
    MouseGetPos &x, &y

    if BloccaCursore {
        accX += x - startX
        accY += y - startY
        accX := Max(-Limite, Min(Limite, accX))
        accY := Max(-Limite, Min(Limite, accY))
        if (x != startX || y != startY)
            MouseMove startX, startY, 0
    } else {
        accX := x - startX
        accY := y - startY
    }

    dist := Sqrt(accX * accX + accY * accY)
    desiderati := Map()

    if (dist >= ZonaMorta) {
        inArrowMode := true
        if Diagonali {
            ; 8 settori da 45 gradi: una direzione e' attiva se la sua
            ; componente supera sin(22.5 gradi) della distanza
            soglia := dist * 0.383
            if (accY <= -soglia)
                desiderati[TastoSu] := true
            if (accY >= soglia)
                desiderati[TastoGiu] := true
            if (accX <= -soglia)
                desiderati[TastoSinistra] := true
            if (accX >= soglia)
                desiderati[TastoDestra] := true
        } else {
            ; solo la direzione prevalente
            if (Abs(accX) > Abs(accY))
                desiderati[accX > 0 ? TastoDestra : TastoSinistra] := true
            else
                desiderati[accY > 0 ? TastoGiu : TastoSu] := true
        }
    }

    AggiornaTasti(desiderati)
}

; Preme i tasti nuovi e rilascia quelli che non servono piu'
AggiornaTasti(desiderati) {
    global premuti
    for tasto in premuti.Clone() {
        if !desiderati.Has(tasto) {
            Send "{Blind}{" tasto " up}"
            premuti.Delete(tasto)
        }
    }
    for tasto in desiderati {
        if !premuti.Has(tasto) {
            Send "{Blind}{" tasto " down}"
            premuti[tasto] := true
        }
    }
}

RilasciaTutti() {
    AggiornaTasti(Map())
}

SopraGui() {
    MouseGetPos(, , &hwnd)
    return (hwnd = MyGui.Hwnd)
}

Toggle(*) {
    SetAttivo(!Attivo)
}

SetAttivo(valore) {
    global Attivo
    Attivo := valore
    if !Attivo {
        SetTimer Tick, 0
        RilasciaTutti()
    }
    AggiornaGui()
}

AggiornaGui() {
    if Attivo {
        Stato.SetFont("c008000 Bold")
        Stato.Text := "ATTIVO`nil trascinamento diventa frecce"
        BtnToggle.Text := "DISATTIVA" (TastoInterruttore != "" ? "  (o " NomeTasto(TastoInterruttore) ")" : "")
    } else {
        Stato.SetFont("cB00000 Bold")
        Stato.Text := "SPENTO`nil mouse funziona normalmente"
        BtnToggle.Text := "ATTIVA" (TastoInterruttore != "" ? "  (o " NomeTasto(TastoInterruttore) ")" : "")
    }
}

NomeTasto(t) {
    switch t {
        case "MButton": return "tasto centrale"
        case "RButton": return "tasto destro"
        case "XButton1": return "tasto laterale 1"
        case "XButton2": return "tasto laterale 2"
        default: return t
    }
}

; Quando il programma si chiude, assicurati di non lasciare tasti premuti
OnExit((*) => RilasciaTutti())
