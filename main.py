from OSMParser.Parsing import rNode, parseAll
from OSMParser.OpenDriveWriting import writeOdrive
import numpy as np

osmPfad = '/home/jhm/Downloads/osm2xodr/map.osm'
topographieKartenPfad = '/home/jhm/Downloads/osm2xodr/topomap.png'
xodrPfad = '/home/jhm/Downloads//osm2xodr/output.xodr'

parseAll(osmPfad, bildpfad=topographieKartenPfad, minimumHeight = 163.0, maximumHeight= 192.0, curveRadius=12)

with open(xodrPfad,'w') as f:
        f.write(writeOdrive())