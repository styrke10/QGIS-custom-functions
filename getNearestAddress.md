# Forudsætninger for anvendelse af getNearestAddress()

Du skal have oprettet en API key på Datafordeler Administration.

Det gøres som følger:
1. Log på Datafordeler Administration med MitID: https://portal.datafordeler.dk/hjem
2. Opret et IT-system (hvis du ikke allerede har det) - vælg dette.
3. Opret en API-key og notér denne omhyggeligt ned (du kan ikke genfinde API-key'en).
4. Registrér din statiske IP-adresse (eksterne, dynamiske IP-adresser er no go!)

Når du har gjort dette, opretter du en global variabel i din QGIS med API-key'en som følger:
1. Gå i menuen 'Settings' -> 'Options' ('Indstillinger' -> 'Indstillinger')
2. Vælg fanen 'Variables' ('Variabler') og tryk på det grønne plus nederst til højre.
3. Navngiv din variabel 'dar_api_key' og indsæt API-key strengen som value/værdi.

Kopiér filen 'getNearestAddress.py' ind i expressions-folderen på din computer: %APPDATA%\QGIS\QGIS3\profiles\default\python\expressions.

Start QGIS, og du skulle nu gerne kunne se funktionen getNearestAddress i Field Calculator'en i gruppen 'Custom'.
