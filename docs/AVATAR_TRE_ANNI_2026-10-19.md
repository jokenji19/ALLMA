# Primo volto di ALLMA: circa tre anni

Build Android **102521**, versione 0.9.0.0.

L’aspetto iniziale passa da circa sei mesi a circa tre anni, in tutte e tre le
presentazioni. Cambiano la geometria e le proporzioni di viso, collo e busto,
oltre ai testi della scelta iniziale e dell’osservatorio.

Il generatore combina i dodici asset CC0 ufficiali MakeHuman: sei macro target
`baby` e sei `child`, mediati all’interno di ciascun gruppo. I riferimenti di
età del progetto sorgente sono uno e dieci anni; la combinazione impiegata è
7/9 del primo gruppo e 2/9 del secondo. Riferimento:
[gestione dell’età in MakeHuman](https://github.com/makehumancommunity/makehuman/blob/master/makehuman/apps/human.py).
È una direzione artistica di circa tre anni, non una stima biologica dell’età.

È eliminato l’accorciamento della parte inferiore del viso usato per i sei mesi.
Il busto è ricentrato sulla stessa linea degli occhi; restano palpebre scolpite,
suddivisione della superficie, 100.000 posizioni distinte, filamenti e riflessi
luminosi. Il generatore registra pesi e hash delle sorgenti nell’asset prodotto.

L’età rappresentata nei dati di presenza è ora `visual_age_months: 36` e lo
stadio è `child`. Questa revisione non aggiunge l’invecchiamento automatico.
L’impronta e la scelta dell’aspetto già salvate continuano a essere usate;
nessuna migrazione o cancellazione dei ricordi è necessaria.

Per rigenerare l’asset, `tools/build_avatar_mesh.py` richiede ora anche
`--child-targets`, oltre alla mesh sorgente e a `--targets` per il gruppo baby.
I file di sviluppo e i risultati del collaudo sono conservati nella cartella
superiore `analisi/2026-10-19/avatar-tre-anni`.

Verificati: geometria completa e indici WebGL1, densità locale delle palpebre,
limiti del renderer, pausa, ripristino del contesto e alternativa Canvas.
Superati 41 test Python e 41 controlli dell’avatar nel browser reale, compresi
salvataggio delle tre presentazioni, rotazione completa, zoom e navigazione.
