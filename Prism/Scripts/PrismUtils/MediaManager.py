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
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import logging
import platform
import subprocess
import traceback
import glob

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
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1

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
            ".exr",
            ".mp4",
            ".mov",
            ".dpx",
        ]

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
                    from oiio22 import OpenImageIO as oiio
            elif platform.system() in ["Linux", "Darwin"]:
                import OpenImageIO as oiio
        except:
            logger.debug("loading oiio failed: %s" % traceback.format_exc())

        return oiio

    @err_catcher(name=__name__)
    def getImageIO(self):
        imageio = None
        os.environ["IMAGEIO_FFMPEG_EXE"] = self.getFFmpeg()
        try:
            import imageio
        except:
            logger.debug("failed to load imageio: %s" % traceback.format_exc())

        return imageio

    @err_catcher(name=__name__)
    def getFFmpeg(self):
        ffmpegPath = os.path.join(
            self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg.exe"
        )
        return ffmpegPath

    @err_catcher(name=__name__)
    def convertMedia(self, inputpath, startNum, outputpath, settings=None):
        inputpath = inputpath.replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1]
        outputExt = os.path.splitext(outputpath)[1]
        videoInput = inputExt in [".mp4", ".mov"]
        startNum = str(startNum) if startNum is not None else None

        ffmpegIsInstalled = False
        if platform.system() == "Windows":
            ffmpegPath = self.getFFmpeg()
            if os.path.exists(ffmpegPath):
                ffmpegIsInstalled = True
        elif platform.system() == "Linux":
            ffmpegPath = "ffmpeg"
            try:
                subprocess.Popen([ffmpegPath])
                ffmpegIsInstalled = True
            except:
                pass

        elif platform.system() == "Darwin":
            ffmpegPath = "ffmpeg"
            try:
                subprocess.Popen([ffmpegPath])
                ffmpegIsInstalled = True
            except:
                pass

        if not ffmpegIsInstalled:
            msg = "Could not find %s" % ffmpegPath
            if platform.system() == "Darwin":
                msg += "\n\nYou can install it with this command:\n\"brew install ffmpeg\""

            self.core.popup(msg, severity="critical")
            return

        if not os.path.exists(os.path.dirname(outputpath)):
            os.makedirs(os.path.dirname(outputpath))

        if videoInput:
            args = OrderedDict([
                ("-apply_trc", "iec61966_2_1"),
                ("-i", inputpath),
                ("-pix_fmt", "yuva420p"),
                ("-start_number", startNum),
            ])

        else:
            fps = "24"
            if self.core.getConfig("globals", "forcefps", configPath=self.core.prismIni):
                fps = self.core.getConfig("globals", "fps", configPath=self.core.prismIni)

            args = OrderedDict([
                ("-start_number", startNum),
                ("-framerate", fps),
                ("-apply_trc", "iec61966_2_1"),
                ("-i", inputpath),
                ("-pix_fmt", "yuva420p"),
                ("-start_number_out", startNum),
            ])

            if startNum is None:
                args.popitem(last=False)
                args.popitem(last=True)

        if outputExt == ".jpg":
            quality = self.core.getConfig("media", "jpgCompression", dft=4, config="project")
            args["-qscale:v"] = str(quality)

        if outputExt == ".mp4":
            quality = self.core.getConfig("media", "mp4Compression", dft=18, config="project")
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
        nProc = subprocess.Popen(argList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = nProc.communicate()

        return result

    @err_catcher(name=__name__)
    def getPixmapFromPath(self, path):
        if platform.system() == "Windows":
            return QPixmap(path)
        else:
            try:
                im = Image.open(path)
                im = im.convert("RGBA")
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (b, g, r, a))
                data = im.tobytes("raw", "RGBA")

                qimg = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)

                return QPixmap(qimg)
            except:
                return QPixmap(path)

    @err_catcher(name=__name__)
    def savePixmap(self, pmap, path):
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        if platform.system() == "Windows":
            pmap.save(path, "JPG")
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
        if pVersion == 2:
            from urllib2 import urlopen
        else:
            from urllib.request import urlopen

        try:
            data = urlopen(url).read()
        except:
            logger.warning("failed to get pixmap from url: %s" % url)
            return

        image = QImage()
        image.loadFromData(data)
        pmap = QPixmap(image)
        return pmap

    @err_catcher(name=__name__)
    def getPixmapFromClipboard(self):
        return QApplication.clipboard().pixmap()

    @err_catcher(name=__name__)
    def scalePixmap(self, pixmap, width, height, keepRatio=True, fitIntoBounds=True):
        if keepRatio:
            if fitIntoBounds:
                mode = Qt.KeepAspectRatio
            else:
                mode = Qt.KeepAspectRatioByExpanding
        else:
            mode = Qt.IgnoreAspectRatio

        pixmap = pixmap.scaled(width, height, mode)
        return pixmap

    @err_catcher(name=__name__)
    def getMediaInformation(self, path):
        resolution = self.getMediaResolution(path)
        width = resolution["width"]
        height = resolution["height"]
        seqInfo = self.getMediaSequence(path)
        isSequence = seqInfo["isSequence"]
        start = seqInfo["start"]
        end = seqInfo["end"]
        files = seqInfo["files"]

        result = {
            "width": width,
            "height": height,
            "isSequence": isSequence,
            "start": start,
            "end": end,
            "files": files
        }

        return result

    @err_catcher(name=__name__)
    def getMediaResolution(self, path):
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
        ]:
            size = self.getPixmapFromPath(path).size()
            pwidth = size.width()
            pheight = size.height()
        elif ext in [".exr", ".dpx"]:
            oiio = self.getOIIO()
            imgSpecs = oiio.ImageBuf(path).spec()
            pwidth = imgSpecs.full_width
            pheight = imgSpecs.full_height
        elif ext in [".mp4", ".mov"]:
            if os.stat(path).st_size == 0:
                vidReader = "Error"
            else:
                imageio = self.getImageIO()
                try:
                    vidReader = imageio.get_reader(path, "ffmpeg")
                except:
                    vidReader = "Error"
                    logger.debug("failed to read videofile: %s" % traceback.format_exc())

            if vidReader != "Error":
                pwidth = vidReader._meta["size"][0]
                pheight = vidReader._meta["size"][1]

        return {"width": pwidth, "height": pheight}

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
                frame = int(base[-self.core.framePadding:])
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
