# osm2xodr
converter for OpenStreetMaps (.osm) to OpenDrive (.xodr) format (just the drivable roads right now - you can edit the code for other osm-ways - its in the function "parseAll()").

just adjust the filenames/paths in the main.py and run it
needs osmread, numpy, PIL and pyproj

If a topographymap is used, adjust the min/max latitudes/longitudes in the osm-header according to the map-coordinates
