# Anvendelse af setRotationFromLine()

setRotationFromLine() beregner rotationen af det linjesegment i det lag, der angives som parameter.



Funktionen kaldes på følgende måde:

setRotationFromLine( linelayer, directional=NULL, tolerance=NULL, offset=NULL )

**Parametre:**

*linelayer:* Navnet på det linjelag, som indeholder de linjer, punkterne skal roteres efter.

*directional:* Angiver om symbolet skal roteres efter linjens digitaliseringsretning:

    <li>0: Uden hensyn til retning (altid mest mulig nordvendt)</li>

    <li>1: Med digitaliseringretningen</li>

    <li>2: Imod digitaliseringretningen</li>

*tolerance:* Den maksimalt tilladte afstand mellem punkt og linje.

*offset:* En offsetvinkel, som lægges til den beregnede vinkel.

Kun parameteren *linelayer* er obligatorisk.



Især nyttig, hvor punktobjekter med et orienteret symbol (pil, ventil etc) skal roteres ift et underliggende linjelag. Kan der anvendes såvel i Field Calculator til en samlet beregning af alle objekters rotation som i default værdien for rotationsfeltet i attributtabellen.


