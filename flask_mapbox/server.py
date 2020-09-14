import os
import pandas as pd
from skimage import io
import numpy as np 
from tensorflow.keras.models import load_model

from flask import Flask, request, session, g, redirect, \
    url_for, abort, render_template, flash, Response


import os
import tifffile as tiff
import numpy as np 
from shutil import copyfile
from multiprocessing import Pool
from skimage import io
from skimage.transform import resize
from geographiclib.constants import Constants
from geographiclib.geodesic import Geodesic
from shapely.ops import unary_union
from shapely.geometry import Polygon
from math import atan, tan, sqrt
import gdal
import time
import random
import json
import shutil

IMG_HEIGHT_RAW = 512
IMG_WIDTH_RAW = 640
IMG_HEIGHT_16 = 128
IMG_WIDTH_16 = 160
NB_CHANNELS = 7

baseFolder = "../data/preprocessing/"
clippedImagesFolder = '../data/preprocessing/clippedImages/16/'
datasetFolder = '../data/images/'
coordsFilePath = "../data/preprocessing/imagesCoords.csv"
resizedImagesFolder = "../data/preprocessing/resizedImages/"
stackedImagesFolder = "../data/preprocessing/stackedImages/" 
modelPath = "../data/model/model_WD.h5"

clipDone = False
writingDone = False
predictProgress = 0

#configuration de flask
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('APP_CONFIG_FILE', silent=True)
MAPBOX_ACCESS_KEY = 'sk.eyJ1IjoiZnJpZW5kbHlmcnVpdHMxIiwiYSI6ImNrY3VoazNqeTBqeDkycnQyODlrbXBlZmgifQ.BqVVTNvgJSmxPLx7bV6JWA'


@app.route('/')
def preprocessing():
    return render_template('preprocessing.html')

@app.route('/start_over')
def start_over():
    clipFolder = '../data/preprocessing/clippedImages/'
    imagesFolder = os.path.join(clippedImagesFolder,'images')
    dirPath = baseFolder
    if os.path.exists(dirPath) and os.path.isdir(dirPath):
        print(dirPath)
        shutil.rmtree(dirPath, ignore_errors=True)
    dirsToCreate = [resizedImagesFolder,stackedImagesFolder,clipFolder,clippedImagesFolder,imagesFolder] 
    print("create")
    for dirToCreate in dirsToCreate:
        print(dirToCreate)
        os.makedirs(dirToCreate)
    return "ok"

@app.route('/resize_img')
def resize_img():
    files = [f for f in os.listdir(datasetFolder) if '.tif' in f]
    multibandImages = []
    pool = Pool(3)
    # pour chaque images multispectrale, on la redimensionne, sinon on ajoute l'infrarouge au dossier final
    for file in files:
        if "nm" in file:
            multibandImages.append(file)
        else :
            copyfile(
                os.path.join(datasetFolder, file),
                os.path.join(resizedImagesFolder, file)
            )
    pool.map(resizeImages,multibandImages)
    pool.close()
    return str(200)
    
@app.route('/progress_resize')
def progress_resize():
    resizedFiles = [f for f in os.listdir(resizedImagesFolder) if '.tif' in f]
    files = [f for f in os.listdir(datasetFolder) if '.tif' in f]

    return str(int(100 * (len(resizedFiles)/len(files))))


@app.route('/stack_img')
def stack_img():
    pool = Pool()
    files = [f for f in os.listdir(datasetFolder) if '.tif' in f]
    imagesToStackArray = []
    while files:
        #on selectionne un index (le numero de chaque image)
        imageIndex = files[0].split('_')[0]
        #on regroupe les differentes bandes par leur numero
        imagesToStack = [image for image in files if imageIndex in image]
        imagesToStack.sort()
        #puis on les supprime de la liste des images restantes
        files = list(set(files) - set(imagesToStack))
        if (len(imagesToStack) == 7):
            imagesToStackArray.append(imagesToStack)
        else:
            for imageName in imagesToStack:
                os.remove(os.path.join(resizedImagesFolder,imageName))

    pool.map(stackImages,imagesToStackArray)
    pool.close()
    return "ok"

@app.route('/progress_stack')
def progress_stack():

    stackImages = [f for f in os.listdir(stackedImagesFolder) if '.tif' in f]
    resizedFiles = [f for f in os.listdir(resizedImagesFolder) if '.tif' in f]

    return str(int(700 * (len(stackImages))/len(resizedFiles)))



@app.route('/prediction')
def prediction():
    global writingDone
    #TODO : pretraiter les images pour avoir les .csv correspondants
    imageFolder = os.path.join(clippedImagesFolder,'images')
    #recuperation des images detectees comme OW/WD, ainsi que leurs coordonnees 
    areas = getCoords(modelPrediction(imageFolder))
    #affichage de la page html contenant la carte (mapbox)
    f=open(os.path.join(clippedImagesFolder,'areas.txt'),'w')
    f.write(json.dumps(areas))
    f.close()
    writingDone = True
    return "ok"

@app.route('/display_prediction')
def dispPrediction():
    with open(os.path.join(clippedImagesFolder,'areas.txt')) as f:
        areas = json.load(f)
    print(areas)
    return render_template(
        'mapbox_js.html', 
        ACCESS_KEY=MAPBOX_ACCESS_KEY,
        areas = areas
    )

def resizeImages(imageName):
    try:
        #ratio entre les focales de la bande verte (570nm) et les autres bandes
        focalRatio570 = 0.525000525000525
        #on applique une reduction de la width pour avoir un ratio egal a celui de l'infrarouge
        #puis on resize l'image a la taille de l'infrarouge
        image = tiff.imread(os.path.join(datasetFolder,imageName))
        #transformation en image 16 bits
        image *= 16
        cropped = image
        if ("570nm" in imageName):
            greenHeight = len(image)
            greenWidth = len(image[0])
            #on augmente la taille de l'image par le ratio des lentilles focales
            image_resized = np.floor(resize(image, (greenHeight // focalRatio570, greenWidth // focalRatio570),
                               anti_aliasing=True,preserve_range=True))
            heightDiff = int((len(image_resized) - greenHeight)/2)
            widthDiff = int((len(image_resized[0]) - greenWidth)/2)
            image = image_resized[heightDiff:(heightDiff + greenHeight), widthDiff:(widthDiff + greenWidth)]
        #decoupage specifique a la position de la camera utilisee
        if ("450nm" in imageName):   
            cropped = image[8:len(image),110:len(image[0])]
        elif ("530nm" in imageName):   
            cropped = image[0:len(image) - 10,78:len(image[0])]
        elif ("570nm" in imageName):   
            cropped = image[80:len(image),138:len(image[0])]
        elif ("675nm" in imageName):   
            cropped = image[20:len(image),90:len(image[0])]
        elif ("730nm" in imageName):   
            cropped = image[0:len(image) - 16,72:len(image[0])]
        elif ("850nm" in imageName):   
            cropped = image[0:len(image) - 45,110:len(image[0])]    
        resized = resize(cropped, (IMG_HEIGHT_RAW,IMG_WIDTH_RAW),preserve_range=True)
        tiff.imsave(os.path.join(resizedImagesFolder,imageName),resized.astype(np.uint16))
    except tifffile.tifffile.TiffFileError:
        print(imageName)

def stackImages(imagesToStack):
    bands_data = []
    #on traite les images selectionnees
    for imageName in imagesToStack[0:7]:
        #on recupère leur bande spectrale
        try :
            image = tiff.imread(os.path.join(resizedImagesFolder,imageName))
        except:
            print(imageName)
        bands_data.append(image)
    #empilement des bandes
    try :
        stackedImage = np.dstack((bands_data[0],bands_data[1],bands_data[2],bands_data[3],bands_data[4],bands_data[5],bands_data[6]))
        tiff.imsave(os.path.join(stackedImagesFolder,imageName.split('_')[0] + ".tif"), stackedImage, planarconfig='contig')
    except:
        for imageName in imagesToStack[0:7]:
            os.remove(os.path.join(resizedImagesFolder,imageName))

    

def getEndpoint(lat1, lon1, d, bearing):
    geod = Geodesic(Constants.WGS84_a, Constants.WGS84_f)
    d = geod.Direct(lat1, lon1, bearing, d)
    return d['lat2'], d['lon2']

#recupere les informations de l'image .tiff
def getImageData(imageName):

    #dictionnaire des informations de l'image
    imageData = {}
    #ouverture de l'image
    tif = tiff.TiffFile(os.path.join(datasetFolder, imageName.split('.')[0] + "_lwir.tif"))
    #calcul du champ de vue de la camera
    for key in tif.pages[0].tags["ExifTag"].value.items():
        if "FocalLength" in str(key):
            # longueur et largeur de l'objectif en x et y selon le type de camera
            xSensor = 4.8 if "nm" in imageName else 10.8801
            ySensor = 3.6 if "nm" in imageName else 8.704
            focalLength = key[1][0]
            #calcul du champ de vue en largeur
            fovWide = 2*atan(xSensor/(2*focalLength))
            #calcul du champ de vue en hauteur
            fovTall = 2*atan(ySensor/(2*focalLength))
    #calcul de latitude, longitude, footprint
    for key, value in tif.pages[0].tags["GPSTag"].value.items():
        #la latitude est définie en ratio de degrés, minutes, secondes
        if key == "GPSLatitude":
            imageData["latitude"] = (value[0]/value[1])+((value[2]/value[3])/60)+((value[4]/value[5])/3600)
        #la longitude est définie en ratio de degrés, minutes, secondes
        elif key == "GPSLongitude": 
            imageData["longitude"] = (value[0]/value[1])+((value[2]/value[3])/60)+((value[4]/value[5])/3600)
        #(altitude par rapport au niveau de la mer)
        elif key == "GPSAltitude":
        #calcul des centerToCornerDistances du drone par rapport aux quatres côtés de l'image
            altitude = value[0]
            bottom = altitude * tan(-0.5 * fovWide)
            top = altitude * tan(0.5 * fovWide)
            left = altitude * tan(-0.5 * fovTall)
            right = altitude * tan(0.5 * fovTall)
            #calcul de la distance entre le centre de l'image (position de la camera) et un des quatres angles de l'image
            imageData["centerToCornerDistance"] = sqrt((right - left)**2 + (top - bottom)**2)/2
            imageData["altitude"] = value[0]

        #orientation par rapport au nord pour le calcul de bearing
        elif key == "GPSTrack":
            # imageData["northOrientation"] = (value[0]/value[1])
            imageData["northOrientation"] = 0
    return imageData


#save image data in a csv file
def imageDataToCsv(imageList, coordsFile):
    for image in imageList:
        finalPoints = []
        #on récupère les données géographiques de l'image
        currentImageData = getImageData(image)
        #bearing (angle) de chaque coin de l'image par rapport au centre de celle-ci et le 
        #https://www.fao.org/tempref/FI/CDrom/FAO_Training/FAO_Training/General/x6707f/GR97.GIF
        angleBearings = [315-180,45-180,225-180,135-180]
        if (int(currentImageData["altitude"]) > 30):
            #calcul des latitutes et longitudes des angles de l'images
            for angle in angleBearings:
                finalPoints.append(getEndpoint(
                    currentImageData["latitude"],currentImageData["longitude"],
                    currentImageData["centerToCornerDistance"],
                    angle + currentImageData["northOrientation"]))
            #ajout au fichier csv de l'image et ses coordonnees
            #on inverse les points 3 et 4 pour le parcours des points lors des etapes futures
            coordsFile.write(
                image + "\t" \
                + str(finalPoints[0][0]) + " " + str(finalPoints[0][1]) + "\t" \
                + str(finalPoints[1][0]) + " " + str(finalPoints[1][1]) + "\t" \
                + str(finalPoints[3][0]) + " " + str(finalPoints[3][1]) + "\t" \
                + str(finalPoints[2][0]) + " " + str(finalPoints[2][1]))
            coordsFile.write("\n")
    coordsFile.close()


#fonction de lecture d'un fichier
def readFile(filePath):
    file = open(filePath,'r')
    return file.readlines()
    
#recuperation des points originaux assignes a l'image
def getPreviousPoints(line):
    previousPoints = []
    pointsToSplit = line.strip('\n').split('\t')
    pointsToSplit = pointsToSplit[1:]
    for pointToSplit in pointsToSplit:
        previousPoints.append((pointToSplit.split(' ')[0],pointToSplit.split(' ')[1]))
    return previousPoints

def getCenterPoint(p1,p2):
    return ((float(p1[0]) + float(p2[0]))/2,(float(p1[1]) + float(p2[1]))/2)

def getNewCorners(p1,p2,p3,p4):
    return getCenterPoint(p1,p3),getCenterPoint(p1,p2),getCenterPoint(p2,p3),getCenterPoint(p3,p4),getCenterPoint(p4,p1)

def getNewRectangles(p1,p2,p3,p4):
    #calcul des points centraux entre deux coins de l'image
    centerPoint, centerp1p2, centerp2p3, centerp3p4, centerp4p1 = getNewCorners(p1,p2,p3,p4)
    #définition des quatre nouveaux rectangles
    newRectangles = []
    newRectangles.append([p1, centerp1p2, centerPoint, centerp4p1])
    newRectangles.append([centerp1p2, p2, centerp2p3, centerPoint])
    newRectangles.append([centerPoint, centerp2p3, p3, centerp3p4])
    newRectangles.append([centerp4p1, centerPoint, centerp3p4, p4])
    return newRectangles

#fonction de decoupage des images en 4
def splitImage(newImagesCoordsFile,imagePath, line):
    # index du morceau d'image actuel 
    indexRect = 0
    #on recupere les coordonées des coins originaux de l'image
    imageName = line.strip('\n').split('\t')[0]
    previousPoints = getPreviousPoints(line)
    #on récupère les dimensions en X et Y de l'image
    band = gdal.Open(os.path.join(imagePath,imageName)).GetRasterBand(1)
    xSize = band.XSize 
    ySize = band.YSize
    stepX =  xSize//4
    stepY =  ySize//4
    croppedImages = []
    img = io.imread(os.path.join(imagePath, imageName))
    #definition des quatres nouveaux rectangles issus des coins et milieux des aretes
    newRectangles4 = getNewRectangles(previousPoints[0], previousPoints[1], previousPoints[2], previousPoints[3])
    for j in range(0, ySize, stepY):
    
        #on redécoupe chaque rectangle en 4
        newRectangles16 = getNewRectangles(newRectangles4[j//stepY][0], newRectangles4[j//stepY][1], newRectangles4[j//stepY][2], newRectangles4[j//stepY][3])
        for i in range(0, xSize, stepX):
           
            # on enregistre les nouvelles coordonnées des images découpées dans le fichier .csv
            newImagesCoordsFile.write(
                imageName.split('.')[0] + '_' + str(indexRect) + ".tif" +  "\t" + \
                str(newRectangles16[indexRect%4][0][0]) + " " + str(newRectangles16[indexRect%4][0][1]) + "\t" + \
                str(newRectangles16[indexRect%4][1][0]) + " " + str(newRectangles16[indexRect%4][1][1]) + "\t" + \
                str(newRectangles16[indexRect%4][2][0]) + " " + str(newRectangles16[indexRect%4][2][1]) + "\t" + \
                str(newRectangles16[indexRect%4][3][0]) + " " + str(newRectangles16[indexRect%4][3][1]) + "\n"
            )
            newImage = img[j:j+stepY, i:i+stepX,:]
            croppedImages.append(newImage)
            indexRect +=1    
    #en decoupant les images de droite a gauche (differement de notre ordre de decoupage des lat/long)
    #on definit ainsi un nouvel index correspondant aux index des rectangles du csv
    cropIndex = [0,1,5,4,2,3,7,6,10,11,15,14,8,9,13,12]
    croppedImages = np.array(croppedImages)
    for i in range(len(croppedImages)):
        io.imsave(os.path.join(clippedImagesFolder, "images",imageName.split('.')[0] + '_' + str(i) + ".tif"), croppedImages[cropIndex[i]], planarconfig='contig')

@app.route('/clip_img')
def clipImages():
    global clipDone
    global areas
    #création du fichiers .csv des coordonnées des images
    coordsFile = open(coordsFilePath,"w")
    coordsFile.write("imageName"+"\t"+"point1"+"\t"+"point2"+
                    "\t"+"point3"+"\t"+"point4")
    coordsFile.write("\n")
    imageList = os.listdir(stackedImagesFolder)
    imageList.sort()
    #extraction et enregistrement des données de chaque image
    imageDataToCsv(imageList, coordsFile)
    #fichier .csv comprenant les coordonnées pour les 4 nouvelles images
    #issues de chaque image du dossier d'entrée
    newImagesCoordsFile = open(clippedImagesFolder + "newImagesCoords.csv","w")
    newImagesCoordsFile.write("imageName" + "\t" + "point1" +  "\t" +  "point2"
     "\t" + "point3" + "\t" + "point4" + "\n")
    # on recupere les anciennes coordonnees
    lines = readFile(coordsFilePath)
    #ligne de nom des colonnes
    lines.pop(0)
    
    #on découpe chaque image du dossier
    for line in lines:
        #on récupère la ligne du csv correspondante 
        splitImage(newImagesCoordsFile,stackedImagesFolder,line)
    newImagesCoordsFile.close()
    clipDone = True
    areas = []
    return "ok"
@app.route('/progress_clip')
def progress_clip():
    clippedFiles = [f for f in os.listdir(os.path.join(clippedImagesFolder,'images')) if '.tif' in f]
    stackedFiles = [f for f in os.listdir(stackedImagesFolder) if '.tif' in f]
    if (clipDone):
        return str(100)
    else :
        return str(int(100 * (len(clippedFiles)/(len(stackedFiles)*16))))
        

@app.route('/progress_predict')
def progress_predict():
    clippedFiles = [f for f in os.listdir(os.path.join(clippedImagesFolder,'images')) if '.tif' in f]
    if (not writingDone):
        return str(int(90 * predictProgress/(len(clippedFiles))))
    else :
        return str(int(100 * predictProgress/(len(clippedFiles))))
#fonction de lecture d'un fichier csv
def readDataFile(fileName, separator=','):
    pd.set_option("display.precision", 20)
    dataFile = pd.read_csv(fileName, sep=separator, encoding="utf-8")
    dataFile = dataFile.fillna("")
    return dataFile

def getCoords(listSolutions):
    #current dir
    #file dir
    dataFile = os.path.join(clippedImagesFolder,'newImagesCoords.csv')
    finalCoords = []
    mergePolygons = []
    # lecture des coordonnees des images decoupees
    imageDataFrame = readDataFile(dataFile, "\t")
    for nameSol, waterType in listSolutions:
        #boucles des intersection des cibles et les images de drone
        for _,imageCoords in imageDataFrame.iterrows():
            #recuperation du nom de l'image
            imageName = imageCoords['imageName']
            if (nameSol == imageName):
                # on recupere les quatres coins de celle ci
                p0 = imageCoords['point1'].split(" ")
                p1 = imageCoords['point2'].split(" ")
                p2 = imageCoords['point3'].split(" ")
                p3 = imageCoords['point4'].split(" ")
                newCoordsSol = [[float(p0[1]),float(p0[0])], [float(p1[1]),float(p1[0])], [float(p2[1]),float(p2[0])], [float(p3[1]),float(p3[0])]]
                polyCoords = [(float(p0[1]), float(p0[0])),(float(p1[1]), float(p1[0])),(float(p2[1]), float(p2[0])),(float(p3[1]), float(p3[0]))]
                finalCoords.append([nameSol,newCoordsSol,waterType])
                mergePolygons.append(Polygon(polyCoords))
    print("unary union")
    mergedPoly = unary_union(mergePolygons)
    multiPolygonList = []
    i = 0
    if mergedPoly.geom_type == 'Polygon':
        mergedPoly = [mergedPoly]

    for poly in mergedPoly:
        formattedPoly = []
        polyPoints = list(poly.exterior.coords)
        for point in polyPoints:
            formattedPoly.append([float(point[0]),float(point[1])])
        multiPolygonList.append(["Polygone " + str(i),formattedPoly,waterType])
        i += 1
    # finalCoords = [listSolutions[0],mergedPoly,waterType]     
    # return finalCoords
    return multiPolygonList
#prediction du modele sur les images en entree
def modelPrediction(imageFolder):
    global predictProgress
    #reseau de neurones entraine a classifier WW et WD
    modelWD = load_model(modelPath)
    #dossier des images
    imageList = sorted(os.listdir(imageFolder))
    debut = 0
    fin = min(1000,len(imageList))
    
    listSolutions = []

    while (debut != len(imageList)):
        Xs = []
        imageListBatch = imageList[debut:fin]
        #on rescale chaque image avant la prediction
        for p in imageListBatch:
            try :
                img = io.imread(os.path.join(imageFolder,p))
            except:
                print(os.path.join(imageFolder,p))

            if (np.array(img).shape == (IMG_HEIGHT_16,IMG_WIDTH_16,NB_CHANNELS)):
                Xs.append(img/65535.)
        Xs = np.array(Xs)
        #on recupere les images detectees comme WD
        Y_pred = modelWD.predict(Xs)

        listSolutions.extend([[i,"WD"] for (i,j) in zip(imageListBatch,Y_pred) if j >= 0.95])
        debut = fin
        predictProgress = fin
        fin = fin + min(1000,len(imageList) - fin)
    print("fin prediction")
    return listSolutions

if (__name__ == '__main__'):
    app.run(threaded=True)