#!/usr/bin/python3
# Anaximander Map Tile Downloader
import math
import os
import shutil

import requests

import tilenames


class TileDownloadPreferences:
    def __init__(self, latStart, lonStart, latEnd, lonEnd, zoom, tileServer, tilesDir="tiles"):
        self.latStart = latStart
        self.lonStart = lonStart
        self.latEnd = latEnd
        self.lonEnd = lonEnd
        self.zoom = zoom
        self.tileServer = tileServer
        self.tilesDir = tilesDir


def getTileFileName(zoom, tileX, tileY, tileExtension):
    return "%d_%d_%d%s" % (zoom, tileX, tileY, tileExtension)


def downloadTile(tileX, tileY, zoom, tileServer, tileExtension):
    processedURL = tileServer.replace("%zoom%", str(zoom)).replace("%xTile%", str(tileX)).replace("%yTile%", str(tileY))
    fileName = getTileFileName(zoom, tileX, tileY, tileExtension)
    if os.path.isfile(fileName):
        print("Skipping " + fileName + ", it already exists")
        return 200

    headers = {
        'User-Agent': 'Anaxi Open Source Tile Stitch Software'
    }

    # Tweaked from https://stackoverflow.com/a/18043472/1709894
    print("Downloading " + processedURL + " to " + fileName)
    tileRequest = requests.get(processedURL, stream=True, headers=headers)
    if tileRequest.status_code == 200:
        with open(fileName, 'wb') as tileImageFile:
            tileRequest.raw.decode_content = True
            shutil.copyfileobj(tileRequest.raw, tileImageFile)
    else:
        print("Error getting", fileName + ":", tileRequest.reason, "(" + str(tileRequest.status_code) + ")")

    return tileRequest.status_code


def downloadTiles(tileStartX, tileStartY, tileEndX, tileEndY, zoom, tileServer, tileExtension):
    err = 0
    # Add 1 to end coord to make range act inclusive
    for y in range(tileStartY, tileEndY + 1):
        for x in range(tileStartX, tileEndX + 1):
            responseCode = downloadTile(x, y, zoom, tileServer, tileExtension)
            if responseCode != 200:
                err = 1
                return err
    return err


def stitchImages(tileStartX, tileStartY, tileEndX, tileEndY, zoom, tileExtension):
    try:
        from PIL import Image
    except ImportError:
        print("Stitching images requires the Pillow library")
        raise

    tilePixelSize = tilenames.tileSizePixels()

    width = abs((tileEndX - tileStartX)) * tilePixelSize
    height = abs((tileStartY - tileEndY)) * tilePixelSize

    image = Image.new("RGB", (width, height))

    for y in range(tileStartY, tileEndY + 1):
        for x in range(tileStartX, tileEndX + 1):
            fileName = getTileFileName(zoom, x, y, tileExtension)
            if not os.path.isfile(fileName):
                print("Aborting stitch, expected " + fileName + " but it wasn't found")
                return 2

            xPastePixel = (x - tileStartX) * tilePixelSize
            yPastePixel = height - (tileEndY - y) * tilePixelSize

            tileImage = Image.open(fileName)
            print("Stitching " + fileName)
            image.paste(tileImage, (xPastePixel, yPastePixel))

    image.info['tileStartX'] = tileStartX
    image.info['tileStartY'] = tileStartY
    image.info['tileEndX'] = tileEndX
    image.info['tileEndY'] = tileEndY

    stitchedImageName = "Map_{}-{}_{}-{}{}".format(tileStartX, tileEndX, tileStartY, tileEndY, tileExtension)
    image.save(stitchedImageName)
    print("Stitched image saved to " + os.path.abspath(stitchedImageName))

    return 0


def interactivePromptPrefs():
    latStart = float(input("Enter Starting Latitude: "))
    lonStart = float(input("Enter Starting Longitude: "))

    latEnd = float(input("Enter Ending Latitude: "))
    lonEnd = float(input("Enter Ending Longitude: "))

    zoom = int(input("Zoom / Level of Detail (usually 0-18, larger = more data & detail): "))
    tileServer = str(input("Tile Server URL: "))

    return TileDownloadPreferences(latStart, lonStart, latEnd, lonEnd, zoom, tileServer)


def processTileParams(prefs):
    tileExtension = os.path.splitext(prefs.tileServer)[1]
    if tileExtension == "":
        print("The Tile Server URL must end with a file type extension (ex. .jpg, .png, etc)")
        return 3

    tileStartX, tileStartY = tilenames.tileXY(prefs.latStart, prefs.lonStart, prefs.zoom, True)
    tileEndX, tileEndY = tilenames.tileXY(prefs.latEnd, prefs.lonEnd, prefs.zoom, True)

    # Sort the numbers low to high
    if tileStartY > tileEndY:
        tileStartY, tileEndY = tileEndY, tileStartY

    if tileStartX > tileEndX:
        tileStartX, tileEndX = tileEndX, tileStartX

    tileStartX, tileStartY = math.floor(tileStartX), math.floor(tileStartY)
    tileEndX, tileEndY = math.ceil(tileEndX), math.ceil(tileEndY)

    # S lat, W lon, N lat, E lon
    startCornerCoords = tilenames.tileEdges(tileStartX, tileStartY, prefs.zoom)
    endCornerCoords = tilenames.tileEdges(tileEndX, tileEndY, prefs.zoom)

    latStartCorner, lonStartCorner = startCornerCoords[2], startCornerCoords[1]  # Get's north-west tile start lat & lon
    latEndCorner, lonEndCorner = endCornerCoords[0], endCornerCoords[3]  # Get's south-east tile end lat & lon

    print("Starting at North-West corner: [" + str(latStartCorner) + ", " + str(lonStartCorner) + "]")
    print("Ending at South-East corner: [" + str(latEndCorner) + ", " + str(lonEndCorner) + "]")

    print("Downloading X tiles", tileStartX, "through", tileEndX)
    print("Downloading Y tiles", tileStartY, "through", tileEndY)

    print("Downloading a total of", abs(tileEndX - tileStartX + 1) * abs(tileEndY - tileStartY + 1), "tiles")

    if not os.path.exists(prefs.tilesDir):
        os.mkdir(prefs.tilesDir)

    os.chdir(prefs.tilesDir)

    downloadErr = downloadTiles(tileStartX, tileStartY, tileEndX, tileEndY, prefs.zoom, prefs.tileServer, tileExtension)
    if downloadErr == 0:
        stitchResponse = input("Downloading successful! Would you like to stitch images together? (y/N) ")
        if "y" in stitchResponse:
            stitchErr = stitchImages(tileStartX, tileStartY, tileEndX, tileEndY, prefs.zoom, tileExtension)
            return stitchErr
        else:
            print("Not stitching images. Goodbye!")
            return downloadErr

    return downloadErr


def main():
    print("Starting Anaxi Tile Downloader...")

    prefs = interactivePromptPrefs()
    #prefs = TileDownloadPreferences(latStart=42.363531, lonStart=-71.096362, latEnd=42.354185, lonEnd=-71.069741,
    #                                zoom=17, tileServer="https://c.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png")

    #tileServer = "http://tile.stamen.com/terrain-background/%zoom%/%xTile%/%yTile%.jpg"

    return processTileParams(prefs)


if __name__ == "__main__":
    exit(main())
