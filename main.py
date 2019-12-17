from OSMParser.Parsing import rNode, parseAll
from OSMParser.OpenDriveWriting import writeOdrive
import numpy as np

osmPfad = '/home/<USER>/Desktop/campusFreudenberg.osm'
topographieKartenPfad = '/home/<USER>/Desktop/OSM2XODR/osm2xodr/topomap.png'
xodrPfad = '/home/<USER>/Desktop/testout.xodr'

parseAll(osmPfad, bildpfad=topographieKartenPfad)

with open(xodrPfad,'w') as f:
        f.write(writeOdrive())