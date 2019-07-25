#!/usr/bin/python3
# Anaximander Map Tile Downloader
import argparse
import math
import os
import shutil
import sys

import requests

import tilenames


class AnaxiPreferences:
    def __init__(self, latStart, lonStart, latEnd, lonEnd, zoom, tileServer,
                 tilesDir="tiles", stitchFormat="", noStitch=False, interactive=True):
        self.latStart = latStart
        self.lonStart = lonStart
        self.latEnd = latEnd
        self.lonEnd = lonEnd
        self.zoom = zoom
        self.tileServer = tileServer
        self.tilesDir = tilesDir
        self.stitchFormat = stitchFormat
        self.noStitch = noStitch
        self.interactive = interactive


class Tile:
    def __init__(self, zoom, x, y, tileServer):
        self.zoom = zoom
        self.tileX = x
        self.tileY = y
        self.tileServer = tileServer

        self.tileServer = self.getProcessedURL()
        self.tileExtension = getFileExtension(tileServer)

    def download(self):
        fileName = self.getFileName()
        if self.doesTileImageFileExist():
            print("Skipping " + fileName + ", it already exists")
            return 200

        headers = {
            'User-Agent': 'Anaxi Open Source Tile Stitch Software'
        }

        # Tweaked from https://stackoverflow.com/a/18043472/1709894
        print("Downloading " + self.tileServer + " to " + fileName)
        tileRequest = requests.get(self.tileServer, stream=True, headers=headers)
        if tileRequest.status_code == 200:
            with open(self.getFileName(), 'wb') as tileImageFile:
                tileRequest.raw.decode_content = True
                shutil.copyfileobj(tileRequest.raw, tileImageFile)
        else:
            print("Error getting", fileName + ":", tileRequest.reason, "(" + str(tileRequest.status_code) + ")")

        return tileRequest.status_code

    def getProcessedURL(self):
        return self.tileServer.replace("%zoom%", str(self.zoom)).replace("%xTile%", str(self.tileX)).replace("%yTile%", str(self.tileY))

    def getFileName(self):
        return "%d_%d_%d%s" % (self.zoom, self.tileX, self.tileY, self.tileExtension)

    def doesTileImageFileExist(self):
        return os.path.isfile(self.getFileName())


class TileCollection:
    def __init__(self, tileStartX, tileStartY, tileEndX, tileEndY, zoom, tileServer):
        self.tileServer = tileServer
        self.tileStartX = tileStartX
        self.tileStartY = tileStartY
        self.tileEndX = tileEndX
        self.tileEndY = tileEndY
        self.zoom = zoom

        self.tiles = []
        for y in range(self.tileStartY, self.tileEndY + 1):
            for x in range(self.tileStartX, self.tileEndX + 1):
                self.tiles.append(Tile(self.zoom, x, y, self.tileServer))

    def downloadTiles(self):
        for tile in self.tiles:
            if tile.download() != 200:
                return 1
        return 0

    def getMaxTileSize(self):
        maxXpx = 0
        maxYpx = 0
        for tile in self.tiles:
            tileImage = Image.open(tile.getFileName())
            if tileImage.size[0] > maxXpx:
                print("Changing tile width to {}".format(tileImage.size[0]))
                maxXpx = tileImage.size[0]

            if tileImage.size[1] > maxYpx:
                print("Changing tile height to {}".format(tileImage.size[1]))
                maxYpx = tileImage.size[1]

        return maxXpx, maxYpx

    def stitchImages(self, stitchSaveFormat=""):
        checkPilInstalled()
        tilePixelSize = self.getMaxTileSize()

        width = abs((self.tileEndX - self.tileStartX)) * tilePixelSize[0]
        height = abs((self.tileStartY - self.tileEndY)) * tilePixelSize[1]

        image = Image.new("RGB", (width, height))

        for tile in self.tiles:
            fileName = tile.getFileName()

            xPastePixel = (tile.tileX - self.tileStartX) * tilePixelSize[0]
            yPastePixel = height - (self.tileEndY - tile.tileY) * tilePixelSize[1]

            tileImage = Image.open(fileName)

            print("Stitching " + fileName)
            image.paste(tileImage, (xPastePixel, yPastePixel))

        image.info['tileStartX'] = self.tileStartX
        image.info['tileStartY'] = self.tileStartY
        image.info['tileEndX'] = self.tileEndX
        image.info['tileEndY'] = self.tileEndY

        if not stitchSaveFormat:
            stitchSaveFormat = self.tiles[0].tileExtension

        stitchedImageName = "Map_{}_{}-{}_{}-{}{}".format(self.zoom,
                                                          self.tileStartX, self.tileEndX,
                                                          self.tileStartY, self.tileEndY,
                                                          stitchSaveFormat)
        print("Saving to {}...".format(stitchedImageName))
        image.save(stitchedImageName)
        print("Stitched image saved to {}".format(os.path.abspath(stitchedImageName)))

        return 0


def checkPilInstalled():
    try:
        global Image
        from PIL import Image
    except (ImportError, ModuleNotFoundError) as e:
        print("ERROR: Stitching images requires the Pillow library")
        raise


def promptForStitchExtension(defaultExtention):
    # Full supported file format list here: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    # To get from code: list(set(Image.registered_extensions().values())
    newExt = input("Format to save as [Blank for suggested, or .jpg, .png, .tiff, etc]: ")
    if not newExt:
        return defaultExtention
    else:
        print("New filetype extension is '{}'".format(newExt))
        return newExt


def interactivePromptPrefs():
    latStart = float(input("Enter Starting Latitude: "))
    lonStart = float(input("Enter Starting Longitude: "))

    latEnd = float(input("Enter Ending Latitude: "))
    lonEnd = float(input("Enter Ending Longitude: "))

    zoom = int(input("Zoom / Level of Detail (usually 0-18, larger = more data & detail): "))
    tileServer = str(input("Tile Server URL: "))
    while getFileExtension(tileServer) == "":
        print("The Tile Server URL must end with a file type extension (ex. .jpg, .png, etc)")
        tileServer = str(input("Tile Server URL: "))

    return AnaxiPreferences(latStart, lonStart, latEnd, lonEnd, zoom, tileServer)


def commandLinePrefsParse():
    parser = argparse.ArgumentParser(description="Download and stitch tile images from GIS Tile Servers")
    coordsGroup = parser  # parser.add_argument_group('coords')
    coordsGroup.add_argument('latStart', type=float, help="Starting Latitude Coordinate")
    coordsGroup.add_argument('lonStart', type=float, help="Starting Longitude Coordinate")
    coordsGroup.add_argument('latEnd', type=float, help="Ending Latitude Coordinate")
    coordsGroup.add_argument('lonEnd', type=float, help="Ending Longitude Coordinate")
    parser.add_argument('zoom', type=int, help="Level of Zoom / Detail (more zoom + large area = huge image)")
    parser.add_argument('tileServer', type=str, help="URL of the Tile Server to download from")
    parser.add_argument('--tilesDir', type=str, default="tiles", help="Where to save tiles / Map")
    parser.add_argument('--stitchFormat', type=str, default="", help="Format to save stitched Map as")
    parser.add_argument('--noStitch', action='store_true', help="Don't stitch tiles together")

    args = parser.parse_args()
    return AnaxiPreferences(args.latStart, args.lonStart, args.latEnd, args.lonEnd,
                            args.zoom, args.tileServer, args.tilesDir, args.stitchFormat, noStitch=args.noStitch)


def getFileExtension(tileServerURL):
    return str(os.path.splitext(tileServerURL)[1].split("?", 1)[0])  # Remove extra URL params from extension


def processTileParams(prefs):
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

    tileCol = TileCollection(tileStartX, tileStartY, tileEndX, tileEndY, prefs.zoom, prefs.tileServer)

    downloadErr = tileCol.downloadTiles()
    if downloadErr == 0:
        print("Download Complete!")
        if prefs.interactive:
            stitchResponse = input("Downloading successful! Would you like to stitch images together? (Y/n) ")
            if "n" not in stitchResponse:
                if not prefs.stitchFormat:
                    prefs.stitchFormat = promptForStitchExtension(tileCol.tiles[0].tileExtension)
                return tileCol.stitchImages(prefs.stitchFormat)
            else:
                print("Not stitching images. Goodbye!")
                return downloadErr
        elif not prefs.noStitch:
            print("Stitching images...")
            if not prefs.stitchFormat:
                prefs.stitchFormat = tileCol.tiles[0].tileExtension
            return tileCol.stitchImages(prefs.stitchFormat)

    return downloadErr


def main():
    print("Starting Anaxi Tile Downloader...")

    prefs = None
    if len(sys.argv) > 1:
        prefs = commandLinePrefsParse()
        prefs.interactive = False
    else:
        prefs = interactivePromptPrefs()
        prefs.interactive = True

    #prefs = AnaxiPreferences(latStart=42.363531, lonStart=-71.096362, latEnd=42.354185, lonEnd=-71.069741,
    #                                zoom=17, tileServer="https://c.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png")

    #prefs.tileServer = "http://tile.stamen.com/terrain-background/%zoom%/%xTile%/%yTile%.jpg"
    #prefs.tileServer = "https://api.maptiler.com/maps/hybrid/256/%zoom%/%xTile%/%yTile%.jpg?key={}".format(os.getenv("MAPTILER"))

    return processTileParams(prefs)


if __name__ == "__main__":
    exit(main())
