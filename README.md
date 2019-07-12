# Anaxi Tile Downloader
Downloads and stitches images downloaded from Map Tile servers.

## Potential Servers
Below is a small list of sources for Tile Servers. Beware, some of the linked servers have restrictions on usage, zoom, and may throttle or deny service if you violate their terms. 

To format the URL correctly, replace the zoom, x tile, and y tile spot with %zoom%, %xTile%, and %yTile% respectively. Ensure that the URL ends in a file extension (usually .jpg for satellite / terrain maps and .png for others). You should have something that looks like this: `https://c.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png` 

* https://wiki.openstreetmap.org/wiki/Tile_servers
* https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Tile_servers
* https://www.trailnotes.org/FetchMap/TileServeSource.html
* https://raw.githubusercontent.com/klakar/QGIS_resources/master/collections/Geosupportsystem/python/qgis_basemaps.py
