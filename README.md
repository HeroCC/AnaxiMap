# Anaxi Tile Downloader
Downloads and stitches images downloaded from Map Tile servers.

## Dependencies
* Python 3
* Python Requests (`pip3 install --user requests==2.*`)
* Python Pillow (`pip3 install --user Pillow=6.*`) -- optional, used for image stitching

## Usage
After ensuring your dependencies are installed, you can run the program with `python3 tsdl.py`. It will prompt you for your bounding Lat and Long coordinates, zoom, and tile server URL. For best results, the larger the area you select with your lat & long, the smaller you should have your zoom. If your zoom is too big, downloading will take longer, your resulting stitched file will be larger, and the tile server may throttle / restrict your usage.

The program will tell you the coords it rounded to (make a note of these for geolocation, they are the top right and bottom left of the generated image), and start downloading the tiles to the `tiles/` folder. 

After downloading all tiles, you will be asked if you'd like to stitch together the images. Type "y" to continue, or anything else to exit. The tiles will be stitched together, and saved to a file named with the pattern `Map_XMIN-XMAX_YMIN-YMAX.(.png|.jpg)`. 

## Example
The following example will download and stitch tiles within an area of the MIT campus in Cambridge, Massachusetts.
```
$ python3 tsdl.py
Starting Anaxi Tile Downloader...
Enter Starting Latitude: 42.363531
Enter Starting Longitude: -71.096362
Enter Ending Latitude: 42.354185
Enter Ending Longitude: -71.069741
Zoom / Level of Detail (usually 0-18, larger = more data & detail): 14
Tile Server URL: https://b.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png
Starting at North-West corner: [42.37477836111418, -71.103515625]
Ending at South-East corner: [42.32606244456203, -71.03759765625]
Downloading X tiles 4956 through 4958
Downloading Y tiles 6059 through 6061
Downloading a total of 9 tiles
Skipping 14_4956_6059.png, it already exists
Skipping 14_4957_6059.png, it already exists
Downloading https://b.tile.openstreetmap.org/14/4958/6059.png to 14_4958_6059.png
Downloading https://b.tile.openstreetmap.org/14/4958/6060.png to 14_4958_6060.png
Downloading https://b.tile.openstreetmap.org/14/4958/6061.png to 14_4958_6061.png
...
Downloading successful! Would you like to stitch images together? (y/N) y
Stitching 14_4956_6059.png
Stitching 14_4957_6059.png
Stitching 14_4958_6059.png
Stitching 14_4956_6060.png
...
Stitched image saved to tiles/Map_4956-4958_6059-6061.png
```

## Potential Servers
Below is a small list of sources for Tile Servers. Beware, some of the linked servers have restrictions on usage, zoom, and may throttle or deny service if you violate their terms. 

To format the URL correctly, replace the zoom, x tile, and y tile spot with %zoom%, %xTile%, and %yTile% respectively. Ensure that the URL ends in a file extension (usually .jpg for satellite / terrain maps and .png for others), and that the tile server returns images that are 256px by 256px. You should have something that looks like this: `https://b.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png` 

* [MapTiler Cloud](https://cloud.maptiler.com/maps/) (free account for non-commercial use)
* https://wiki.openstreetmap.org/wiki/Tile_servers
* https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Tile_servers
* https://www.trailnotes.org/FetchMap/TileServeSource.html
* https://raw.githubusercontent.com/klakar/QGIS_resources/master/collections/Geosupportsystem/python/qgis_basemaps.py
