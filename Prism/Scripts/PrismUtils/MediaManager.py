# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import logging
import platform
import subprocess
import traceback
import glob
import re

from collections import OrderedDict

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

if platform.system() in ["Linux", "Darwin"]:
    try:
        from PIL import Image
    except:
        pass

try:
    import numpy
except:
    pass

if platform.system() == "Windows":
    if pVersion == 3:
        import winreg as _winreg
    elif pVersion == 2:
        import _winreg

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class MediaManager(object):
    def __init__(self, core):
        self.core = core
        self.supportedFormats = [
            ".jpg",
            ".jpeg",
            ".JPG",
            ".png",
            ".PNG",
            ".tif",
            ".tiff",
            ".tga",
            ".dpx",
            ".exr",
            ".hdr",
            ".mp4",
            ".mov",
            ".avi",
        ]
        self.videoFormats = [".mp4", ".mov", ".avi"]
        self.getImageIO()

    @err_catcher(name=__name__)
    def filterValidMediaFiles(self, filepaths):
        validFiles = []
        for mediaFile in sorted(filepaths):
            if os.path.splitext(mediaFile)[1] in self.supportedFormats:
                validFiles.append(mediaFile)

        return validFiles

    @err_catcher(name=__name__)
    def detectSequence(self, filepaths):
        seq = []
        base = re.sub("\d+", "", filepaths[0])
        for filepath in sorted(filepaths):
            if re.sub("\d+", "", filepath) == base:
                seq.append(filepath)

        return seq

    @err_catcher(name=__name__)
    def getSequenceFromFilename(self, filename):
        seq = filename
        baseName, extension = os.path.splitext(os.path.basename(filename))
        if len(baseName) >= self.core.framePadding:
            endStr = baseName[-self.core.framePadding:]
            if pVersion == 2:
                endStr = unicode(endStr)

            if (
                endStr.isnumeric()
                and not (len(baseName) > self.core.framePadding and (baseName[-(self.core.framePadding + 1)] == "v"))
                and extension not in self.core.media.videoFormats
            ):
                pattern = "#"
                seqFile = baseName[:-self.core.framePadding] + pattern*self.core.framePadding + extension
                seq = os.path.join(os.path.dirname(filename), seqFile)

        return seq

    @err_catcher(name=__name__)
    def isFilenameInSequence(self, filename, sequence):
        cleanSeq = self.getFilenameWithoutFrameNumber(os.path.basename(sequence.replace("#", "")))
        cleanFilename = self.getFilenameWithoutFrameNumber(os.path.basename(filename))
        inseq = cleanSeq == cleanFilename
        return inseq

    @err_catcher(name=__name__)
    def getFrameNumberFromFilename(self, filename):
        baseName, extension = os.path.splitext(filename)
        if len(baseName) >= self.core.framePadding:
            endStr = baseName[-self.core.framePadding:]
            if pVersion == 2:
                endStr = unicode(endStr)

            if endStr.isnumeric():
                return endStr

    @err_catcher(name=__name__)
    def getFilenameWithFrameNumber(self, filename, framenumber):
        framename = filename.replace("#" * self.core.framePadding, "%0{}d".format(self.core.framePadding) % int(framenumber))
        return framename

    @err_catcher(name=__name__)
    def getFilenameWithoutFrameNumber(self, filename):
        sname = filename
        baseName, extension = os.path.splitext(filename)
        if len(baseName) >= self.core.framePadding:
            endStr = baseName[-self.core.framePadding:]
            if pVersion == 2:
                endStr = unicode(endStr)

            if endStr.isnumeric() and (len(baseName) == self.core.framePadding or baseName[-(self.core.framePadding + 1)] != "v"):
                sname = baseName[:-self.core.framePadding] + extension

        return sname

    @err_catcher(name=__name__)
    def detectSequences(self, files, getFirstFile=False, sequencePattern=True):
        foundSrc = {}
        psources = []
        for file in files:
            baseName, extension = os.path.splitext(file)
            if extension in self.core.media.supportedFormats:
                filename = self.getFilenameWithoutFrameNumber(file)
                psources.append(os.path.splitext(filename))

        for file in sorted(files):
            baseName, extension = os.path.splitext(file)
            if extension in self.core.media.supportedFormats:
                if getFirstFile:
                    return [file]

                padfile = file
                if len(baseName) >= self.core.framePadding:
                    postFrameStr = ""
                    if ".cryptomatte" in baseName:
                        baseNameData = baseName.split(".cryptomatte")
                        baseName = baseNameData[0]
                        postFrameStr = ".cryptomatte" + baseNameData[-1]

                    endStr = baseName[-self.core.framePadding:]
                    if pVersion == 2:
                        endStr = unicode(endStr)

                    if sequencePattern:
                        if (
                            endStr.isnumeric()
                            and not (len(baseName) > self.core.framePadding and (baseName[-(self.core.framePadding+1)] == "v"))
                            and extension not in self.core.media.videoFormats
                        ):
                            pattern = "#"
                            padfile = baseName[:-self.core.framePadding] + pattern*self.core.framePadding + postFrameStr + extension

                if padfile in foundSrc:
                    foundSrc[padfile].append(file)
                else:
                    foundSrc[padfile] = [file]

        return foundSrc

    @err_catcher(name=__name__)
    def getImgSources(self, path, getFirstFile=False, sequencePattern=True):
        foundSrc = []
        files = []
        for root, folder, files in os.walk(path):
            break

        foundSrc = self.detectSequences(files, getFirstFile=getFirstFile, sequencePattern=sequencePattern)
        if foundSrc:
            foundSrc = [os.path.join(path, src) for src in foundSrc]

        return foundSrc

    @err_catcher(name=__name__)
    def getFilesFromSequence(self, sequence):
        files = glob.glob(sequence.replace("#", "?"))
        files = sorted(files)
        return files

    @err_catcher(name=__name__)
    def getFirstFilePpathFromSequence(self, sequence):
        files = self.getFilesFromSequence(sequence)
        if files:
            return files[0]

    @err_catcher(name=__name__)
    def getFrameRangeFromSequence(self, filepaths):
        startPath = filepaths[0]
        try:
            start = int(os.path.splitext(startPath)[0][-self.core.framePadding:])
        except:
            start = "?"
            if ".cryptomatte" in startPath:
                startPathData = startPath.split(".cryptomatte")
                startPath = startPathData[0]
                try:
                    start = int(startPath[-self.core.framePadding:])
                except:
                    pass

        endPath = filepaths[-1]
        try:
            end = int(os.path.splitext(endPath)[0][-self.core.framePadding:])
        except:
            end = "?"
            if ".cryptomatte" in endPath:
                endPathData = endPath.split(".cryptomatte")
                endPath = endPathData[0]
                try:
                    end = int(endPath[-self.core.framePadding:])
                except:
                    pass

        return start, end

    @err_catcher(name=__name__)
    def getVideoReader(self, filepath):
        if os.stat(filepath).st_size == 0:
            reader = "Error - empty file: %s" % filepath
        else:
            imageio = self.getImageIO()
            filepath = str(filepath)  # unicode causes errors in Python 2
            try:
                reader = imageio.get_reader(filepath, "ffmpeg")
            except Exception as e:
                reader = "Error - %s" % e

        return reader

    @err_catcher(name=__name__)
    def checkMSVC(self):
        if platform.system() != "Windows":
            return

        dllPath = os.path.join(os.environ["WINDIR"], "System32", "msvcp140.dll")
        if not os.path.exists(dllPath):
            if self.core.getConfig("globals", "msvcSkipped", config="user"):
                return

            msg = "Microsoft Visual C++ Redistributable is not installed on this computer. It is required by several Prism features including generating previews for EXR files.\n\nDo you want to download and install it now?\n(After the download has finished you have to execute the file in order to install it.)"
            result = self.core.popupQuestion(msg, buttons=["Download", "Cancel"])
            if result == "Download":
                url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
                self.core.openWebsite(url)
            else:
                self.core.setConfig("globals", "msvcSkipped", True, config="user")

    @err_catcher(name=__name__)
    def getOIIO(self):
        oiio = None
        try:
            if platform.system() == "Windows":
                if pVersion == 2:
                    if self.core.appPlugin.pluginName == "Nuke":
                        from oiio22_msvc1426 import OpenImageIO as oiio
                    else:
                        from oiio1618 import OpenImageIO as oiio
                else:
                    from oiio_2_4 import OpenImageIO as oiio

            elif platform.system() in ["Linux", "Darwin"]:
                import OpenImageIO as oiio
        except:
            logger.debug("loading oiio failed: %s" % traceback.format_exc())
            self.checkMSVC()

        return oiio

    @err_catcher(name=__name__)
    def getImageIO(self):
        if not hasattr(self, "_imageio"):
            imageio = None
            os.environ["IMAGEIO_FFMPEG_EXE"] = self.getFFmpeg()
            sys.path.insert(0, r"D:\Dropbox\Workstation\Tools\Prism\Repos\Prism\Prism\PythonLibs\Python3")
            try:
                import imageio
                import imageio.plugins.ffmpeg
                import imageio_ffmpeg
            except:
                logger.debug("failed to load imageio: %s" % traceback.format_exc())

            self._imageio = imageio

        return self._imageio

    @err_catcher(name=__name__)
    def getFFmpeg(self, validate=False):
        if platform.system() == "Windows":
            ffmpegPath = os.path.join(
                self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg.exe"
            )
        elif platform.system() == "Linux":
            ffmpegPath = "ffmpeg"

        elif platform.system() == "Darwin":
            ffmpegPath = "ffmpeg"

        if validate:
            result = self.validateFFmpeg(ffmpegPath)
            if not result:
                return

        return ffmpegPath

    @err_catcher(name=__name__)
    def validateFFmpeg(self, path):
        ffmpegIsInstalled = False

        if platform.system() == "Windows":
            if os.path.exists(path):
                ffmpegIsInstalled = True
        elif platform.system() == "Linux":
            try:
                subprocess.Popen([path], shell=True)
                ffmpegIsInstalled = True
            except:
                pass

        elif platform.system() == "Darwin":
            try:
                subprocess.Popen([path], shell=True)
                ffmpegIsInstalled = True
            except:
                pass

        return ffmpegIsInstalled

    @err_catcher(name=__name__)
    def checkOddResolution(self, path, popup=False):
        res = self.getMediaResolution(path)
        if not res or not res["width"] or not res["height"]:
            return True

        if int(res["width"]) % 2 == 1 or int(res["height"]) % 2 == 1:
            if popup:
                self.core.popup("Media with odd resolution can't be converted to mp4.")

            return False

        return True

    @err_catcher(name=__name__)
    def convertMedia(self, inputpath, startNum, outputpath, settings=None):
        inputpath = inputpath.replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1]
        outputExt = os.path.splitext(outputpath)[1]
        videoInput = inputExt in [".mp4", ".mov"]
        startNum = str(startNum) if startNum is not None else None

        ffmpegPath = self.getFFmpeg(validate=True)

        if not ffmpegPath:
            msg = "Could not find ffmpeg"
            if platform.system() == "Darwin":
                msg += (
                    '\n\nYou can install it with this command:\n"brew install ffmpeg"'
                )

            self.core.popup(msg, severity="critical")
            return

        if not os.path.exists(os.path.dirname(outputpath)):
            os.makedirs(os.path.dirname(outputpath))

        if videoInput:
            args = OrderedDict(
                [
                    ("-apply_trc", "iec61966_2_1"),
                    ("-i", inputpath),
                    ("-pix_fmt", "yuva420p"),
                    ("-start_number", startNum),
                ]
            )

        else:
            fps = "25"
            if self.core.getConfig(
                "globals", "forcefps", configPath=self.core.prismIni
            ):
                fps = self.core.getConfig(
                    "globals", "fps", configPath=self.core.prismIni
                )

            args = OrderedDict(
                [
                    ("-start_number", startNum),
                    ("-framerate", fps),
                    ("-apply_trc", "iec61966_2_1"),
                    ("-i", inputpath),
                    ("-pix_fmt", "yuva420p"),
                    ("-start_number_out", startNum),
                ]
            )

            if startNum is None:
                args.popitem(last=False)
                args.popitem(last=True)

        if outputExt == ".jpg":
            quality = self.core.getConfig(
                "media", "jpgCompression", dft=4, config="project"
            )
            args["-qscale:v"] = str(quality)

        if outputExt == ".mp4":
            quality = self.core.getConfig(
                "media", "mp4Compression", dft=18, config="project"
            )
            args["-crf"] = str(quality)

        if settings:
            args.update(settings)

        argList = [ffmpegPath]

        for k in args.keys():
            if not args[k]:
                continue

            if isinstance(args[k], list):
                al = [k]
                al.extend([str(x) for x in args[k]])
            else:
                val = str(args[k])
                if k == "-start_number_out":
                    k = "-start_number"
                al = [k, val]

            argList += al

        argList += [outputpath, "-y"]
        logger.debug("Run ffmpeg with this settings: " + str(argList))
        nProc = subprocess.Popen(
            argList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        result = nProc.communicate()

        if sys.version[0] == "3":
            result = [x.decode("utf-8", "ignore") for x in result]

        return result

    @err_catcher(name=__name__)
    def invalidateOiioCache(self, force=False):
        oiio = self.getOIIO()
        if not oiio:
            return

        if eval(os.getenv("PRISM_REFRESH_OIIO_CACHE", "False")) or force:
            oiio.ImageCache().invalidate_all()

    @err_catcher(name=__name__)
    def getLayersFromFile(self, filepath):
        base, ext = os.path.splitext(filepath)
        if ext not in [".exr"]:
            return []

        oiio = self.getOIIO()
        if not oiio:
            return []

        imgInput = oiio.ImageInput.open(filepath)
        if not imgInput:
            return []

        imgNum = 0
        names = []
        while imgInput.seek_subimage(imgNum, 0):
            cnames = imgInput.spec().channelnames
            if ("r" in cnames or "R" in cnames) and ("g" in cnames or "G" in cnames) and ("b" in cnames or "B" in cnames):
                if ("a" in cnames or "A" in cnames):
                    names.append("RGBA")
                else:
                    names.append("RGB")

            exts = [".R", ".G", ".B", ".r", ".g", ".b", ".red", ".green", ".blue", ".x", ".y", ".z"]
            for name in cnames:
                for ext in exts:
                    if name.endswith(ext):
                        name = name[:-len(ext)]
                        if name not in names:
                            names.append(name)

            imgNum += 1

        imgInput.close()
        return names

    @err_catcher(name=__name__)
    def getThumbnailPath(self, path):
        thumbPath = os.path.join(os.path.dirname(path), "_thumbs", os.path.basename(os.path.splitext(path)[0]) + ".jpg")
        return thumbPath

    @err_catcher(name=__name__)
    def getUseThumbnailForFile(self, filepath):
        _, ext = os.path.splitext(filepath)
        useThumb = ext in [".exr", ".dpx", ".hdr"] or ext in self.videoFormats
        return useThumb        

    @err_catcher(name=__name__)
    def getUseThumbnails(self):
        return self.core.getConfig("globals", "useMediaThumbnails", dft=True)

    @err_catcher(name=__name__)
    def setUseThumbnails(self, state):
        return self.core.setConfig("globals", "useMediaThumbnails", val=state)

    @err_catcher(name=__name__)
    def getPixmapFromExrPath(self, path, width=None, height=None, channel=None, allowThumb=True, regenerateThumb=False):
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getPixmapFromPath(thumbPath, width=width, height=height)

        oiio = self.getOIIO()
        if not oiio:
            # msg = "OpenImageIO is not available. Unable to read the file."
            # self.core.popup(msg)
            return

        path = str(path)  # for python 2
        imgInput = oiio.ImageInput.open(path)
        chbegin = 0
        chend = 3
        subimage = 0
        if channel:
            while imgInput.seek_subimage(subimage, 0):
                idx = imgInput.spec().channelindex(channel + ".R")
                if idx == -1:
                    idx = imgInput.spec().channelindex(channel + ".red")
                    if idx == -1:
                        idx = imgInput.spec().channelindex(channel + ".r")
                        if idx == -1:
                            idx = imgInput.spec().channelindex(channel + ".x")
                            if idx == -1 and channel in ["RGB", "RGBA"]:
                                idx = imgInput.spec().channelindex("R")

                if idx == -1:
                    subimage += 1
                else:
                    chbegin = idx
                    chend = chbegin + 3
                    break

        pixels = imgInput.read_image(subimage=subimage, miplevel=0, chbegin=chbegin, chend=chend)
        rgbImgSrc = oiio.ImageBuf(
            oiio.ImageSpec(imgInput.spec().full_width, imgInput.spec().full_height, 3, oiio.UINT16)
        )
        imgInput.close()

        if "numpy" in globals():
            rgbImgSrc.set_pixels(oiio.ROI.All, numpy.array(pixels))
        else:
            for h in range(height):
                for w in range(width):
                    color = [pixels[h][w][0], pixels[h][w][1], pixels[h][w][2]]
                    rgbImgSrc.setpixel(w, h, 0, color)

        # slow when many channels are in the exr file
        # imgSrc = oiio.ImageBuf(path)
        # rgbImgSrc = oiio.ImageBuf()
        # oiio.ImageBufAlgo.channels(rgbImgSrc, imgSrc, (0, 1, 2))
        imgWidth = rgbImgSrc.spec().full_width
        imgHeight = rgbImgSrc.spec().full_height
        if not imgWidth or not imgHeight:
            return

        xOffset = 0
        yOffset = 0
        if width and height:
            if (imgWidth / float(imgHeight)) > width / float(height):
                newImgWidth = width
                newImgHeight = width / float(imgWidth) * imgHeight
            else:
                newImgHeight = height
                newImgWidth = height / float(imgHeight) * imgWidth
        else:
            newImgWidth = imgWidth
            newImgHeight = imgHeight

        imgDst = oiio.ImageBuf(
            oiio.ImageSpec(int(newImgWidth), int(newImgHeight), 3, oiio.UINT16)
        )
        oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
        sRGBimg = oiio.ImageBuf()
        oiio.ImageBufAlgo.pow(sRGBimg, imgDst, (1.0 / 2.2, 1.0 / 2.2, 1.0 / 2.2))
        bckImg = oiio.ImageBuf(
            oiio.ImageSpec(int(newImgWidth), int(newImgHeight), 3, oiio.UINT16)
        )
        oiio.ImageBufAlgo.fill(bckImg, (0.5, 0.5, 0.5))
        oiio.ImageBufAlgo.paste(bckImg, xOffset, yOffset, 0, 0, sRGBimg)
        qimg = QImage(int(newImgWidth), int(newImgHeight), QImage.Format_RGB32)
        for i in range(int(newImgWidth)):
            for k in range(int(newImgHeight)):
                rgb = qRgb(
                    bckImg.getpixel(i, k)[0] * 255,
                    bckImg.getpixel(i, k)[1] * 255,
                    bckImg.getpixel(i, k)[2] * 255,
                )
                qimg.setPixel(i, k, rgb)

        pixmap = QPixmap.fromImage(qimg)
        if thumbEnabled and allowThumb:
            thumbPath = self.getThumbnailPath(path)
            self.savePixmap(pixmap, thumbPath)

        return pixmap

    @err_catcher(name=__name__)
    def getPixmapFromPath(self, path, width=None, height=None, colorAdjust=False):
        if path:
            _, ext = os.path.splitext(path)
            if ext in self.core.media.videoFormats:
                return self.getPixmapFromVideoPath(path)
            elif ext in [".exr", ".dpx", ".hdr"]:
                return self.core.media.getPixmapFromExrPath(
                    path, width, height
                )

        pixmap = QPixmap(path)
        if (width or height) and not pixmap.isNull():
            pixmap = self.scalePixmap(pixmap, width, height)

        return pixmap

    @err_catcher(name=__name__)
    def getPixmapFromVideoPath(self, path, allowThumb=True, regenerateThumb=False, videoReader=None, imgNum=0):
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb and imgNum == 0:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getPixmapFromPath(thumbPath)

        _, ext = os.path.splitext(path)
        try:
            vidFile = self.core.media.getVideoReader(path) if videoReader is None else videoReader
            if self.core.isStr(vidFile):
                logger.warning(vidFile)
                imgPath = os.path.join(
                    self.core.projects.getFallbackFolder(),
                    "%s.jpg" % ext[1:].lower(),
                )
                pmsmall = self.core.media.getPixmapFromPath(imgPath)
            else:
                image = vidFile.get_data(imgNum)
                fileRes = vidFile._meta["size"]
                width = fileRes[0]
                height = fileRes[1]
                qimg = QImage(image, width, height, 3*width, QImage.Format_RGB888)
                pmsmall = QPixmap.fromImage(qimg)
                if thumbEnabled and imgNum == 0:
                    thumbPath = self.getThumbnailPath(path)
                    self.savePixmap(pmsmall, thumbPath)

        except Exception as e:
            logger.debug(traceback.format_exc())
            imgPath = os.path.join(
                self.core.projects.getFallbackFolder(),
                "%s.jpg" % ext[1:].lower(),
            )
            pmsmall = self.core.media.getPixmapFromPath(imgPath)

        return pmsmall

    @err_catcher(name=__name__)
    def savePixmap(self, pmap, path):
        while True:
            if os.path.exists(os.path.dirname(path)):
                break
            else:
                try:
                    os.makedirs(os.path.dirname(path))
                    break
                except FileExistsError:
                    break
                except:
                    msg = "Failed to create folder. Make sure you have the required permissions to create this folder.\n\n%s" % os.path.dirname(path)
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"])
                    if result != "Retry":
                        return

        if platform.system() == "Windows":
            if os.path.splitext(path)[1].lower() == ".png":
                pmap.save(path, "PNG", 95)
            else:
                pmap.save(path, "JPG", 95)
        else:
            try:
                img = pmap.toImage()
                buf = QBuffer()
                buf.open(QIODevice.ReadWrite)
                img.save(buf, "PNG")

                strio = StringIO()
                strio.write(buf.data())
                buf.close()
                strio.seek(0)
                pimg = Image.open(strio)
                pimg.save(path)
            except:
                pmap.save(path, "JPG")

    @err_catcher(name=__name__)
    def getPixmapFromUrl(self, url):
        import requests
        logger.debug("getting image from url: %s" % url)
        data = requests.get(url).content
        image = QImage()
        image.loadFromData(data)
        pmap = QPixmap(image)
        return pmap

    @err_catcher(name=__name__)
    def getPixmapFromClipboard(self):
        return QApplication.clipboard().pixmap()

    @err_catcher(name=__name__)
    def scalePixmap(self, pixmap, width, height, keepRatio=True, fitIntoBounds=True, crop=False, fillBackground=False):
        if keepRatio:
            if fitIntoBounds:
                mode = Qt.KeepAspectRatio
            else:
                mode = Qt.KeepAspectRatioByExpanding
        else:
            mode = Qt.IgnoreAspectRatio

        try:
            pixmap = pixmap.scaled(
                width, height, mode, transformMode=Qt.SmoothTransformation
            )
        except AttributeError:
            pixmap = pixmap.scaled(
                width, height, mode
            )

        if fitIntoBounds:
            if fillBackground:
                new_pixmap = QPixmap(width, height)
                new_pixmap.fill(Qt.black)
                painter = QPainter(new_pixmap)
                painter.drawPixmap((width-pixmap.width())/2, (height-pixmap.height())/2, pixmap)
                painter.end()
                pixmap = new_pixmap
        else:
            if crop:
                rect = QRect(int((pixmap.width()-width)/2), int((pixmap.height()-height)/2), width, height)
                pixmap = pixmap.copy(rect)

        return pixmap

    @err_catcher(name=__name__)
    def getColoredIcon(self, path, force=False, r=150, g=210, b=240):
        ssheet = self.core.getActiveStyleSheet()
        if self.core.appPlugin.pluginName == "Standalone" and ssheet and ssheet.get("name") == "Blue Moon" or force:
            image = QImage(path)
            cimage = QImage(image)
            cimage.fill((QColor(r, g, b)))
            cimage.setAlphaChannel(image.convertToFormat(QImage.Format_Alpha8))
            pixmap = QPixmap.fromImage(cimage)
        else:
            pixmap = QPixmap(path)

        return QIcon(pixmap)

    @err_catcher(name=__name__)
    def getMediaInformation(self, path):
        seqInfo = self.getMediaSequence(path)
        isSequence = seqInfo["isSequence"]
        start = seqInfo["start"]
        end = seqInfo["end"]
        files = seqInfo["files"]
        if files:
            resolution = self.getMediaResolution(files[0])
            width = resolution["width"]
            height = resolution["height"]
        else:
            width = None
            height = None

        result = {
            "width": width,
            "height": height,
            "isSequence": isSequence,
            "start": start,
            "end": end,
            "files": files,
        }

        return result

    @err_catcher(name=__name__)
    def getMediaResolution(self, path, videoReader=None):
        pwidth = None
        pheight = None
        base, ext = os.path.splitext(path)

        if ext in [
            ".jpg",
            ".jpeg",
            ".JPG",
            ".png",
            ".PNG",
            ".tif",
            ".tiff",
            ".tga",
            ".gif",
        ]:
            pm = self.getPixmapFromPath(path)
            if pm:
                size = pm.size()
                pwidth = size.width()
                pheight = size.height()
        elif ext in [".exr", ".dpx", ".hdr"]:
            oiio = self.getOIIO()
            if oiio:
                path = str(path)  # for python 2
                buf = oiio.ImageBuf(path)
                imgSpecs = buf.spec()
                pwidth = imgSpecs.full_width
                pheight = imgSpecs.full_height
        elif ext in [".mp4", ".mov", ".avi"]:
            if videoReader is None:
                videoReader = self.getVideoReader(path)

            if not self.core.isStr(videoReader) and "size" in videoReader._meta:
                pwidth = videoReader._meta["size"][0]
                pheight = videoReader._meta["size"][1]

        return {"width": pwidth, "height": pheight}

    @err_catcher(name=__name__)
    def getVideoDuration(self, path, videoReader=None):
        if videoReader is None:
            videoReader = self.getVideoReader(path)

        if self.core.isStr(videoReader):
            logger.warning(videoReader)
            return

        duration = videoReader.count_frames()
        return duration

    @err_catcher(name=__name__)
    def getMediaSequence(self, path):
        start = None
        end = None
        isSequence = None

        matchingFiles = glob.glob(path)
        isSequence = len(matchingFiles) > 1

        frames = []
        for file in matchingFiles:
            base, ext = os.path.splitext(file)
            if len(base) < self.core.framePadding:
                continue

            try:
                frame = int(base[-self.core.framePadding :])
            except:
                continue

            frames.append(frame)

        if frames:
            start = min(frames)
            end = max(frames)

        result = {
            "start": start,
            "end": end,
            "isSequence": isSequence,
            "files": sorted(matchingFiles),
        }

        return result

    @err_catcher(name=__name__)
    def getExternalMediaPlayer(self):
        player = {
            "name": self.core.getConfig("globals", "mediaPlayerName") or "Media Player",
            "path": self.core.getConfig("globals", "mediaPlayerPath"),
            "framePattern": self.core.getConfig("globals", "mediaPlayerFramePattern") or False
        }
        if not player["path"]:
            path = self.core.getConfig("globals", "rvpath")
            if not path:
                path = self.core.getConfig("globals", "djvpath")

            if path:
                player["path"] = path

        return player

    @err_catcher(name=__name__)
    def playMediaInExternalPlayer(self, path):
        progPath = self.getExternalMediaPlayer().get("path")
        if not progPath:
            logger.warning("no media player path defined")
            return

        if not os.path.exists(path):
            base, ext = os.path.splitext(path)
            pattern = base.strip(".#") + ".*" + ext
            paths = glob.glob(pattern)
            if not paths:
                logger.warning("media filepath doesn't exist: %s" % path)
                return

            path = paths[0]

        comd = [progPath, path]

        with open(os.devnull, "w") as f:
            try:
                subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
            except:
                try:
                    subprocess.Popen(
                        comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                    )
                except Exception as e:
                    raise RuntimeError("%s - %s" % (comd, e))

    @err_catcher(name=__name__)
    def getFallbackPixmap(self, big=False):
        if big:
            filename = "noFileBig.jpg"
        else:
            filename = "noFileSmall.jpg"

        if getattr(self.core, "projectPath", None):
            imgFile = os.path.join(
                self.core.projects.getFallbackFolder(), filename
            )
        else:
            base = self.core.projects.getPreset("Default")["path"]
            imgFile = os.path.join(
                base, "00_Pipeline/Fallbacks/" + filename
            )

        return self.core.media.getPixmapFromPath(imgFile)

    @property
    @err_catcher(name=__name__)
    def emptyPrvPixmap(self):
        if not hasattr(self, "_emptyPrvPixmap"):
            self._emptyPrvPixmap = self.getFallbackPixmap()

        return self._emptyPrvPixmap

    @property
    @err_catcher(name=__name__)
    def emptyPrvPixmapBig(self):
        if not hasattr(self, "_emptyPrvPixmapBig"):
            self._emptyPrvPixmapBig = self.getFallbackPixmap(big=True)

        return self._emptyPrvPixmapBig
