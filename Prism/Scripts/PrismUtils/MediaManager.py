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
import time
import threading
from typing import Any, Optional, List, Dict, Tuple

from collections import OrderedDict

# imageio / imageio-ffmpeg and CPython's subprocess._wait share non-thread-safe
# C-extension state.  Concurrent calls to either imageio.get_reader() or
# subprocess.communicate() from multiple thumbnail threads cause a fatal
# "seterror_argument failed to call update_mapping" crash.  One lock
# serialises ALL ffmpeg operations across both code paths.
_FFMPEG_LOCK = threading.Lock()

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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class MediaManager(object):
    """Manages media file operations, sequences, and conversions.
    
    Handles detection and processing of image sequences, video files, and single images.
    Provides functionality for format conversion, thumbnail generation, and media file validation.
    Supports various image formats (jpg, png, exr, dpx, etc.) and video formats (mp4, mov, etc.).
    
    Attributes:
        core: Reference to the Prism core instance.
        supportedFormats (List[str]): List of supported file extensions.
        videoFormats (List[str]): List of video file extensions.
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the media manager.
        
        Args:
            core: Prism core instance
        """
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
            ".psd",
            ".pdf",
            ".mp4",
            ".mov",
            ".avi",
            ".m4v",
            ".mxf",
        ]
        self.videoFormats = [".mp4", ".mov", ".avi", ".m4v", ".mxf"]
        self.getImageIO()

    @err_catcher(name=__name__)
    def filterValidMediaFiles(self, filepaths: List[str]) -> List[str]:
        """Filter a list of file paths to include only supported media files.
        
        Args:
            filepaths: List of file paths to filter.
            
        Returns:
            List[str]: List of valid media file paths with supported extensions.
        """
        validFiles = []
        for mediaFile in sorted(filepaths):
            if os.path.splitext(mediaFile)[1].lower() in self.supportedFormats:
                validFiles.append(mediaFile)
            elif os.path.basename(mediaFile) == "REDIRECT.txt":
                validFiles.append(mediaFile)

        return validFiles

    @err_catcher(name=__name__)
    def detectSequence(self, filepaths: List[str], baseFile: Optional[str] = None) -> List[str]:
        """Detect all files in a sequence based on filename patterns.
        
        Groups files with the same base name and only differing frame numbers.
        
        Args:
            filepaths: List of file paths to analyze.
            baseFile: Optional base file to match against. Uses first file if None.
            
        Returns:
            List[str]: List of files belonging to the same sequence.
        """
        seq = []
        baseFile = baseFile or filepaths[0]
        base = re.sub(r"\d+", "", baseFile)
        for filepath in sorted(filepaths):
            if re.sub(r"\d+", "", filepath) == base:
                seq.append(filepath)

        return seq

    @err_catcher(name=__name__)
    def getSequenceFromFilename(self, filename: str) -> str:
        """Convert a filename with frame numbers to a sequence pattern.
        
        Replaces frame numbers with '#' padding characters to create a sequence pattern.
        
        Args:
            filename: Path to a file with a frame number.
            
        Returns:
            str: Sequence pattern with '#' characters, or original filename if not a sequence.
        """
        seq = filename
        baseName, extension = os.path.splitext(os.path.basename(filename))
        extension = extension.lower()
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
    def isFilenameInSequence(self, filename: str, sequence: str) -> bool:
        """Check if a filename belongs to a given sequence.
        
        Args:
            filename: File path to check.
            sequence: Sequence pattern with '#' padding.
            
        Returns:
            bool: True if filename matches the sequence pattern, False otherwise.
        """
        cleanSeq = self.getFilenameWithoutFrameNumber(os.path.basename(sequence.replace("#", "")))
        cleanFilename = self.getFilenameWithoutFrameNumber(os.path.basename(filename))
        inseq = cleanSeq == cleanFilename
        return inseq

    @err_catcher(name=__name__)
    def getFrameNumberFromFilename(self, filename: str) -> Optional[str]:
        """Extract the frame number from a filename.
        
        Args:
            filename: File path or name containing a frame number.
            
        Returns:
            Optional[str]: Frame number string, or None if not found.
        """
        baseName, extension = os.path.splitext(filename)
        if len(baseName) >= self.core.framePadding:
            endStr = baseName[-self.core.framePadding:]
            if pVersion == 2:
                endStr = unicode(endStr)

            if endStr.isnumeric():
                return endStr

    @err_catcher(name=__name__)
    def getFilenameWithFrameNumber(self, filename: str, framenumber: int) -> str:
        """Replace '#' padding in a filename with an actual frame number.
        
        Args:
            filename: Sequence pattern with '#' padding characters.
            framenumber: Frame number to insert.
            
        Returns:
            str: Filename with padded frame number.
        """
        framename = filename.replace("#" * self.core.framePadding, "%0{}d".format(self.core.framePadding) % int(framenumber))
        return framename

    @err_catcher(name=__name__)
    def getFilenameWithoutFrameNumber(self, filename: str) -> str:
        """Remove frame number from a filename.
        
        Args:
            filename: File path or name containing a frame number.
            
        Returns:
            str: Filename with frame number removed.
        """
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
    def detectSequences(self, files: List[str], getFirstFile: bool = False, sequencePattern: bool = True) -> Dict[str, List[str]]:
        """Detect all image sequences in a list of files.
        
        Groups files together by their base names, creating sequence patterns
        for files that differ only in frame numbers.
        
        Args:
            files: List of file paths to analyze.
            getFirstFile: If True, return immediately after finding first file.
            sequencePattern: If True, create sequence patterns with '#' padding.
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping sequence patterns to file lists.
        """
        foundSrc = {}
        psources = []
        for file in files:
            baseName, extension = os.path.splitext(file)
            extension = extension.lower()
            if extension in self.core.media.supportedFormats:
                filename = self.getFilenameWithoutFrameNumber(file)
                psources.append(os.path.splitext(filename))

        for file in sorted(files):
            baseName, extension = os.path.splitext(file)
            extension = extension.lower()
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
    def getImgSources(self, path: str, getFirstFile: bool = False, sequencePattern: bool = True) -> List[str]:
        """Get all image sources from a directory.
        
        Scans a directory and detects all image sequences and single files.
        
        Args:
            path: Directory path to scan.
            getFirstFile: If True, return immediately after finding first file.
            sequencePattern: If True, create sequence patterns with '#' padding.
            
        Returns:
            List[str]: List of file paths or sequence patterns.
        """
        foundSrc = []
        files = []
        for root, folder, files in os.walk(path):
            break

        foundSrc = self.detectSequences(files, getFirstFile=getFirstFile, sequencePattern=sequencePattern)
        if foundSrc:
            foundSrc = [os.path.join(path, src) for src in foundSrc]

        return foundSrc

    @err_catcher(name=__name__)
    def getFilesFromSequence(self, sequence: str) -> List[str]:
        """Get all actual file paths from a sequence pattern.
        
        Args:
            sequence: Sequence pattern with '#' or '?' wildcards.
            
        Returns:
            List[str]: Sorted list of matching file paths.
        """
        files = glob.glob(sequence.replace("#", "?"))
        files = sorted(files)
        return files

    @err_catcher(name=__name__)
    def getFirstFilePpathFromSequence(self, sequence: str) -> Optional[str]:
        """Get the first file path from a sequence pattern.
        
        Args:
            sequence: Sequence pattern with '#' or '?' wildcards.
            
        Returns:
            Optional[str]: First matching file path, or None if no files found.
        """
        files = self.getFilesFromSequence(sequence)
        if files:
            return files[0]

    @err_catcher(name=__name__)
    def getFrameRangeFromSequence(self, filepaths: List[str], baseFile: Optional[str] = None) -> List:
        """Extract the frame range from a list of sequence files.
        
        Args:
            filepaths: List of file paths in the sequence.
            baseFile: Optional base file to use for extraction. Uses first file if None.
            
        Returns:
            List: [start_frame, end_frame] as integers, or ['?', '?'] if extraction fails.
        """
        baseFile = baseFile or filepaths[0]
        startPath = baseFile
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

        return [start, end]

    @err_catcher(name=__name__)
    def getVideoReader(self, filepath: str) -> Any:
        """Get a video reader object for reading video frames.
        
        Args:
            filepath: Path to the video file.
            
        Returns:
            Any: ImageIO video reader object, or error string if loading fails.
        """
        if os.stat(filepath).st_size == 0:
            reader = "Error - empty file: %s" % filepath
        else:
            imageio = self.getImageIO()
            if not imageio:
                details = ""
                try:
                    import imageio
                    import imageio.plugins.ffmpeg
                    import imageio_ffmpeg
                except Exception as e:
                    details = str(e)

                msg = "Error: imageio module couldn't be loaded"
                if details:
                    msg += ": %s" % details

                return msg

            filepath = str(filepath)  # unicode causes errors in Python 2
            if platform.system() == "Windows":
                filepath = filepath.lower()

            try:
                with _FFMPEG_LOCK:
                    reader = imageio.get_reader(filepath, "ffmpeg")
            except Exception as e:
                reader = "Error - %s" % e

        return reader

    @err_catcher(name=__name__)
    def checkMSVC(self) -> None:
        """Check if Microsoft Visual C++ Redistributable is installed on Windows.
        
        Prompts user to download and install if missing and not previously skipped.
        Required for EXR file preview generation.
        """
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
    def getOIIO(self) -> Any:
        """Get the OpenImageIO module if available.
        
        Attempts to import OpenImageIO (OIIO) for advanced image processing.
        Falls back to checking for MSVC if import fails on Windows.
        
        Returns:
            Any: OpenImageIO module if successful, None otherwise.
        """
        oiio = None

        try:
            if platform.system() == "Windows":
                import OpenImageIO as oiio
            elif platform.system() in ["Linux", "Darwin"]:
                import OpenImageIO as oiio

            oiio.ImageBuf
            oiio.ImageInput
        except:
            logger.debug("loading oiio failed: %s" % traceback.format_exc())
            self.checkMSVC()

        return oiio

    @err_catcher(name=__name__)
    def getImageIO(self) -> Any:
        """Get the ImageIO module for video/image processing.
        
        Initializes and configures ImageIO with FFmpeg support. Adds support
        for .m4v and .mxf video formats.
        
        Returns:
            Any: ImageIO module if successful, None otherwise.
        """
        if not hasattr(self, "_imageio"):
            imageio = None
            os.environ["IMAGEIO_FFMPEG_EXE"] = self.getFFmpeg()
            try:
                import imageio
                import imageio.plugins.ffmpeg
                import imageio_ffmpeg
            except:
                logger.debug("failed to load imageio: %s" % traceback.format_exc())
            else:
                try:
                    imageio.config.known_plugins["FFMPEG"].legacy_args["extensions"] += " .m4v"
                    for ext in imageio.config.extension_list:
                        if ext.extension == ".m4v":
                            ext.priority.insert(0, "FFMPEG")
                except:
                    pass

                try:
                    imageio.config.known_plugins["FFMPEG"].legacy_args["extensions"] += " .mxf"
                    for ext in imageio.config.extension_list:
                        if ext.extension == ".mxf":
                            ext.priority.insert(0, "FFMPEG")
                except:
                    pass

            self._imageio = imageio

        return self._imageio

    @err_catcher(name=__name__)
    def getFFmpeg(self, validate: bool = False) -> str:
        """Get the path to the FFmpeg executable.
        
        Args:
            validate: If True, validates that FFmpeg exists and is executable.
            
        Returns:
            str: Path to FFmpeg executable. Returns empty string if validation fails.
        """
        if os.getenv("PRISM_FFMPEG"):
            ffmpegPath = os.getenv("PRISM_FFMPEG")
        else:
            if platform.system() == "Windows":
                ffmpegPath = os.path.join(
                    self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg.exe"
                )
            elif platform.system() == "Linux":
                ffmpegPath = os.path.join(
                    self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg"
                )
            elif platform.system() == "Darwin":
                ffmpegPath = os.path.join(
                    self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg"
                )

        if validate:
            result = self.validateFFmpeg(ffmpegPath)
            if not result:
                return

        return ffmpegPath

    @err_catcher(name=__name__)
    def validateFFmpeg(self, path: str) -> bool:
        """Validate that FFmpeg is available at the given path.
        
        Args:
            path: Path to the FFmpeg executable to validate.
            
        Returns:
            bool: True if FFmpeg is available and executable, False otherwise.
        """
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
    def checkOddResolution(self, path: str, popup: bool = False) -> bool:
        """Check if media resolution has odd dimensions.
        
        Media with odd width or height cannot be properly converted to mp4 format.
        
        Args:
            path: Path to the media file to check.
            popup: If True, shows popup message when odd resolution detected.
            
        Returns:
            bool: False if resolution is odd, True otherwise or if resolution cannot be determined.
        """
        res = self.getMediaResolution(path)
        if not res or not res["width"] or not res["height"]:
            return True

        if int(res["width"]) % 2 == 1 or int(res["height"]) % 2 == 1:
            if popup:
                self.core.popup("Media with odd resolution can't be converted to mp4.")

            return False

        return True

    @err_catcher(name=__name__)
    def convertMedia(self, inputpath: str, startNum: Optional[int], outputpath: str, settings: Optional[Dict] = None) -> Tuple:
        """Convert media files using FFmpeg.
        
        Converts between image sequences and video formats, or between different
        image/video formats. Automatically handles frame padding and format-specific settings.
        
        Args:
            inputpath: Path to input file or sequence pattern.
            startNum: Starting frame number for sequences, None for videos.
            outputpath: Path for output file or sequence pattern.
            settings: Optional dict of additional FFmpeg arguments.
            
        Returns:
            Tuple: (stdout, stderr) from FFmpeg process.
        """
        inputpath = inputpath.replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1].lower()
        outputExt = os.path.splitext(outputpath)[1].lower()
        videoInput = inputExt in self.videoFormats
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
            try:
                os.makedirs(os.path.dirname(outputpath))
            except FileExistsError:
                pass

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

            checkPath = inputpath
            if "%" in inputpath or "#" in inputpath:
                pattern = re.sub(r"%\d*d", "*", inputpath).replace("#", "?")
                matches = sorted(glob.glob(pattern))
                if matches:
                    checkPath = matches[0]

            res = self.getMediaResolution(checkPath)
            if not res["width"] or not res["height"] or int(res["width"]) % 2 == 1 or int(res["height"]) % 2 == 1:
                args["-vf"] = "pad=ceil(iw/2)*2:ceil(ih/2)*2"

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
        if platform.system() == "Windows":
            shell = True
        else:
            shell = False

        try:
            nProc = subprocess.Popen(
                argList, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell
            )
        except Exception as e:
            msg = "ffmpeg conversion failed to start: %s" % str(e)
            self.core.popup(msg)
            return

        result = nProc.communicate()

        if sys.version[0] == "3":
            result = [x.decode("utf-8", "ignore") for x in result]

        logger.debug("Conversion result: " + str(result))
        return result

    @err_catcher(name=__name__)
    def invalidateOiioCache(self, force: bool = False) -> None:
        """Invalidate the OpenImageIO image cache.
        
        Clears cached image data to ensure fresh reads. Useful when external
        processes modify images.
        
        Args:
            force: If True, always invalidate. If False, only invalidate if PRISM_REFRESH_OIIO_CACHE env var is set.
        """
        oiio = self.getOIIO()
        if not oiio:
            return

        if eval(os.getenv("PRISM_REFRESH_OIIO_CACHE", "False")) or force:
            oiio.ImageCache().invalidate_all()

    @err_catcher(name=__name__)
    def getLayersFromFile(self, filepath: str) -> List[str]:
        """Extract layer names from an EXR file.
        
        Reads all subimages and channels from an EXR file and returns the unique layer names.
        
        Args:
            filepath: Path to the EXR file.
            
        Returns:
            List[str]: List of layer names found in the file.
        """
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

            exts = [".R", ".G", ".B", ".Z", ".r", ".g", ".b", ".red", ".green", ".blue", ".x", ".y", ".z"]
            for name in cnames:
                canAdd = True
                for ext in exts:
                    if name.endswith(ext):
                        lname = name[:-len(ext)]
                        canAdd = False
                        if lname not in names:
                            names.append(lname)
                            break
                else:
                    if canAdd and name not in ["R", "G", "B", "r", "g", "b"]:
                        names.append(name)

            imgNum += 1

        imgInput.close()
        return names

    @err_catcher(name=__name__)
    def getMetaDataFromExrFile(self, filepath: str) -> List[Dict]:
        """Extract metadata from an EXR file.
        
        Args:
            filepath: Path to the EXR file.
            
        Returns:
            List[Dict]: List of dicts containing metadata attributes and values.
        """
        base, ext = os.path.splitext(filepath)
        if ext not in [".exr"]:
            return []

        oiio = self.getOIIO()
        if not oiio:
            return []

        img = oiio.ImageInput.open(filepath)
        if not img:
            return []

        spec = img.spec()
        metaData = []

        for attr in spec.extra_attribs:
            metaData.append({attr.name: attr.value})

        img.close()
        return metaData

    @err_catcher(name=__name__)
    def getThumbnailPath(self, path: str) -> str:
        """Get the thumbnail cache path for a media file.
        
        Args:
            path: Path to the original media file.
            
        Returns:
            str: Path where the thumbnail should be stored.
        """
        thumbPath = os.path.join(os.path.dirname(path), "_thumbs", os.path.basename(os.path.splitext(path)[0]) + ".jpg")
        return thumbPath

    @err_catcher(name=__name__)
    def getUseThumbnailForFile(self, filepath: str) -> bool:
        """Determine if thumbnails should be used for a file type.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            bool: True if thumbnails are recommended for this file type.
        """
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        useThumb = ext in [".exr", ".dpx", ".hdr", ".psd", ".pdf"] or ext in self.videoFormats
        return useThumb        

    @err_catcher(name=__name__)
    def getUseThumbnails(self) -> bool:
        """Check if thumbnail caching is globally enabled.
        
        Returns:
            bool: True if thumbnails are enabled in config.
        """
        return self.core.getConfig("globals", "useMediaThumbnails", dft=True)

    @err_catcher(name=__name__)
    def setUseThumbnails(self, state: bool) -> Any:
        """Set whether thumbnail caching is globally enabled.
        
        Args:
            state: True to enable thumbnails, False to disable.
            
        Returns:
            Any: Result from setConfig operation.
        """
        return self.core.setConfig("globals", "useMediaThumbnails", val=state)

    @err_catcher(name=__name__)
    def startNukeProcess(self) -> Optional[subprocess.Popen]:
        """Start a Nuke process for generating previews.
        
        Launches Nuke in terminal mode for image processing operations. The process
        runs in the background and can accept Python scripts via stdin.
        
        Returns:
            Optional[subprocess.Popen]: The Nuke subprocess if started successfully, None otherwise.
        """
        nukePath = os.getenv("PRISM_NUKE_EXE")
        if not nukePath or not os.path.exists(nukePath):
            return

        if os.getenv("PRISM_NUKE_INTERACTIVE_LICENSE", "0") == "1":
            mode = "-ti"
        else:
            mode = "-t"

        args = [nukePath, mode]
        logger.debug("starting Nuke with these args:\n\n%s" % args)
        env = self.core.startEnv.copy()
        self.nukeProc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )
        import threading

        def read_output(stream: Any) -> None:
            """Read and print output from stream.
            
            Args:
                stream: Input stream to read from
            """
            for line in iter(stream.readline, ""):
                print(line, end="")

        threading.Thread(target=read_output, args=(self.nukeProc.stdout,), daemon=True).start()
        threading.Thread(target=read_output, args=(self.nukeProc.stderr,), daemon=True).start()
        return self.nukeProc

    @err_catcher(name=__name__)
    def sendScriptToNuke(self, script: str) -> None:
        """Send a Python script to the running Nuke process.
        
        Args:
            script: Python script to execute in Nuke.
        """
        if self.nukeProc.stdin:
            self.nukeProc.stdin.write(script + "\n")
            self.nukeProc.stdin.flush()
        else:
            print("Failed to send script. Nuke process stdin is not available.")

    @err_catcher(name=__name__)
    def getPixmapFromExrPathWithoutOIIO(self, path: str, width: Optional[int] = None, height: Optional[int] = None, 
                                        channel: Optional[str] = None, allowThumb: bool = True, 
                                        regenerateThumb: bool = False) -> Optional[QPixmap]:
        """Get a QPixmap from an EXR file without using OpenImageIO.
        
        Falls back to either Nuke or FFmpeg for reading EXR files when OIIO is unavailable.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract.
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QPixmap]: The image as a QPixmap, or None if failed.
        """
        useNuke = os.getenv("PRISM_USE_NUKE_FOR_PREVIEWS", "0") == "1"
        if useNuke:
            pmap = self.getPixmapFromExrPathFromNuke(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)
        else:
            pmap = self.getPixmapFromExrPathFromFfmpeg(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)

        return pmap

    @err_catcher(name=__name__)
    def getQImageFromExrPathWithoutOIIO(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                                        channel: Optional[str] = None, allowThumb: bool = True,
                                        regenerateThumb: bool = False) -> Optional[QImage]:
        """Get a QImage from an EXR file without using OpenImageIO.
        
        Falls back to either Nuke or FFmpeg for reading EXR files when OIIO is unavailable.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract.
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QImage]: The image as a QImage, or None if failed.
        """
        useNuke = os.getenv("PRISM_USE_NUKE_FOR_PREVIEWS", "0") == "1"
        if useNuke:
            pmap = self.getPixmapFromExrPathFromNuke(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)
            qimg = pmap.toImage()
        else:
            qimg = self.getQImageFromExrPathFromFfmpeg(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)

        return qimg

    @err_catcher(name=__name__)
    def generateImageFromExrPathFromFfmpeg(self, path: str, allowThumb: bool = True) -> Optional[str]:
        """Generate a JPEG thumbnail from an EXR file using FFmpeg.
        
        Converts EXR files to JPEG format with proper color space conversion.
        Waits for up to 30 seconds for FFmpeg to complete the conversion.
        
        Args:
            path: Path to the EXR file.
            allowThumb: Whether to save the result as a cached thumbnail.
            
        Returns:
            Optional[str]: Path to the generated JPEG file, or None if failed.
        """
        ffmpegPath = self.getFFmpeg()
        if not ffmpegPath or not os.path.exists(ffmpegPath):
            return

        thumbEnabled = self.getUseThumbnails()
        if thumbEnabled and allowThumb:
            outputPath = self.getThumbnailPath(path)
        else:
            outputPath = self.core.getTempFilepath(filename=os.path.splitext(os.path.basename(path))[0] + ".jpg")

        if not os.path.exists(os.path.dirname(outputPath)):
            while True:
                try:
                    os.makedirs(os.path.dirname(outputPath), exist_ok=True)
                    break
                except FileExistsError:
                    pass
                except Exception as e:
                    if os.getenv("PRISM_IGNORE_THUMBNAIL_DIR_CREATION_ERRORS", "0") == "1":
                        return

                    msg = "Failed to create thumbnail directory: %s\n\n%s\n\nRetry?" % (os.path.dirname(outputPath), str(e))
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], default="Cancel")
                    if result != "Retry":
                        return

        outputPath = outputPath.replace("\\", "/")

        args = [ffmpegPath]
        args.append("-hide_banner")
        args.append("-y")
        args.append("-loglevel")
        args.append("error")
        args.append("-apply_trc")
        args.append("iec61966_2_1")
        # args.append("-layer")
        # args.append("ViewLayer.Combined")  # Blender EXR files
        args.append("-i")
        args.append(path)
        args.append("-pix_fmt")
        args.append("yuvj420p")
        args.append("-update")
        args.append("true")
        args.append(outputPath)
        logger.debug("starting FFMPEG with these args:\n\n%s" % args)
        env = self.core.startEnv.copy()
        popenKwargs = {
            "env": env,
            "text": True,
            "bufsize": 1,
        }
        if platform.system() == "Windows":
            popenKwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        # Use a local variable so concurrent calls from multiple thumbnail workers
        # don't overwrite each other's process reference via self.ffmpegProc.
        # _FFMPEG_LOCK serialises Popen+communicate so CPython's subprocess._wait
        # internal state is never entered by more than one thread at a time.
        with _FFMPEG_LOCK:
            ffmpegProc = subprocess.Popen(args, **popenKwargs)
            ffmpegProc.communicate()

        for idx in range(30):
            if os.path.exists(outputPath):
                logger.debug("ffmpeg thumbnail generated: %s" % outputPath)
                break

            if ffmpegProc.poll():
                logger.debug("failed to generate thumbnail using ffmpeg: %s" % outputPath)
                return

            time.sleep(1)
        else:
            logger.warning("failed to generate thumbnail with FFMPEG.")
            return

        return outputPath

    @err_catcher(name=__name__)
    def getPixmapFromExrPathFromFfmpeg(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                                       channel: Optional[str] = None, allowThumb: bool = True,
                                       regenerateThumb: bool = False) -> Optional[QPixmap]:
        """Get a QPixmap from an EXR file using FFmpeg.
        
        Generates a JPEG thumbnail via FFmpeg and loads it as a QPixmap.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract (not used in FFmpeg conversion).
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QPixmap]: The image as a QPixmap, or None if failed.
        """
        outputPath = self.generateImageFromExrPathFromFfmpeg(path, allowThumb)
        if not outputPath:
            return

        pmap = self.getPixmapFromPath(outputPath, width=width, height=height)
        thumbEnabled = self.getUseThumbnails()
        if not thumbEnabled or not allowThumb:
            try:
                os.remove(outputPath)
            except:
                pass

        return pmap

    @err_catcher(name=__name__)
    def getQImageFromExrPathFromFfmpeg(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                                       channel: Optional[str] = None, allowThumb: bool = True,
                                       regenerateThumb: bool = False) -> Optional[QImage]:
        """Get a QImage from an EXR file using FFmpeg.
        
        Generates a JPEG thumbnail via FFmpeg and loads it as a QImage.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract (not used in FFmpeg conversion).
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QImage]: The image as a QImage, or None if failed.
        """
        outputPath = self.generateImageFromExrPathFromFfmpeg(path, allowThumb)
        if not outputPath:
            return

        qimg = self.getQImageFromPath(outputPath, width=width, height=height)
        thumbEnabled = self.getUseThumbnails()
        if not thumbEnabled or not allowThumb:
            try:
                os.remove(outputPath)
            except:
                pass

        return qimg

    @err_catcher(name=__name__)
    def getPixmapFromExrPathFromNuke(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                                     channel: Optional[str] = None, allowThumb: bool = True,
                                     regenerateThumb: bool = False) -> Optional[QPixmap]:
        """Get a QPixmap from an EXR file using Nuke.
        
        Uses Nuke's Read and Write nodes to convert EXR files to JPEG format.
        Waits for up to 30 seconds for Nuke to complete the conversion.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract (not used in Nuke conversion).
            allowThumb: Whether to use/save cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QPixmap]: The image as a QPixmap, or None if failed.
        """
        if getattr(self, "nukeProc", None) and not self.nukeProc.poll():
            nukeProc = self.nukeProc
        else:
            nukeProc = self.startNukeProcess()

        if not nukeProc:
            return

        thumbEnabled = self.getUseThumbnails()
        if thumbEnabled and allowThumb:
            outputPath = self.getThumbnailPath(path)
            cleanTemp = False
        else:
            outputPath = self.core.getTempFilepath(filename=os.path.splitext(os.path.basename(path))[0] + ".jpg")
            cleanTemp = True

        if not os.path.exists(os.path.dirname(outputPath)):
            try:
                os.makedirs(os.path.dirname(outputPath))
            except FileExistsError:
                pass

        outputPath = outputPath.replace("\\", "/")
        start = end = 1

        cmd = """
read = nuke.createNode("Read")
write = nuke.createNode("Write")
write.setInput(0, read)
nuke.root().knob("first_frame").setValue(float(%s))
nuke.root().knob("last_frame").setValue(float(%s))
read.knob("file").fromUserText(\"%s\")
write.knob("file").setValue(\"%s\")
nuke.execute(write, %s, %s)
""" % (start, end, path.replace("\\", "/"), outputPath, start, end)

        self.sendScriptToNuke(cmd)
        for idx in range(30):
            if os.path.exists(outputPath):
                logger.debug("nuke thumbnail generated: %s" % outputPath)
                break

            time.sleep(1)
        else:
            logger.warning("failed to generate thumbnail with Nuke.")
            return

        pmap = self.getPixmapFromPath(outputPath, width=width, height=height)
        if cleanTemp:
            try:
                os.remove(outputPath)
            except:
                pass

        return pmap

    @err_catcher(name=__name__)
    def getIsNumpyAvailable(self):
        return bool("numpy" in globals())

    @err_catcher(name=__name__)
    def getPixmapFromExrPath(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                              channel: Optional[str] = None, allowThumb: bool = True,
                              regenerateThumb: bool = False) -> Optional[QPixmap]:
        """Get a QPixmap from an EXR file.
        
        Attempts to read EXR files using OpenImageIO first, falls back to FFmpeg or Nuke if unavailable.
        Automatically generates and caches thumbnails when enabled.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract (e.g., 'RGB', 'beauty', 'diffuse').
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QPixmap]: The image as a QPixmap, or None if failed.
        """
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb and path:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getPixmapFromPath(thumbPath, width=width, height=height)

        oiio = self.getOIIO()
        if not oiio:
            # msg = "OpenImageIO is not available. Unable to read the file."
            # self.core.popup(msg)
            return self.getPixmapFromExrPathWithoutOIIO(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)

        qimg = self.getQImageFromExrPath(path, width=width, height=height, channel=channel, allowThumb=allowThumb, regenerateThumb=regenerateThumb)
        if not qimg:
            return

        pixmap = QPixmap.fromImage(qimg)
        if thumbEnabled and allowThumb:
            thumbPath = self.getThumbnailPath(path)
            self.savePixmap(pixmap, thumbPath)

        return pixmap

    @err_catcher(name=__name__)
    def getQImageFromExrPath(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                              channel: Optional[str] = None, allowThumb: bool = True,
                              regenerateThumb: bool = False) -> Optional[QImage]:
        """Get a QImage from an EXR file.
        
        Attempts to read EXR files using OpenImageIO first, falls back to FFmpeg or Nuke if unavailable.
        Supports multi-channel EXR files and automatic thumbnail caching. Applies gamma correction  
        and converts to sRGB color space.
        
        Args:
            path: Path to the EXR file.
            width: Target width for scaling.
            height: Target height for scaling.
            channel: Channel name to extract (e.g., 'RGB', 'beauty', 'diffuse').
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QImage]: The image as a QImage, or None if failed.
        """
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb and path:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getQImageFromPath(thumbPath, width=width, height=height)

        oiio = self.getOIIO()
        if not oiio:
            return self.getQImageFromExrPathWithoutOIIO(
                path,
                width=width,
                height=height,
                channel=channel,
                allowThumb=allowThumb,
                regenerateThumb=regenerateThumb
            )

        path = str(path)  # for python 2
        imgInput = oiio.ImageInput.open(path)
        if not imgInput:
            error = oiio.geterror()
            logger.debug("failed to read media file: %s - %s" % (path, error))
            return

        chbegin = 0
        chend = 3
        numChannels = 3
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
                            if idx == -1:
                                idx = imgInput.spec().channelindex(channel + ".Z")
                                if idx != -1:
                                    numChannels = 1
                                elif idx == -1 and channel in ["RGB", "RGBA"]:
                                    idx = imgInput.spec().channelindex("R")
                                elif idx == -1:
                                    idx = imgInput.spec().channelindex(channel)
                                    numChannels = 1

                if idx == -1:
                    subimage += 1
                else:
                    chbegin = idx
                    chend = chbegin + numChannels
                    break

        try:
            pixels = imgInput.read_image(subimage=subimage, miplevel=0, chbegin=chbegin, chend=chend)
        except Exception as e:
            logger.warning("failed to read image: %s - %s" % (path, e))
            return

        if pixels is None:
            logger.warning("failed to read image (no pixels): %s" % (path))
            return

        rgbImgSrc = oiio.ImageBuf(
            oiio.ImageSpec(imgInput.spec().full_width, imgInput.spec().full_height, numChannels, oiio.UINT16)
        )
        imgInput.close()

        if self.getIsNumpyAvailable():
            rgbImgSrc.set_pixels(imgInput.spec().roi, numpy.array(pixels))
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
            oiio.ImageSpec(int(newImgWidth), int(newImgHeight), numChannels, oiio.UINT16)
        )
        oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
        sRGBimg = oiio.ImageBuf()
        oiio.ImageBufAlgo.pow(sRGBimg, imgDst, (1.0 / 2.2, 1.0 / 2.2, 1.0 / 2.2))
        bckImg = oiio.ImageBuf(
            oiio.ImageSpec(int(newImgWidth), int(newImgHeight), numChannels, oiio.UINT16)
        )
        oiio.ImageBufAlgo.fill(bckImg, (0.5, 0.5, 0.5))
        oiio.ImageBufAlgo.paste(bckImg, xOffset, yOffset, 0, 0, sRGBimg)
        if self.getIsNumpyAvailable():
            arr = numpy.array(bckImg.get_pixels(oiio.UINT8), dtype=numpy.uint8)
            if numChannels == 1:
                arr = numpy.repeat(arr, 3, axis=2)
            arr = numpy.ascontiguousarray(arr)
            imgH, imgW = arr.shape[:2]
            qimg = QImage(arr.data, imgW, imgH, imgW * 3, QImage.Format_RGB888).copy()
        else:
            qimg = QImage(int(newImgWidth), int(newImgHeight), QImage.Format_RGB32)
            for i in range(int(newImgWidth)):
                for k in range(int(newImgHeight)):
                    if numChannels == 3:
                        rgb = qRgb(
                            bckImg.getpixel(i, k)[0] * 255,
                            bckImg.getpixel(i, k)[1] * 255,
                            bckImg.getpixel(i, k)[2] * 255,
                        )
                    else:
                        rgb = qRgb(
                            bckImg.getpixel(i, k)[0] * 255,
                            bckImg.getpixel(i, k)[0] * 255,
                            bckImg.getpixel(i, k)[0] * 255,
                        )
                    qimg.setPixel(i, k, rgb)
        if thumbEnabled and allowThumb:
            thumbPath = self.getThumbnailPath(path)
            self.saveQImage(qimg, thumbPath)

        return qimg

    @err_catcher(name=__name__)
    def getPixmapFromPath(self, path: str, width: Optional[int] = None, height: Optional[int] = None, 
                          colorAdjust: bool = False) -> Optional[QPixmap]:
        """Get a QPixmap from any supported media file path.
        
        Automatically handles different file formats including images, videos, and EXR files.
        Routes to appropriate reader based on file extension.
        
        Args:
            path: Path to the media file.
            width: Target width for scaling.
            height: Target height for scaling.
            colorAdjust: Whether to apply color adjustments (not currently used).
            
        Returns:
            Optional[QPixmap]: The image as a QPixmap, or None if failed.
        """
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in self.core.media.videoFormats:
            return self.getPixmapFromVideoPath(path)
        elif ext in [".exr", ".dpx", ".hdr", ".psd"]:
            return self.core.media.getPixmapFromExrPath(
                path, width, height
            )
        elif ext in [".pdf"]:
            return self.core.media.getPixmapFromPdfPath(
                path, width, height
            )

        pixmap = QPixmap(path)
        if pixmap.isNull():
            pixmap = self.core.media.getPixmapFromExrPath(
                path, width, height
            )

        if (width or height) and pixmap and not pixmap.isNull():
            pixmap = self.scalePixmap(pixmap, width, height)

        return pixmap

    @err_catcher(name=__name__)
    def getQImageFromPath(self, path: str, width: Optional[int] = None, height: Optional[int] = None,
                          colorAdjust: bool = False) -> Optional[QImage]:
        """Get a QImage from any supported media file path.
        
        Automatically handles different file formats including images, videos, and EXR files.
        Routes to appropriate reader based on file extension.
        
        Args:
            path: Path to the media file.
            width: Target width for scaling.
            height: Target height for scaling.
            colorAdjust: Whether to apply color adjustments (not currently used).
            
        Returns:
            Optional[QImage]: The image as a QImage, or None if failed.
        """
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in self.core.media.videoFormats:
            return self.getQImageFromVideoPath(path)
        elif ext in [".exr", ".dpx", ".hdr", ".psd"]:
            return self.core.media.getQImageFromExrPath(
                path, width, height
            )
        elif ext in [".pdf"]:
            return self.core.media.getQImageFromPdfPath(
                path, width, height
            )

        qimg = QImage(path)
        if qimg.isNull():
            qimg = self.core.media.getQImageFromExrPath(
                path, width, height
            )

        if (width or height) and qimg and not qimg.isNull():
            isGuiThread = (
                QApplication.instance()
                and QApplication.instance().thread() == QThread.currentThread()
            )
            if isGuiThread:  # doesn't seem to be threadsafe
                qimg = self.scalePixmap(qimg, width, height)

        return qimg

    @err_catcher(name=__name__)
    def getQImageFromVideoPath(self, path: str, allowThumb: bool = True, regenerateThumb: bool = False,
                               videoReader: Optional[Any] = None, imgNum: int = 0) -> Optional[QImage]:
        """Get a QImage from a video file.
        
        Extracts a frame from a video file using imageio. Falls back to a placeholder
        image if the video cannot be read. Supports thumbnail caching.
        
        Args:
            path: Path to the video file.
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            videoReader: Existing video reader object to reuse.
            imgNum: Frame number to extract (0-based).
            
        Returns:
            Optional[QImage]: The frame as a QImage, or a fallback image if failed.
        """
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb and imgNum == 0:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getQImageFromPath(thumbPath)

        _, ext = os.path.splitext(path)
        try:
            vidFile = self.core.media.getVideoReader(path) if videoReader is None else videoReader
            if self.core.isStr(vidFile):
                logger.warning(vidFile)
                imgPath = os.path.join(
                    self.core.projects.getFallbackFolder(),
                    "%s.jpg" % ext[1:].lower(),
                )
                qimg = self.getQImageFromPath(imgPath)
            else:
                image = vidFile.get_data(imgNum)
                fileRes = vidFile._meta["size"]
                width = fileRes[0]
                height = fileRes[1]
                qimg = QImage(image, width, height, 3 * width, QImage.Format_RGB888)
                if thumbEnabled and imgNum == 0:
                    thumbPath = self.getThumbnailPath(path)
                    self.saveQImage(qimg, thumbPath)

        except Exception as e:
            logger.debug(traceback.format_exc())
            imgPath = os.path.join(
                self.core.projects.getFallbackFolder(),
                "%s.jpg" % ext[1:].lower(),
            )
            qimg = self.getQImageFromPath(imgPath)

        return qimg

    @err_catcher(name=__name__)
    def getPixmapFromVideoPath(self, path: str, allowThumb: bool = True, regenerateThumb: bool = False,
                               videoReader: Optional[Any] = None, imgNum: int = 0) -> Optional[QPixmap]:
        """Get a QPixmap from a video file.
        
        Extracts a frame from a video file and converts it to a QPixmap. Falls back to
        a placeholder image if the video cannot be read. Supports thumbnail caching.
        
        Args:
            path: Path to the video file.
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            videoReader: Existing video reader object to reuse.
            imgNum: Frame number to extract (0-based).
            
        Returns:
            Optional[QPixmap]: The frame as a QPixmap, or a fallback image if failed.
        """
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
                pmsmall = self.getPixmapFromPath(imgPath)
            else:
                qimg = self.getQImageFromVideoPath(path, allowThumb=allowThumb, regenerateThumb=regenerateThumb, videoReader=vidFile, imgNum=imgNum)
                pmsmall = QPixmap.fromImage(qimg)

        except Exception as e:
            logger.debug(traceback.format_exc())
            imgPath = os.path.join(
                self.core.projects.getFallbackFolder(),
                "%s.jpg" % ext[1:].lower(),
            )
            pmsmall = self.getPixmapFromPath(imgPath)

        return pmsmall

    @err_catcher(name=__name__)
    def getPixmapFromPdfPath(
        self,
        path: str,
        width: Optional[int] = 800,
        height: Optional[int] = 1000,
        allowThumb: bool = True,
        regenerateThumb: bool = False,
    ) -> Optional[QPixmap]:
        """Get a QPixmap from a PDF file.
        
        Renders the first page of a PDF file to a QPixmap with a white background.
        The PDF page's aspect ratio is preserved, and the image is scaled to fit
        within the provided width and height bounds. Uses the Qt PDF module for
        rendering. Supports thumbnail caching for performance.
        
        Args:
            path: Path to the PDF file.
            width: Maximum width for rendering (default: 800).
            height: Maximum height for rendering (default: 1000).
            allowThumb: Whether to use cached thumbnails.
            regenerateThumb: Whether to regenerate existing thumbnails.
            
        Returns:
            Optional[QPixmap]: The rendered PDF page as a QPixmap with white background,
                              scaled to fit within bounds while preserving aspect ratio,
                              or None if failed.
        """
        image = self.getQImageFromPdfPath(
            path, width=width, height=height, allowThumb=allowThumb, regenerateThumb=regenerateThumb
        )
        pixmap = QPixmap.fromImage(image)
        return pixmap

    @err_catcher(name=__name__)
    def getQImageFromPdfPath(
        self,
        path: str,
        width: Optional[int] = 800,
        height: Optional[int] = 1000,
        allowThumb: bool = True,
        regenerateThumb: bool = False,
    ) -> Optional[QImage]:
        """Get a QImage from a PDF file.
        
        Renders the first page of a PDF file to a QImage with a white background.
        Uses QPdfDocument from PySide6.QtPdf for rendering. The PDF page's aspect
        ratio is preserved, and the image is scaled to fit within the provided width
        and height bounds. The PDF is composited onto a white background to ensure
        proper display of transparent PDFs. Supports automatic thumbnail caching.
        
        Args:
            path: Path to the PDF file.
            width: Maximum width for rendering in pixels (default: 800).
            height: Maximum height for rendering in pixels (default: 1000).
            allowThumb: Whether to use cached thumbnails if available.
            regenerateThumb: Whether to force regeneration of existing thumbnails.
            
        Returns:
            Optional[QImage]: The rendered PDF page as a QImage with white background,
                             scaled to fit within bounds while preserving aspect ratio,
                             or None if failed.
        """
        thumbEnabled = self.getUseThumbnails()
        if allowThumb and thumbEnabled and not regenerateThumb and path:
            thumbPath = self.getThumbnailPath(path)
            if os.path.exists(thumbPath):
                return self.getPixmapFromPath(thumbPath, width=width, height=height)

        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:
            logger.warning("PySide6.QtPdf is not available. Cannot render PDF.")
            return None
        doc = QPdfDocument()
        doc.load(path)
        page_index = 0
        width = width if width else 800
        height = height if height else 1000
        
        # Get the original PDF page size to preserve aspect ratio
        page_size = doc.pagePointSize(page_index)
        pdf_width = page_size.width()
        pdf_height = page_size.height()
        
        if pdf_width > 0 and pdf_height > 0:
            pdf_aspect = pdf_width / pdf_height
            target_aspect = width / height
            
            # Calculate render size to fit within bounds while preserving aspect ratio
            if pdf_aspect > target_aspect:
                # PDF is wider - fit to width
                render_width = width
                render_height = int(width / pdf_aspect)
            else:
                # PDF is taller - fit to height
                render_height = height
                render_width = int(height * pdf_aspect)
        else:
            # Fallback if page size cannot be determined
            render_width = width
            render_height = height
        
        # Render PDF to image at calculated size
        image = doc.render(page_index, QSize(render_width, render_height))
        
        # Create a white background image
        white_image = QImage(image.size(), QImage.Format_RGB32)
        white_image.fill(Qt.white)
        
        # Composite the PDF render on top of white background
        painter = QPainter(white_image)
        painter.drawImage(0, 0, image)
        painter.end()
        
        # Save thumbnail with white background
        pixmap = QPixmap.fromImage(white_image)
        if thumbEnabled and allowThumb:
            thumbPath = self.getThumbnailPath(path)
            self.savePixmap(pixmap, thumbPath)

        return white_image

    @err_catcher(name=__name__)
    def savePixmap(self, pmap: QPixmap, path: str) -> None:
        """Save a QPixmap to disk.
        
        Creates necessary directories and saves the pixmap as PNG or JPEG. On Linux/Mac,
        uses PIL for better compatibility. Prompts user if directory creation fails.
        
        Args:
            pmap: The QPixmap to save.
            path: Destination file path.
        """
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
    def saveQImage(self, qimg: QImage, path: str) -> None:
        """Save a QImage to disk.
        
        Creates necessary directories and saves the image as PNG or JPEG. On Linux/Mac,
        uses PIL for better compatibility. Prompts user if directory creation fails.
        
        Args:
            qimg: The QImage to save.
            path: Destination file path.
        """
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
                qimg.save(path, "PNG", 95)
            else:
                qimg.save(path, "JPG", 95)
        else:
            try:
                buf = QBuffer()
                buf.open(QIODevice.ReadWrite)
                qimg.save(buf, "PNG")

                strio = StringIO()
                strio.write(buf.data())
                buf.close()
                strio.seek(0)
                pimg = Image.open(strio)
                pimg.save(path)
            except:
                qimg.save(path, "JPG")

    @err_catcher(name=__name__)
    def getPixmapFromUrl(self, url: str, headers: Optional[Dict] = None) -> QPixmap:
        """Download an image from a URL and return it as a QPixmap.
        
        Args:
            url: The URL to download the image from.
            headers: Optional HTTP headers to include in the request.
            
        Returns:
            QPixmap: The downloaded image as a QPixmap.
        """
        import requests
        logger.debug("getting image from url: %s" % url)
        data = requests.get(url, headers=headers).content
        image = QImage()
        image.loadFromData(data)
        pmap = QPixmap(image)
        return pmap

    @err_catcher(name=__name__)
    def getQImageFromUrl(self, url: str, headers: Optional[Dict] = None) -> QImage:
        """Download an image from a URL and return it as a QImage.
        
        Args:
            url: The URL to download the image from.
            headers: Optional HTTP headers to include in the request.
            
        Returns:
            QImage: The downloaded image as a QImage.
        """
        import requests
        logger.debug("getting image from url: %s" % url)
        data = requests.get(url, headers=headers).content
        image = QImage()
        image.loadFromData(data)
        return image

    @err_catcher(name=__name__)
    def getPixmapFromClipboard(self) -> QPixmap:
        """Get the current pixmap from the system clipboard.
        
        Returns:
            QPixmap: The pixmap from the clipboard, or an empty pixmap if none exists.
        """
        return QApplication.clipboard().pixmap()

    @err_catcher(name=__name__)
    def scalePixmap(self, pixmap: QPixmap, width: int, height: int, keepRatio: bool = True,
                    fitIntoBounds: bool = True, crop: bool = False, fillBackground: Any = False) -> QPixmap:
        """Scale a pixmap to the specified dimensions.
        
        Args:
            pixmap: The pixmap to scale.
            width: Target width in pixels.
            height: Target height in pixels.
            keepRatio: Whether to maintain the original aspect ratio.
            fitIntoBounds: If True, scales to fit within bounds. If False, scales to fill bounds.
            crop: Whether to crop the image to exact dimensions when not fitting.
            fillBackground: Background color/fill when fitIntoBounds is True. Can be QColor, True for black, or False for none.
            
        Returns:
            QPixmap: The scaled pixmap.
        """
        if not pixmap:
            return pixmap

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
                if fillBackground is True:
                    new_pixmap.fill(Qt.black)
                else:
                    new_pixmap.fill(fillBackground)

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
    def getColoredIcon(self, path: str, force: bool = False, r: int = 150, g: int = 210, b: int = 240) -> QIcon:
        """Get a colored version of an icon.
        
        Applies a color tint to an icon when using certain themes or when forced.
        Used to match icons with the application's color scheme.
        
        Args:
            path: Path to the icon file.
            force: Whether to force color application regardless of theme.
            r: Red color component (0-255).
            g: Green color component (0-255).
            b: Blue color component (0-255).
            
        Returns:
            QIcon: The colored icon.
        """
        ssheet = self.core.getActiveStyleSheet()
        if getattr(self.core, "appPlugin", None) and self.core.appPlugin.pluginName == "Standalone" and ssheet and ssheet.get("name") == "Blue Moon" or force:
            image = QImage(path)
            cimage = QImage(image)
            cimage.fill((QColor(r, g, b)))
            cimage.setAlphaChannel(image.convertToFormat(QImage.Format_Alpha8))
            pixmap = QPixmap.fromImage(cimage)
        else:
            pixmap = QPixmap(path)

        return QIcon(pixmap)

    @err_catcher(name=__name__)
    def getMediaInformation(self, path: str) -> Dict[str, Any]:
        """Get comprehensive information about a media file or sequence.
        
        Retrieves resolution, frame range, and sequence information for the media.
        
        Args:
            path: Path to the media file or sequence pattern.
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - width: Image width in pixels
                - height: Image height in pixels
                - isSequence: Whether the path represents a sequence
                - start: First frame number (for sequences)
                - end: Last frame number (for sequences)
                - files: List of all files in the sequence
        """
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
    def getMediaResolution(self, path: str, videoReader: Optional[Any] = None) -> Dict[str, Optional[int]]:
        """Get the resolution of a media file.
        
        Supports images (jpg, png, tif, etc.), EXR files, and videos. Uses appropriate
        reader based on file extension.
        
        Args:
            path: Path to the media file.
            videoReader: Existing video reader object to reuse.
            
        Returns:
            Dict[str, Optional[int]]: Dictionary with 'width' and 'height' keys, or None values if failed.
        """
        pwidth = None
        pheight = None
        base, ext = os.path.splitext(path)
        ext = ext.lower()

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
            qimg = self.getQImageFromPath(path)
            if qimg:
                size = qimg.size()
                pwidth = size.width()
                pheight = size.height()
        elif ext in [".exr", ".dpx", ".hdr", ".psd"]:
            oiio = self.getOIIO()
            if oiio:
                path = str(path)  # for python 2
                buf = oiio.ImageBuf(path)
                imgSpecs = buf.spec()
                pwidth = imgSpecs.full_width
                pheight = imgSpecs.full_height
            else:
                qimg = self.getQImageFromExrPathWithoutOIIO(path)
                if qimg:
                    size = qimg.size()
                    pwidth = size.width()
                    pheight = size.height()
        
        elif ext in [".pdf"]:
            try:
                from PySide6.QtPdf import QPdfDocument
            except ImportError:
                logger.warning("PySide6.QtPdf is not available. Cannot get PDF resolution.")
            else:
                doc = QPdfDocument()
                doc.load(path)
                page_size = doc.pagePointSize(0)
                pwidth = int(page_size.width())
                pheight = int(page_size.height())
        elif ext in self.videoFormats:
            if videoReader is None:
                videoReader = self.getVideoReader(path)

            if not self.core.isStr(videoReader) and "size" in videoReader._meta:
                pwidth = videoReader._meta["size"][0]
                pheight = videoReader._meta["size"][1]

        return {"width": pwidth, "height": pheight}

    @err_catcher(name=__name__)
    def getVideoDuration(self, path: str, videoReader: Optional[Any] = None) -> Optional[int]:
        """Get the duration of a video file in frames.
        
        Args:
            path: Path to the video file.
            videoReader: Existing video reader object to reuse.
            
        Returns:
            Optional[int]: Number of frames in the video, or None if failed.
        """
        if videoReader is None:
            videoReader = self.getVideoReader(path)

        if self.core.isStr(videoReader):
            logger.warning(videoReader)
            return

        duration = videoReader.count_frames()
        return duration

    @err_catcher(name=__name__)
    def getMediaSequence(self, path: str) -> Dict[str, Any]:
        """Get sequence information from a file path pattern.
        
        Analyzes a glob pattern to find all matching files and determine frame range.
        
        Args:
            path: Path pattern (e.g., '/path/to/file.####.exr').
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - start: First frame number (or None)
                - end: Last frame number (or None)
                - isSequence: Whether multiple files were found
                - files: Sorted list of all matching files
        """
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
    def getExternalMediaPlayers(self) -> List[Dict[str, Any]]:
        """Get list of configured external media players.
        
        Retrieves media player configurations from user settings, including legacy
        RV and DJV settings.
        
        Returns:
            List[Dict[str, Any]]: List of media player configurations, each containing:
                - name: Display name of the player
                - path: Executable path
                - framePattern: Whether the player understands frame pattern syntax
        """
        playerData = self.core.getConfig("globals", "mediaPlayers") or []
        players = []
        if playerData:
            for player in playerData:
                pl = {
                    "name": player.get("name") or "Media Player",
                    "path": player.get("path"),
                    "framePattern": player.get("understandsFramepattern"),
                }
                if not pl["path"]:
                    path = self.core.getConfig("globals", "rvpath")
                    if not path:
                        path = self.core.getConfig("globals", "djvpath")

                    if path:
                        pl["path"] = path

                players.append(pl)
        else:
            gblData = self.core.getConfig("globals") or {}
            name = None
            path = None
            understandsFramepattern = None
            if "mediaPlayerName" in gblData:
                name = gblData["mediaPlayerName"]

            if "rvpath" in gblData:
                path = gblData["rvpath"]

            if "djvpath" in gblData:
                path = gblData["djvpath"]

            if "mediaPlayerPath" in gblData:
                path = gblData["mediaPlayerPath"]

            if "mediaPlayerFramePattern" in gblData:
                understandsFramepattern = gblData["mediaPlayerFramePattern"]

            if name is not None and path is not None and understandsFramepattern is not None:
                data = {"name": name, "path": path, "understandsFramepattern": understandsFramepattern}
                players.append(data)

        return players

    @err_catcher(name=__name__)
    def getExternalMediaPlayer(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific external media player by name.
        
        Args:
            name: Name of the media player. If None, returns the first configured player.
            
        Returns:
            Optional[Dict[str, Any]]: Media player configuration dictionary, or None if not found.
        """
        players = self.getExternalMediaPlayers()
        if not players:
            return

        if name:
            for player in players:
                if player["name"] == name:
                    return player

            return

        return players[0]

    @err_catcher(name=__name__)
    def playMediaInExternalPlayer(self, path: str, name: Optional[str] = None) -> None:
        """Open a media file in an external player.
        
        Launches the specified (or default) media player with the given file. Handles
        both single files and sequences, expanding glob patterns if needed.
        
        Args:
            path: Path to the media file or sequence pattern.
            name: Name of the media player to use. If None, uses the default player.
            
        Raises:
            RuntimeError: If the media player fails to launch.
        """
        mediaPlayer = self.getExternalMediaPlayer(name=name)
        path = os.path.normpath(path)
        progPath = mediaPlayer.get("path") if mediaPlayer else ""
        if not progPath:
            self.core.popup("No media player path set in your user settings..")
            return

        if not os.path.exists(path):
            base, ext = os.path.splitext(path)
            pattern = base.strip(".#") + ".*" + ext
            paths = glob.glob(pattern)
            if not paths:
                logger.warning("media filepath doesn't exist: %s" % path)
                return

            if not mediaPlayer.get("framePattern"):
                path = paths[0]

        comd = [progPath, path]
        if platform.system() == "Darwin" and progPath.endswith(".app"):
            comd = ["open", "-a"] + comd

        logger.debug("opening media: %s" % comd)
        with open(os.devnull, "w") as f:
            try:
                subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
            except:
                comd = "%s \"%s\"" % (comd[0], comd[1])
                try:
                    subprocess.Popen(
                        comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                    )
                except Exception as e:
                    raise RuntimeError("%s - %s" % (comd, e))

    @err_catcher(name=__name__)
    def getFallbackImagePath(self, big: bool = False) -> str:
        """Get the path to a fallback placeholder image.
        
        Used when media files cannot be loaded or don't exist.
        
        Args:
            big: Whether to get the large or small fallback image.
            
        Returns:
            str: Path to the fallback image file.
        """
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

        return imgFile

    @err_catcher(name=__name__)
    def getFallbackPixmap(self, big: bool = False) -> QPixmap:
        """Get a fallback placeholder pixmap.
        
        Returns a placeholder image used when media files cannot be loaded.
        
        Args:
            big: Whether to get the large or small fallback pixmap.
            
        Returns:
            QPixmap: The fallback pixmap.
        """
        imgFile = self.getFallbackImagePath(big=big)
        pmap = self.core.media.getPixmapFromPath(imgFile)
        if not pmap:
            pmap = QPixmap()

        return pmap
    
    @err_catcher(name=__name__)
    def getFallbackQImage(self, big: bool = False) -> QImage:
        """Get a fallback placeholder QImage.
        
        Returns a placeholder image used when media files cannot be loaded.
        
        Args:
            big: Whether to get the large or small fallback image.
            
        Returns:
            QImage: The fallback image.
        """
        imgFile = self.getFallbackImagePath(big=big)
        qimg = self.getQImageFromPath(imgFile)
        if not qimg:
            qimg = QImage()

        return qimg

    @err_catcher(name=__name__)
    def buildOtioTimeline(self, shots: List[Dict], fps: float = 24, mediaIdentifier: Optional[str] = None) -> Any:
        """Build an OTIO timeline from a list of shot entity dicts.

        Args:
            shots: List of shot entity dicts (each with 'sequence', 'shot', etc.).
            fps: Frames per second for the timeline. Defaults to 24.
            mediaIdentifier: Optional identifier name used to resolve media references for each shot.

        Returns:
            opentimelineio.schema.Timeline, or None if opentimelineio is unavailable.
        """
        try:
            import opentimelineio as otio
        except ImportError:
            self.core.popup("opentimelineio is not installed. Cannot build OTIO timeline.")
            return None

        timeline = otio.schema.Timeline(name="Timeline")
        track = otio.schema.Track(name="Video", kind=otio.schema.TrackKind.Video)
        timeline.tracks.append(track)

        for shot in shots:
            shotName = self.core.entities.getShotName(shot) or ""
            shotRange = self.core.entities.getShotRange(shot)
            startFrame = shotRange[0] if shotRange else 0
            endFrame = shotRange[1] if shotRange else startFrame
            duration = max(1, endFrame - startFrame + 1)

            media_reference = otio.schema.MissingReference()
            if mediaIdentifier:
                idfs = self.core.mediaProducts.getIdentifiersByType(shot)
                found = False
                for mtype in idfs.values():
                    if found:
                        break
                    for idf in mtype:
                        if idf.get("identifier") == mediaIdentifier:
                            versions = self.core.mediaProducts.getVersionsFromIdentifier(idf)
                            latestVersion = self.core.mediaProducts.getLatestVersionFromVersions(versions)
                            if latestVersion:
                                filepath = self.core.mediaProducts.getFileFromVersion(latestVersion, findExisting=True)
                                if filepath:
                                    media_reference = otio.schema.ExternalReference(
                                        target_url=filepath.replace("\\", "/")
                                    )
                            found = True
                            break

            clip = otio.schema.Clip(
                name=shotName,
                media_reference=media_reference,
                source_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(startFrame, fps),
                    duration=otio.opentime.RationalTime(duration, fps),
                ),
            )
            track.append(clip)

        return timeline

    @err_catcher(name=__name__)
    def saveOtioAsProduct(self, shots: List[Dict], entity: Dict, product: str, fps: Optional[float] = None, mediaIdentifier: Optional[str] = None, location: str = "global", comment: str = "") -> Optional[Dict]:
        """Build an OTIO timeline from shots and save it as a product version.

        Args:
            shots: List of shot entity dicts.
            entity: Target entity dict for the product.
            product: Product name.
            fps: Frames per second. Uses the project FPS setting if None.
            mediaIdentifier: Optional media identifier to resolve clip sources.
            location: Storage location name. Defaults to 'global'.
            comment: Optional comment for the product version.
        Returns:
            Dict with 'createdFiles' and 'versionPath' keys, or None on failure.
        """
        try:
            import opentimelineio as otio
        except ImportError:
            self.core.popup("opentimelineio is not installed. Cannot save OTIO timeline.")
            return None

        if fps is None:
            fps = self.core.projects.getFps() or 24

        timeline = self.buildOtioTimeline(shots, fps=fps, mediaIdentifier=mediaIdentifier)
        if timeline is None:
            return None

        import tempfile
        tmpDir = tempfile.mkdtemp()
        otioPath = os.path.join(tmpDir, product + ".otio")
        try:
            otio.adapters.write_to_file(timeline, otioPath)
        except Exception as e:
            self.core.popup("Failed to write OTIO file:\n%s" % str(e))
            return None

        result = self.core.products.ingestProductVersion(
            files=[otioPath],
            entity=entity,
            product=product,
            location=location,
            comment=comment,
        )
        return result

    @property
    @err_catcher(name=__name__)
    def emptyPrvPixmap(self) -> QPixmap:
        """Cached empty/fallback preview pixmap (small size).
        
        Lazy-loaded property that caches the small fallback pixmap for reuse.
        
        Returns:
            QPixmap: The cached small fallback pixmap.
        """
        if not hasattr(self, "_emptyPrvPixmap"):
            self._emptyPrvPixmap = self.getFallbackPixmap()

        return self._emptyPrvPixmap

    @property
    @err_catcher(name=__name__)
    def emptyPrvPixmapBig(self) -> QPixmap:
        """Cached empty/fallback preview pixmap (big size).
        
        Lazy-loaded property that caches the large fallback pixmap for reuse.
        
        Returns:
            QPixmap: The cached large fallback pixmap.
        """
        if not hasattr(self, "_emptyPrvPixmapBig"):
            self._emptyPrvPixmapBig = self.getFallbackPixmap(big=True)

        return self._emptyPrvPixmapBig
