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
####################################################
#
#
#   XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#
#
####################################################


import os
import json
import logging
import shutil
import psutil
import re
from contextlib import contextmanager
from multiprocessing import cpu_count as MP_cpu_count
from typing import Any, Optional, TYPE_CHECKING


import numpy as np
import av
import OpenImageIO as oiio


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


#   Supported  Video Codecs that FFmpeg can Process
SUPPORTED_CODECS = [
    "h264",
    "hevc",
    "mpeg4",
    "mpeg2video",
    "prores",
    "dnxhd",
    "dnxhr",
    "mjpeg",
    "jpeg2000",
    "rawvideo",
    "vp8",
    "vp9",
    "av1",
]

#   Cache Image Maximum Value for Float16
#   The Image Frame Cache working Space is Float16 Linear
FLOAT16_MAX = np.finfo(np.float16).max

COLOR_WHITE =           "#eff0f1"
COLOR_BLUE =            "#465A78"
COLOR_GREEN =           "#188518"
COLOR_GREEN_BRIGHT =    "#1AD31A"
COLOR_ORANGE =          "#A16D0B"
COLOR_RED =             "#741414"
COLOR_RED_BRIGHT =      "#FF3E3E"



#   FX Control Definitions
FX_CONTROLS = {
    "exposure": {
        "label": "Exposure",
        "minimum": -5.0,
        "maximum": 5.0,
        "default": 0.0,
        "domain": "scene",
        "math": "pow(2.0, value)",
        "mathTip": "color * pow(2.0, @VALUE@)",
        "uniforms": [{"name": "uExposureGain"}],
    },

    "lift": {
        "label": "Lift",
        "minimum": -1.0,
        "maximum": 1.0,
        "default": 0.0,
        "domain": "scene",
        "math": "value",
        "mathTip": "color + @VALUE@ * (1.0 - color)",
        "uniforms": [{"name": "uLift"}],
    },

    "gamma": {
        "label": "Gamma",
        "minimum": 0.01,
        "maximum": 2.0,
        "default": 1.0,
        "domain": "scene",
        "math": "1.0 / max(0.0001, value)",
        "mathTip": "pow(max(color, 0.0), 1.0 / @VALUE@)",
        "uniforms": [{"name": "uInvGamma"}],
    },

    "gain": {
        "label": "Gain",
        "minimum": 0.01,
        "maximum": 2.0,
        "default": 1.0,
        "domain": "scene",
        "math": "value",
        "mathTip": "color * @VALUE@",
        "uniforms": [{"name": "uGain"}],
    },

    "saturation": {
        "label": "Saturation",
        "minimum": 0.0,
        "maximum": 2.0,
        "default": 1.0,
        "domain": "scene",
        "math": "value",
        "mathTip": "mix(luma(color), color, @VALUE@)",
        "uniforms": [{"name": "uSaturation"}],
    },

    "temperature": {
        "label": "White Balance",
        "minimum": -1.0,
        "maximum": 1.0,
        "default": 0.0,
        "domain": "scene",
        "math": "value",
        "mathTip": "color * vec3(1.0 + max(@VALUE@, 0.0), 1.0, 1.0 + max(-@VALUE@, 0.0))",
        "uniforms": [{"name": "uTemperature"}],
    },

    "tint": {
        "label": "Tint",
        "minimum": -1.0,
        "maximum": 1.0,
        "default": 0.0,
        "domain": "scene",
        "math": "value",
        "mathTip": "color * vec3(1.0, max(0.0, 1.0 + @VALUE@), 1.0)",
        "uniforms": [{"name": "uTint"}],
    },

    "brightness": {
        "label": "Brightness",
        "minimum": -1.0,
        "maximum": 1.0,
        "default": 0.0,
        "domain": "display",
        "math": "value",
        "mathTip": "color + @VALUE@",
        "uniforms": [{"name": "uBrightness"}],
    },

    "contrast": {
        "label": "Contrast",
        "minimum": 0.0,
        "maximum": 2.0,
        "default": 1.0,
        "domain": "display",
        "math": "value",
        "mathTip": "(color - ContrastPivot) * @VALUE@ + ContrastPivot",
        "uniforms": [{"name": "uContrast"}],
    },

    "contrastPivot": {
        "label": "Contrast Pivot",
        "minimum": 0.0,
        "maximum": 1.0,
        "default": 0.5,
        "domain": "display",
        "math": "value",
        "mathTip": "Contrast midpoint used by Contrast",
        "uniforms": [{"name": "uContrastPivot"}],
    },

    "blackPoint": {
        "label": "Black Point",
        "minimum": 0.0,
        "maximum": 1.0,
        "default": 0.0,
        "domain": "display",
        "math": "value",
        "mathTip": "clamp((color - @VALUE@) / (1.0 - @VALUE@), 0.0, 1.0)",
        "uniforms": [
            {"name": "uBlackPoint"}
        ],
    },

    "whitePoint": {
        "label": "White Point",
        "minimum": 0.0,
        "maximum": 1.0,
        "default": 1.0,
        "domain": "display",
        "math": "value",
        "mathTip": "color / max(@VALUE@, 0.0001)",
        "uniforms": [
            {"name": "uWhitePoint"}
        ],
    },
}

FX_MATH_ALLOWED_FUNCS = {
    "pow": pow,
    "max": max,
    "min": min,
    "abs": abs,
}


if TYPE_CHECKING:
    from PrismCore import PrismCore
    from ProjectScripts.PreviewPlayer_GL import PreviewPlayer_GL
    from ProjectScripts.PreviewPlayer_GL_Modules import PresetsCollection
    

logger = logging.getLogger(__name__)



##################################################
##################    SYSTEM    ##################

def explorerDialogue(title: str = None,
                     dir: str = None,
                     selDir: bool = True,
                     save: bool = False,
                     filter: str = None
                     ) -> str:
    '''Show a File Dialog to Pick a Directory, File, or Save As.

    Args:
        title (str): The title of the dialog.
        dir (str): The initial directory to open.
        selDir (bool): If True, select a directory; if False, select a file
        save (bool): If True, show a save dialog; if False, show an open dialog.
        filter (str): The file filter for the dialog.
        
    Returns:
        str: The selected path, or None if cancelled.
    '''
    
    if save:
        presetPath, _ = QFileDialog.getSaveFileName(
            None, title or "Save File", dir or "", filter or ""
        )
        return presetPath

    if selDir:
        #   Directory selection
        dialog = QFileDialog(None, title or "Select Path", dir or "")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    else:
        #   File selection
        dialog = QFileDialog(None, title or "Select File", dir or "")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if filter:
            dialog.setNameFilter(filter)

    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
    dialog.setOption(QFileDialog.Option.ReadOnly, True)

    if dialog.exec():
        return dialog.selectedFiles()[0]

    return None


def getFileSize(filePath: str) -> int:
    '''Return the file size in bytes.
    
    Args:
        filePath (str): The file path to get the size of.
    
    Returns:
        int: The file size in bytes.
    '''

    return os.stat(filePath).st_size


def getDefaultCacheThreads() -> int:
    '''Returns Good Initial Number for Cache Threads based on CPUs

        Returns:
        int: The recommended number of cache threads.
    '''

    try:
        numProcs = MP_cpu_count()

        if numProcs <= 2:
            return 1
        elif numProcs <= 4:
            return 2
        elif numProcs <= 8:
            return numProcs - 2
        elif numProcs <= 16:
            return numProcs - 4
        else:
            return min(8, numProcs // 2)
    
    except Exception as e:
        logger.warning(f"ERROR: Unable to Resolve Number of CPUs on the System.  Using Fallback. {e}")
        return 4


def getTotalRAM() -> int:
    '''Return the total system RAM in bytes.
    
    Returns:
        int: The total system RAM in bytes.
    '''

    try:
        return psutil.virtual_memory().total
    
    except Exception as e:
        logger.warning(f"ERROR: Unable to Resolve System RAM.  Using Fallback. {e}")
        #   Fallback to 8 GB
        return 8 * 1024 * 1024 * 1024
    

def getAvailableRAM() -> int:
    '''Return the available system RAM in bytes.
    
    Returns:
        int: The available system RAM in bytes.
    '''

    try:
        return psutil.virtual_memory().available
    
    except Exception as e:
        logger.warning(f"ERROR: Unable to Resolve Available System RAM.  Using Fallback. {e}")
        #   Fallback to 4 GB
        return 4 * 1024 * 1024 * 1024
    

def getMaxSafetyRAMSize(factor: float = 0.1) -> int:
    '''Return a safe maximum RAM size based on factor of total RAM.

    Args:
        factor (float): The factor to multiply the total RAM by to determine the safe maximum size. Defaults to 0.9.   
    
    Returns:
        int: The maximum cache size in bytes.
    '''

    try:
        return int(getTotalRAM() * (1.0 - factor))
    
    except Exception as e:
        logger.warning(f"ERROR: Unable to Resolve Safe Cache Size.  Using Fallback. {e}")
        #   Fallback to 6 GB
        return 6 * 1024 * 1024 * 1024



##################################################
##################  FORMATTING  ##################

def getBasename(filePath: str) -> str:
    '''Return the basename for a file path.
    
    Args:
        filePath (str): The file path to extract the basename from.
        
    Returns:
        str: The basename of the file path.
    '''

    return os.path.basename(filePath)


def getFileExtension(filePath: str = None, fileName: str = None) -> str:
    '''Return the lowercase file extension for a path or file name.
    
    Args:
        filePath (str): The file path to extract the extension from.
        fileName (str): The file name to extract the extension from.
    
    Returns:
        str: The lowercase file extension, including the leading dot.
    '''

    basefile = getBasename(filePath) if filePath else fileName
    _, extension = os.path.splitext(basefile or "")
    return extension.lower()


def getFileSizeStr(size_bytes: int) -> str:
    '''Return a human readable file size string.
    
    Args:
        size_bytes (int): The file size in bytes.
        
    Returns:
        str: The human readable file size string.
    '''

    size_mb = size_bytes / 1024.0 / 1024.0
    if size_mb < 1:
        size_kb = size_bytes / 1024.0
        size = size_kb
        unit = "KB"
    elif size_mb < 1024:
        size = size_mb
        unit = "MB"
    else:
        size = size_mb / 1024.0
        unit = "GB"

    int_digits = len(str(int(size)))
    if int_digits >= 3:
        fmt = "%.0f"
    elif int_digits == 2:
        fmt = "%.1f"
    else:
        fmt = "%.2f"

    return f"{fmt % size} {unit}"


def getIconFromPath(imagePath:str, normalLevel:float = 0.9, dimLevel:float = 0.4,tint:tuple = None) -> QIcon:
    '''Returns QIcon with Both Normal and Disabled Versions and optional tint.

    Args:
        imagePath (str): The path to the image file.
        normalLevel (float): The brightness level for the normal icon (0.0 to 1.0).
        dimLevel (float): The brightness level for the disabled icon (0.0 to 1.0).
        tint (tuple[int, int, int], optional): RGB color to tint the icon. example (255, 0, 0).

    Returns:
        QIcon: The generated QIcon with normal and disabled versions.
    '''

    try:
        #   Get Original Image
        pixmap_orig = QPixmap(imagePath)
        image_orig = pixmap_orig.toImage().convertToFormat(QImage.Format_ARGB32)

        #   Normal Version
        image_norm = QImage(image_orig.size(),QImage.Format_ARGB32)

        for y in range(image_orig.height()):
            for x in range(image_orig.width()):
                srcColor = image_orig.pixelColor(x, y)

                if tint is not None:
                    intensity = srcColor.red() / 255.0

                    color = QColor(
                        int(tint[0] * intensity * normalLevel),
                        int(tint[1] * intensity * normalLevel),
                        int(tint[2] * intensity * normalLevel),
                        srcColor.alpha()
                    )

                else:
                    normVal = int(srcColor.red() * normalLevel)
                    color = QColor(normVal, normVal, normVal, srcColor.alpha())

                image_norm.setPixelColor(x, y, color)

        pixmap_norm = QPixmap.fromImage(image_norm)

        #   Disabled Version
        image_dim = QImage(image_orig.size(), QImage.Format_ARGB32)

        for y in range(image_orig.height()):
            for x in range(image_orig.width()):

                srcColor = image_orig.pixelColor(x, y)

                if tint is not None:
                    intensity = srcColor.red() / 255.0

                    color = QColor(
                        int(tint[0] * intensity * dimLevel),
                        int(tint[1] * intensity * dimLevel),
                        int(tint[2] * intensity * dimLevel),
                        srcColor.alpha()
                    )

                else:
                    dimVal = int(srcColor.red() * dimLevel)
                    color = QColor(dimVal, dimVal, dimVal, srcColor.alpha())

                image_dim.setPixelColor(x, y, color)

        pixmap_dim = QPixmap.fromImage(image_dim)

        #   Convert to QIcon
        icon = QIcon()
        icon.addPixmap(pixmap_norm, QIcon.Normal)
        icon.addPixmap(pixmap_dim, QIcon.Disabled)

        return icon

    except Exception as e:
        logger.warning(f"ERROR: Failed to Create Icon:\n{e}")
        return QIcon()


def normalizeData(data):
    '''Normalize nested data structures for comparison.
    
    Args:
        data (Any): The data to normalize, which can be a dictionary, list, tuple, or other types.
    '''

    if isinstance(data, dict):
        return {key: normalizeData(value) for key, value in data.items()}
    if isinstance(data, list):
        return [normalizeData(value) for value in data]
    if isinstance(data, tuple):
        return tuple(normalizeData(value) for value in data)

    return str(data)


def createMenuAction(
    actionName: str,
    menu: QMenu,
    parent: QObject,
    function: callable,
    icon: QIcon = None,
    enabled: bool = True,
) -> QAction:
    
    '''Create a QAction and add it to a menu.
    
    Args:
        actionName (str): The name of the action.
        menu (QMenu): The menu to add the action to.
        parent (QObject): The parent object for the action.
        function (callable): The function to connect to the action's triggered signal.
        icon (QIcon, optional): The icon for the action. Defaults to None.
        enabled (bool, optional): Whether the action is enabled. Defaults to True.
        
    Returns:
        QAction: The created QAction.
    '''

    menuAction = QAction(actionName, parent)
    if icon:
        menuAction.setIcon(icon)

    menuAction.triggered.connect(function)
    menuAction.setEnabled(enabled)
    menu.addAction(menuAction)
    return menuAction


def isCodecSupported(codec: str) -> bool:
    '''Return whether FFmpeg codec support is expected in Prism.
    
    Args:
        codec (str): The codec name to check.
        
    Returns:
        bool: True if the codec is supported, False otherwise.
    '''

    return codec.lower() in SUPPORTED_CODECS if codec else True


def normalizeMetadata(metadata: Any) -> dict[str, Any]:
    '''Normalize metadata to ensure it is a dictionary.
    
    Args:
        metadata (Any): The metadata to normalize.
        
    Returns:
        dict[str, Any]: The normalized metadata as a dictionary.
    '''

    return metadata if isinstance(metadata, dict) else {}


def getInfoMetric(metadata: dict[str, Any], keys: list[str], fallback: Any = "----") -> Any:
    '''Return the first available metric from the metadata for the given keys, or the fallback value.
    
    Args:
        metadata (dict[str, Any]): The metadata dictionary to search.
        keys (list[str]): The list of keys to check in order.
        fallback (Any, optional): The fallback value to return if no keys are found. Defaults to "----".
        
    Returns:
        Any: The value of the first found key, or the fallback value.
    '''

    for key in keys:
        value = metadata.get(key)
        if value not in [None, "", 0]:
            return value

    return fallback


def getBaseFile(files: list[str]) -> str:
    '''Return the base file for a media set.
    
    Args:
        files (list[str]): The list of media file paths.
        
    Returns:
        str: The base file path, or an empty string if the list is empty.
    '''

    if not files:
        return ""

    return files[0]


def formatFPS(fps: float | None) -> str:
    '''Format the given FPS value as a string with two decimal places, or "None" if the value is None.
    
    Args:
        fps (float | None): The frames per second value to format.
        
    Returns:
        str: The formatted FPS string or "N/A" if fps is None.
    '''

    return f"{fps:.2f} fps" if fps is not None else "---"


def isDropFrameTimecode(timecodeStart: str = "", timecodeMode: str = "") -> bool:
    '''Return whether a timecode should be treated as drop-frame.

    Args:
        timecodeStart (str, optional): The start timecode string.
        timecodeMode (str, optional): The reported timecode mode string.

    Returns:
        bool: True if the timecode is drop-frame, False otherwise.
    '''

    tc = str(timecodeStart or "")
    mode = str(timecodeMode or "").lower()
    return ";" in tc or mode.startswith("drop")


def timecodeToFrameCount(timecode: str, fps: float, dropFrame: bool = False) -> int | None:
    '''Convert SMPTE timecode to an absolute frame count.

    Args:
        timecode (str): Timecode in HH:MM:SS:FF or HH:MM:SS;FF format.
        fps (float): Source frames per second.
        dropFrame (bool, optional): Whether to use drop-frame conversion. Defaults to False.

    Returns:
        int | None: The absolute frame count, or None when parsing fails.
    '''

    if not timecode:
        return None

    parts = str(timecode).strip().replace(";", ":").split(":")
    if len(parts) != 4:
        return None

    try:
        hh, mm, ss, ff = [int(p) for p in parts]
    except Exception:
        return None

    nominalFps = max(1, int(round(float(fps) or 0.0)))

    if dropFrame:
        dropFrames = int(round(nominalFps * 2 / 30.0))
        totalMinutes = hh * 60 + mm
        frameCount = (
            ((hh * 3600) + (mm * 60) + ss) * nominalFps
            + ff
            - dropFrames * (totalMinutes - (totalMinutes // 10))
        )
        return int(frameCount)

    frameCount = ((hh * 3600) + (mm * 60) + ss) * nominalFps + ff
    return int(frameCount)


def frameCountToTimecode(frameCount: int, fps: float, dropFrame: bool = False) -> str:
    '''Convert an absolute frame count to SMPTE timecode.

    Args:
        frameCount (int): Absolute frame count.
        fps (float): Source frames per second.
        dropFrame (bool, optional): Whether to use drop-frame conversion. Defaults to False.

    Returns:
        str: Timecode in HH:MM:SS:FF format.
    '''

    nominalFps = max(1, int(round(float(fps) or 0.0)))
    frameCount = max(0, int(frameCount))

    if not dropFrame:
        hh = frameCount // (nominalFps * 3600)
        rem = frameCount % (nominalFps * 3600)
        mm = rem // (nominalFps * 60)
        rem = rem % (nominalFps * 60)
        ss = rem // nominalFps
        ff = rem % nominalFps
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    dropFrames = int(round(nominalFps * 2 / 30.0))
    framesPer10Minutes = (nominalFps * 60 * 10) - (dropFrames * 9)
    framesPerHour = framesPer10Minutes * 6
    framesPer24Hours = framesPerHour * 24
    framesPerMinute = (nominalFps * 60) - dropFrames

    frameNumber = frameCount % framesPer24Hours

    hours = frameNumber // framesPerHour
    frameNumber = frameNumber % framesPerHour

    tenMinuteBlocks = frameNumber // framesPer10Minutes
    frameNumber = frameNumber % framesPer10Minutes

    minutes = tenMinuteBlocks * 10 + (frameNumber // framesPerMinute)
    frameNumber = frameNumber % framesPerMinute

    if (minutes % 10) != 0:
        frameNumber += dropFrames

    seconds = frameNumber // nominalFps
    frames = frameNumber % nominalFps

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def getTimecodeReference(timecodeStart: str, timecodeMode: str, fps: float, mediaStartFrame: int = 1) -> dict[str, Any] | None:
    '''Build reference data used to translate between media frames and display timecode.

    Args:
        timecodeStart (str): Source start timecode from media metadata.
        timecodeMode (str): Timecode mode label from media metadata.
        fps (float): Media frame rate.
        mediaStartFrame (int, optional): Source start frame in Prism. Defaults to 1.

    Returns:
        dict[str, Any] | None: Timecode reference dictionary, or None when invalid.
    '''

    tcStart = str(timecodeStart or "").strip()
    fpsValue = float(fps or 0.0)
    if not tcStart or fpsValue <= 0.0:
        return None

    dropFrame = isDropFrameTimecode(tcStart, timecodeMode)
    startFrameCount = timecodeToFrameCount(tcStart, fpsValue, dropFrame=dropFrame)
    if startFrameCount is None:
        return None

    return {
        "startFrameCount": int(startFrameCount),
        "mediaStartFrame": int(mediaStartFrame or 1),
        "fps": fpsValue,
        "dropFrame": bool(dropFrame),
    }


def frameNumberToTimecode(frameNumber: int, timecodeRef: dict[str, Any]) -> str | None:
    '''Convert a media frame number to display timecode using a timecode reference.

    Args:
        frameNumber (int): Media frame number.
        timecodeRef (dict[str, Any]): Reference dictionary from getTimecodeReference().

    Returns:
        str | None: Converted timecode string, or None when conversion fails.
    '''

    if not timecodeRef:
        return None

    try:
        delta = int(frameNumber) - int(timecodeRef["mediaStartFrame"])
        frameCount = int(timecodeRef["startFrameCount"]) + delta
        frameCount = max(0, frameCount)

        return frameCountToTimecode(
            frameCount,
            fps=float(timecodeRef["fps"]),
            dropFrame=bool(timecodeRef["dropFrame"]),
        )
    except Exception:
        return None


def timecodeToFrameNumber(timecode: str, timecodeRef: dict[str, Any]) -> int | None:
    '''Convert a display timecode string to a media frame number.

    Args:
        timecode (str): Timecode in HH:MM:SS:FF or HH:MM:SS;FF format.
        timecodeRef (dict[str, Any]): Reference dictionary from getTimecodeReference().

    Returns:
        int | None: Converted media frame number, or None when conversion fails.
    '''

    if not timecodeRef:
        return None

    try:
        parsedFrameCount = timecodeToFrameCount(
            timecode,
            fps=float(timecodeRef["fps"]),
            dropFrame=bool(timecodeRef["dropFrame"]),
        )
        if parsedFrameCount is None:
            return None

        delta = int(parsedFrameCount) - int(timecodeRef["startFrameCount"])
        return int(timecodeRef["mediaStartFrame"]) + delta

    except Exception:
        return None


def getInvalidMediaInfo(mediaFiles:list[str], metadata:dict, reason:str, codec:str="") -> dict:
    '''Build the fallback slide data for unsupported preview media.
    
    Args:
        mediaFiles (list[str]): List of media file paths.
        metadata (dict): Metadata associated with the media files.
        reason (str): Reason why the media is considered invalid.
        codec (str, optional): Codec of the media. Defaults to "".

    Returns:
        dict[str, str]: Dictionary containing fallback slide data.'''

    mediaPath = mediaFiles[0] if mediaFiles else ""
    metadata = normalizeMetadata(metadata)
    codec = (codec or metadata.get("codec_name") or "").strip() or "unknown"
    fileName = getBasename(mediaPath) if mediaPath else "Unknown file"

    errorText = None
    if codec and codec.lower() != "unknown":
        errorText = f"Codec: {codec}"

    return {
        "title": "Unsupported Media",
        "message": reason,
        "details": fileName,
        "error": errorText,
    }



##############################################
#################    IMAGE    ################

def qimgToNumpyRGBA(qimg: QImage) -> Optional[np.ndarray]:
    '''Convert a QImage to a NumPy array with RGBA channels.
    
    Args:
        qimg (QImage): The QImage to convert.
        
    Returns:
        Optional[np.ndarray]: NumPy array with shape (height, width, 4) and dtype uint8, or None.'''

    if qimg is None or qimg.isNull():
        return None

    rgba = qimg.convertToFormat(QImage.Format_RGBA8888)

    width = rgba.width()
    height = rgba.height()
    if width <= 0 or height <= 0:
        return None

    ptr = rgba.bits()
    byte_count = height * width * 4

    arr = np.frombuffer(ptr, dtype=np.uint8, count=byte_count).reshape((height, width, 4)).copy()

    return arr


def resizeNumpyImage(img_np: np.ndarray, dst_w: int, dst_h: int) -> Optional[np.ndarray]:
    '''Resize a NumPy image to the specified width and height using OpenImageIO.
    
    Args:
        img_np (np.ndarray): The input image as a NumPy array with shape (height, width, channels).
        dst_w (int): The desired width of the output image.
        dst_h (int): The desired height of the output image.
        
    Returns:
        Optional[np.ndarray]: The resized image as a NumPy array, or None if the resizing fails.
    '''

    if img_np is None or not isinstance(img_np, np.ndarray):
        return None

    if img_np.ndim != 3 or img_np.shape[2] not in [3, 4]:
        return None

    try:
        src_h, src_w, channels = img_np.shape

        if (src_w, src_h) == (dst_w, dst_h):
            return img_np

        #   Normalize Source Buffer
        src = np.ascontiguousarray(img_np.astype(np.float32, copy=False))

        #   Create OIIO Source Buffer
        srcSpec = oiio.ImageSpec(src_w, src_h, channels, oiio.FLOAT)
        srcBuf = oiio.ImageBuf(srcSpec)
        srcROI = oiio.ROI(0, src_w, 0, src_h, 0, 1, 0, channels)

        srcBuf.set_pixels(srcROI, src)

        #   Create Destination Buffer
        dstSpec = oiio.ImageSpec(dst_w, dst_h, channels, oiio.FLOAT)
        dstBuf = oiio.ImageBuf(dstSpec)

        #   Resize
        ok = oiio.ImageBufAlgo.resize(dstBuf, srcBuf, filtername="triangle")

        if not ok:
            logger.warning("OIIO resize failed")
            return None

        #   Extract Pixels
        dst = dstBuf.get_pixels(oiio.FLOAT)

        if dst is None:
            logger.warning("OIIO returned empty resize buffer")
            return None

        dst = np.asarray(dst)

        expected_size = dst_w * dst_h * channels

        if dst.size != expected_size:
            logger.warning(
                f"OIIO resize returned unexpected buffer size: "
                f"{dst.size}, expected {expected_size}"
            )
            return None

        result = dst.reshape(dst_h, dst_w, channels)

        return np.ascontiguousarray(result)

    except Exception as e:
        logger.warning(f"Failed to resize image with OIIO: {e}")
        return None


def loadImgAsRGBA(path: str) -> Optional[np.ndarray]:
    '''Load an image from the specified path and convert it to a NumPy array with RGBA channels.
    
    Args:
        path (str): The path to the image file.
        
    Returns:
        Optional[np.ndarray]: The loaded image as a NumPy array with shape (height, width, 4) and dtype uint8, or None if the loading fails.
    '''

    qimg = QImage(path)
    return qimgToNumpyRGBA(qimg)


def buildLoadingImage(player: 'PreviewPlayer_GL') -> np.ndarray:
    '''Builds a transparent loading image with centered text.
    
    Args:
        player (PreviewPlayer_GL): The preview player instance.

    Returns:
        np.ndarray: The generated RGBA image as a NumPy array.
    '''

    try:
        #   Get Current Preview Window Size
        display = getattr(player, "DisplayWindow", None)
        if display:
            size = display.size()
            width = max(1, size.width())
            height = max(1, size.height())
        else:
            width = 300
            height = 169

        #   Create Transparent Image
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        #   Init Painter
        painter = QPainter(image)
        painter.setRenderHint(QPainter.TextAntialiasing)

        text = "Loading"

        #   Find Largest Font That Fits ~2/3 of Window Width
        font = QFont("Arial")
        targetWidth = int(width * 0.67)
        fontSize = max(8, height // 8)

        while fontSize > 8:
            font.setPixelSize(fontSize)
            metrics = QFontMetrics(font)

            if metrics.horizontalAdvance(text) <= targetWidth:
                break

            fontSize -= 2

        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(image.rect(), Qt.AlignCenter, text,)
        painter.end()

        #   Flip Image for OpenGL
        image.mirror(False, True)

        return qimgToNumpyRGBA(image)

    except Exception as e:
        logger.warning(f"Failed to build Loading Image: {e}")
        return None

    
def buildFallbackImg(player:'PreviewPlayer_GL', msg:str, error:str = "", details: str = "") -> np.ndarray:
    '''Build a Fallback slide to display when media is unsupported.
    
    Args:
        player (PreviewPlayer_GL): The preview player instance.
        msg (str): The message text to display.
        error (str, optional): The error text to display. Defaults to "".
        details (str, optional): The details text to display. Defaults to "".
        
    Returns:
        np.ndarray: The generated RGBA image as a NumPy array.
    '''

    #   STYLING CONSTANTS
    COLOR_BG = QColor(0, 0, 0, 170)
    COLOR_ACCENT = QColor(204, 102, 102, 220)
    ACCENT_TOP = 3
    ACCENT_BORDER = 1
    CORNER_RADIUS = 8
    TEXT_COLOR = Qt.white
    TEXT_FONT = QFont("Arial")

    try:
        ###   CARD LAYOUT

        #   Get Current Preview Window Size
        display = getattr(player, "DisplayWindow", None)
        if display:
            size = display.size()
            width = max(1, size.width())
            height = max(1, size.height())

        #   Fallback to Default Size
        else:
            width = 300
            height = 169

        #   Create Transparent QImage
        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        #   Init Painter
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        #   Draw Card Background
        margin = max(16, width // 12)
        cardRect = QRect(margin, margin // 2, width - margin * 2, height - margin)

        #   Semi-transparent with Red Border
        painter.setBrush(COLOR_BG)
        painter.setPen(QPen(COLOR_ACCENT, ACCENT_BORDER))
        painter.drawRoundedRect(cardRect, CORNER_RADIUS, CORNER_RADIUS)

        card = QRect(cardRect.left(), cardRect.top(), cardRect.width(), ACCENT_TOP)
        cardColor = COLOR_ACCENT
        painter.fillRect(card, cardColor)

        ###  TEXT LAYOUT

        #   Calc Padding of Text from Card Edges
        pad = max(22, width // 16)
        textRect = cardRect.adjusted(pad, pad, -pad, -pad)

        ##  TEXT BLOCKS
        title = "Preview Not Available"

        #   Font Styling for Blocks (block name, bold, font size)
        blocks = [
            (title,   True,  28),
            (msg,     False, 18),
            (error,   False, 18),
            (details, False, 13),
        ]

        #   Scale Text to Fit Card
        scale = max(0.5, min(width / 600.0, height / 350.0))
        flags = Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap

        #   Loop to Scale Text Down Until it Fits
        while True:
            fonts = []
            heights = []
            contentHeight = 0

            #   Loop Through Each Block and Get Height with Current Scale
            for text, bold, baseSize in blocks:
                #   Skip Empty Blocks
                if not text:
                    fonts.append(None)
                    heights.append(0)
                    continue

                #   Create Font and Metrics
                font = QFont(TEXT_FONT)
                font.setBold(bold)
                font.setPixelSize(max(8, int(baseSize * scale)))

                metrics = QFontMetrics(font)
                bounds = metrics.boundingRect(
                    QRect(0, 0, textRect.width(), 10000),
                    flags,
                    text,
                )

                fonts.append(font)
                heights.append(bounds.height())
                contentHeight += bounds.height()

            #   Check if Content Fits or Scale is Too Small
            if contentHeight <= textRect.height() or scale <= 0.35:
                break

            #   Reduce Scale and Try Again
            scale *= 0.95

        #   Draw Text After Scaling
        painter.setPen(TEXT_COLOR)

        #   Filter Out Empty Blocks
        visibleItems = []
        blockData = zip(blocks, fonts, heights)

        for idx, ((text, _, _), font, blockHeight) in enumerate(blockData):
            if not text:
                continue

            visibleItems.append(
                (
                    idx,
                    text,
                    font,
                    blockHeight,
                )
            )

        if visibleItems:
            #   Calc Total Content Height and Remaining Space
            contentHeight = sum(item[3] for item in visibleItems)
            remainingSpace = max(0,textRect.height() - contentHeight)

            gaps = []

            #   Calc Vertical Gaps Between Blocks (to handle if Error or Details are empty)
            if len(visibleItems) > 1:
                gapCount = len(visibleItems) - 1

                if gapCount == 3:
                    weights = [0.45, 0.10, 0.45]

                elif gapCount == 2:
                    weights = [0.55, 0.45]

                else:
                    weights = [1.0]

                weightTotal = sum(weights)
                gaps = [int(remainingSpace * (weight / weightTotal)) for weight in weights]

            #   Set Initial Y Position for First Block
            y = textRect.top()

            #   Draw Each Block of Text
            for idx, (_, text, font, blockHeight) in enumerate(visibleItems):
                painter.setFont(font)

                painter.drawText(
                    QRect(textRect.left(), y, textRect.width(), blockHeight,),
                    flags,
                    text,
                )

                #   Increment Y Position for Next Block
                y += blockHeight

                #   Add Vertical Gap if There Are More Blocks to Draw
                if idx < len(gaps):
                    y += gaps[idx]

        painter.end()

        #   Flip Image for OpenGL
        image.mirror(False, True)

        return qimgToNumpyRGBA(image)

    except Exception as e:
        logger.warning(f"Failed to build Fallback Image: {e}")
        return None


def makeBlackFrame(Player: 'PreviewPlayer_GL') -> Optional[np.ndarray]:
    '''Generate a Black 16:9 Frame at Current Preview Width
    
    Args:
        Player (PreviewPlayer_GL): The preview player instance to get the display window size.
        
    Returns:
        Optional[np.ndarray]: A NumPy array representing the black frame with shape (height, width, 3) and dtype uint8, or None if the generation fails.'''

    try:
        width = Player.DisplayWindow.width()
        if width <= 0:
            width = 300

        height = int(width / (16/9))

        Player.MediaData.pwidth = width
        Player.MediaData.pheight = height

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        return frame
    
    except Exception as e:
        logger.warning(f"ERROR: Failed to Generate Black Frame: {e}")
        return None


def makeRedXFrame(Player: 'PreviewPlayer_GL') -> Optional[np.ndarray]:
    '''Generate a Black 16:9 Frame with a Red X.

    Args:
        Player (PreviewPlayer_GL): Preview player instance.

    Returns:
        Optional[np.ndarray]: RGB uint8 image.
    '''

    try:
        width = Player.DisplayWindow.width()
        if width <= 0:
            width = 300

        height = int(width / (16 / 9))

        Player.MediaData.pwidth = width
        Player.MediaData.pheight = height

        # Black background
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Red color
        red = np.array([255, 0, 0], dtype=np.uint8)

        # Line thickness scales with image size
        thickness = max(2, min(width, height) // 100)

        yy, xx = np.indices((height, width))

        # Main diagonal
        mask1 = np.abs(yy - (xx * height / width)) <= thickness

        # Opposite diagonal
        mask2 = np.abs(
            yy - ((height - 1) - (xx * height / width))
        ) <= thickness

        frame[mask1 | mask2] = red

        return frame

    except Exception as e:
        logger.warning(f"ERROR: Failed to Generate Red X Frame: {e}")
        return None


def holdingFrame(Player: 'PreviewPlayer_GL', mode: str = "black") -> Optional[np.ndarray]:
    '''Return a holding frame based on the specified mode.

    Args:
        Player (PreviewPlayer_GL): The preview player instance.
        mode (str, optional): The mode of the holding frame ("black" or "redX"). Defaults to "black".
        
    Returns:
        Optional[np.ndarray]: The generated holding frame as a NumPy array, or None if the generation fails.
    '''

    if mode == "black":
        return makeBlackFrame(Player)

    elif mode == "redX":
        return makeRedXFrame(Player)

    else:
        return makeBlackFrame(Player)


def probeVideoInfo(mediaPath: str, fast: bool = False) -> dict:
    '''Probe video stream metadata using PyAV.

    Args:
        mediaPath (str): Path to media file.
        fast (bool): If True, only return codec validation data.

    Returns:
        dict:
            - Fast: return codec and hasVideo.
            - Full: all metadata.
    '''

    specs = {
        "hasVideo": False,
        "codec": "",
        "width": None,
        "height": None,
        "fps": None,
        "timecodeStart": None,
        "timecodeMode": None,
        "frame_start": None,
        "frame_end": None,
        "durationFrames": None,
    }

    #   Open Video Container and Get Stream
    container = None
    try:
        container = av.open(mediaPath)

        if not container.streams.video:
            return specs

        stream = container.streams.video[0]

    except Exception as e:
        logger.warning(f"PyAV video probe failed for {mediaPath}: {e}")
        return specs

    ##   CODEC
    try:
        specs["codec"] = stream.codec_context.name or ""
    except Exception:
        logger.warning(f"PyAV Probe: Unable to get codec name")
        specs["codec"] = ""

    ##  HASVIDEO
    try:
        specs["hasVideo"] = bool(specs["codec"] and specs["codec"].lower() != "none")
    except Exception:
        logger.warning(f"PyAV Probe: Unable to determine if stream has video")


    ####   Return Basic specs if Fast Mode
    if fast:
        return specs

    ##  RESOLUTION
    try:
        specs["width"] = stream.width
        specs["height"] = stream.height
    except:
        logger.warning(f"PyAV Probe: Unable to get stream resolution")

    ##  FPS
    try:
        fps = None

        fpsFields = [
            getattr(stream, "average_rate", None),
            getattr(stream, "guessed_rate", None),
            getattr(stream, "base_rate", None),
            getattr(stream, "rate", None),
        ]

        for rate in fpsFields:
            try:
                if rate is None:
                    continue
                value = float(rate)
                if value > 0:
                    fps = value
                    break

            except Exception:
                pass

        if fps is None:
            try:
                tb = getattr(stream, "time_base", None)
                if tb:
                    num = float(getattr(tb, "numerator", 0) or 0)
                    den = float(getattr(tb, "denominator", 0) or 0)

                    if num > 0 and den > 0:
                        value = den / num

                        if value > 0:
                            fps = value

            except Exception:
                pass

        specs["fps"] = fps if fps else None

    except:
        logger.warning(f"PyAV Probe: Unable to get stream FPS")

    ##  FRAME COUNT
    try:
        frameCount = None

        #   Try for Direct Frame Count
        try:
            if stream.frames and stream.frames > 0:
                frameCount = int(stream.frames)
        except Exception:
            pass

        if frameCount:
            specs["durationFrames"] = frameCount


        #   Try to Calculate Frame Count from Duration and FPS
        elif (stream.duration and stream.time_base and specs["fps"]):
            durationSec = float(stream.duration * stream.time_base)
            specs["durationFrames"] = max(1, int(round(durationSec * specs["fps"])))

        #   Try to Calculate Frame Count from Container Duration and FPS
        elif container.duration and specs["fps"]:
            durationSec = float(container.duration) / float(av.time_base)
            specs["durationFrames"] = max(1, int(round(durationSec * specs["fps"])))

    except:
        logger.warning(f"PyAV Probe: Unable to get stream frame count")

    ##  TIMECODE
    try:
        timecode = None
        timecodeMode = None

        #   Key Names for Search
        timecodeKeys = (
            "timecode",
            "timecode_start",
            "timecode_start_time",
            "start_timecode",
        )

        #   Search Each Stream for Timecode Metadata
        for stream in container.streams:
            metadata = getattr(stream, "metadata", {}) or {}

            for key in timecodeKeys:
                tc = metadata.get(key)

                if tc:
                    timecode = str(tc).strip()
                    break

            if timecode:
                break

        #   Search Container Metadata for Timecode Metadata
        if not timecode:
            metadata = getattr(container, "metadata", {}) or {}

            for key in timecodeKeys:
                tc = metadata.get(key)

                if tc:
                    timecode = str(tc).strip()
                    break

        #   Capture Timecode Mode (DF/NDF) from Timecode String.
        if timecode:
            if ";" in timecode:
                timecodeMode = "Drop Frame"

            else:
                timecodeMode = "Non Drop Frame"

            specs["timecodeStart"] = timecode
            specs["timecodeMode"] = timecodeMode

    except Exception:
        logger.warning("PyAV Probe: Unable to get stream timecode")

    ##  START/END FRAMES (SMPTE DF/NDF Calcs)
    try:
        if specs["timecodeStart"] and specs["fps"] and specs["durationFrames"]:
            dropFrame = isDropFrameTimecode(specs["timecodeStart"], specs.get("timecodeMode", ""))
            frameStart = timecodeToFrameCount(specs["timecodeStart"], specs["fps"], dropFrame=dropFrame)
            if frameStart is not None:
                specs["frame_start"] = int(frameStart)
                specs["frame_end"] = int(frameStart + specs["durationFrames"] - 1)

    except Exception as e:
        logger.warning(f"PyAV Probe: Unable to get stream start/end frames: {e}")

    finally:
        if container:
            try:
                container.close()
            except Exception:
                pass

    return specs



#################################################
###############    Qt Objects    ################

@contextmanager
def blockSignals(*objects: QObject):
    '''Context manager to temporarily block signals for multiple QObject instances.
    
    Args:
        *objects (QObject): The QObject instances for which to block signals.'''
    
    states = [obj.blockSignals(True) for obj in objects]
    try:
        yield
    finally:
        for obj, state in zip(objects, states):
            obj.blockSignals(state)


def getPopupPosition(popup:QWidget, parent:QWidget, mousePos:QPoint=None, adjustSize:bool=False) -> QPoint:
    '''Returns a screen position for a popup.

    Args:
        popup (QWidget): The popup/dialog being positioned.
        parent (QWidget): Widget used to determine the current monitor.
        mousePos (QPoint, optional): Position for the popup. If omitted, will center on current screen.
        adjustSize (bool, optional): If True, the popup will be adjusted to its sizeHint() before positioning.

    Returns:
        QPoint: Position for popup.move().
    '''

    if adjustSize:
        popup.adjustSize()

    #   Anchor at Mouse Position if Given
    if mousePos is not None:
        screen = QApplication.screenAt(mousePos)
        if screen is None:
            screen = QApplication.primaryScreen()

        avail = screen.availableGeometry()
        x = mousePos.x()
        y = mousePos.y()

        #   Fit on Screen
        if y + popup.height() > avail.bottom():
            y -= popup.height()

        if x + popup.width() > avail.right():
            x = avail.right() - popup.width()

        #   Clamp to Screen
        x = max(avail.left(), x)
        y = max(avail.top(), y)

        return QPoint(x, y)

    #   Center on Screen
    screen = parent.screen()
    if screen is None:
        screen = QApplication.primaryScreen()
    avail = screen.availableGeometry()

    x = avail.x() + (avail.width() - popup.width()) // 2
    y = avail.y() + (avail.height() - popup.height()) // 2

    return QPoint(x, y)



################################################
#################    PRESETS    ################

def getPresetExt(pType:str) -> str:
    '''Returns Preset File Extension by Type
    
    Args:
        pType (str): The type of the preset (e.g., "metadata", "ocio").

    Returns:
        str: The file extension for the given preset type.
    '''

    if pType == "metadata":
        ext = ".m_preset"
    elif pType == "ocio":
        ext = ".o_preset"
    else:
        ext = ""

    return ext


def getProjectPresetDir(core:'PrismCore', presetType: str) -> str:
    '''Return the project preset directory.  Will create if it does not exist.

    Args:
        core (PrismCore): The core application instance.
        presetType (str): The type of the preset (e.g., "metadata", "ocio").

    Returns:
        str: The path to the project preset directory for the given preset type.
    '''

    projPipelineDir = core.projects.getPipelineFolder()
    projPresetDir = os.path.join(projPipelineDir, "Presets", presetType.upper())

    if not os.path.exists(projPresetDir):
        os.makedirs(projPresetDir, exist_ok=True)

    return projPresetDir


def getLocalPresetDir(core:'PrismCore', presetType:str) -> str:
    '''Returns Local UserPreset Dir by Type. Will create if it does not exist.

    Args:
        core (PrismCore): The core application instance.
        presetType (str): The type of the preset (e.g., "metadata", "ocio").

    Returns:
        str: The path to the local user preset directory for the given preset type.
    '''

    userDir = core.getUserPrefDir()
    localPresetDir = os.path.join(userDir, "Presets", presetType.capitalize())
    
    if not os.path.exists(localPresetDir):
        os.makedirs(localPresetDir, exist_ok=True)

    return localPresetDir


def loadPreset(presetPath: str) -> dict:
    '''Load a preset file while ignoring commented lines.

    Args:
        presetPath (str): The path to the preset file.

    Returns:
        dict: The loaded preset data.
    '''

    with open(presetPath, "r", encoding="utf-8") as fileHandle:
        raw = fileHandle.read()

    raw = re.sub(r"^\s*#.*$", "", raw, flags=re.MULTILINE)
    return json.loads(raw)


def loadPresets(dir: str, model:'PresetsCollection', ext: str) -> None:
    '''Load preset files into a preset collection model.

    Args:
        dir (str): The directory containing the preset files.
        model (PresetsCollection): The preset collection model to populate.
        ext (str): The file extension of the preset files to load.
    '''

    if not os.path.isdir(dir):
        return

    presetFiles = {
        os.path.splitext(pf)[0]: os.path.join(dir, pf)
        for pf in os.listdir(dir)
        if getFileExtension(fileName=pf) == ext
    }

    for name, path in presetFiles.items():
        pData = loadPreset(path)
        model.addPreset(name, pData["data"])


def importPreset(core:'PrismCore', pType:str, local:bool=False) -> dict | None:
    '''Import Preset from File.

    Args:
        core (PrismCore): The core application instance.
        pType (str): The type of the preset (e.g., "metadata", "ocio").
        local (bool): If True, import the preset from the local plugin presets directory; otherwise, import from the project-specific presets directory.

    Returns:
        dict | None: The imported preset data if successful; otherwise, None.
    '''

    presetDir = None
    presetExt = getPresetExt(pType)

    if local:
        #   Get Local Preset Dir for Explorer
        presetDir = getLocalPresetDir(core, pType)
    
    #   Call Explorer to Select Preset to Import
    presetPath_source = explorerDialogue(
                            "Select Preset File",
                            dir = presetDir,
                            selDir = False,
                            filter = f"Preset Files (*{presetExt})"
                            )
    
    if not presetPath_source or not os.path.isfile(presetPath_source):
        return None
    
    try:
        #   Get Preset File Name and Make Project Destination Path
        _, presetName = os.path.split(presetPath_source)
        presetPath_dest = os.path.join(getProjectPresetDir(core, pType), presetName)

        #   If Exists Already Ask for Overwrite
        if os.path.exists(presetPath_dest):
            title = "Overwrite Preset"
            text = ("A Preset with the same name:\n\n"
                    f"{presetName}\n\n"
                    "exists in the Project Presets Directory.\n\n"
                    "Would you like to Overwrite?")
            buttons = ["Overwrite", "Cancel"]
            result = core.popupQuestion(text=text, title=title, buttons=buttons)

            #   Abort
            if result != "Overwrite":
                return None

        #   Copy from Source to Project Presets Dir
        shutil.copy(presetPath_source, presetPath_dest)

        #   Load Data and Add to Presets Dict
        importData = loadPreset(presetPath_dest)

        return importData

    except Exception as e:
        logger.warning(f"ERROR: Unable to Import Preset: {e}")


def exportPreset(core:'PrismCore', pType:str, pName:str, pData:dict) -> bool:
    '''Export Preset to Selected Location.

    Args:
        core (PrismCore): The core application instance.
        pType (str): The type of the preset (e.g., "metadata", "ocio").
        pName (str): The name of the preset.
        pData (dict): The data of the preset.

    Returns:
        bool: True if the export was successful; otherwise, False.
    '''

    presetExt = getPresetExt(pType)
    initialName = pName + presetExt   

    #   Open Explorer to Choose Destination Path
    presetPath = explorerDialogue(
                        "Save Preset File",
                        dir = initialName,
                        selDir = False,
                        save = True,
                        filter = f"Preset Files (*{presetExt})"
                    )

    if not presetPath:
        return False

    try:
        #   Replace Any Extension with '.*_preset'
        root, ext = os.path.splitext(presetPath)
        if ext.lower() != f"{presetExt.lower()}":
            presetPath = f"{root}{presetExt}"

        pData = {"name": pName,
                 "data": pData}

        #   Save Preset
        savePreset(core, pType, pName, pData, path=presetPath)
        return True

    except Exception as e:
        logger.warning(f"ERROR: Unable to Export Preset: {e}")
        return False


def savePreset(core:'PrismCore',
               pType:str,
               pName:str,
               pData:dict,
               project:bool=True,
               path:str=None,
               checkExists:bool=True
               ) -> None:
    
    '''Saves Preset by Type to Either Project or Local User Presets Dir.

    Args:
        core (PrismCore): The core application instance.
        pType (str): The type of the preset.
        pName (str): The name of the preset.
        pData (dict): The data of the preset.
        project (bool): If True, save to the project-specific presets directory; otherwise, save to the local user presets directory.
        path (str, optional): The full path to save the preset. If provided, this path will be used instead of the default directories.
        checkExists (bool): If True, check if the preset already exists and prompt for overwrite.
    '''

    presetExt = getPresetExt(pType)
    if not presetExt or presetExt == "":
        return

    #   Create Preset File Name with Extension
    presetName = f"{pName}{presetExt}"

    #   Saves to Project Presets Dir
    if project:
        projPipelineDir = getProjectPresetDir(core, pType)
        presetPath = os.path.join(projPipelineDir, presetName)

    #   Saves to Local Plugin Presets Dir
    else:
        localPresetDir = getLocalPresetDir(core, pType)
        presetPath = os.path.join(localPresetDir, presetName)

    #   Saves to Passed Path
    if path:
        presetPath = path

    #   Popup Question if Exists
    if os.path.exists(presetPath) and checkExists:
        title = "Preset Exists!"
        msg = ("A Preset already exists with the name:\n\n"
                f"     {presetName}\n\n"
                "Would you like to Overwrite the Preset?")
        buttons = ["Overwrite", "Cancel"]
        result = core.popupQuestion(text=msg, title=title, buttons=buttons)
        if result != "Overwrite":
            return

    pTitle = pType.capitalize()
    commentHeader = f"""\
############################################################################
#
#                This is a Prism Pipeline Preset File
#                           {pTitle} Preset
#
############################################################################
"""

    #   Write Preset to Applicable Presets Dir
    try:
        json_str = json.dumps(pData, indent=4, ensure_ascii=False)

        with open(presetPath, "w", encoding="utf-8") as f:
            f.write(commentHeader + "\n" + json_str)

        logger.debug(f"Preset'{presetName}' Saved.")

    except Exception as e:
        logger.warning(f"ERROR:  Failed to Save Preset: {e}")


def deletePreset(core:'PrismCore', pType:str, pName:str) -> None:
    '''Delete Preset by Type from Project Preset Dir.

    Args:
        core (PrismCore): The core application instance.
        pType (str): The type of the preset.
        pName (str): The name of the preset.
    '''

    presetExt = getPresetExt(pType)
    if not presetExt or presetExt == "":
        return

    #   Create Preset File Name with Extension
    presetName = f"{pName}{presetExt}"

    #   Generate Preset Path
    projPipelineDir = getProjectPresetDir(core, pType)
    presetPath = os.path.join(projPipelineDir, presetName)

    #   Attempt to Delete Preset
    if os.path.exists(presetPath):
        try:
            os.remove(presetPath)
            logger.debug(f"Removed Preset: {presetName}")

        except Exception as e:
            msg = f"ERROR: Unable to Remove Preset: {e}"
            logger.warning(msg)
            core.popup(msg)

    else:
        logger.warning(f"ERROR: Preset '{presetName} does not appear to Exist in the Project")


