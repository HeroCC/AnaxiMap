#!/usr/bin/env python3

from setuptools import setup

setup(
  name             = "AnaxiTile",
  version          = "0.0.1",
  author           = "Conlan Cesar",
  author_email     = "herocc@herocc.com",
  description      = "Downloads and Stitches images grabbed from GIS Tile Services.",
  url              = "http://github.com/lschumm/seymour",
  install_requires = [
    "requests == 2.22.0",
    "Pillow   == 6.1.0",
  ]
)
