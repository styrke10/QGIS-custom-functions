# Anvendelse af setRotationFromLine()

setRotationFromLine() beregner retningen af det nærmeste linjesegment i det lag, der angives som parameter. Værdien kan derfor (typisk) bruges til at rotere et punktsymbol (f.eks. en ventil eller et stoppestedssymbol), som er placeret på linjen.



Funktionen kaldes på følgende måde:

setRotationFromLine( linelayer, directional=NULL, tolerance=NULL, offset=NULL )

**Parametre:**

*linelayer:* Navnet på det linjelag, som indeholder de linjer, punkterne skal roteres efter (d.v.s. retningen skal beregnes på).

*directional:* Angiver om symbolet skal roteres/retningen beregnes efter linjens digitaliseringsretning:

    0: Uden hensyn til retning (altid mest mulig nordvendt)
    
    1: Med digitaliseringretningen
    
    2: Imod digitaliseringretningen

*tolerance:* Den maksimalt tilladte afstand mellem punkt og linje.

*offset:* En offsetvinkel, som lægges til den beregnede vinkel.

Kun parameteren *linelayer* er obligatorisk.



Som nævnt især nyttig, hvor punktobjekter med et orienteret symbol skal roteres ift et underliggende linjelag. Kan der anvendes såvel i Field Calculator til en samlet beregning af alle objekters rotation som i default værdien for rotationsfeltet i attributtabellen.


