from OSMParser.Parsing import rNode, parseAll
from OSMParser.OpenDriveWriting import writeOdrive
import numpy as np

osmPfad = '/home/jhm/Downloads/map(12).osm'
topographieKartenPfad = '/home/jhm/Desktop/Arbeit/OSM2XODR/osm2xodr/topomap.png'
xodrPfad = '/home/jhm/Downloads/testout.xodr'


parseAll(osmPfad, bildpfad=topographieKartenPfad, minCurveRadius= 9)

with open(xodrPfad,'w') as f:
        f.write(writeOdrive())