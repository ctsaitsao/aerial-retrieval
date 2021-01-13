import os
import math
from urllib import request
from PIL import Image
import itertools 
import re
import osmnx as ox
import cv2
import matplotlib.pyplot as plt

### PART 1: AERIAL IMAGE RETRIEVAL ###

class TileSystem:  # class adapted from: https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system, translated to Python from C#

    def __init__(self):
        self.EarthRadius = 6378137
        self.MinLatitude = -85.05112878 
        self.MaxLatitude = 85.05112878
        self.MinLongitude = -180
        self.MaxLongitude = 180

    def Clip(self, n, minValue, maxValue):
        return min(max(n, minValue), maxValue)

    def MapSize(self, levelOfDetail):
        return 256 << levelOfDetail

    def GroundResolution(self, latitude, levelOfDetail):
        latitude = self.Clip(latitude, self.MinLatitude, self.MaxLatitude)
        return math.cos(latitude * math.pi / 180) * 2 * math.pi * self.EarthRadius / self.MapSize(levelOfDetail)

    def MapScale(self, latitude, levelOfDetail, screenDpi):
        return self.GroundResolution(latitude, levelOfDetail) * screenDpi / 0.0254

    def LatLongToPixelXY(self, latitude, longitude, levelOfDetail):
        latitude = self.Clip(latitude, self.MinLatitude, self.MaxLatitude)
        longitude = self.Clip(longitude, self.MinLongitude, self.MaxLongitude)

        x = (longitude + 180) / 360
        sinLatitude = math.sin(latitude * math.pi / 180)
        y = 0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi)
 
        mapSize = self.MapSize(levelOfDetail)
        pixelX = math.floor(self.Clip(x * mapSize + 0.5, 0, mapSize - 1))
        pixelY = math.floor(self.Clip(y * mapSize + 0.5, 0, mapSize - 1))
        return pixelX, pixelY

    def PixelXYToLatLong(self, pixelX, pixelY, levelOfDetail):
        mapSize = self.MapSize(levelOfDetail)
        x = (self.Clip(pixelX, 0, mapSize - 1) / mapSize) - 0.5
        y = 0.5 - 360 * (self.Clip(pixelY, 0, mapSize - 1) / mapSize)   ################################ 360!!!!

        latitude = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
        longitude = 360 * x
        return latitude, longitude

    def PixelXYToTileXY(self, pixelX, pixelY):
        tileX = math.floor(pixelX / 256)
        tileY = math.floor(pixelY / 256)
        return tileX, tileY

    def TileXYToPixelXY(self, tileX, tileY):
        pixelX = tileX * 256
        pixelY = tileY * 256
        return pixelX, pixelY

    def TileXYToQuadKey(self, tileX, tileY, levelOfDetail):   #######################
        tileXbits = '{0:0{1}b}'.format(tileX, levelOfDetail)
        tileYbits = '{0:0{1}b}'.format(tileY, levelOfDetail)

        quadKeyBin = ''.join(itertools.chain(*zip(tileYbits, tileXbits)))
        return ''.join([str(int(num, 2)) for num in re.findall('..?', quadKeyBin)])

    def QuadKeyToTileXY(self, quadKey):   #######
        quadKeyBin = ''.join(['{0:02b}'.format(int(num)) for num in quadKey])
        tileX, tileY = int(quadKeyBin[1::2], 2), int(quadKeyBin[::2], 2)
        return tileX, tileY

# NU Main campus coordinates:  
north = 42.062451
south = 42.049705
east = -87.668189
west = -87.686433  

# Interesting location (San Salvador, El Salvador) coordinates:
# north = 13.70389
# south = 13.6925
# east = -89.18
# west = -89.20167    

def retrieveAndStitch(tileX_start, tileX_end, tileY, levelOfDetail):
    image_list = []
    for tileX in range(tileX_start, tileX_end + 1):
        quadKey = tileSystem.TileXYToQuadKey(tileX, tileY, levelOfDetail)
        with request.urlopen('http://ecn.t0.tiles.virtualearth.net/tiles/a{}.jpeg?g=8549'.format(quadKey)) as file:
            img = Image.open(file)

        image_list.append(img)

    stitched_img = Image.new('RGB', (len(image_list) * 256, 256))
    for i, img in enumerate(image_list):
        stitched_img.paste(img, (i * 256, 0))
    return stitched_img

tileSystem = TileSystem()

levelOfDetail = 18

pixel_SW_X, pixel_SW_Y = tileSystem.LatLongToPixelXY(south, west, levelOfDetail)
pixel_NE_X, pixel_NE_Y = tileSystem.LatLongToPixelXY(north, east, levelOfDetail)

pixel_X_min = min(pixel_SW_X, pixel_NE_X)
pixel_X_max = max(pixel_SW_X, pixel_NE_X)
pixel_Y_min = min(pixel_SW_Y, pixel_NE_Y)
pixel_Y_max = max(pixel_SW_Y, pixel_NE_Y)

# tile_SW_X, tile_SW_Y = tileSystem.PixelXYToTileXY(pixel_SW_X, pixel_SW_Y)
# tile_NE_X, tile_NE_Y = tileSystem.PixelXYToTileXY(pixel_NE_X, pixel_NE_Y)

tile_SW_X, tile_SW_Y = tileSystem.PixelXYToTileXY(pixel_X_min, pixel_Y_min)
tile_NE_X, tile_NE_Y = tileSystem.PixelXYToTileXY(pixel_X_max, pixel_Y_max)

stitched_img = Image.new('RGB', ((tile_NE_X - tile_SW_X + 1) * 256, (tile_NE_Y - tile_SW_Y + 1) * 256))
for i in range(tile_SW_Y, tile_NE_Y + 1):
    hor_img = retrieveAndStitch(tile_SW_X, tile_NE_X, i, levelOfDetail)
    stitched_img.paste(hor_img, (0, (i - tile_SW_Y) * 256))

pixel_NW_X, pixel_NW_Y = tileSystem.TileXYToPixelXY(tile_SW_X, tile_SW_Y)
retrieved_img = stitched_img.crop((pixel_X_min - pixel_NW_X, pixel_Y_min - pixel_NW_Y, pixel_X_max - pixel_NW_X, pixel_Y_max - pixel_NW_Y))

print("Image retrieved.")

retrieved_img.save(os.path.join('images', 'aerial_image.jpeg'))

### PART 2: OSM DATA RETRIEVAL & IMAGE OVERLAYING ###

bg = cv2.imread('./images/aerial_image.jpeg', 1)
shrink_factor = 5
shrunk_height = int(round(bg.shape[0]/shrink_factor))
shrunk_width = int(round(bg.shape[1]/shrink_factor))
bg = cv2.resize(bg, (shrunk_width, shrunk_height))

graph = ox.graph_from_bbox(north, south, east, west, network_type='all', retain_all=True)
_, _ = ox.plot_graph(graph, bgcolor='black', show=False, save=True, filename='OSM_data', node_color='#FFFFFF', edge_color='#FFFFFF')

fg = cv2.imread('./images/OSM_data.png', 1)
fg = cv2.resize(fg, (shrunk_width, shrunk_height))

final = cv2.bitwise_or(fg, bg)
cv2.imwrite('./images/final.png', final)

cv2.imshow('final', final)
cv2.waitKey(0)  
cv2.destroyAllWindows()  