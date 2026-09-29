"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
 
Erstatning for DAWA's /adgangsadresser/reverse (lukker 1. oktober 2026).
Bruger Datafordelerens GraphQL-tjeneste for DAR (v3).
 
Opsætning:
    Opret en global QGIS-variabel 'dar_api_key' med din Datafordeler API-nøgle
    (Indstillinger -> Indstillinger... -> Variabler).
"""
 
from qgis.core import qgsfunction, QgsExpressionContextUtils, QgsMessageLog, Qgis
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import urllib.error
import json
import math
import os
import ssl
 
 
# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
darGraphqlUrl = 'https://graphql.datafordeler.dk/DAR/v3'
apiKeyVariable = 'dar_api_key'            # navn på global QGIS-variabel
startHalfSize = 100.0                     # halv sidelængde (m) på første søgeboks
maxHalfSize = 6400.0                      # stop søgning herefter
pageSize = 1000                           # max tilladt af Datafordeleren
maxPages = 5                              # max sider pr. søgeboks
husnummerStatuses = ['2', '3']            # DAR livscyklus: 2 = foreløbig, 3 = gældende
requestTimeout = 30                       # sekunder
 
logTag = 'getNearestAddress'
addressCache = {}                         # (x, y) afrundet til cm -> adressetekst
 
 
# ---------------------------------------------------------------------------
# GraphQL-forespørgsler
# ---------------------------------------------------------------------------
adressepunktQuery = """
query ($t: DafDateTime!, $wkt: String!, $n: Int!, $after: String) {
  DAR_Adressepunkt(first: $n, after: $after, virkningstid: $t, registreringstid: $t,
                   where: { position: { intersects: { wkt: $wkt, crs: 25832 } } }) {
    nodes { id_lokalId position { wkt } }
    pageInfo { hasNextPage endCursor }
  }
}
"""
 
husnummerQuery = """
query ($t: DafDateTime!, $ids: [String!], $statuses: [String!]) {
  DAR_Husnummer(first: 1000, virkningstid: $t, registreringstid: $t,
                where: { adgangspunkt: { in: $ids }, status: { in: $statuses } }) {
    nodes { id_lokalId adgangspunkt husnummertekst navngivenVej postnummer }
  }
}
"""
 
navngivenVejQuery = """
query ($t: DafDateTime!, $id: String!) {
  DAR_NavngivenVej(first: 1, virkningstid: $t, registreringstid: $t,
                   where: { id_lokalId: { eq: $id } }) {
    nodes { vejnavn }
  }
}
"""
 
postnummerQuery = """
query ($t: DafDateTime!, $id: String!) {
  DAR_Postnummer(first: 1, virkningstid: $t, registreringstid: $t,
                 where: { id_lokalId: { eq: $id } }) {
    nodes { postnr navn }
  }
}
"""
 
 
# ---------------------------------------------------------------------------
# Hjælpefunktioner
# ---------------------------------------------------------------------------
def getApiKey():
    apiKey = QgsExpressionContextUtils.globalScope().variable(apiKeyVariable)
    if not apiKey:
        raise RuntimeError(f"Global QGIS-variabel '{apiKeyVariable}' med Datafordeler API-nøgle mangler")
    return str(apiKey)
 
 
def runGraphql(query, variables):
    # Laver GraphQL request med den angivne query og parametre
    url = f"{darGraphqlUrl}?{urllib.parse.urlencode({'apiKey': getApiKey()})}"
    body = json.dumps({'query': query, 'variables': variables}).encode('utf-8')
    request = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=requestTimeout) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        # GraphQL-fejl returneres ofte som HTTP 400 med forklaringen i body
        errorBody = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {errorBody}') from None
    if result.get('errors'):
        raise RuntimeError('; '.join(e.get('message', str(e)) for e in result['errors']))
    return result['data']
 
 
def parsePointWkt(wkt):
    # 'POINT (x y)' eller 'POINT(x y)'
    inner = wkt[wkt.index('(') + 1:wkt.rindex(')')].split()
    return float(inner[0]), float(inner[1])
 
 
def boxWkt(x, y, halfSize):
    x0, y0, x1, y1 = x - halfSize, y - halfSize, x + halfSize, y + halfSize
    return f'POLYGON (({x0} {y0}, {x1} {y0}, {x1} {y1}, {x0} {y1}, {x0} {y0}))'
 
 
def fetchAdressepunkter(x, y, halfSize, timeStamp):
    """Returnerer liste af (afstand, adressepunktId) inden for boksen, sorteret efter afstand."""
    candidates = []
    after = None
    for _ in range(maxPages):
        data = runGraphql(adressepunktQuery, {'t': timeStamp, 'wkt': boxWkt(x, y, halfSize),
                                              'n': pageSize, 'after': after})
        connection = data['DAR_Adressepunkt']
        # Collect candidates in list
        for node in connection['nodes'] or []:
            if node.get('position') and node['position'].get('wkt'):
                px, py = parsePointWkt(node['position']['wkt'])
                candidates.append((math.hypot(px - x, py - y), node['id_lokalId']))
        if not connection['pageInfo']['hasNextPage']:
            break
        after = connection['pageInfo']['endCursor']
    else:
        QgsMessageLog.logMessage(f'Mere end {maxPages * pageSize} adressepunkter i boksen - resultat kan være ufuldstændigt',
                                 logTag, Qgis.Warning)
    # Sort candidates by distance
    candidates.sort()
    return candidates
 
 
def findNearestHusnummer(candidates, timeStamp):
    """
    Adressepunkter omfatter både adgangspunkter og vejpunkter. Kun de adressepunkter,
    der er adgangspunkt for et (gældende/foreløbigt) husnummer, er relevante.
    Kandidaterne behandles i afstandsorden i bidder af 100 (max for 'in'-filteret);
    første bid med et match indeholder det nærmeste husnummer.
    """
    for start in range(0, len(candidates), 100):
        chunk = candidates[start:start + 100]
        # Konvertér til et dictionary med id: afstand
        distanceById = {pointId: distance for distance, pointId in chunk}
        # Find de elementer, som faktisk er adgangsadressepunkter (og ikke vejpunkter eller historiske adressepunkter)
        data = runGraphql(husnummerQuery, {'t': timeStamp, 'ids': list(distanceById),
                                           'statuses': husnummerStatuses})
        nodes = data['DAR_Husnummer']['nodes'] or []
        # Find nærmeste adressepunkt (hvis ingen -> prøv næste chunk
        if nodes:
            nearest = min(nodes, key=lambda n: distanceById.get(n['adgangspunkt'], math.inf))
            return distanceById[nearest['adgangspunkt']], nearest
    return None, None
 
 
vejnavnCache = {}                         # navngivenVej-id -> vejnavn
postnummerCache = {}                      # postnummer-id -> (postnr, navn)
 
 
def getVejnavn(vejId, timeStamp):
    if vejId not in vejnavnCache:
        nodes = runGraphql(navngivenVejQuery, {'t': timeStamp, 'id': vejId})['DAR_NavngivenVej']['nodes'] or []
        vejnavnCache[vejId] = nodes[0]['vejnavn'] if nodes else ''
    return vejnavnCache[vejId]
 
 
def getPostnummer(postnrId, timeStamp):
    if postnrId not in postnummerCache:
        nodes = runGraphql(postnummerQuery, {'t': timeStamp, 'id': postnrId})['DAR_Postnummer']['nodes'] or []
        postnummerCache[postnrId] = (nodes[0]['postnr'], nodes[0]['navn']) if nodes else ('', '')
    return postnummerCache[postnrId]
 
 
def formatAddress(husnummer, timeStamp):
    vejnavn = getVejnavn(husnummer['navngivenVej'], timeStamp)
    postnr, postnrNavn = getPostnummer(husnummer['postnummer'], timeStamp)
    return f"{vejnavn} {husnummer['husnummertekst'] or ''}, {postnr} {postnrNavn}".strip()
 
 
def lookupNearestAddress(x, y):
    # Generer stadig større rektangler, som der forespørges indenfor, indtil der findes kandidater
    timeStamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    halfSize = startHalfSize
    while halfSize <= maxHalfSize:
        candidates = fetchAdressepunkter(x, y, halfSize, timeStamp)
        distance, husnummer = findNearestHusnummer(candidates, timeStamp)
        if husnummer is not None:
            if distance > halfSize:
                # Et punkt uden for kvadratet kan ligge tættere end det fundne
                # (hjørnerne er længere væk end kanterne). Søg én gang til med
                # en boks, der dækker hele cirklen med radius = afstanden.
                candidates = fetchAdressepunkter(x, y, math.ceil(distance), timeStamp)
                distance, husnummer = findNearestHusnummer(candidates, timeStamp)
            return formatAddress(husnummer, timeStamp)
        halfSize *= 2
    return None
 
 
# ---------------------------------------------------------------------------
# QGIS funktionen
# ---------------------------------------------------------------------------
@qgsfunction(args='auto', group='Custom')
def getNearestAddress(x, y, feature, parent):
    """
    Henter - via Datafordelerens GraphQL-tjeneste for DAR - den nærmeste (danske) adgangsadresse til det punkt, som er defineret af parametrene x og y.<br>
    <h3>Syntax:</h3>
    getNearestAddress( x, y )
 
    <h3>Parametre:</h3>
    <ul>
    <li>x:  X koordinat</li>
    <li>y:  Y koordinat</li>
    </ul>
 
    <h3>Eksempler:</h3>
    <ul>
      <li>getNearestAddress(507181.02, 6149080.57) -> 'Industrivej Vest 41, 6600 Vejen'</li>
      <li>getNearestAddress($x, $y) -> 'Jernbanegade 27, 6000 Kolding'</li>
    </ul>
    Koordinater skal angives i ETRS89 UTM Zone 32N (EPSG:25832).<br>
    Kræver den globale variabel <b>'dar_api_key'</b> med en Datafordeler API-nøgle.<br><br>
    """
 
    # Samme SSL-håndtering som det oprindelige script (slår certifikatkontrol fra)
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context
 
    if x is None or y is None:
        return None
 
    cacheKey = (round(float(x), 2), round(float(y), 2))
    if cacheKey in addressCache:
        return addressCache[cacheKey]
 
    try:
        address = lookupNearestAddress(float(x), float(y))
    except Exception as e:
        parent.setEvalErrorString(f'getNearestAddress: {e}')
        QgsMessageLog.logMessage(str(e), logTag, Qgis.Critical)
        return None
 
    addressCache[cacheKey] = address
    return address
