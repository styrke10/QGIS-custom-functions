"""
Define new functions using @qgsfunction. feature and parent must always be the
last args. Use args=-1 to pass a list of values as arguments
"""

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *
import math


@qgsfunction(args=-1, group='Custom', handlesnull=True, usesgeometry=True)
def setRotationFromLine(values, feature, parent):
    """
    Beregner rotationsvinklen for et punkt på et linjesegment.<br><br>
    <h3>Syntax:</h3>
    setRotationFromLine( linelayer, directional=NULL, tolerance=NULL, offset=NULL )
    
    <h3>Parametre:</h3>
    <ul>
    <li>linelayer: Navnet på det linjelag, som indeholder de linjer, punkterne skal roteres efter.</li>
    <li>directional: Angiver om symbolet skal roteres efter linjens digitaliseringsretning:</li>
    <ul>
    <li>0: Uden hensyn til retning (altid mest mulig nordvendt)</li>
    <li>1: Med digitaliseringretningen</li>
    <li>2: Imod digitaliseringretningen</li>
    </ul>
    <li>tolerance: Den maksimalt tilladte afstand mellem punkt og linje.</li>
    <li>offset: En offsetvinkel, som lægges til den beregnede vinkel.</li>
    </ul>

    """

    # unpack arguments – pad missing ones with None
    if len(values) < 1 or len(values) > 4:
        parent.setEvalErrorString('getRotationAngle: forventer 1-4 argumenter')
        return None
    linelayer, directional, tolerance, offset = (list(values) + [None] * 4)[:4]

    # initializations
    if tolerance is None: tolerance = 0.1           # search tolerance
    if offset is None: offset = 0                   # angle offset
 
    # get linelayer
    layers = QgsProject.instance().mapLayersByName(linelayer)
    if not layers:
        parent.setEvalErrorString(f'Lag "{linelayer}" findes ikke')
        return None
    lines = layers[0]

    x = feature.geometry().asPoint().x()
    y = feature.geometry().asPoint().y()

    # get the rectangular search area
    searchRect = QgsRectangle(x - tolerance, y - tolerance,  x + tolerance, y + tolerance)

    # find lines
    found = []
    distance = QgsDistanceArea()
    for line in lines.getFeatures(QgsFeatureRequest().setFilterRect(searchRect)):

        # get the distance to the nearest segment on line and the vertex ending this (and placed on left or right side - not used)
        (dist, res_pnt, v_after, leftOf) = line.geometry().closestSegmentWithContext(feature.geometry().asPoint())

        # if we are very close to a vertex and not on the last one, the angle should be calculated from previous and next vertex
        if distance.measureLine(feature.geometry().asPoint(), QgsPointXY(line.geometry().vertexAt(v_after))) <= tolerance and not (line.geometry().vertexAt(v_after+1)).isEmpty():
            p1 = line.geometry().vertexAt(v_after+1)   # next vertex and one
        else:
            p1 = line.geometry().vertexAt(v_after)   # next vertex after point
        p2 = line.geometry().vertexAt(v_after-1) # previous vertex
        found.append([dist,p1,p2])

    # if found were found, use the segment closest to the input point
    if len(found) > 0:
        sort_found = sorted(found, key=lambda tup: tup[0])
        p1 = sort_found[0][1]
        p2 = sort_found[0][2]

        # calculate bearing
        if sort_found[0][0] <= tolerance ** 2:  # only rotate points within tolerance of lines, tolerance is squared, because the distance is also
            # Calculate rotation - will always be in the digitized direction
            angle = math.degrees(math.atan2(p1.x() - p2.x(), p1.y() - p2.y())) + offset
            
            if directional == 2:
                # Rotate 180 degrees
                angle = (angle + 180) % 360
            elif not directional or directional == 0:  ## if direction shouldn't be considered, we always place the symbol turning nicely upwards
                angle = (angle % 360) if math.cos(math.radians(angle % 360)) > 0 else ((angle % 360)-180)
            #elif directional == 1:
            #    pass

        else:
            angle = -360

        return angle
    else:
        return -360
