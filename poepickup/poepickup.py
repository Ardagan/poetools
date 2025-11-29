import os
import pyautogui
import ctypes
import time
from PIL import ImageGrab
import numpy as np
import cv2 as cv
import keyboard
import math
import winsound
import json

HOTKEY = ']'
EXIT_HOTKEY = '['
PIPETTE_HOTKEY = '\\'

LOOT_COLORS = [
   (213, 159, 0),
   (119, 200, 160),
   (171, 122, 221),
   (210, 178, 134),
   (248, 150, 13),
   (235, 220, 244),
   (235, 235, 235),
   (166, 113, 217),
   (180, 0, 254),
   (239, 88, 28),
   (28, 141, 192),
   (34, 0, 22),
   (255, 255, 255)
   ]

COLOR_DEVIATION = 2
CONTOUR_SIZE = 500

windowHeight = 1900
windowWidth = 1024
windowCenter = (windowWidth/2, windowHeight/2)

def init(): 
   global windowHeight, windowWidth, windowCenter, HOTKEY, EXIT_HOTKEY, LOOT_COLORS, PIPETTE_HOTKEY

   windowWidth = ctypes.windll.user32.GetSystemMetrics(0)
   windowHeight = ctypes.windll.user32.GetSystemMetrics(1)
   windowCenter = (windowWidth/2, windowHeight/2)

   configData = {}
   with open('config.json', 'r') as config_file:
      configData = json.load(config_file)
   
   HOTKEY = configData.get("hotkey", HOTKEY)
   EXIT_HOTKEY = configData.get('exit_hotkey', EXIT_HOTKEY)
   LOOT_COLORS = configData.get('loot_colors', LOOT_COLORS)
   PIPETTE_HOTKEY = configData.get('pipette_hotkey', PIPETTE_HOTKEY)


def leftClick(cX, cY, sleep=0.01, doReturn = False):
   last = pyautogui.position()
   ctypes.windll.user32.SetCursorPos(cX, cY)
   time.sleep(0.015)
   ctypes.windll.user32.mouse_event(2, 0, 0, 0,0) # left down
   time.sleep(0.005)
   ctypes.windll.user32.mouse_event(4, 0, 0, 0,0) # left up
   if (doReturn):
      ctypes.windll.user32.SetCursorPos(int(last[0]), int(last[1]))

def extrapolate(xVals, yVals, lagCompensation = 1.0):
   if len(xVals) < 2 or len(yVals) < 2:
      return (0, 0)

   slope = (xVals[1] - xVals[0]) * lagCompensation, (yVals[1] - yVals[0]) * lagCompensation
   return slope


def calculateBounds(lootColor):
   lowerBound = (
      max(0, min(255,lootColor[0] - COLOR_DEVIATION)),
      max(0, min(255,lootColor[1] - COLOR_DEVIATION)),
      max(0, min(255,lootColor[2] - COLOR_DEVIATION)))
   upperBound = (
      max(0, min(255,lootColor[0] + COLOR_DEVIATION)),
      max(0, min(255,lootColor[1] + COLOR_DEVIATION)),
      max(0, min(255,lootColor[2] + COLOR_DEVIATION)))
   return [lowerBound,upperBound]


def getFrameSnapshot():
   imgSrc = ImageGrab.grab(bbox=(0, 0, windowWidth, windowHeight))
   # imgSrc.show()
   imgArray = np.array(imgSrc)
   return imgArray


def findLoot(frame, lootColor):
   ### detect the loot ###
   bounds = calculateBounds(lootColor)

   ### build grayscale to simplify search
   frameGray = cv.inRange(frame, bounds[0], bounds[1])

   ### Set all grayscale image to max values
   _, thresh = cv.threshold(frameGray, 100, 255, 0)
   ### this effectively erodes 1-pixel boundaries around loot boxes
   thresh = cv.erode(thresh, None, iterations=1)
   thresh = cv.dilate(thresh, None, iterations=1)

   contours, hierarchy = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
   validContours = []
   
   for contour in contours:
      if cv.contourArea(contour) > CONTOUR_SIZE:
            validContours.append(contour)

   # cv.drawContours(frame, contours, -1, (255,0,0), 2)
   # cv.drawContours(frame, validContours, -1, (255,0,0), 2)

   # frame1 = cv.resize(frame, (800, 600), interpolation = cv.INTER_AREA)

   # cv.imshow("test", frame1)
   # cv.waitKey(0)
   # cv.destroyAllWindows()

   itemCoords = getCountoursCenters(validContours)

   return itemCoords

def getCountoursCenters(contours):
   result = []
   for contour in contours:
      last = pyautogui.position()

      # find center of the loot
      M = cv.moments(contour)
      cX = int(M["m10"] / M["m00"])
      cY = int(M["m01"] / M["m00"])
      result.append((cX, cY))
   return result
   

def grabLoot(itemCoords):
   closestCenter = itemCoords[0]
   dist = math.dist(windowCenter, itemCoords[0])

   for center in itemCoords:
      curDist = math.dist(windowCenter, center)
      if curDist < dist:
         dist = curDist
         closestCenter = center

   leftClick(closestCenter[0], closestCenter[1])
   return closestCenter


def myQuit():
   print("Quit invoked")
   os._exit(0)

def pipetteColor():
   x, y = pyautogui.position()
   px = pyautogui.pixel(x, y)
   print((x, y), px)


def findLootForMultipleColors(frame, colors):
   contours = []
   for color in colors:
      currContours = findLoot(frame, color)
      # print(f"Found {len(currContours)} loot of color: {color}")
      contours += currContours # append array
   return contours

def grabLootSingle(lootCoords):
   if (len(lootCoords) == 0):
      return None

   pickedLootCoordinates = grabLoot(lootCoords)
   return pickedLootCoordinates

def isMoving(lootCoordsCurr, lootCoordsPrev):
   if (len(lootCoordsCurr) == 0 or len(lootCoordsPrev) == 0):
      return False

   prevClosest = lootCoordsPrev[0]
   prevClosestDist = math.dist(windowCenter, prevClosest)
   prevSecondClosest = prevClosest
   prevSecondClosestDist = prevClosestDist

   for itemCoords in lootCoordsPrev:
      dist = math.dist(windowCenter, itemCoords)
      if (dist < prevClosestDist):
         prevSecondClosestDist = prevClosestDist
         prevSecondClosest = prevClosest
         prevClosestDist = dist
         prevClosest = itemCoords

   currClosest = lootCoordsCurr[0]
   currClosestDist = math.dist(windowCenter, currClosest)

   for itemCoords in lootCoordsCurr:
      dist = math.dist(windowCenter, itemCoords)
      if (dist < currClosestDist):
         currClosest = itemCoords
         currClosestDist = dist

   amMoving = not((currClosest == prevSecondClosest) or (currClosest == prevClosest))
   if (amMoving):
      print(f"moving. [{currClosest}][{prevClosest}, {prevSecondClosest}]")

   return amMoving


def grabLootAll():
   winsound.Beep(1000, 50)
   frameCurr = getFrameSnapshot()
   framePrev = frameCurr
   lootCoordsCurr = findLootForMultipleColors(frameCurr, LOOT_COLORS)
   lootCoordsPrev = lootCoordsCurr

   print("grabLootAll: Grabbing")
   while(len(lootCoordsCurr) > 0):
      print(f"Items found: {lootCoordsCurr}")

      if(isMoving(lootCoordsCurr, lootCoordsPrev)):
         # print("moving, skipping iteration")
         None
      else:
         # print("Picking up loot")
         grabbedLoot = grabLootSingle(lootCoordsCurr)

      # time.sleep(0.005)

      framePrev = frameCurr
      lootCoordsPrev = lootCoordsCurr

      frameCurr = getFrameSnapshot()
      lootCoordsCurr = findLootForMultipleColors(frameCurr, LOOT_COLORS)

   print("grabLootAll: Done.")
   winsound.Beep(500, 50)
         


def mydebug():
   frame = getFrameSnapshot()
   loot = findLoot(frame, (255, 255, 255))

init()

print("Ready to grab some loot!\n")

keyboard.add_hotkey(HOTKEY, grabLootAll)
# keyboard.add_hotkey(HOTKEY, mydebug)
keyboard.add_hotkey(EXIT_HOTKEY, myQuit)
keyboard.add_hotkey(PIPETTE_HOTKEY, pipetteColor)


while True:
   time.sleep(1) #keep it alive
