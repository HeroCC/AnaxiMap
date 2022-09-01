#!/usr/bin/python3
# Anaximander Map Tile Downloader
import argparse
import math
import os
import random
import shutil
import sys
from mimetypes import guess_extension

import requests

import tilenames


class AnaxiPreferences:
    def __init__(self, latStart, lonStart, latEnd, lonEnd, zoom, tileServer,
                 name="tiles", stitchFormat="", noStitch=False, interactive=True, forceDownload=False,
                 dryRun=False):
        self.latStart = latStart
        self.lonStart = lonStart
        self.latEnd = latEnd
        self.lonEnd = lonEnd
        self.zoom = zoom
        self.tileServer = tileServer
        self.name = name
        self.stitchFormat = stitchFormat
        self.noStitch = noStitch
        self.interactive = interactive
        self.forceDownload = forceDownload
        self.dryRun = dryRun


class Tile:
    def __init__(self, zoom, x, y, tileServer):
        self.zoom = zoom
        self.tileX = x
        self.tileY = y
        self.tileServer = tileServer

        self.tileServer = self.getProcessedURL()
        self.tileExtension = getFileExtension(tileServer)

    def download(self, forceDownload=False):
        fileName = self.getFileName()
        if self.doesTileImageFileExist() and not forceDownload:
            if self.isCorruptFile():
                print("Cached image possibly corrupt, downloading again")
            else:
                print("Skipping " + fileName + ", it already exists")
                return 200

        headers = {
            'User-Agent': 'Anaxi Open Source Tile Stitch Software'
        }

        # Tweaked from https://stackoverflow.com/a/18043472/1709894
        tileRequest = requests.get(self.tileServer, stream=True, headers=headers)
        if tileRequest.status_code == 200:
            if not self.tileExtension:
                self.tileExtension = guess_extension(tileRequest.headers['content-type'], strict=False)
                if self.tileExtension == ".jpe":
                    # There is a bug in Python's Mimetypes library, fixed in later versions, that chooses .jpe for .jpg
                    # Despite .JPG being much more recognized
                    self.tileExtension = ".jpg"
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

    def isCorruptFile(self):
        if checkPilInstalled():
            try:
                Image.open(self.getFileName())
            except OSError as e:
                return True

        return False  # assume not corrupt if PIL isn't installed


class TileCollection:
    def __init__(self, tileStartX, tileStartY, tileEndX, tileEndY, zoom, tileServer, name):
        self.tileServer = tileServer
        self.tileStartX = tileStartX
        self.tileStartY = tileStartY
        self.tileEndX = tileEndX
        self.tileEndY = tileEndY
        self.zoom = zoom
        self.name = name

        self.tiles = []
        self.__regenTiles()

    def downloadTiles(self, forceDownload=False):
        error = 0
        if not getFileExtension(self.tileServer) and not forceDownload:
            tile = self.tiles[0]
            tile.download()
            print("Guessing future tile extensions will be", tile.tileExtension + ". Pass --forceDownload to bypass")
            newExt = tile.tileExtension
            for tile in self.tiles:
                # Regening the tiles with the new extension breaks some download URLs, and not doing so breaks cache.
                # This is a happy medium, although a bit hacky
                tile.tileExtension = newExt
            #self.tileServer += tile.tileExtension
            #self.__regenTiles()

        downloadedTiles = 0
        for tile in self.tiles:
            downloadResult = tile.download(forceDownload)
            downloadedTiles += 1
            print("Saving [" + str(downloadedTiles), "of", str(len(self.tiles)) + "]", tile.getProcessedURL(), "to", tile.getFileName())
            if downloadResult != 200:
                error = 1
                if not forceDownload:
                    break

        return error

    def __regenTiles(self):
        self.tiles = []
        for y in range(self.tileStartY, self.tileEndY + 1):
            for x in range(self.tileStartX, self.tileEndX + 1):
                self.tiles.append(Tile(self.zoom, x, y, self.tileServer))

    def getMapName(self, stitchSaveFormat=""):
        if not stitchSaveFormat:
            stitchSaveFormat = self.tiles[0].tileExtension

        stitchSaveFormat = stitchSaveFormat.strip()

        if self.name != "tiles":
            return self.name + stitchSaveFormat

        return "Map_{}_{}-{}_{}-{}{}".format(self.zoom, self.tileStartX, self.tileEndX, self.tileStartY, self.tileEndY, stitchSaveFormat)

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
        if not checkPilInstalled():
            print("ERROR: Stitching images requires the Pillow library")
            return 10

        for tile in self.tiles:
            if tile.isCorruptFile():
                print(tile.getFileName(), "may be corrupt, redownloading")
                tile.download(forceDownload=True)

        tilePixelSize = self.getMaxTileSize()

        width = abs((self.tileEndX - self.tileStartX)) * tilePixelSize[0]
        height = abs((self.tileStartY - self.tileEndY)) * tilePixelSize[1]

        image = Image.new("RGB" + ("A" if stitchSaveFormat not in [".jpg", ".jpeg"] else ""), (width, height))

        stitchedTiles = 0
        for tile in self.tiles:
            fileName = tile.getFileName()

            xPastePixel = (tile.tileX - self.tileStartX) * tilePixelSize[0]
            yPastePixel = height - (self.tileEndY - tile.tileY) * tilePixelSize[1]

            tileImage = Image.open(fileName)

            image.paste(tileImage, (xPastePixel, yPastePixel))
            stitchedTiles += 1
            print("Stitched [" + str(stitchedTiles), "of", str(len(self.tiles)) + "]", fileName)

        image.info['tileStartX'] = self.tileStartX
        image.info['tileStartY'] = self.tileStartY
        image.info['tileEndX'] = self.tileEndX
        image.info['tileEndY'] = self.tileEndY

        stitchedImageName = self.getMapName(stitchSaveFormat)
        print("Saving to {}...".format(stitchedImageName))
        image.save(stitchedImageName)
        print("Stitched image saved to {}".format(os.path.abspath(stitchedImageName)))

        return {'err': 0, 'image': image, 'imageName': stitchedImageName}


def checkPilInstalled():
    installed = False
    try:
        global Image
        from PIL import Image
        installed = True
    except (ImportError, ModuleNotFoundError) as e:
        pass
    return installed


def getDefaultTileServers():
    # Connections sourced, with a few tweaks, from 
    # https://raw.githubusercontent.com/klakar/QGIS_resources/master/collections/Geosupportsystem/python/qgis_basemaps.py
    # [sourcetype, title, authconfig, password, license, url, username, zmax, zmin]

    sources = []
    sources.append(["connections-xyz", "Google Maps", "", "", "", "https://mt.google.com/vt/lyrs=m&x=%xTile%&y=%yTile%&z=%zoom%", "", "19", "0"])
    sources.append(["connections-xyz", "Google Satellite", "", "", "", "https://mt.google.com/vt/lyrs=s&x=%xTile%&y=%yTile%&z=%zoom%", "", "19", "0"])
    sources.append(["connections-xyz", "Google Terrain", "", "", "", "https://mt.google.com/vt/lyrs=t&x=%xTile%&y=%yTile%&z=%zoom%", "", "19", "0"])
    sources.append(["connections-xyz", "Google Terrain Hybrid", "", "", "", "https://mt.google.com/vt/lyrs=p&x=%xTile%&y=%yTile%&z=%zoom%", "", "19", "0"])
    sources.append(["connections-xyz", "Google Satellite Hybrid", "", "", "", "https://mt.google.com/vt/lyrs=y&x=%xTile%&y=%yTile%&z=%zoom%", "", "19", "0"])
    sources.append(["connections-xyz", "US National Map Imagery", "", "", "Public Domain (Excluding Alaska) https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer", "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "16", "0"]),
    sources.append(["connections-xyz", "Stamen Terrain", "", "", "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL", "http://tile.stamen.com/terrain/%zoom%/%xTile%/%yTile%.png", "", "20", "0"])
    sources.append(["connections-xyz", "Stamen Toner", "", "", "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL", "http://tile.stamen.com/toner/%zoom%/%xTile%/%yTile%.png", "", "20", "0"])
    sources.append(["connections-xyz", "Stamen Toner Light", "", "", "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL", "http://tile.stamen.com/toner-lite/%zoom%/%xTile%/%yTile%.png", "", "20", "0"])
    sources.append(["connections-xyz", "Stamen Watercolor", "", "", "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL", "http://tile.stamen.com/watercolor/%zoom%/%xTile%/%yTile%.jpg", "", "18", "0"])
    sources.append(["connections-xyz", "Wikimedia Map", "", "", "OpenStreetMap contributors, under ODbL", "https://maps.wikimedia.org/osm-intl/%zoom%/%xTile%/%yTile%.png", "", "20", "1"])
    sources.append(["connections-xyz", "Wikimedia Hike Bike Map", "", "", "OpenStreetMap contributors, under ODbL", "http://tiles.wmflabs.org/hikebike/%zoom%/%xTile%/%yTile%.png", "", "17", "1"])
    sources.append(["connections-xyz", "Esri Boundaries Places", "", "", "", "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "20", "0"])
    sources.append(["connections-xyz", "Esri Gray (dark)", "", "", "", "http://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "16", "0"])
    sources.append(["connections-xyz", "Esri Gray (light)", "", "", "", "http://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "16", "0"])
    sources.append(["connections-xyz", "Esri National Geographic", "", "", "", "http://services.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "12", "0"])
    sources.append(["connections-xyz", "Esri Ocean", "", "", "", "https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "10", "0"])
    sources.append(["connections-xyz", "Esri Satellite", "", "", "", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "17", "0"])
    sources.append(["connections-xyz", "Esri Standard", "", "", "", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "17", "0"])
    sources.append(["connections-xyz", "Esri Terrain", "", "", "", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "13", "0"])
    sources.append(["connections-xyz", "Esri Transportation", "", "", "", "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "20", "0"])
    sources.append(["connections-xyz", "Esri Topo World", "", "", "", "http://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/%zoom%/%yTile%/%xTile%", "", "20", "0"])
    sources.append(["connections-xyz", "OpenStreetMap Standard", "", "", "OpenStreetMap contributors, CC-BY-SA", "http://tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png", "", "19", "0"])
    sources.append(["connections-xyz", "OpenStreetMap H.O.T.", "", "", "OpenStreetMap contributors, CC-BY-SA", "http://tile.openstreetmap.fr/hot/%zoom%/%xTile%/%yTile%.png", "", "19", "0"])
    sources.append(["connections-xyz", "OpenStreetMap Monochrome", "", "", "OpenStreetMap contributors, CC-BY-SA", "http://tiles.wmflabs.org/bw-mapnik/%zoom%/%xTile%/%yTile%.png", "", "19", "0"])
    sources.append(["connections-xyz", "OpenTopoMap", "", "", "Kartendaten: © OpenStreetMap-Mitwirkende, SRTM | Kartendarstellung: © OpenTopoMap (CC-BY-SA)", "https://tile.opentopomap.org/%zoom%/%xTile%/%yTile%.png", "", "17", "1"])
    sources.append(["connections-xyz", "CartoDb Dark Matter", "", "", "Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.", "http://basemaps.cartocdn.com/dark_all/%zoom%/%xTile%/%yTile%.png", "", "20", "0"])
    sources.append(["connections-xyz", "CartoDb Positron", "", "", "Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.", "http://basemaps.cartocdn.com/light_all/%zoom%/%xTile%/%yTile%.png", "", "20", "0"])
    return sources


def printDefaultTileSources():
    print("Below are some builtin tile servers. "
          "IDs are prone to change, we recommend you use this as a reference and hardcode your URLs. "
          "Use the IDs anywhere a Tile server URL can be used")
    for i, source in enumerate(getDefaultTileServers()):
        printDefaultSourceData(source, i)


def printDefaultSourceData(source, i=""):
    sourceName = source[1]
    sourceLicense = source[4]
    sourceURL = source[5]
    sourceZoom = [int(source[8]), int(source[7])]

    indentation = '    '

    print(i, sourceName + ":")
    print(indentation + "URL:", sourceURL)
    print(indentation + "License:", sourceLicense)
    print(indentation + "[Min, Max] Zoom:", sourceZoom)
    print()


def interactivePromptPrefs():
    latStart = float(input("Enter Starting Latitude: "))
    lonStart = float(input("Enter Starting Longitude: "))

    latEnd = float(input("Enter Ending Latitude: "))
    lonEnd = float(input("Enter Ending Longitude: "))

    zoom = int(input("Zoom / Level of Detail (usually 0-18, larger = more data & detail): "))
    tileServer = str(input("Tile Server URL or ID: "))

    prefs = AnaxiPreferences(latStart, lonStart, latEnd, lonEnd, zoom, tileServer, interactive=True)

    stitch = str(input("Would you like to stitch images together after downloading? (Y/n) ")).lower()
    if stitch.startswith("y") or not stitch.strip():
        prefs.noStitch = False

        # Full supported file format list here: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
        # To get from code: list(set(Image.registered_extensions().values())
        prefs.stitchFormat = str(input("Format to save as [Blank for suggested, or .jpg, .png, .tiff, etc]: ")).strip()
    else:
        print("Not stitching tiles")
        prefs.noStitch = True

    return prefs


def commandLinePrefsParse():
    parser = argparse.ArgumentParser(description="Download and stitch tile images from GIS / TMS Tile Servers")
    coordsGroup = parser  # parser.add_argument_group('coords')
    coordsGroup.add_argument('latStart', type=float, help="Starting Latitude Coordinate")
    coordsGroup.add_argument('lonStart', type=float, help="Starting Longitude Coordinate")
    coordsGroup.add_argument('latEnd', type=float, help="Ending Latitude Coordinate")
    coordsGroup.add_argument('lonEnd', type=float, help="Ending Longitude Coordinate")
    parser.add_argument('zoom', type=int, help="Level of Zoom / Detail (more zoom + large area = huge image)")
    parser.add_argument('tileServer', type=str, help="URL (or ID) of the Tile Server to download from")
    parser.add_argument('--name', type=str, default="tiles", help="Where to save tiles / Map")
    parser.add_argument('--stitchFormat', type=str, default="", help="Format to save stitched Map as")
    parser.add_argument('--noStitch', action='store_true', help="Don't stitch tiles together")
    parser.add_argument('--forceDownload', action='store_true', help="Skip checking if files are already downloaded")
    parser.add_argument('--printSourcesAndExit', action='store_true', help="Print known tile sources and exit")  # Not handled by argparse
    parser.add_argument('--dryRun', action='store_true', help="Print download area, expected number of tiles and exit")

    args = parser.parse_args()
    return AnaxiPreferences(args.latStart, args.lonStart, args.latEnd, args.lonEnd, args.zoom, args.tileServer,
                            args.name, args.stitchFormat, interactive=False, noStitch=args.noStitch,
                            forceDownload=args.forceDownload, dryRun=args.dryRun)


def getFileExtension(tileServerURL):
    return str(os.path.splitext(tileServerURL)[1].split("?", 1)[0])  # Remove extra URL params from extension


def genInfoFile(tileCollection):
    infoFileName = tileCollection.getMapName(" ") + ".info"
    print("Writing info file to", infoFileName)

    # S lat, W lon, N lat, E lon
    startCornerCoords = tilenames.tileEdges(tileCollection.tileStartX, tileCollection.tileStartY, tileCollection.zoom)
    endCornerCoords = tilenames.tileEdges(tileCollection.tileEndX, tileCollection.tileEndY, tileCollection.zoom)

    latStartCorner, lonStartCorner = startCornerCoords[2], startCornerCoords[1]  # Get's north-west tile start lat & lon
    latEndCorner, lonEndCorner = endCornerCoords[0], endCornerCoords[3]  # Get's south-east tile end lat & lon

    infoFile = open(infoFileName, "w")
    print("// Generated with Anaxi Tile Downloader", file=infoFile)
    print("lat_north=", latStartCorner, file=infoFile)
    print("lat_south=", latEndCorner, file=infoFile)
    print("lon_east=", lonEndCorner, file=infoFile)
    print("lon_west=", lonStartCorner, file=infoFile)
    print("tileStartX=", tileCollection.tileStartX, file=infoFile)
    print("tileStartY=", tileCollection.tileStartY, file=infoFile)
    print("tileEndX=", tileCollection.tileEndX, file=infoFile)
    print("tileEndY=", tileCollection.tileEndY, file=infoFile)
    print("zoom=", tileCollection.zoom, file=infoFile)
    print("numTiles=", len(tileCollection.tiles), file=infoFile)
    print("mapFile=", tileCollection.getMapName(), file=infoFile)
    print("cmd=", " ".join(sys.argv), file=infoFile)


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

    print("Each tile at this zoom will be ~", str(tilenames.horozontalDistance(latStartCorner, prefs.zoom)), "meters wide")

    if prefs.dryRun:
        try:
            checkPilInstalled()
        except (ImportError, ModuleNotFoundError) as e:
            print("PIL is not installed, image stitching will not be supported")

        print("Dry run, exiting now...")
        return 0

    if not os.path.exists(prefs.name):
        os.mkdir(prefs.name)

    os.chdir(prefs.name)

    tileCol = TileCollection(tileStartX, tileStartY, tileEndX, tileEndY, prefs.zoom, prefs.tileServer, prefs.name)

    if not os.path.exists("raw"):
        os.mkdir("raw")

    os.chdir("raw")

    downloadErr = tileCol.downloadTiles(prefs.forceDownload)
    if downloadErr == 0:
        print("Download Complete!")
        if not prefs.noStitch:
            print("Stitching images...")
            stitchResult = tileCol.stitchImages(prefs.stitchFormat)
            if stitchResult["err"] == 0:
                os.rename(stitchResult["imageName"], "../" + stitchResult["imageName"])
                os.chdir("..")
                return genInfoFile(tileCol)

    return downloadErr


def main():
    print("Starting Anaxi Tile Downloader... \n")

    if len(sys.argv) > 1:
        if sys.argv[1] == "--printSourcesAndExit":
            printDefaultTileSources()
            exit(0)

        prefs = commandLinePrefsParse()
    else:
        prefs = interactivePromptPrefs()

    try:
        tid = int(prefs.tileServer)
        tileSource = getDefaultTileServers()[tid]

        print("Using", tileSource[1], "as Tile Server Source")
        printDefaultSourceData(tileSource)
        prefs.tileServer = getDefaultTileServers()[tid][5]
    except ValueError:
        pass

    if not getFileExtension(prefs.tileServer):
        print("WARNING: The source you've given does not have a filetype extension. "
              "We will do our best to guess, though this sometimes fails. \n")

    #prefs = AnaxiPreferences(latStart=42.363531, lonStart=-71.096362, latEnd=42.354185, lonEnd=-71.069741,
    #                                zoom=17, tileServer="https://c.tile.openstreetmap.org/%zoom%/%xTile%/%yTile%.png")

    #prefs.tileServer = "http://tile.stamen.com/terrain-background/%zoom%/%xTile%/%yTile%.jpg"
    #prefs.tileServer = "https://api.maptiler.com/maps/hybrid/256/%zoom%/%xTile%/%yTile%.jpg?key={}".format(os.getenv("MAPTILER"))

    return processTileParams(prefs)


if __name__ == "__main__":
    exit(main())
