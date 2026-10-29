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
import copy
import logging
import re
from collections import deque
from dataclasses import dataclass, field, fields
from enum import Enum, auto
from contextlib import contextmanager
from typing import Optional, Any, TYPE_CHECKING

import numpy as np
from OpenGL.GL import *
import av

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


import ProjectScripts.PreviewPlayer_GL_Utils as Utils
from ProjectScripts.PreviewPlayer_GL_Utils import FLOAT16_MAX


if TYPE_CHECKING:
    from Scripts.PrismCore import PrismCore
    from ProjectScripts.PreviewPlayer_GL import PreviewPlayer_GL


from PrismUtils.Decorators import err_catcher
logger = logging.getLogger(__name__)



######################################
#######   Preview Media Data   #######

@dataclass(slots=True)
class PreviewMediaData:
    '''Container for preview-selection data shared between the UI and worker threads.'''

    state:  str = "ready"
    error:  str = ""
    token:  int = 0

    requestedMediaFiles:    list[str] = field(default_factory=list)
    requestedMetadata:      dict[str, Any] = field(default_factory=dict)

    mediaFiles:             list[str] = field(default_factory=list)
    metadata:               dict[str, Any] = field(default_factory=dict)

    selectedLayer:          str | None = None

    isSeq:                  bool = False
    isVideo:                bool = False

    fallbackDuration:       int = 1
    useFallback:            dict | bool = False

    fps:                    float = 24.0
    codec:                  str = ""

    pstart:                 int = 0
    pend:                   int = 0
    timecodeStart:          str = ""
    timecodeMode:           str = ""
    pduration:              int = 0

    pwidth:                 int = 0
    pheight:                int = 0

    @property
    def baseFile(self) -> str:
        return self.mediaFiles[0] if self.mediaFiles else ""

    @property
    def requestedBaseFile(self) -> str:
        return self.requestedMediaFiles[0] if self.requestedMediaFiles else ""

    @property
    def extension(self) -> str:
        return Utils.getFileExtension(filePath=self.baseFile)

    @property
    def requestedExtension(self) -> str:
        return Utils.getFileExtension(filePath=self.requestedBaseFile)

    @property
    def hasMedia(self) -> bool:
        return bool(self.mediaFiles)


    def getData(self) -> dict:
        '''Returns a dict with all the data values.
        
        Returns:
            dict: A deep copy of the dataclass fields as a dictionary.
        '''

        return {
            field.name: copy.deepcopy(getattr(self, field.name))
            for field in fields(self)
        }


    def update(self, data: dict[str, Any] | None = None, **kwargs):
        '''Updates one or more fields.

        Args:
            data: Optional dictionary of field/value pairs.
            **kwargs: Field/value pairs to update.
        '''

        if data is not None:
            kwargs.update(data)

        validFields = self.__dataclass_fields__

        for key, value in kwargs.items():
            if key not in validFields:
                logger.warning(f"{type(self).__name__} has no field '{key}'")
                continue

            setattr(self, key, value)



######################################
#######      Frame Cache       #######

class FrameState(Enum):
    '''Represents the state of a cached frame.

    States:
        EMPTY: Frame Cache Slot is Empty
        LOADING: Frame currently being cached
        READY: Frame is cached
        FAILED: Frame failed to cache
    '''

    EMPTY = auto()
    LOADING = auto()
    READY = auto()
    FAILED = auto()


@dataclass
class CachedFrame:
    '''Container for a cached frame in the frame cache.
    
    Args:
    - state (FrameState): The state of the cached frame.
    - image (np.ndarray | None): The image data of the cached frame.
    - colorSpace (str | None): The color space of the cached frame.
    - sourceFormat (str | None): The source format of the cached frame.
    - metadata (dict | None): Additional metadata for the cached frame.
    '''

    state: FrameState = FrameState.EMPTY
    image: np.ndarray | None = None
    colorSpace: str | None = None
    sourceFormat: str | None = None
    metadata: dict | None = None

    @property
    def channels(self):
        return self.image.shape[2] if self.image is not None else 0

    @property
    def dtype(self):
        return self.image.dtype

    @property
    def isFloat(self):
        return np.issubdtype(self.image.dtype, np.floating)

    @property
    def hasAlpha(self):
        return self.channels == 4



class FrameCache:
    '''The Cache of Frames for media files, supporting both video and image sequences.

    Args:
    ------
    - CacheMgr (FrameCacheManager): The frame cache manager instance.
    - mutex (QMutex): A mutex for thread-safe access to the cache.

    API:
    ------
    - configureCache(): Configures the frame cache with the specified total number of frames.
    - getCachedFrames(): Returns a list of all cached frame indices.
    - setCachedFrame(index: int, image: np.ndarray): Sets a cached frame at the specified index.
    - checkCacheFull(): Checks if the cache is at its maximum limits.
    - isCacheComplete() -> bool: Checks if the cache is complete (all frames are ready).
    - clearCache(): Clears the frame cache.
    '''

    def __init__(self, CacheMgr: 'FrameCacheManager', mutex: QMutex):
        self.CacheMgr = CacheMgr
        self.mutex = mutex
        self.frames: dict[int, CachedFrame] = {}
        self.frameKeys: list[int] = []
        self.readyFrameCount: int = 0

        self.maxCacheFrames: int | None = None
        self.totalFrames: int = 0
        self.frameBytes: int | None = None
        self.cacheFull = False
        self.maxSafetyRamFactor: float = 0.9


    ###########################
    ########    API    ########

    @err_catcher(name=__name__)
    def configureCache(self, totalFrames: int, frameKeys: list[int] = None, preserveReadyByKey: dict[int, CachedFrame] = None):
        '''Configures the frame cache with the specified total number of frames.
        
        Args:
            totalFrames (int): The total number of frames to configure in the cache.
        '''

        self.frameBytes = None
        self.cacheSize = 0
        if frameKeys is None:
            frameKeys = list(range(totalFrames))

        self.frameKeys = [int(k) for k in frameKeys]
        self.totalFrames = len(self.frameKeys)
        self.maxCacheFrames = None
        self.cacheFull = False     
        self.readyFrameCount = 0

        with self._mutexLock():
            self.frames = {}

            for frameKey in self.frameKeys:
                cachedFrame = preserveReadyByKey.get(frameKey) if preserveReadyByKey else None
                if cachedFrame and cachedFrame.state == FrameState.READY and cachedFrame.image is not None:
                    self.frames[frameKey] = cachedFrame
                    self.readyFrameCount += 1
                else:
                    self.frames[frameKey] = CachedFrame()


    @err_catcher(name=__name__)
    def getCachedFrames(self) -> list[int]:
        '''Returns a list of all cached frame indices.

        Returns:
            list[int]: A list of cached frame indices.
        '''

        cached = []
        for idx, frameKey in enumerate(self.frameKeys):
            frame = self.frames.get(frameKey)
            if frame and frame.state == FrameState.READY:
                cached.append(idx)

        return cached


    @err_catcher(name=__name__)
    def setCachedFrame(self, index: int, image: np.ndarray):
        '''Sets a cached frame at the specified index.

        Args:
            index (int): The index at which to set the frame.
            frame (np.ndarray): The frame to cache.
        '''

        try:
            with self._mutexLock():
                if self.cacheFull:
                    return

                frameKey = self._getFrameKey(index)
                if frameKey is None:
                    return

                cachedFrame = self.frames.get(frameKey)
                if cachedFrame is None:
                    return

                wasReady = cachedFrame.state == FrameState.READY

                cachedFrame.image = image
                cachedFrame.state = FrameState.READY

                if not wasReady:
                    self.readyFrameCount += 1

        except Exception as e:
            logger.warning(f"Error setting cached frame at index {index}: {e}")
            self._setFrameFailed(index)


    @err_catcher(name=__name__)
    def checkCacheFull(self):
        '''Checks if the Cache is at its Max Limits.'''

        #   Sets the Max's if Not Yet Set
        if not self.maxCacheFrames:
            self._setMaxCacheFrames()

        #   Check if the Cache is at Max Frames Capacity
        try:
            cachedCount = self.readyFrameCount
            if self.maxCacheFrames and cachedCount > self.maxCacheFrames:
                logger.debug(f"Frame Cache at maximum: {cachedCount} frames ({self.maxCacheFrames} max).")  

                self.CacheMgr.stop() 
                self.cacheFull = True
                self.CacheMgr.Player.PlayControls.updateCacheSlider()
                return
            
        except Exception as e:
            logger.warning(f"Error checking max cache: {e}")
            return

        #   Check if RAM is at Max Capacity
        try:
            if Utils.getAvailableRAM() < Utils.getMaxSafetyRAMSize(self.maxSafetyRamFactor):
                logger.debug(f"Frame Cache reached max RAM protection: {self.maxSafetyRamFactor*100}% of {Utils.getTotalRAM()}.")

                self.CacheMgr.stop() 
                self.cacheFull = True
                self.CacheMgr.Player.PlayControls.updateCacheSlider()

        except Exception as e:
            logger.warning(f"Error checking max RAM: {e}")


    @err_catcher(name=__name__)
    def isCacheComplete(self) -> bool:
        '''Checks if the cache is complete (all frames are ready).

        Returns:
            bool: True if all frames are ready, False otherwise.
        '''

        targetFrames = self.CacheMgr.cacheableFrameCount or self.totalFrames
        return targetFrames > 0 and self.readyFrameCount >= targetFrames


    @err_catcher(name=__name__)
    def clearCache(self):
        '''Clears the frame cache.'''

        with self._mutexLock():
            self.frames.clear()

        self.frameBytes = None
        self.cacheSize = 0
        self.totalFrames = 0
        self.frameKeys = []
        self.maxCacheFrames = None
        self.readyFrameCount = 0

        self.cacheFull = False    


    ################################
    ########    INTERNAL    ########

    @contextmanager
    def _mutexLock(self):
        '''Context manager to lock the mutex.'''

        self.mutex.lock()
        try:
            yield
        finally:
            self.mutex.unlock()


    @err_catcher(name=__name__)
    def _getCachedFramesList(self, cached:bool=False) -> list[int | None]:
        '''Returns a list of all frame indices, optionally filtered to only include cached frames.

        Args:
            cached (bool, optional): If True, only return cached frames. Defaults to False.

        Returns:
            list[int | None]: A list of cached frames indices, with None for missing frames.
        '''

        if cached:
            return self.getCachedFrames()

        return [i for i in range(self.totalFrames)]


    @err_catcher(name=__name__)
    def _getFrameKey(self, index: int) -> int | None:
        '''Returns the internal frame key for a timeline frame index.'''

        try:
            idx = int(index)
        except Exception:
            return None

        if idx < 0 or idx >= len(self.frameKeys):
            return None

        return self.frameKeys[idx]

    
    @err_catcher(name=__name__)
    def _setMaxCacheFrames(self):
        '''Sets the Max frames that can be cached based on the provided image size.
        
        Args:
            image (np.ndarray): The image to determine the frame bytes from.
        '''

        try:
            image = self._getCachedFrame(0).image if self._getCachedFrame(0) else None

            if image is not None:
                #   Get Size of Image Numpy Array
                frameBytes = image.nbytes if hasattr(image, "nbytes") else None

                if frameBytes is not None:
                    #   Calculate Max Cache Frames based on RAM and User Setting 'maxCacheMemPercent'
                    maxCacheBytes = int(self.CacheMgr.maxCacheMemPercent / 100 * Utils.getTotalRAM())
                    self.maxCacheFrames = int(maxCacheBytes / frameBytes) if frameBytes > 0 else 0
                    logger.debug(f"Max Cache Frames set to {self.maxCacheFrames} ({self.CacheMgr.maxCacheMemPercent}% of RAM)")

        except Exception as e:
            logger.warning(f"Error setting max cache frames: {e}")
            self.maxCacheFrames = None


    @err_catcher(name=__name__)
    def _setFrameLoading(self, index: int):
        '''Marks a frame as loading.

        Args:
            index (int): The index of the frame to mark as loading.
        '''

        with self._mutexLock():
            frameKey = self._getFrameKey(index)
            if frameKey is None:
                return

            frame = self.frames.get(frameKey)
            if frame is None:
                return
            if frame.state == FrameState.READY and self.readyFrameCount > 0:
                self.readyFrameCount -= 1
            frame.state = FrameState.LOADING


    @err_catcher(name=__name__)
    def _setFrameFailed(self, index: int):
        '''Marks a frame as failed.

        Args:
            index (int): The index of the frame to mark as failed.
        '''

        with self._mutexLock():
            frameKey = self._getFrameKey(index)
            if frameKey is None:
                return

            frame = self.frames.get(frameKey)
            if frame is None:
                return
            if frame.state == FrameState.READY and self.readyFrameCount > 0:
                self.readyFrameCount -= 1
            frame.state = FrameState.FAILED


    @err_catcher(name=__name__)
    def _resetLoadingFrames(self):
        '''Resets non-complete loading frames back to empty.

        This is used when caching is stopped mid-build so a subsequent start can
        re-queue those frames.
        '''

        with self._mutexLock():
            for frame in self.frames.values():
                if frame.state == FrameState.LOADING:
                    frame.state = FrameState.EMPTY

    
    @err_catcher(name=__name__)
    def _getCachedFrame(self, index: int) -> CachedFrame | None:
        '''Retrieves a cached frame by its index.

        Args:
            index (int): The index of the frame to retrieve.

        Returns:
            CachedFrame | None: The cached frame if it exists, otherwise None.
        '''

        frameKey = self._getFrameKey(index)
        if frameKey is None:
            return None

        return self.frames.get(frameKey, None)
    

    @err_catcher(name=__name__)
    def _isCachedFrameReady(self, index: int) -> bool:
        '''Checks if a cached frame at the specified index is ready.

        Args:
            index (int): The index of the frame to check.

        Returns:
            bool: True if the frame is ready, False otherwise.
        '''

        frame = self._getCachedFrame(index)
        return frame is not None and frame.state == FrameState.READY


    @err_catcher(name=__name__)
    def _isCachedFrameEmpty(self, index: int) -> bool:
        '''Checks if a cached frame at the specified index is empty.

        Args:
            index (int): The index of the frame to check.

        Returns:
            bool: True if the frame is empty, False otherwise.
        '''

        frame = self._getCachedFrame(index)
        return frame is None or frame.state == FrameState.EMPTY


    @err_catcher(name=__name__)
    def _getReadyImage(self, index: int) -> np.ndarray | None:
        '''Retrieves the image data of a cached frame if it is ready.

        Args:
            index (int): The index of the frame to retrieve.

        Returns:
            np.ndarray | None: The image data if the frame is ready, otherwise None.
        '''

        frame = self._getCachedFrame(index)
        if frame and frame.state == FrameState.READY:
            return frame.image

        return None


        
class FrameCacheManager(QObject):
    '''Manages a cache of frames for media files, supporting both video and image sequences.

    Signals:
    ------
    - cacheUpdated (int): Emitted when the cache is updated with the number of frames cached.
    - cacheComplete (): Emitted when the caching process is complete.
    - firstFrameComplete (int): Emitted when the first frame is cached, with the frame index.

    Args:
    ------
    - core (PrismCore): Prism Core instance
    - Player (PreviewPlayer_GL): The preview player instance associated with this cache.
    - pWidth (int): Width for preview frames, default is 400

    API:
    ------
    - setThreadpool(threadNum: int): Sets the number of threads for cache workers.
    - setSignalIntervalMs(intervalMs: int): Sets the minimum interval for cacheUpdated signal emissions.
    - setMedia(mediaFiles: list, prevWidth: int, isSeq: bool, prevData: dict): Sets the media files and related metadata for caching.
    - resetThreadpools(waitTimeoutMs: int): Resets the thread pools for cache workers.
    - start(): Starts the caching process.
    - stop(): Stops the caching process.
    - rescan(): Initiates a rescan of the media files to update the cache.
    - clear(): Clears the cache.
    - frameToIdx(frameNumber: int, clamp: bool): Converts a frame number to the internal zero-based timeline index.
    - idxToFrame(index: int): Converts an internal zero-based timeline index to a frame number.
    - getFrame(index: int): Retrieves a cached frame by its index.
    - getPreviousFrame(index: int): Retrieves the previously cached frame before the specified index.
    - generateFrame(index: int, priority: bool): Generates a frame at the specified index, optionally with priority.
    '''

    cacheUpdated = Signal(int)
    cacheComplete = Signal()
    firstFrameComplete = Signal(int)


    def __init__(self, core: 'PrismCore', Player: 'PreviewPlayer_GL', pWidth=400):
        super().__init__()
        self.core = core
        self.Player = Player

        self.mutex = QMutex()
        self.Cache = FrameCache(self, self.mutex)

        #   Cache Frame Width
        self.pWidth = int(pWidth)

        #   Cache Workers and RAM Protection
        self.cacheThreads = 4
        self.maxCacheMemPercent = 50

        self.workers = []
        self.mediaFiles = []

        self.cacheableFrameCount = 0
        self._firstFrameEmitted = False
        self.isRunning = False
        self.isVideo = False
        self.progressEmitStep = 1
        self._reportedFrames = set()
        self._pendingFrameRequests = set()
        self._sequenceQueue = deque()

        #   Sender-side Prog Signal Throttle (PreviewPlayer_GL.setUiRefreshIntervalMs syncs this to uiRefreshIntervalMs)
        self.progressEmitIntervalMs = 50

        #   Throttles Progress Signal Updates
        self.progressEmitTimer = QElapsedTimer()
        self.progressEmitTimer.start()


    #########################
    #######   API    ########

    @err_catcher(name=__name__)
    def setThreadpool(self, threadNum:int):
        '''Sets the Threadpool for Cache Workers. Also Sets up a dedicated priority threadpool for immediate tasks.

        Args:
            threadNum (int): The number of threads to use for caching.
        '''

        #   Set Main Worker Threadpool
        self.cacheThreads = threadNum
        self.threadpool = QThreadPool(self)
        self.threadpool.setMaxThreadCount(threadNum)

        #   Set Priority Worker Threadpool (single-threaded for immediate tasks)
        self.priorityThreadpool = QThreadPool(self)
        self.priorityThreadpool.setMaxThreadCount(1)

        logger.debug(f"Cache Threads set to {threadNum}")


    @err_catcher(name=__name__)
    def setSignalIntervalMs(self, intervalMs: int):
        '''Sets sender-side throttle for cacheUpdated signal emission.

        Args:
            intervalMs (int): The minimum interval in milliseconds between cacheUpdated signal emissions.
        '''

        self.progressEmitIntervalMs = max(0, int(intervalMs))


    @err_catcher(name=__name__)
    def setMedia(self, mediaFiles:list, prevWidth:int, isSeq:bool, prevData:dict):
        '''Sets the media files and related metadata for the frame cache manager.

        Args:
            mediaFiles (list): List of media file paths.
            prevWidth (int): The width of the preview.
            isSeq (bool): Whether the media files are an image sequence.
            prevData (dict): Dictionary containing metadata such as start, end, duration, fps, codec, height, and selectedLayer.
        '''

        self.stop()
        self.resetThreadpools(waitTimeoutMs=1000)
        self.clear()

        self.mediaFiles = mediaFiles
        self.isSeq = isSeq
        self.mediaFiles = list(mediaFiles)
        self.cacheableFrameCount = len(mediaFiles)

        #   Media Data
        self.pstart = prevData["start"]
        self.pend = prevData["end"]
        self.pduration = prevData["duration"]
        self.fps = prevData["fps"]
        self.codec = prevData["codec"]
        self.pwidth = prevWidth
        self.pheight = prevData["height"]
        self.selectedLayer = prevData.get("selectedLayer")
        self.isVideo = bool(prevData.get("isVideo", False))

        self._reportedFrames = set()
        self._pendingFrameRequests = set()
        self._sequenceQueue = deque()
        self.progressEmitTimer.restart()

        #   IMAGE SEQUENCE
        if self.isSeq:
            sData =  self._buildSequenceMediaMap(self.mediaFiles, self.pstart, self.pend)
            self.mediaFiles, self.pstart, self.pend, self.cacheableFrameCount = sData

            self.totalFrames = max(1, len(self.mediaFiles))
            self.pduration = self.totalFrames

        #   SINGLE IMAGE
        elif not self.isVideo:
            self.totalFrames = len(self.mediaFiles)
            self.cacheableFrameCount = len(self.mediaFiles)

        #   VIDEO
        else:
            #   TotalFrames Based on Duration or Default to 1
            self.totalFrames = max(1, int(self.pduration or 1))
            self.cacheableFrameCount = self.totalFrames

            #   Attempt to Read Codec Info from Video Stream if Not Already Provided
            if not self.codec:
                mediaPath = self.mediaFiles[0]

                try:
                    container = av.open(mediaPath)
                    stream = container.streams.video[0]
                    if stream.codec_context and stream.codec_context.name:
                        self.codec = stream.codec_context.name.lower()
                    container.close()

                except Exception as e:
                    logger.warning(f"Unable to read codec info from media stream: {e}")

        #   Set Progress Emit Step
        if self.isVideo and self.totalFrames > 0:
            self.progressEmitStep = max(1, self.totalFrames // 200)
        else:
            self.progressEmitStep = 1

        #   Configure Cache with Total Frames
        self.Cache.configureCache(self.totalFrames, frameKeys=self._getCacheFrameKeys())


    @err_catcher(name=__name__)
    def resetThreadpools(self, waitTimeoutMs: int = 0):
        '''Clears queued work from cache threadpools and optionally waits for running jobs.

        Args:
            waitTimeoutMs (int, optional): Milliseconds to wait for active workers to finish.
                If 0, only queued tasks are cleared. Defaults to 0.
        '''

        timeout = max(0, int(waitTimeoutMs))

        for poolName in ("threadpool", "priorityThreadpool"):
            if not hasattr(self, poolName):
                continue

            pool = getattr(self, poolName)

            try:
                pool.clear()
            except Exception:
                pass

            if timeout > 0:
                try:
                    pool.waitForDone(timeout)
                except Exception:
                    pass


    @err_catcher(name=__name__)
    def start(self):
        '''Starts the Frame Caching'''

        if not self.mediaFiles:
            return

        if not hasattr(self, "threadpool"):
            self.setThreadpool(self.cacheThreads)
        
        logger.debug("Frame Caching Started")

        if self.Cache.cacheFull:
            logger.debug("Frame Caching cannot start: Cache is full.")
            return

        #   Keep Worker References for all Threadpools
        poolsIdle = True
        for poolName in ("threadpool", "priorityThreadpool"):
            if not hasattr(self, poolName):
                continue
            pool = getattr(self, poolName)
            try:
                if pool.activeThreadCount() > 0:
                    poolsIdle = False
                    break
            except Exception:
                pass

        if poolsIdle:
            self.workers = []

        startedWorkers = 0
        self.isRunning = True

        #   Image Sequences (launch a worker per sequence image)
        if self.isSeq or not self.isVideo:
            pendingImageJobs = []

            #   Collect empty cache slots for queueing
            with self.Cache._mutexLock():
                for frame_idx in range(self.totalFrames):
                    if self.Cache.cacheFull:
                        break

                    imgPath = self.mediaFiles[frame_idx] if frame_idx < len(self.mediaFiles) else None
                    if not imgPath:
                        continue

                    cachedFrame = self.Cache._getCachedFrame(frame_idx)
                    if cachedFrame is None or cachedFrame.state != FrameState.EMPTY:
                        continue

                    pendingImageJobs.append((frame_idx, imgPath))

            self._sequenceQueue.extend(pendingImageJobs)

            maxLaunch = max(1, int(self.cacheThreads))
            for _ in range(min(maxLaunch, len(self._sequenceQueue))):
                if self._startNextSequenceWorker():
                    startedWorkers += 1

        #   Non-Sequences (launch single video cache worker)
        else:
            mediaPath = self.mediaFiles[0]

            if self.Cache.cacheFull:
                return

            worker = VideoCacheWorker(
                self.core,
                self.Player,
                self.Cache,
                mediaPath,
                self.fps,
                self.pWidth,
                self._onWorkerProgress,
            )

            worker.setAutoDelete(True)

            self.workers.append(worker)
            self.threadpool.start(worker)
            startedWorkers += 1

        self.isRunning = startedWorkers > 0
    

    @err_catcher(name=__name__)
    def stop(self):
        '''Stops the Frame Caching'''

        self.isRunning = False

        for worker in self.workers:
            worker.stop()

        self.resetThreadpools(waitTimeoutMs=1000)
        self.Cache._resetLoadingFrames()
        self.workers.clear()
        self._pendingFrameRequests.clear()
        self._sequenceQueue.clear()

        logger.debug("Frame Cache Stopped")


    @err_catcher(name=__name__)
    def rescan(self, mediaFiles: list[str], selectedLayer: str = None) -> bool:
        '''Rescans sequence media, updates frame range, and preserves ready cache frames by frame number.

        Args:
            mediaFiles (list[str]): List of media file paths to rescan.
            selectedLayer (str, optional): The selected layer to update. Defaults to None.

        Returns:
            bool: True if the sequence media or frame range changed, False otherwise.
        '''

        if self.Cache.cacheFull or not self.isSeq or not mediaFiles:
            return False

        #   Preserve the current running state
        wasRunning = self.isRunning
        oldMediaFiles = list(self.mediaFiles)
        oldStart = self.pstart
        oldEnd = self.pend
        oldTotal = self.totalFrames
        oldCacheable = self.cacheableFrameCount

        #   Stop the current caching process
        with self.Cache._mutexLock():
            preservedReady = {
                frameKey: cachedFrame
                for frameKey, cachedFrame in self.Cache.frames.items()
                if cachedFrame.state == FrameState.READY and cachedFrame.image is not None
            }

        self.stop()

        #   Update the media files and selected layer
        self.mediaFiles = list(mediaFiles)
        if selectedLayer is not None:
            self.selectedLayer = selectedLayer

        #   Rebuild the sequence media map and update frame range
        self.mediaFiles, newStart, newEnd, newCacheable = self._buildSequenceMediaMap(self.mediaFiles)

        #   Update the internal frame range and cacheable frame count
        self.pstart = newStart
        self.pend = newEnd
        self.totalFrames = max(1, len(self.mediaFiles))
        self.pduration = self.totalFrames
        self.cacheableFrameCount = newCacheable

        #   Configure the cache with the updated frame range and preserved ready frames
        self.Cache.configureCache(
            self.totalFrames,
            frameKeys=self._getCacheFrameKeys(),
            preserveReadyByKey=preservedReady,
        )

        #   Clear pending frame requests and sequence queue
        self._pendingFrameRequests.clear()
        self._sequenceQueue.clear()

        #   Rebuild the sequence queue with frames that are not yet cached
        for frameIdx in range(self.totalFrames):
            imgPath = self.mediaFiles[frameIdx] if frameIdx < len(self.mediaFiles) else None
            if not imgPath:
                continue
            if self.Cache._isCachedFrameEmpty(frameIdx):
                self._sequenceQueue.append((frameIdx, imgPath))

        #   Update the set of reported frames based on the current cache state
        self._reportedFrames = set(self.Cache.getCachedFrames())

        #   Determine if any Changes from the previous state
        changed = (
            oldStart != self.pstart
            or oldEnd != self.pend
            or oldTotal != self.totalFrames
            or oldCacheable != self.cacheableFrameCount
            or oldMediaFiles != self.mediaFiles
        )

        if changed:
            logger.debug(f"Frame Cache Rescan: Start={self.pstart}, End={self.pend}, Total={self.totalFrames}, Cacheable={self.cacheableFrameCount}")

        else:
            logger.debug("Frame Cache Rescan: No changes detected.")

        if self._sequenceQueue and (changed or wasRunning):
            self.start()

        return changed


    @err_catcher(name=__name__)
    def clear(self):
        '''Clears the Current Frame Cache'''

        self.Cache.clearCache()
        logger.debug("Frame Cache Cleared")


    @err_catcher(name=__name__)
    def frameToIdx(self, frameNumber: int, clamp: bool = False) -> int | None:
        '''Converts a frame number to the internal zero-based timeline index.

        Args:
            frameNumber (int): The frame number to convert.
            clamp (bool, optional): Whether to clamp the index within valid range. Defaults to False.

        Returns:
            int | None: The corresponding zero-based timeline index, or None if invalid.
        '''

        try:
            idx = int(frameNumber) - int(self.pstart)
        except Exception:
            return None

        if clamp:
            total = max(1, int(self.totalFrames or 1))
            return max(0, min(idx, total - 1))

        if idx < 0 or idx >= int(self.totalFrames or 0):
            return None

        return idx


    @err_catcher(name=__name__)
    def idxToFrame(self, frameIdx: int, clamp: bool = False) -> int | None:
        '''Converts an internal zero-based timeline index to frame number.

        Args:
            frameIdx (int): The internal zero-based timeline index to convert.
            clamp (bool, optional): Whether to clamp the frame number within valid range. Defaults to False.

        Returns:
            int | None: The corresponding frame number, or None if invalid.
        '''

        try:
            idx = int(frameIdx)
        except Exception:
            return None

        total = int(self.totalFrames or 0)
        if total <= 0:
            return int(self.pstart)

        if clamp:
            idx = max(0, min(idx, total - 1))
        elif idx < 0 or idx >= total:
            return None

        return int(self.pstart) + idx


    @err_catcher(name=__name__)
    def getFrame(self, frameNumber: int) -> np.array:
        '''Retrieves the frame at the specified frame number from the cache.

        Args:
            frameNumber (int): The frame number to retrieve.

        Returns:
            np.array: The frame data as a numpy array, or None if unavailable.
        '''

        frameIdx = self.frameToIdx(frameNumber)
        if frameIdx is None:
            return None

        return self.Cache._getReadyImage(frameIdx)


    @err_catcher(name=__name__)
    def getPreviousCachedFrame(self, frameNumber: int) -> np.array:
        '''Retrieves the most recent cached frame before the specified frame number.

        Args:
            frameNumber (int): The frame number to start searching backward from.

        Returns:
            np.array: The most recent cached frame data as a numpy array, or None if unavailable.
        '''

        frameIdx = self.frameToIdx(frameNumber)
        if frameIdx is None:
            return None

        for idx in range(frameIdx - 1, -1, -1):
            image = self.Cache._getReadyImage(idx)
            if image is not None:
             return image

        return None


    @err_catcher(name=__name__)
    def generateFrame(self, frameNumber: int, priority: bool = False) -> np.array:
        '''Generates the frame at the specified frame number, either from an image sequence or a video file.

        Args:
            frameNumber (int): The frame number to generate.
            priority (bool, optional): Whether to prioritize this frame request. Defaults to False.

        Returns:
            np.array: The generated frame data as a numpy array, or None if unavailable.
        '''

        if not self.mediaFiles:
            return None

        frameIdx = self.frameToIdx(frameNumber)
        if frameIdx is None:
            return None

        if frameIdx < 0 or frameIdx >= self.totalFrames:
            return None

        if not hasattr(self, "threadpool"):
            self.setThreadpool(self.cacheThreads)

        if self.Cache._isCachedFrameReady(frameIdx):
            return self.Cache._getReadyImage(frameIdx)

        if self.Cache._getCachedFrame(frameIdx) is None:
            return None

        if frameIdx in self._pendingFrameRequests:
            return None

        ###   Image Sequence
        if (self.isSeq or not self.isVideo) and self.Cache._isCachedFrameEmpty(frameIdx):
            if self.isSeq:
                imgPath = self.mediaFiles[frameIdx] if frameIdx < len(self.mediaFiles) else None
            else:
                imgPath = self.mediaFiles[frameIdx]

            if not imgPath:
                return None

            self.Cache._setFrameLoading(frameIdx)
            self._pendingFrameRequests.add(frameIdx)

            worker = ImageCacheWorker(
                self.core,
                self.Player,
                self.Cache,
                imgPath,
                frameIdx,
                self.pWidth,
                self._onWorkerProgress,
                selectedLayer=self.selectedLayer,
            )

            worker.setAutoDelete(True)
            self.workers.append(worker)

            if priority and hasattr(self, "priorityThreadpool"):
                self.priorityThreadpool.start(worker)
            else:
                self.threadpool.start(worker)

        ###   Video
        else:
            mediaPath = self.mediaFiles[0]

            maxPending = max(2, self.cacheThreads * 2)
            if not priority and len(self._pendingFrameRequests) >= maxPending:
                return None

            self.Cache._setFrameLoading(frameIdx)
            self._pendingFrameRequests.add(frameIdx)

            worker = VideoFrameRequestWorker(
                self.core,
                self.Player,
                self.Cache,
                mediaPath,
                frameIdx,
                self.pWidth,
                self.fps,
                self._onWorkerProgress,
                self._onWorkerFailed,
            )

            worker.setAutoDelete(True)
            self.workers.append(worker)

            if priority and hasattr(self, "priorityThreadpool"):
                self.priorityThreadpool.start(worker)
            else:
                self.threadpool.start(worker)

        return None


    ##############################
    #######   INTERNAL    ########

    @err_catcher(name=__name__)
    def _onWorkerProgress(self, frameIdx: int, firstFrame: bool = False):
        '''Handles progress updates from worker threads.

        Args:
            frameIdx (int): The index of the frame that has been processed.
            firstFrame (bool, optional): Whether this is the first frame. Defaults to False.
        '''

        if firstFrame:
            frameNumber = self.idxToFrame(frameIdx, clamp=True)
            self.firstFrameComplete.emit(frameNumber)
            self._firstFrameEmitted = True

        requestedFrame = frameIdx in self._pendingFrameRequests

        shouldEmit = requestedFrame or firstFrame or self.progressEmitStep <= 1 or frameIdx == (self.totalFrames - 1)
        if not shouldEmit and frameIdx % self.progressEmitStep == 0:
            shouldEmit = True

        timeReady = (
            self.progressEmitIntervalMs <= 0
            or not self.progressEmitTimer.isValid()
            or self.progressEmitTimer.elapsed() >= self.progressEmitIntervalMs
        )

        if shouldEmit and (requestedFrame or firstFrame or frameIdx == (self.totalFrames - 1) or timeReady):
            frameNumber = self.idxToFrame(frameIdx, clamp=True)
            self.cacheUpdated.emit(frameNumber)
            self.progressEmitTimer.restart()

        self._pendingFrameRequests.discard(frameIdx)

        if (self.isSeq or not self.isVideo) and self.isRunning:
            self._startNextSequenceWorker()


        if frameIdx not in self._reportedFrames and self.Cache._isCachedFrameReady(frameIdx):
            self._reportedFrames.add(frameIdx)

        cacheableFrames = self.cacheableFrameCount or self.totalFrames
        isComplete = len(self._reportedFrames) >= cacheableFrames
        if not isComplete and self.isVideo and frameIdx == (self.totalFrames - 1):
            isComplete = self.Cache.isCacheComplete()

        if isComplete and self.isRunning:
            self.isRunning = False
            logger.debug("Frame Cache Complete")
            self.cacheComplete.emit()


    @err_catcher(name=__name__)
    def _onWorkerFailed(self, frameIdx: int, message: str = ""):
        '''Handles worker decode failures for specific frame requests.

        Args:
            frameIdx (int): The index of the frame that failed to decode.
            message (str, optional): An optional error message describing the failure.
        '''

        self._pendingFrameRequests.discard(frameIdx)

        if (self.isSeq or not self.isVideo) and self.isRunning:
            self._startNextSequenceWorker()

        if self.Cache._getCachedFrame(frameIdx) is not None:
            self.Cache._setFrameFailed(frameIdx)

        if message:
            logger.warning(f"Frame request failed for frame {frameIdx}: {message}")


    @err_catcher(name=__name__)
    def _startNextSequenceWorker(self) -> bool:
        '''Starts the next queued image worker for sequence/non-video caching.

        Returns:
            bool: True if a worker was started, False otherwise.
        '''

        if self.Cache.cacheFull or not self._sequenceQueue:
            return False

        while self._sequenceQueue:
            frame_idx, imgPath = self._sequenceQueue.popleft()

            with self.Cache._mutexLock():
                if self.Cache.cacheFull:
                    return False

                cachedFrame = self.Cache._getCachedFrame(frame_idx)
                if cachedFrame is None or cachedFrame.state != FrameState.EMPTY:
                    continue

                cachedFrame.state = FrameState.LOADING

            self._pendingFrameRequests.add(frame_idx)

            worker = ImageCacheWorker(
                self.core,
                self.Player,
                self.Cache,
                imgPath,
                frame_idx,
                self.pWidth,
                self._onWorkerProgress,
                selectedLayer=self.selectedLayer,
            )

            worker.setAutoDelete(True)
            self.workers.append(worker)
            self.threadpool.start(worker)

            return True

        return False


    @err_catcher(name=__name__)
    def _buildSequenceMediaMap(self, mediaFiles:list[str], pstart:int = None, pend:int = None) -> tuple[list[str], int, int, int]:
        '''Build sequence media list indexed by timeline frame index and aligned to sequence frame numbers.
        
        Args:
            mediaFiles (list[str]): List of media file paths to process.
            pstart (int, optional): The starting frame number of the sequence. Defaults to None.
            pend (int, optional): The ending frame number of the sequence. Defaults to None.

        Returns:
            tuple[list[str], int, int, int]: A tuple containing the sequence media files list, start frame, end frame, and cacheable frame count.
        '''

        frameMap = {}

        #   Build a mapping of frame numbers to media file paths
        for imgPath in mediaFiles:
            frameNumberStr = self.core.media.getFrameNumberFromFilename(os.path.basename(imgPath))
            if frameNumberStr is None:
                continue

            try:
                frameNumber = int(frameNumberStr)
            except Exception:
                continue

            if frameNumber not in frameMap:
                frameMap[frameNumber] = imgPath

        #   If there are valid frames, determine the sequence start and end, and build the sequence media list
        if frameMap:
            seqStart = int(pstart) if pstart is not None else min(frameMap.keys())
            seqEnd = int(pend) if pend is not None else max(frameMap.keys())
            if seqEnd < seqStart:
                seqStart, seqEnd = seqEnd, seqStart

            totalFrames = max(1, seqEnd - seqStart + 1)
            mediaFiles = [None] * totalFrames
            cacheableFrameCount = 0

            for frameNumber, imgPath in frameMap.items():
                frameIdx = frameNumber - seqStart
                if 0 <= frameIdx < totalFrames:
                    if mediaFiles[frameIdx] is None:
                        cacheableFrameCount += 1
                    mediaFiles[frameIdx] = imgPath

            return mediaFiles, seqStart, seqEnd, cacheableFrameCount

        #   If there are no valid frames, fall back to a default sequence based on the provided media files
        fallbackMediaFiles = list(mediaFiles)
        seqStart = int(pstart) if pstart is not None else 1
        seqEnd = int(pend) if pend is not None else (seqStart + max(0, len(fallbackMediaFiles) - 1))
        if seqEnd < seqStart:
            seqStart, seqEnd = seqEnd, seqStart

        totalFrames = max(1, seqEnd - seqStart + 1)
        mediaFiles = [None] * totalFrames
        cacheableFrameCount = 0

        for frameIdx, imgPath in enumerate(fallbackMediaFiles[:totalFrames]):
            mediaFiles[frameIdx] = imgPath
            if imgPath:
                cacheableFrameCount += 1

        return mediaFiles, seqStart, seqEnd, cacheableFrameCount


    @err_catcher(name=__name__)
    def _getCacheFrameKeys(self) -> list[int]:
        '''Returns frame keys used by the internal cache dictionary.

        Returns:
            list[int]: A list of frame keys corresponding to the internal cache frames.
        '''

        return [int(self.pstart) + i for i in range(self.totalFrames)]



class FrameCacheRescanSignals(QObject):
    cachedRescanned = Signal(bool)

class FrameCacheRescanWorker(QRunnable):
    '''Worker that rescans the frame cache for new or updated media files.
    
    Signals:
    --------
        - cachedRescanned (Signal): Emitted when the cache rescan is completed, with a boolean indicating if changes were detected.

    Args:
    -----
        - Player (PreviewPlayer_GL): The preview player instance.
        - CacheMgr (FrameCacheManager): The frame cache manager instance.

    API:
    -----
        - run(): Starts the rescan worker.
    '''

    def __init__(self, Player: 'PreviewPlayer_GL', CacheMgr: 'FrameCacheManager'):
        super().__init__()

        self.Player = Player
        self.CacheMgr = CacheMgr
        self.signals = FrameCacheRescanSignals() 


    @err_catcher(name=__name__)
    def _getDirectoryFileCount(self) -> int:
        '''Returns the number of files in the current sequence directory.

        Returns:
            int: The number of files in the sequence directory.
        '''


        mediaFiles = [p for p in getattr(self.CacheMgr, "mediaFiles", []) if p]
        if not mediaFiles:
            return 0

        seqDir = os.path.dirname(mediaFiles[0])
        if not seqDir:
            return 0

        count = 0
        try:
            with os.scandir(seqDir) as entries:
                for entry in entries:
                    if entry.is_file():
                        count += 1
        except Exception:
            return 0

        return count


    @err_catcher(name=__name__)
    def run(self):
        '''Start the frame cache rescan worker.'''

        changed = False

        try:
            #   Get the Known Count of Cacheable Frames from the Cache Manager
            knownCount = int(getattr(self.CacheMgr, "cacheableFrameCount", 0) or 0)
            if knownCount <= 0:
                knownCount = len([f for f in getattr(self.CacheMgr, "mediaFiles", []) if f])

            #   Get the Actual Count in the Directory
            dirCount = self._getDirectoryFileCount()
            if dirCount <= knownCount:
                return

            if not self.Player.getSelectedMediaFiles(self.Player.previewLoadToken):
                return

            if not self.Player.validateMedia():
                return

            mediaData = self.Player.MediaData.getData()
            validMedia = list(mediaData.get("mediaFiles") or [])
            metadata = dict(mediaData.get("metadata") or mediaData.get("requestedMetadata") or {})
            requestedMedia = list(mediaData.get("requestedMediaFiles") or [])
            selectedLayer = mediaData.get("selectedLayer")
            useFallback = mediaData.get("useFallback")
            isVideo = bool(mediaData.get("isVideo", False))

            if not validMedia:
                return

            if useFallback or isVideo:
                return

            #   Call to Cache Manager for Rescan
            changed = bool(self.CacheMgr.rescan(validMedia, selectedLayer=selectedLayer))

            #   Update the Player with the New Media and Metadata
            self.Player.MediaData.mediaFiles = validMedia
            self.Player.MediaData.metadata = metadata
            self.Player.MediaData.update(
                mediaFiles=list(validMedia),
                metadata=dict(metadata),
                requestedMediaFiles=list(requestedMedia),
                requestedMetadata=dict(mediaData.get("requestedMetadata") or {}),
                selectedLayer=selectedLayer,
                useFallback=useFallback,
                isSeq=True,
                isVideo=isVideo,
                state="ready" if not useFallback else "fallback",
            )

        finally:
            self.signals.cachedRescanned.emit(changed)



class VideoFrameRequestWorker(QRunnable):
    '''Worker that decodes a single requested video frame off the UI thread.
    
    Args:
    ------
    - core (PrismCore): The core instance.
    - Player (PreviewPlayer_GL): The preview player instance.
    - Cache (FrameCache): The frame cache instance.
    - mediaPath (str): The path to the media file.
    - frameIdx (int): The index of the frame to decode.
    - pWidth (int): The preview width.
    - fps (float): The frames per second of the media.
    - progCallback (callable): The callback function for progress updates.
    - failCallback (callable, optional): The callback function for failure events.

    API:
    ----
    - stop(): Stops the video frame request worker.
    - run(): Starts the video frame request worker.
    '''

    def __init__(self,
                 core: 'PrismCore',
                 Player: 'PreviewPlayer_GL',
                 Cache: 'FrameCache',
                 mediaPath: str,
                 frameIdx: int,
                 pWidth: int,
                 fps: float,
                 progCallback: callable,
                 failCallback: callable = None
                 ):
        
        super().__init__()

        self.core = core
        self.mediaPath = mediaPath
        self.frameIdx = int(frameIdx)
        self.Player = Player
        self.Cache = Cache
        self.pWidth = int(pWidth)
        self.fps = float(fps) if fps else 24.0
        self.progCallback = progCallback
        self.failCallback = failCallback

        self._running = True


    @err_catcher(name=__name__)
    def _cacheFallbackFrame(self, reason: str, error: str | None = None, details: str = "") -> bool:
        '''Build and cache a Fallback frame for the requested frame.'''

        info = Utils.getInvalidMediaInfo([self.mediaPath] if self.mediaPath else [], {}, reason=reason)
        infoDetails = info.get("details", "")
        mergedDetails = f"{infoDetails}\n{details}".strip() if details else infoDetails

        img = Utils.buildFallbackImg(
            player=self.Player,
            msg=info.get("message", reason),
            error=error,
            details=mergedDetails,
        )

        if img is None:
            return False

        img = img.astype(np.float32)
        img *= (1.0 / 255.0)
        np.clip(img, -FLOAT16_MAX, FLOAT16_MAX, out=img)
        img = np.ascontiguousarray(img.astype(np.float16, copy=False))

        if self.Cache.cacheFull:
            return False

        self.Cache.setCachedFrame(self.frameIdx, img)
        if self.progCallback:
            self.progCallback(self.frameIdx, firstFrame=False)

        return True


    @err_catcher(name=__name__)
    def stop(self):
        '''Stop Video Frame Request Worker'''

        self._running = False


    @err_catcher(name=__name__)
    def run(self):
        '''Start Video Frame Request Worker'''

        try:
            #   Abort if the worker is not running or the cache is full
            if self._running is False or self.Cache.cacheFull:
                return

            #   Open the media container using PyAV
            container = av.open(self.mediaPath)

            #   Find the first video stream in the container
            stream = None
            for s in container.streams:
                if s.type == "video":
                    stream = s
                    break

            if stream is None:
                logger.warning("No video stream found in media container")
                container.close()
                self._cacheFallbackFrame("No Supported Video Stream")
                return

            #   Set the thread type for the stream to AUTO if possible
            try:
                stream.thread_type = "AUTO"
            except Exception:
                pass

            #   Seek to the approximate position of the requested frame based on the calculated fps
            try:
                target_pts = int((self.frameIdx / self.fps) / float(stream.time_base))
                container.seek(max(0, target_pts), stream=stream, backward=True)
            except Exception:
                pass

            best_img = None
            best_dist = None

            #   Decode frames from the container and find the best match for the requested frame index
            for frame in container.decode(stream):
                if not self._running or self.Cache.cacheFull:
                    container.close()
                    return

                if frame.time is None:
                    continue

                #   Calculate the actual frame index and the distance from the requested frame index
                actual_idx = int(round(frame.time * self.fps))
                dist = abs(actual_idx - self.frameIdx)

                #   Update the best match if this frame is closer to the requested frame index
                if best_dist is None or dist < best_dist:
                    best_dist = dist

                    src_w, src_h = frame.width, frame.height
                    if src_w <= 0 or src_h <= 0:
                        continue

                    #   Calculate the scaling factor and dimensions
                    scale = self.pWidth / float(src_w)
                    dst_w = self.pWidth
                    dst_h = max(1, int(round(src_h * scale)))

                    #   Reformat the frame
                    try:
                        f2 = frame.reformat(
                            width=dst_w,
                            height=dst_h,
                            format="rgba",
                            interpolation="BILINEAR",
                        )
                        img = f2.to_ndarray()

                    except Exception:
                        img = frame.to_ndarray(format="rgba")
                        if img.shape[1] != dst_w or img.shape[0] != dst_h:
                            resized = Utils.resizeNumpyImage(img, dst_w, dst_h)
                            if resized is not None:
                                img = resized

                    #   Flip the image vertically and convert to float32
                    img = np.flipud(img)
                    img = img.astype(np.float32)
                    img *= (1.0 / 255.0)
                    best_img = np.ascontiguousarray(img.astype(np.float16, copy=False))

                #   Stop if passed the requested frame after seeking
                if actual_idx >= self.frameIdx and best_img is not None:
                    break

            container.close()

            if best_img is None:
                logger.warning(f"Unable to decode requested frame {self.frameIdx}")
                if not self._cacheFallbackFrame(
                    "Unable to Decode Video Frame",
                    details=f"Requested Frame: {self.frameIdx}",
                ) and self.failCallback:
                    self.failCallback(self.frameIdx, "Unable to decode requested frame")
                return

            if self.Cache.cacheFull:
                container.close()
                return

            #   Add frame to Cache
            self.Cache.setCachedFrame(self.frameIdx, best_img)

            if self.progCallback:
                self.progCallback(self.frameIdx, firstFrame=False)

        except Exception as e:
            if not self._cacheFallbackFrame("Video Decode Error", error=str(e)) and self.failCallback:
                self.failCallback(self.frameIdx, str(e))



class VideoCacheWorker(QRunnable):
    '''Worker for caching video frames in a separate thread. Handles decoding, scaling, and storing frames in a shared cache.
    
    Args:
    ----
    - core (PrismCore): Prism Core instance
    - Player (PreviewPlayer_GL): Reference to the preview player instance
    - Cache (FrameCache): Reference to shared cache dictionary
    - mediaPath (str): Path to the media file
    - fps (float): Frames per second of the media
    - pWidth (int): Width to scale frames to
    - progCallback (callable): Callback function for progress updates

    API:
    ----
    - stop(): Stops the video cache worker.
    - run(): Starts the video cache worker.
    '''

    def __init__(self,
                 core: 'PrismCore',
                 Player: 'PreviewPlayer_GL',
                 Cache: 'FrameCache',
                 mediaPath: str,
                 fps: float,
                 pWidth: int,
                 progCallback: callable
                 ):
        
        super().__init__()

        self.core = core
        self.Player = Player
        self.Cache = Cache
        self.mediaPath = mediaPath
        self.fps = float(fps) if fps else 24.0
        self.pWidth = pWidth
        self.progCallback = progCallback
        self._running = True


    @err_catcher(name=__name__)
    def _fillFallbackFrames(self):
        '''Fill the cache with a fallback image for all frames in case of failure.'''

        try:
            info = Utils.getInvalidMediaInfo([self.mediaPath] if self.mediaPath else [], {}, reason="Video Decode Failed")
            img = Utils.buildFallbackImg(
                player=self.Player,
                msg=info.get("message", "Video Decode Failed"),
                details=info.get("details", ""),
            )
            if img is None:
                return

            img = img.astype(np.float32)
            img *= (1.0 / 255.0)
            np.clip(img, -FLOAT16_MAX, FLOAT16_MAX, out=img)
            img = np.ascontiguousarray(img.astype(np.float16, copy=False))

            for i in self.Cache._getCachedFramesList():
                self.Cache.setCachedFrame(i, img)

            if self.progCallback:
                self.progCallback(0, firstFrame=True)

        except Exception as fe:
            logger.error(f"Failed to build fallback slide frame: {fe}")


    @err_catcher(name=__name__)
    def stop(self):
        '''Stop Frame Cache Worker'''

        self._running = False


    @err_catcher(name=__name__)
    def run(self):
        '''Start Video Cache Worker'''

        try:
            if not self._running or self.Cache.cacheFull:
                return

            #   Open the media container using FFmpeg (PyAV)
            container = av.open(self.mediaPath)

            #   Find the first video stream in the container
            stream = None
            for s in container.streams:
                if s.type == "video":
                    stream = s
                    break

            #   Ensure a valid video stream was found
            if stream is None:
                logger.warning("No video stream found in media container")
                container.close()
                self._fillFallbackFrames()
                return

            #   Ensure the video stream has a decodable codec
            if (
                not stream.codec_context
                or not stream.codec_context.name
                or stream.codec_context.name.lower() == "none"
            ):
                logger.warning("No decodable video codec found in media stream")
                container.close()
                self._fillFallbackFrames()
                return

            #   Set FFmpeg threading to AUTO if possible
            try:
                stream.thread_type = "AUTO"
            except Exception:
                pass

            firstFrame_signaled = False
            decoded_any = False
            stopped_early = False

            #   Iterate through decoded frames and cache them
            for frame in container.decode(stream):
                #   Stop if not running or cache is full
                if not self._running or self.Cache.cacheFull:
                    stopped_early = True
                    container.close()
                    break

                #   Skip frames with no timestamp information
                if frame.time is None:
                    continue

                #   Calculate the actual frame index based on the timestamp and FPS
                actual_frame_idx = int(round(frame.time * self.fps))

                decoded_any = True

                #   Get source frame dimensions
                src_w = frame.width
                src_h = frame.height

                #   Skip frames with invalid dimensions
                if src_w <= 0 or src_h <= 0:
                    continue

                #   Calculate the scaling factor and destination dimensions
                scale = self.pWidth / float(src_w)
                dst_w = self.pWidth
                dst_h = max(1, int(round(src_h * scale)))

                #   Reformat the frame to the res and format
                try:
                    f2 = frame.reformat(
                        width=dst_w,
                        height=dst_h,
                        format="rgba",
                        interpolation="BILINEAR"
                    )

                    #   Convert to numpy array
                    img = f2.to_ndarray()


                #   Fallback to original frame if reformatting fails
                except Exception:
                    img = frame.to_ndarray(format="rgba")

                    if (
                        img.shape[1] != dst_w
                        or img.shape[0] != dst_h
                    ):
                        resized = Utils.resizeNumpyImage(
                            img,
                            dst_w,
                            dst_h
                        )

                        if resized is not None:
                            img = resized

                #   Flip Vertically
                img = np.flipud(img)

                #   Convert to Float16 Cache Format (0-1 range)
                img = img.astype(np.float32)
                img *= (1.0 / 255.0)
                img = np.ascontiguousarray(img.astype(np.float16, copy=False))

                #   Cache Using Frame Number
                if self.Cache.cacheFull:
                    container.close()
                    return

                if not self.Cache._isCachedFrameReady(actual_frame_idx):
                    self.Cache.setCachedFrame(actual_frame_idx, img)

                #   First frame callback
                if not firstFrame_signaled and self.progCallback:
                    firstFrame_signaled = True

                    self.progCallback(actual_frame_idx, firstFrame=True )

                #   Progress callback
                if self.progCallback:
                    self.progCallback(actual_frame_idx, firstFrame=False)

            if stopped_early:
                return

            if not decoded_any:
                if self._running:
                    self._fillFallbackFrames()
                return

            container.close()

        except Exception as e:
            logger.warning(f"ERROR: Unable to Cache Video File: {self.mediaPath}: {e}")
            self._fillFallbackFrames()



class ImageCacheWorker(QRunnable):
    '''Worker for loading and caching individual image frames in a separate thread.
    
    Args:
    ------
    - core (PrismCore): Prism Core instance
    - Player ('PreviewPlayer_GL'): Reference to the preview player instance
    - Cache ('FrameCache'): Reference to shared cache object
    - imgPath (str): Path to the image file
    - frame_idx (int): Index of the frame
    - pWidth (int): Width to scale frames to
    - progCallback (callable): Callback function for progress updates
    - selectedLayer (str, optional): Selected layer name, if any

    API:
    ----
    - stop(): Stops the image cache worker.
    - run(): Starts the image cache worker.
    '''

    def __init__(self,
                 core: 'PrismCore',
                 Player: 'PreviewPlayer_GL',
                 Cache: 'FrameCache',
                 imgPath: str,
                 frame_idx: int,
                 pWidth: int,
                 progCallback: callable,
                 selectedLayer=None
                 ):
        
        super().__init__()

        self.core = core
        self.Player = Player
        self.Cache = Cache
        self.imgPath = imgPath
        self.frame_idx = frame_idx
        self.pWidth = int(pWidth)
        self.progCallback = progCallback
        self.selectedLayer = selectedLayer

        self._running = True

        self.Oiio = self.core.media.getOIIO()
        self.oiio = self.Oiio



    #######################
    ######    API   #######

    @err_catcher(name=__name__)
    def stop(self):
        '''Stop Frame Cache Worker'''

        self._running = False


    @err_catcher(name=__name__)
    def run(self):
        '''Start Image Cache Worker'''

        try:
            #   Check if the worker should stop early or if the cache is full
            if not self._running or self.Cache.cacheFull:
                return

            #   Open the image using OIIO
            inp = self.Oiio.ImageInput.open(self.imgPath)
            if not inp:
                logger.warning(f"OIIO could not open: {self.imgPath}")
                self._cacheFallbackFrame("Image Decode Failed", error="OIIO could not open file")
                return

            #   Retrieve the image specification and channel names
            spec = inp.spec()
            channels = spec.channelnames
            img_np = None

            #   If a specific layer is selected, iterate through subimages to find it
            if self.selectedLayer:
                subimage = 0
                while inp.seek_subimage(subimage, 0):
                    if self.Cache.cacheFull or not self._running:
                        inp.close()
                        return

                    #   Find the selected layer within the current subimage
                    spec = inp.spec()
                    readFormat = self._getReadFormatForSpec(spec)
                    channels = spec.channelnames
                    channelIndices = {name: i for i, name in enumerate(channels)}

                    selectedChannels = self._getLayerChannels(channels, self.selectedLayer)

                    #   If the selected channels are found
                    if selectedChannels:
                        try:
                            #   If there are at least 3 selected channels, read them as a group
                            if len(selectedChannels) >= 3:
                                chbegin = channelIndices[selectedChannels[0]]
                                channelCount = len(selectedChannels)
                                chend = channelIndices[selectedChannels[channelCount - 1]] + 1

                                img = inp.read_image(
                                    subimage=subimage,
                                    miplevel=0,
                                    chbegin=chbegin,
                                    chend=chend,
                                    format=readFormat
                                )

                                if img is not None:
                                    img_np = np.asarray(img).reshape(
                                        spec.height,
                                        spec.width,
                                        channelCount
                                    )
                                    break

                            #   Otherwise read the single selected channel
                            else:
                                chidx = channelIndices[selectedChannels[0]]

                                img = inp.read_image(
                                    subimage=subimage,
                                    miplevel=0,
                                    chbegin=chidx,
                                    chend=chidx + 1,
                                    format=readFormat
                                )

                                if img is not None:
                                    img_np = np.asarray(img).reshape(
                                        spec.height,
                                        spec.width,
                                        1
                                    )
                                    break

                        except Exception:
                            pass

                    subimage += 1

                #   Reset to the first subimage after searching for the selected layer
                inp.seek_subimage(0, 0)
                spec = inp.spec()

            #   If no specific layer was selected or found, read the entire image
            if img_np is None:
                readFormat = self._getReadFormatForSpec(spec)
                img = inp.read_image(format=readFormat)

                if img is None:
                    logger.warning(f"OIIO returned no pixels for image: {self.imgPath}")
                    self._cacheFallbackFrame("Image Decode Failed", error="OIIO returned no pixels")
                    return

                img_np = np.asarray(img).reshape(
                    spec.height,
                    spec.width,
                    spec.nchannels
                )

            inp.close()

            #   Determine the number of channels in the image
            channels = img_np.shape[-1]

            #   If the image has only one channel, copy it to create a 3 channel RGB
            if channels == 1:
                img_np = np.repeat(img_np, 3, axis=-1)
                channels = 3

            #   If the image has 3 channels, add an alpha channel to make it RGBA
            if channels == 3:
                alpha = np.ones(
                    (
                        img_np.shape[0],
                        img_np.shape[1],
                        1
                    ),
                    dtype=img_np.dtype
                )

                img_np = np.concatenate(
                    (img_np, alpha),
                    axis=-1
                )

            #   If the image has more than 4 channels, keep only the first 4 (RGBA)
            elif channels > 4:
                img_np = img_np[..., :4]

            #   Resize the image to fit the preview width while maintaining aspect ratio
            src_w, src_h = spec.width, spec.height
            scale = self.pWidth / float(src_w)
            dst_w, dst_h = self.pWidth, max(1, int(round(src_h * scale)))

            if (dst_w, dst_h) != (src_w, src_h):
                resized = Utils.resizeNumpyImage(img_np, dst_w, dst_h)

                if resized is not None:
                    img_np = resized

            #   Flip the image vertically
            img_np = np.flipud(img_np)

            #   Clamp Image to Float16
            np.clip(img_np, -FLOAT16_MAX, FLOAT16_MAX, out=img_np)

            #   Convert to Float16
            img_np = np.ascontiguousarray(img_np.astype(np.float16, copy=False))

            #   Save to Cache
            if not self.Cache.cacheFull:
                self.Cache.setCachedFrame(self.frame_idx, img_np)

            if self.progCallback:
                self.progCallback(self.frame_idx, firstFrame=(self.frame_idx == 0))

        except Exception as e:
            logger.warning(f"ERROR: Unable to Cache Image {self.imgPath}: {e}")
            if not self._cacheFallbackFrame("Image Decode Error", error=str(e)):
                logger.error("Failed to build fallback slide frame for image decode error")



    ###########################
    ######   INTERNAL   #######

    @err_catcher(name=__name__)
    def _getLayerChannels(self, channels: list, layerName: str) -> list | None:
        '''Retrieves the relevant channels for the specified layer name from the list of channels.

        Args:
            channels (list): List of channel names.
            layerName (str): Name of the layer to retrieve channels for.

        Returns:
            list | None: List of channel names corresponding to the layer, or None if not found.
        '''

        if not layerName:
            return None

        #   Get lowercase names
        lowerChannels = [c.lower() for c in channels]
        lowerLayer = layerName.lower().strip()

        #   Exact Channel Selection (single-channel passes like Z, Mist.Z, etc).
        for idx, c in enumerate(lowerChannels):
            if c == lowerLayer:
                return [channels[idx]]

        #   Typical OIIO layout uses "layer.R", "layer.G", "layer.B"
        prefix = lowerLayer + "."
        prefixed = [channels[i] for i, c in enumerate(lowerChannels) if c.startswith(prefix)]
        prefixedRgb = [c for c in prefixed if not c.lower().endswith(".a")]
        prefixedAlpha = [c for c in prefixed if c.lower().endswith(".a")]
        if len(prefixedRgb) >= 3:
            if lowerLayer == "rgba" and prefixedAlpha:
                return prefixedRgb[:3] + [prefixedAlpha[0]]

            return prefixedRgb[:3]

        #   Single-channel layer prefix fallback (e.g. Mist.Z -> Mist in combobox).
        if prefixed:
            return [prefixed[0]]

        #   Handle common flat channel names for RGB/RGBA selections.
        if lowerLayer in ["rgb", "rgba"]:
            rgbMap = {}
            alphaChannel = None
            for original, lower in zip(channels, lowerChannels):
                if lower.endswith(".r") or lower == "r":
                    rgbMap["r"] = original
                elif lower.endswith(".g") or lower == "g":
                    rgbMap["g"] = original
                elif lower.endswith(".b") or lower == "b":
                    rgbMap["b"] = original
                elif lower.endswith(".a") or lower == "a":
                    alphaChannel = original

            #   Return RGB/RGBA channels if available
            if len(rgbMap) == 3:
                if lowerLayer == "rgba" and alphaChannel:
                    return [rgbMap["r"], rgbMap["g"], rgbMap["b"], alphaChannel]

                return [rgbMap["r"], rgbMap["g"], rgbMap["b"]]

        return None


    @err_catcher(name=__name__)
    def _isHalfFormat(self, formatDesc: Any) -> bool:
        '''Returns whether an OIIO channel format descriptor represents half float.

        Args:
            formatDesc (Any): OIIO channel format descriptor.

        Returns:
            bool: True if the format represents half float, False otherwise.
        '''

        if formatDesc is None:
            return False

        try:
            formatName = str(formatDesc).lower()
            if "half" in formatName or "float16" in formatName:
                return True
        except Exception:
            pass

        try:
            baseType = getattr(formatDesc, "basetype", None)
            if baseType is not None:
                baseName = str(baseType).lower()
                if "half" in baseName or "float16" in baseName:
                    return True
        except Exception:
            pass

        return False


    @err_catcher(name=__name__)
    def _getReadFormatForSpec(self, spec: Any) -> Any:
        '''Returns OIIO read format for a spec.  Uses HALF when source is half float; otherwise FLOAT.

        Args:
            spec (Any): OIIO image specification.

        Returns:
            Any: OIIO read format (HALF or FLOAT).
        '''

        try:
            oiioHalf = getattr(self.Oiio, "HALF", None)
            if oiioHalf is None:
                return self.Oiio.FLOAT

            channelFormats = getattr(spec, "channelformats", None)
            if channelFormats:
                formats = [f for f in channelFormats if f is not None]
                if formats and all(self._isHalfFormat(f) for f in formats):
                    return oiioHalf

            specFormat = getattr(spec, "format", None)
            if self._isHalfFormat(specFormat):
                return oiioHalf

        except Exception:
            pass

        return self.Oiio.FLOAT


    @err_catcher(name=__name__)
    def _cacheFallbackFrame(self, reason: str, error: str | None = None, details: str = "") -> bool:
        '''Build and cache a Fallback frame for image decode failures.'''

        info = Utils.getInvalidMediaInfo([self.imgPath] if self.imgPath else [], {}, reason=reason)
        infoDetails = info.get("details", "")
        mergedDetails = f"{infoDetails}\n{details}".strip() if details else infoDetails

        img = Utils.buildFallbackImg(
            player=self.Player,
            msg=info.get("message", reason),
            error=error,
            details=mergedDetails,
        )

        if img is None:
            return False

        img = img.astype(np.float32)
        img *= (1.0 / 255.0)
        np.clip(img, -FLOAT16_MAX, FLOAT16_MAX, out=img)
        img = np.ascontiguousarray(img.astype(np.float16, copy=False))

        if self.Cache.cacheFull:
            return False

        self.Cache.setCachedFrame(self.frame_idx, img)
        if self.progCallback:
            self.progCallback(self.frame_idx, firstFrame=(self.frame_idx == 0))

        return True




# ################################################
# #################    PRESETS    ################

@dataclass
class PresetModel:
    '''Holds Preset Data'''
    name: str
    data: dict



class PresetsCollection:
    '''Holds all Preset Models
    
    Args:
    ------
    - pType (str): The type of presets this collection holds ("ocio")

    API:
    ----
    - clear(): Clears all presets.
    - addPreset(name: str, data: dict): Adds a new preset or updates an existing one.
    - removePreset(presetName: str) -> bool: Removes a preset by name.
    - getHeaders() -> list[str]: Returns table headers for the presets.
    - getNumberPresets() -> int: Returns the number of presets.
    - getAllPresets() -> list[PresetModel]: Returns a list of all preset models.
    - getOrderedPresets() -> list[PresetModel]: Returns presets in the project order.
    - getPresetNames() -> list[str]: Returns a list of all preset names.
    - getOrderedPresetNames() -> list[str]: Returns a list of ordered preset names.
    - getPresetData(presetName: str) -> dict: Returns the data for a specific preset.
    - getTooltip() -> str: Returns an HTML tooltip with each preset listed.
    - setCurrPreset(presetName: str): Sets the current preset.
    - getCurrPreset() -> Optional[str]: Returns the current preset.
    '''

    def __init__(self, pType:str):
        self.pType = pType
        self.presets: list[PresetModel] = []
        self.currentPreset: Optional[str] = None
        self.presetOrder: list[str] = []


    @err_catcher(name=__name__)
    def clear(self):
        '''Clears all presets'''

        self.presets.clear()
        self.presetOrder.clear()


    @err_catcher(name=__name__)
    def addPreset(self, name: str, data: dict):
        '''Creates PresetModel
        
        Args:
            name (str): The name of the preset.
            data (dict): The data associated with the preset.
        '''

        #   Overwrite Data if Already Exists
        for preset in self.presets:
            if preset.name == name:
                preset.data = data
                return
        #   If Not, Add New
        self.presets.append(PresetModel(name, data))

        
    @err_catcher(name=__name__)
    def removePreset(self, presetName: str) -> bool:
        '''Removes a Preset by Name. Returns True if removed.
        
        Args:
            presetName (str): The name of the preset to remove.
        
        Returns:
            bool: True if the preset was removed, False otherwise.
        '''

        removed = [p for p in self.presets if p.name != presetName]
        if len(removed) != len(self.presets):
            self.presets = removed
            if presetName in self.presetOrder:
                self.presetOrder.remove(presetName)
            return True
        return False
    

    @err_catcher(name=__name__)
    def getHeaders(self) -> list[str]:
        '''Returns Table Headers: "Name" + keys from first preset data
        
        Returns:
            list[str]: A list of table header names.
        '''

        #   Fallback if no Presets Exist
        if not self.presets:
            return ["Name", "Description", "Color_Space",
                   "Display", "View", "Look", "LUT"]
        
        
        return ["Name"] + list(self.presets[0].data.keys())
    

    @err_catcher(name=__name__)
    def getNumberPresets(self) -> int:
        '''Returns the Number of Presets
        
        Returns:
            int: The number of presets.
        '''

        return len(self.getPresetNames())


    @err_catcher(name=__name__)
    def getAllPresets(self) -> list[PresetModel]:
        '''Returns List of PresetModels
        
        Returns:
            list[PresetModel]: A list of all preset models.
        '''

        return self.presets


    @err_catcher(name=__name__)
    def getOrderedPresets(self) -> list[PresetModel]:
        '''Returns Presets in the Project Order

        Returns:
            list[PresetModel]: A list of preset models in the project order.
        '''

        preset_map = {p.name: p for p in self.presets}
        ordered = [preset_map[name] for name in self.presetOrder if name in preset_map]

        #   Add Presets Not in presetOrder
        missing = sorted(set(preset_map.keys()) - set(self.presetOrder))
        for name in missing:
            ordered.append(preset_map[name])
            self.presetOrder.append(name)

        return ordered
    

    @err_catcher(name=__name__)
    def getPresetNames(self) -> list[str]:
        '''Returns List of All Preset Names
        
        Returns:
            list[str]: A list of all preset names.
        '''

        return [preset.name for preset in self.presets]
    
    
    @err_catcher(name=__name__)
    def getOrderedPresetNames(self) -> list[str]:
        '''Returns List of Ordered Preset Names
        
        Returns:
            list[str]: A list of ordered preset names.
        '''
        
        return [preset.name for preset in self.getOrderedPresets()]
    

    @err_catcher(name=__name__)
    def getPresetData(self, presetName: str) -> dict:
        '''Returns Preset Data for a Preset Name
        
        Args:
            presetName (str): The name of the preset.
        
        Returns:
            dict: The data dictionary for the specified preset, or an empty dictionary if not found.
        '''

        for preset in self.presets:
            if preset.name == presetName:
                return preset.data
        return {}


    @err_catcher(name=__name__)
    def getTooltip(self) -> str:
        '''Returns HTML Tooltip with Each Preset Listed
        
        Returns:
            str: The HTML string representing the tooltip with each preset listed.
        '''

        try:
            #   Start HTML with div wrapper
            tooltip_html = "<div style='min-width: 400px;'>"
            tooltip_html += "<table>"

            for preset in self.getOrderedPresets():
                desc = preset.data.get("Description", "")
                tooltip_html += f"""
                    <tr>
                        <td style="white-space: nowrap;"><b>{preset.name}</b></td>
                        <td style="padding-left: 10px; white-space: nowrap;">{desc}</td>
                    </tr>
                    <tr><td colspan='2' style='height: 10px;'>&nbsp;</td></tr>  <!-- spacer row -->
                """

            tooltip_html += "</table></div>"
            return tooltip_html
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Presets Tooltip:\n{e}")
            return ""
        

    @err_catcher(name=__name__)
    def setCurrPreset(self, presetName: str):
        '''Sets Current Preset
        
        Args:
            presetName (str): The name of the preset to set as current.
        '''

        if presetName in self.getPresetNames():
            self.currentPreset = presetName

        else:
            logger.warning(f"Preset '{presetName}' does not exist.")
        

    @err_catcher(name=__name__)
    def getCurrPreset(self) -> Optional[str]:
        '''Returns Current Preset
        
        Returns:
            Optional[str]: The name of the current preset, or None if no preset is set.
        '''

        return self.currentPreset



#################################################
###############    OCIO    ######################

class OcioTransforms():
    '''Object to Hold OCIO Config Transforms
    
    Args:
    ------
    - core (PrismCore): The Prism Core object.
    - ocioConfig (Any): The OCIO configuration object.

    API:
    ----
    - getColorSpaces() -> list: Returns a list of all color space names.
    - getInputColorSpaces() -> list: Returns a list of input color space names.
    - getDisplays() -> list: Returns a list of all display names.
    - getViews(display: str = None) -> list: Returns a list of view names for a given display or all views if display is None.
    - getLooks() -> list: Returns a list of all look names.
    - getLooksForDisplayView(display: str, view: str) -> list: Returns a list of look names used by the specified display/view.
    - getAllTransforms() -> dict: Returns a dictionary containing lists of color spaces, displays, and looks.
    - getAllTransforms_flat() -> list: Returns a flat list of all transforms in the config, grouped with dummy header items for each type.
    '''

    def __init__(self, core, ocioConfig: Any):
        self.core = core
        self.ocioConfig = ocioConfig


    @err_catcher(name=__name__)
    def getColorSpaces(self) -> list:
        '''Return a List of all Color Space Names.
        
        Returns:
            list: A list of all color space names.
        '''

        return [cs.getName() for cs in self.ocioConfig.getColorSpaces()]


    @err_catcher(name=__name__)
    def getInputColorSpaces(self) -> list:
        '''Return Only Input Color Spaces (role-based)
        
        Returns:
            list: A list of input color space names.
        '''

        return [
            cs.getName()
            for cs in self.ocioConfig.getColorSpaces()
            if cs.getFamily().lower() == "input" or "input" in cs.getName().lower()
            ]


    @err_catcher(name=__name__)
    def getDisplays(self) -> list:
        '''Return all Display Names.
        
        Returns:
            list: A list of all display names.
        '''

        return list(self.ocioConfig.getDisplays())


    @err_catcher(name=__name__)
    def getViews(self, display:str = None) -> list:
        '''Return all Views for a Given Display, or All Views if Display is None.
        
        Args:
            display (str, optional): The display name. If None, returns all views across all displays.
        
        Returns:
            list: A list of view names.
        '''

        if display:
            return list(self.ocioConfig.getViews(display))
        else:
            # flatten all views across all displays
            views = []
            for d in self.ocioConfig.getDisplays():
                views.extend(self.ocioConfig.getViews(d))

            return list(set(views))


    @err_catcher(name=__name__)
    def getLooks(self) -> list:
        '''Return all Looks.
        
        Returns:
            list: A list of look names.
        '''

        return [lk.getName() for lk in self.ocioConfig.getLooks()]


    @err_catcher(name=__name__)
    def getLooksForDisplayView(self, display:str, view:str) -> list:
        '''Return Looks Used by a Given Display/View, if Defined.
        
        Args:
            display (str): The display name.
            view (str): The view name.
        
        Returns:
            list: A list of look names used by the specified display/view, or an empty list if none are defined.
        '''

        viewType = self.ocioConfig.getView(display, view)
        looks = viewType.getLooks() if viewType else ""
        if looks:
            return [lk.strip() for lk in looks.split(",")]
        
        return []


    @err_catcher(name=__name__)
    def getAllTransforms(self) -> dict:
        '''Return All Transforms Defined in the Config.
        
        Returns:
            dict: A dictionary containing lists of color spaces, displays, and looks.
        '''

        transforms = {
            "colorSpaces": self.getColorSpaces(),
            "displays": self.getDisplays(),
            "looks": self.getLooks(),
        }
        return transforms
    

    @err_catcher(name=__name__)
    def getAllTransforms_flat(self) -> list:
        '''Get a Flat List of All transforms in the Config grouped with Dummy Header Items for Each Type.

        Returns:
            list: A flat list of all transforms in the config, grouped with dummy header items for each type.
        '''

        transforms = []

        #   Color Spaces
        transforms.append("** Color Spaces **")
        for cs in self.ocioConfig.getColorSpaces():
            transforms.append(str(cs.getName()))

        #   Displays + Views
        transforms.append("** Displays / Views **")
        for display in self.ocioConfig.getDisplays():
            for view in self.ocioConfig.getViews(display):
                transforms.append(f"{display} / {view}")

        #   Looks
        transforms.append("** Looks **")
        for look in self.ocioConfig.getLooks():
            transforms.append(str(look.getName()))

        return transforms



class OcioPresetsEditor(QDialog):
    '''Editor for OCIO Presets within the Preview Player.
    
    Args:
    ------
    - core (PrismCore): The Prism Core instance.
    - Player (PreviewPlayer_GL): The preview player instance.

    API:
    ----
    - showEvent(event: QShowEvent): Handles the show event for the dialog.
    - getPresets() -> list: Returns a list of all OCIO presets.
    - result() -> str: Returns the result of the dialog, "Save" or "Cancel".
    - closeEvent(event: QCloseEvent): Handles the close event for the dialog.
    '''

    def __init__(self, core: 'PrismCore', Player: 'PreviewPlayer_GL'):
        super().__init__(Player)

        self.core = core
        self.Player = Player

        self.OcioModule = self.Player.OcioModule
        self.OcioPresets = self.Player.OcioPresets

        presetDir = Utils.getProjectPresetDir(self.core, "ocio")
        Utils.loadPresets(presetDir, self.OcioPresets, ".o_preset")

        self._editingRow = None
        self._action = None

        self.editorStyle = """
                QLineEdit, QComboBox {
                    background-color: #353F4E;
                    selection-background-color: #353F4E;
                    selection-color: #353F4E;
                }
                """
        
        self.setWindowTitle("OCIO Preset Editor")

        self._setupUI()
        self._connectEvents()
        self._getOcioTransforms()
        self._populateTable()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        logger.debug("Loaded OCIO Presets Editor")


    ##########################
    ########    UI    ########

    @err_catcher(name=__name__)
    def _setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1700, min(2500, calc_width))
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Create table
        self.headers = self.OcioPresets.getHeaders()
        rows = self.OcioPresets.getNumberPresets()
        self.tw_presets = QTableWidget(rows, len(self.headers), self)
        self.tw_presets.setHorizontalHeaderLabels(self.headers)
        self.tw_presets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_presets.setSelectionBehavior(QTableWidget.SelectRows)
        self.tw_presets.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tw_presets.setShowGrid(False)
        self.tw_presets.setStyleSheet("""
            QTableView::item {
                border-right: 1px solid grey;
            }
        """)

        #   Footer Buttons
        lo_buttonBox    = QHBoxLayout()
        self.b_moveup   = QPushButton("Move Up")
        self.b_moveDn   = QPushButton("Move Down")
        self.b_test     = QPushButton("Validate Preset")
        self.b_save     = QPushButton("Save")
        self.b_cancel   = QPushButton("Cancel")

        for button in (self.b_moveup, self.b_moveDn, self.b_test, self.b_save, self.b_cancel):
            button.setAutoDefault(False)
            button.setDefault(False)

        lo_buttonBox.addWidget(self.b_moveup)
        lo_buttonBox.addWidget(self.b_moveDn)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_test)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_save)
        lo_buttonBox.addWidget(self.b_cancel)

        #   Add to Main Layout
        lo_main.addWidget(self.tw_presets)
        lo_main.addLayout(lo_buttonBox)

        #   Stretch Columns over Entire Width
        self.tw_presets.horizontalHeader().setStretchLastSection(False)
        self.tw_presets.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        ##   ToolTips
        tip = """
        Run a quick test on the Preset to validate.

        This will check various points such as:
        - Acceptable Preset Name
        - Transforms are in the Current OCIO Config
        - View and Look are in the Applicable Display
        - Selected Lut exists
        """
        self.b_test.setToolTip(tip)

        self.b_moveup.setToolTip("Move Selected Preset Up One Row")
        self.b_moveDn.setToolTip("Move Selected Preset Down One Row")
        self.b_save.setToolTip("Save Changes and Close Window")
        self.b_cancel.setToolTip("Discard Changes and Close Window")


    #   Make Signal Connections
    @err_catcher(name=__name__)
    def _connectEvents(self):
        self.tw_presets.customContextMenuRequested.connect(lambda x: self._rclList(x, self.tw_presets))
        self.tw_presets.itemSelectionChanged.connect(self._onRowChanged)

        self.b_test.clicked.connect(self._onValidate)
        self.b_moveup.clicked.connect(self._onMoveUp)
        self.b_moveDn.clicked.connect(self._onMoveDown)
        self.b_save.clicked.connect(lambda: self._onFinish("Save"))
        self.b_cancel.clicked.connect(lambda: self._onFinish("Cancel"))


    @err_catcher(name=__name__)
    def _rclList(self, pos: QPoint, lw: QListWidget):
        '''Display the right-click context menu.

        Args:
            pos (QPoint): The position where the context menu should appear.
            lw (QListWidget): The list widget for which the context menu is being displayed.
        '''

        cpos = QCursor.pos()
        item = lw.itemAt(pos)

        rcmenu = QMenu(self)

        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action

        #   If Called from Item
        if item:
            row = item.row()
            nameItem = self.tw_presets.item(row, 0)

            Utils.createMenuAction("Edit Preset", rcmenu, self, lambda: self._editPreset(item=nameItem))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Save Preset to User Presets Directory", rcmenu, self, lambda: self._saveToLocal(item=nameItem))
            Utils.createMenuAction("Export Preset to File", rcmenu, self, lambda: self._exportPreset(item=nameItem))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Delete Preset", rcmenu, self, lambda: self._deletePreset(item=nameItem))

            rcmenu.addAction(_separator())

        #   Always Displayed
        Utils.createMenuAction("Create New Preset", rcmenu, self, lambda: self._editPreset(addNew=True))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Import Preset from User Presets Directory", rcmenu, self, lambda: self._importPreset(local=True))
        Utils.createMenuAction("Import Preset from File", rcmenu, self, lambda: self._importPreset())

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Open Project Presets Directory", rcmenu, self, lambda: self._openPresetsDir(project=True))
        Utils.createMenuAction("Open User Presets Directory", rcmenu, self, lambda: self._openPresetsDir(project=False))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    @err_catcher(name=__name__)
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        '''Filter events for the dialog.

        Args:
            obj (QObject): The object receiving the event.
            event (QEvent): The event instance.

        Returns:
            bool: True if the event is handled, False otherwise.
        '''

        #   If no row is currently being edited, pass the event to the default handler
        if self._editingRow is None:
            return super().eventFilter(obj, event)

        eventType = event.type()

        if eventType == QEvent.MouseButtonPress:
            #   Get the global position of the mouse event
            globalPos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            keepEditing = False

            #   Check if the mouse event occurred within the viewport of the presets table
            viewport = self.tw_presets.viewport()
            localPos = viewport.mapFromGlobal(globalPos)
            if viewport.rect().contains(localPos):
                index = self.tw_presets.indexAt(localPos)
                keepEditing = index.isValid() and index.row() == self._editingRow

            #   If the mouse event did not occur within the viewport or the index is not valid, keepEditing remains False
            if not keepEditing:
                popupWidget = QApplication.activePopupWidget()
                modalWidget = QApplication.activeModalWidget()
                widget = QApplication.widgetAt(globalPos)
                keepEditing = (
                    (popupWidget is not None and popupWidget is not self)
                    or (modalWidget is not None and modalWidget is not self)
                    or self._widgetBelongsToEditingRow(widget)
                )

            #   If mouse click occurred outside the editing row, commit the active row edits
            if not keepEditing:
                self._commitActiveRowEdits()

        return super().eventFilter(obj, event)


    @err_catcher(name=__name__)
    def keyPressEvent(self, event: QKeyEvent):
        '''Handle key press events for the dialog.

        Args:
            event (QKeyEvent): The key event instance.
        '''

        #   Handle key press to commit edits for the active row
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._editingRow is not None and self._widgetBelongsToEditingRow(QApplication.focusWidget()):
                self._commitActiveRowEdits()

            event.accept()
            return

        super().keyPressEvent(event)


    @err_catcher(name=__name__)
    def _adjustColumnWidths(self):
        '''Adjust the column widths of the presets table based on the viewport width and column weights.'''

        total_width = self.tw_presets.viewport().width()

        #   Column weights (column index: weight)
        weights = {
            0: 1.0,  # Name
            1: 2.0,  # Description
            2: 1.5,  # Color Space
            3: 1.5,  # Display
            4: 1.5,  # View
            5: 1.5,  # Look
            6: 2.0   # Luts
        }

        total_weight = sum(weights.values())
        #   Iterate and Set Widths
        for col in range(self.tw_presets.columnCount()):
            weight = weights.get(col, 1)
            col_width = int((weight / total_weight) * total_width)
            self.tw_presets.setColumnWidth(col, col_width)


    @err_catcher(name=__name__)
    def _populateTable(self):
        '''Populate the presets table with the current OCIO presets.'''

        try:
            #   Clear Table
            self.tw_presets.setRowCount(0)
            #   Add Each Preset
            for preset in self.OcioPresets.getOrderedPresets():
                row = self.tw_presets.rowCount()
                self.tw_presets.insertRow(row)
                self.tw_presets.setItem(row, 0, QTableWidgetItem(preset.name))
                
                for col, key in enumerate(self.headers[1:], start=1):
                    value = preset.data.get(key, "")

                    #   If LUT, display only the base filename and set the full path as a tooltip
                    if key == "LUT":
                        baseFilename = os.path.basename(value) if value else ""
                        item = QTableWidgetItem(baseFilename)
                        item.setToolTip(value)

                    #   All others just set value
                    else:
                        item = QTableWidgetItem(str(value))
                        item.setToolTip(value)

                    self.tw_presets.setItem(row, col, item)
                    #   Re-Apply Widths
                    QTimer.singleShot(0, self._adjustColumnWidths)
                    
        except Exception as e:
            logger.warning(f"ERROR: Failed to Populate OCIO Presets Table:\n{e}")


    ###########################
    ########    API    ########

    @err_catcher(name=__name__)
    def showEvent(self, event: QShowEvent):
        '''Handle the Qt show event for the window.
        
        Args:
            event (QShowEvent): The show event.
        '''

        super().showEvent(event)
        QTimer.singleShot(0, self._adjustColumnWidths)


    @err_catcher(name=__name__)
    def getPresets(self) -> tuple[list[PresetModel], list[str]]:
        '''Get the current list of presets and their order.

        Returns:
            tuple[list[PresetModel], list[str]]: A tuple containing the list of presets and their order.
        '''

        return self.presetData, self.presetOrder


    @err_catcher(name=__name__)
    def result(self) -> str:
        '''Get the result of the last action performed.

        Returns:
            str: The result of the last action.
        '''
        
        return self._action


    @err_catcher(name=__name__)
    def closeEvent(self, event: QCloseEvent):
        '''Handle the close event for the dialog.
        
        Args:
            event (QCloseEvent): The close event instance.
        '''

        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

        super().closeEvent(event)



    ################################
    ########    INTERNAL    ########

    @err_catcher(name=__name__)
    def _openPresetsDir(self, project:bool=True):
        '''Open the presets directory in the file explorer.

        Args:
            project (bool): If True, open the project-specific presets directory; otherwise, open the local presets directory.
        '''

        if project:
            presetDir = Utils.getProjectPresetDir(self.core, "ocio")
        else:
            presetDir = Utils.getLocalPresetDir(self.core, "ocio")

        self.core.openFolder(presetDir)


    @err_catcher(name=__name__)
    def _importPreset(self, local:bool=False):
        '''Import an OCIO preset from a file.

        Args:
            local (bool): If True, import the preset from the local presets directory; otherwise, import from the project-specific presets directory.
        '''

        try:
            importData = Utils.importPreset(self.core, "ocio", local=local)

            if importData:
                presetName = importData["name"]
                self.OcioPresets.addPreset(presetName, importData["data"])

                self._populateTable()
                logger.debug(f"Imported Preset '{presetName}'")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Import Preset: {e}")


    @err_catcher(name=__name__)
    def _exportPreset(self, item:QTableWidgetItem):
        '''Export the selected OCIO preset to a file.

        Args:
            item (QTableWidgetItem): The table item representing the preset to export.
        '''

        try:
            #   Get Preset Name and Data
            pName = item.text()
            pData = self.OcioPresets.getPresetData(item.text())

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return

        Utils.exportPreset(self.core, "ocio", pName, pData)
        logger.debug(f"Exported Preset {pName}")


    @err_catcher(name=__name__)
    def _saveToLocal(self, item:QTableWidgetItem):
        '''Save the selected OCIO preset to the local user presets directory.

        Args:
            item (QTableWidgetItem): The table item representing the preset to save.
        '''

        try:
            pName = item.text()
            currData = self.OcioPresets.getPresetData(pName)

            pData = {"name": pName,
                     "data": currData}

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return
        
        Utils.savePreset(self.core, "ocio", pName, pData, project=False)


    @err_catcher(name=__name__)
    def _editPreset(self, addNew:bool=False, item:QTableWidgetItem=None):
        '''Edit the selected OCIO preset or add a new one.

        Args:
            addNew (bool): If True, add a new preset row; otherwise, edit the selected preset.
            item (QTableWidgetItem, optional): The table item representing the preset to edit. Defaults to None.
        '''

        #   Determine the row to edit based on the provided item or the currently selected row in the table
        row = item.row() if item is not None else self.tw_presets.currentRow()

        #   If no row is selected, default to the last row
        if self._editingRow is not None:
            if addNew or self._editingRow != row:
                self._commitActiveRowEdits()
            else:
                return

        if addNew:
            #   Create New Empty Row
            if row < 0:
                row = self.tw_presets.rowCount()
            else:
                row += 1

            #   Insert the new row into the table
            self.tw_presets.insertRow(row)

            for col in range(self.tw_presets.columnCount()):
                self.tw_presets.setItem(row, col, QTableWidgetItem(""))

            #   Select the newly inserted row
            self.tw_presets.selectRow(row)

        if row < 0:
            return

        #   Change Row Cells to Editable Widgets
        headers = self.headers

        for col, key in enumerate(headers):
            match key:
                case "Name":
                    editor = QLineEdit()
                    editor.setPlaceholderText("Enter Preset Name")
                    editor.setText(self.tw_presets.item(row, col).text() if self.tw_presets.item(row, col) else "")
                    editor.setStyleSheet(self.editorStyle)
                    self.tw_presets.setCellWidget(row, col, editor)

                case "Description":
                    editor = QLineEdit()
                    editor.setPlaceholderText("Enter Short Description")
                    editor.setText(self.tw_presets.item(row, col).text() if self.tw_presets.item(row, col) else "")
                    editor.setStyleSheet(self.editorStyle)
                    self.tw_presets.setCellWidget(row, col, editor)

                case "Color_Space":
                    transformItems = self.OcioTransforms.getColorSpaces()
                    self._createComboCell(row, col, transformItems)

                case "Display":
                    transformItems = self.OcioTransforms.getDisplays()
                    self._createComboCell(row, col, transformItems)

                case "View":
                    transformItems = self.OcioTransforms.getViews()
                    self._createComboCell(row, col, transformItems)

                case "Look":
                    transformItems = self.OcioTransforms.getLooks()
                    self._createComboCell(row, col, transformItems)

                case "LUT":
                    lutFilename = self.tw_presets.item(row, col).text() if self.tw_presets.item(row, col) else ""
                    lutFilePath = self.tw_presets.item(row, col).toolTip() if self.tw_presets.item(row, col) else ""
                    self._createLutCell(row, col, lutFilename, lutFilePath)

                case _:
                    #   Fallback: Leave as Text
                    item = self.tw_presets.item(row, col)
                    if not item:
                        item = QTableWidgetItem("")
                        self.tw_presets.setItem(row, col, item)

        self._editingRow = row


    @err_catcher(name=__name__)
    def _deletePreset(self, item:QTableWidgetItem):
        '''Deletes the selected preset after user confirmation.

        Args:
            item (QTableWidgetItem): The table item representing the preset to delete.
        '''

        row = item.row()

        #   Get Selected Preset Name
        presetItem = self.tw_presets.item(row, 0)
        presetName = presetItem.text() if presetItem else "Unknown"

        #   Confirmation Dialogue
        title = "Delete Preset"
        text = f"Would you like to remove the Preset:\n\n{presetName}"
        buttons = ["Remove", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Remove":
            self.tw_presets.removeRow(row)
            Utils.deletePreset(self.core, "ocio", presetName)
            self.OcioPresets.removePreset(presetName)


    @err_catcher(name=__name__)
    def _getOcioTransforms(self):
        '''Retrieve and create the OCIO Transforms data object.'''

        if self.OcioModule is None:
            self.ocioConfig = None
            self.OcioTransforms = None
            logger.warning("PyOpenColorIO is not available. Cannot build OCIO transform lists.")
            return

        self.ocioConfig = self.OcioModule.GetCurrentConfig()
        self.OcioTransforms = OcioTransforms(self.core, self.ocioConfig)


    @err_catcher(name=__name__)
    def _createComboCell(self, row:int, col:int, items:list):
        '''Creates a combo box cell for the given row and column with the provided items.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.
            items (list): The list of items to populate the combo box with.
        '''

        editor = QComboBox()
        editor.setStyleSheet(self.editorStyle)

        #   Add Empty String at the Top
        editor.addItem("")

        #   Add Items and Handle Header-Style Entries
        for item in items:
            text = str(item)
            editor.addItem(text)
            if text.startswith("**"):
                idx = editor.count() - 1
                editor.setItemData(idx, 0, Qt.UserRole - 1)
                editor.setItemData(idx, QFont("Arial", weight=QFont.Bold), Qt.FontRole)

        #   Auto-expand Popup Width to Fit Longest Item
        font_metrics = editor.fontMetrics()
        max_width = max(font_metrics.horizontalAdvance(editor.itemText(i)) for i in range(editor.count())) + 50
        editor.view().setMinimumWidth(max_width)

        #   Get Current Cell Value
        current_value = self.tw_presets.item(row, col).text() if self.tw_presets.item(row, col) else ""

        #   Match Current Value in Combo
        idx = editor.findText(current_value)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            #   If Value Not in the list, Add it Temporarily
            if current_value.strip():
                editor.insertItem(0, current_value)
                editor.setCurrentIndex(0)

        #   Clear Original Text (to stop being superimposed)
        self.tw_presets.setItem(row, col, QTableWidgetItem(""))

        #   Set Combo box in the Cell
        self.tw_presets.setCellWidget(row, col, editor)


    @err_catcher(name=__name__)
    def _createLutCell(self, row:int, col:int, lutFilename:str ="", lutFilePath:str =""):
        '''Creates a custom line edit cell with an explorer button for selecting LUT files.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.
            lutFilename (str, optional): The initial LUT file name to set in the line edit. Defaults to an empty string.
            lutFilePath (str, optional): The initial LUT file path to set as the tooltip. Defaults to an empty string.
        '''

        #   Helper to Open Explorer
        def chooseFile():
            currPath = line.toolTip()
            lutFilepath, _ = QFileDialog.getOpenFileName(
                self, "Select LUT File", currPath, "LUT Files (*.cube *.3dl *.lut);;All Files (*)"
            )
            if lutFilepath:
                lutBasename = os.path.basename(lutFilepath)
                line.setText(lutBasename)
                line.setToolTip(lutFilepath)

        #   Clear Original Content 
        self.tw_presets.setItem(row, col, QTableWidgetItem(""))

        #   Create Cantainer Widget
        container = QWidget()
        lo = QHBoxLayout(container)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(2)

        #   Create Line Edit
        line = QLineEdit()
        line.setText(lutFilename)
        line.setToolTip(lutFilePath)
        line.setPlaceholderText("Select or enter LUT path...")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        line.setStyleSheet(self.editorStyle)

        #    Create Explorer Button
        btn = QPushButton()
        iconPath = os.path.join(self.Player.iconDir, "folder.png")
        icon = self.core.media.getColoredIcon(iconPath)
        btn.setIcon(icon)
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(25, 25)
        btn.clicked.connect(chooseFile)

        lo.addWidget(line)
        lo.addWidget(btn)

        self.tw_presets.setCellWidget(row, col, container)


    @err_catcher(name=__name__)
    def _commitActiveRowEdits(self):
        '''Commits the edits made to the currently active row, if any.'''

        if self._editingRow is None:
            return

        row = self._editingRow
        self._editingRow = None
        self._commitRowEdits(row)


    @err_catcher(name=__name__)
    def _getLutPathFromItem(self, row: int, col: int = 6) -> str:
        '''Returns the LUT full path from the Tooltip (LUT lineedit displays the basename).

        Args:
            row (int): The row index of the LUT cell.
            col (int, optional): The column index of the LUT cell. Defaults to 6.

        Returns:
            str: The full path of the LUT file, or an empty string if not set.
        '''

        item = self.tw_presets.item(row, col)
        if not item:
            return ""

        lutPath = (item.toolTip() or "").strip()
        if lutPath:
            return lutPath

        return (item.text() or "").strip()


    @err_catcher(name=__name__)
    def _widgetBelongsToEditingRow(self, widget: QWidget | None) -> bool:
        '''Checks if the given widget belongs to the currently active editing row.

        Args:
            widget (QWidget | None): The widget to check.

        Returns:
            bool: True if the widget belongs to the active editing row, False otherwise.
        '''

        if self._editingRow is None or widget is None:
            return False

        for col in range(self.tw_presets.columnCount()):
            cellWidget = self.tw_presets.cellWidget(self._editingRow, col)
            if cellWidget is not None and (widget is cellWidget or cellWidget.isAncestorOf(widget)):
                return True

            if isinstance(cellWidget, QComboBox):
                comboView = cellWidget.view()
                comboWindow = comboView.window() if comboView is not None else None
                if comboView is not None and (widget is comboView or comboView.isAncestorOf(widget)):
                    return True

                if comboWindow is not None and (widget is comboWindow or comboWindow.isAncestorOf(widget)):
                    return True

        return False


    @err_catcher(name=__name__)
    def _commitRowEdits(self, row:int):
        '''Commits the edits made to a specific row by replacing cell widgets with their text values.

        Args:
            row (int): The row index of the row to commit.
        '''

        headers = self.headers

        #   Get Value Based on Widget Type
        for col, key in enumerate(headers):
            widget = self.tw_presets.cellWidget(row, col)
            if widget is None:
                continue

            #   Line Edit
            if isinstance(widget, QLineEdit):
                value = widget.text()

            #   Combo Box
            elif isinstance(widget, QComboBox):
                value = widget.currentText()

            #   LUT Widget
            elif isinstance(widget, QWidget):
                line_edit = widget.findChild(QLineEdit)
                if key == "LUT":
                    typedValue = (line_edit.text() or "").strip() if line_edit else ""
                    lutPath = (line_edit.toolTip() or "").strip() if line_edit else ""

                    # If a user manually types a path, prefer that over a stale tooltip path.
                    if typedValue and (os.path.isabs(typedValue) or os.path.isfile(typedValue)):
                        lutPath = typedValue

                    if not lutPath:
                        lutPath = typedValue

                    displayValue = os.path.basename(lutPath) if lutPath else ""

                    self.tw_presets.removeCellWidget(row, col)
                    lutItem = QTableWidgetItem(displayValue)
                    lutItem.setToolTip(lutPath)
                    self.tw_presets.setItem(row, col, lutItem)
                    continue

                value = line_edit.text() if line_edit else ""
            else:
                value = ""

            #   Replace Widget with a QTableWidgetItem
            self.tw_presets.removeCellWidget(row, col)
            self.tw_presets.setItem(row, col, QTableWidgetItem(value))


    @err_catcher(name=__name__)
    def _onValidate(self):
        '''Validates the currently selected preset in the table.

        Checks the preset name, color space, display, view, look, and LUT for validity and returns the results.
        '''

        self._commitActiveRowEdits()

        row = self.tw_presets.currentRow()
        if row == -1:
            self.core.popup(title="No Selection", text="Please Select a Preset to Validate.")
            return

        if self.ocioConfig is None:
            self.core.popup(title="OCIO Unavailable", text="No OCIO config is currently available.")
            return

        #   Get data from the table
        name        = self.tw_presets.item(row, 0).text()
        colorSpace  = self.tw_presets.item(row, 2).text()
        display     = self.tw_presets.item(row, 3).text()
        view        = self.tw_presets.item(row, 4).text()
        look        = self.tw_presets.item(row, 5).text()
        lut         = self._getLutPathFromItem(row, 6)

        results = []
        
        ##   Preset Name Check
        valid_name_pattern = re.compile(
            r'^[A-Za-z0-9 \-!@#$%^&()_+=.,;{}\[\]~`^]{1,20}$'
        )

        if not name:
            results.append(("Preset Name", False, "Preset name cannot be blank."))

        elif not valid_name_pattern.match(name):
            results.append((
                "Preset Name", 
                False, 
                f"'{name}' is not valid.\n\n"
                "           Allowed characters: letters, numbers, spaces, dashes, underscores, and common symbols.\n\n"
                "           Length: 1-20 characters.\n\n"
                "           Not allowed: \\ / : * ? \" < > |"
            ))
        else:
            results.append(("Preset Name", True, ""))

        ##   Check Colorspace
        if self.ocioConfig.getColorSpace(colorSpace):
            results.append(("ColorSpace", True, ""))
        else:
            results.append(("ColorSpace", False, f"'{colorSpace}' not found in config"))

        ##   Check Display + View
        if display in self.ocioConfig.getDisplays():
            if view in self.ocioConfig.getViews(display):
                results.append(("Display/View", True, ""))
            else:
                results.append(("Display/View", False, f"View '{view}' not found in display '{display}'"))
        else:
            results.append(("Display", False, f"Display '{display}' not found in config"))

        ##   Check Look
        if look:
            if self.ocioConfig.getLook(look):
                results.append(("Look", True, ""))
            else:
                results.append(("Look", False, f"Look '{look}' not found in config"))
        else:
            results.append(("Look", True, "(not set)"))

        ##   Check LUT
        if lut:
            if os.path.isfile(lut):
                results.append(("LUT", True, ""))
            else:
                results.append(("LUT", False, f"LUT file '{lut}' does not exist"))
        else:
            results.append(("LUT", True, "(not set)"))

        self._showValidationPopup(name, results)


    @err_catcher(name=__name__)
    def _showValidationPopup(self, presetName: str, results: list[tuple[str, bool, str]]):
        '''Shows a formatted validation report popup with aligned, color-coded results.
        
        Args:
            presetName (str): The name of the preset being validated.
            results (list[tuple[str, bool, str]]): A list of validation results, each containing the check label, pass/fail status, and details message.
        '''

        valPopup = QDialog(self)
        valPopup.setWindowTitle("Preset Validation Results")
        valPopup.setModal(True)

        #   Set Deminstions
        valPopup.setMinimumWidth(800)
        valPopup.setMinimumHeight(420)

        #   Move to Center of Current Monitor
        pos = Utils.getPopupPosition(valPopup, self)
        valPopup.move(pos)

        lo_main = QVBoxLayout(valPopup)

        l_title = QLabel(f"Preset:   {presetName}")
        l_title.setStyleSheet(f"font-weight: 600; padding: 4px; color: {Utils.COLOR_WHITE};")

        lo_main.addWidget(l_title)

        table = QTableWidget(len(results), 3, valPopup)
        table.setHorizontalHeaderLabels(["Check", "Status", "Details"])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setStyleSheet("""
            QTableWidget::item {
                padding-left: 12px;
                padding-right: 12px;
            }
        """)

        for row, (label, passed, msg) in enumerate(results):
            statusText = "Passed" if passed else "Failed"
            detailsText = msg if msg else "OK"

            labelItem = QTableWidgetItem(f"{label}:")
            statusItem = QTableWidgetItem(statusText)
            detailsItem = QTableWidgetItem(detailsText)

            statusItem.setTextAlignment(Qt.AlignCenter)

            if passed:
                statusColor = QColor(Utils.COLOR_GREEN_BRIGHT)
            else:
                statusColor = QColor(Utils.COLOR_RED_BRIGHT)

            statusItem.setForeground(QBrush(statusColor))
            detailsItem.setForeground(QBrush(statusColor))

            table.setItem(row, 0, labelItem)
            table.setItem(row, 1, statusItem)
            table.setItem(row, 2, detailsItem)

        lo_main.addWidget(table)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        buttonBox.rejected.connect(valPopup.reject)
        buttonBox.accepted.connect(valPopup.accept)
        lo_main.addWidget(buttonBox)

        valPopup.exec_()


    @err_catcher(name=__name__)
    def _onRowChanged(self):
        '''Called When Row Changed (used to commit edit changes)'''

        new_row = self.tw_presets.currentRow()

        if self._editingRow is not None and self._editingRow != new_row:
            self._commitActiveRowEdits()


    @err_catcher(name=__name__)
    def _onMoveUp(self):
        '''Moves the selected preset up by one row in the table.'''

        self._commitActiveRowEdits()

        row = self.tw_presets.currentRow()
        if row > 0:
            self._swapRows(row, row-1)
            self.tw_presets.selectRow(row-1)


    @err_catcher(name=__name__)
    def _onMoveDown(self):
        '''Moves the selected preset down by one row in the table.'''

        self._commitActiveRowEdits()

        row = self.tw_presets.currentRow()
        if row < self.tw_presets.rowCount() - 1:
            self._swapRows(row, row+1)
            self.tw_presets.selectRow(row+1)


    @err_catcher(name=__name__)
    def _swapRows(self, r1:int, r2:int):
        '''Swaps the contents of two rows in the table.

        Args:
            r1 (int): The index of the first row.
            r2 (int): The index of the second row.
        '''

        for c in range(self.tw_presets.columnCount()):
            t1 = self.tw_presets.takeItem(r1, c)
            t2 = self.tw_presets.takeItem(r2, c)
            self.tw_presets.setItem(r1, c, t2)
            self.tw_presets.setItem(r2, c, t1)


    @err_catcher(name=__name__)
    def _onFinish(self, action:str):
        '''Handles the finish action for the dialog, committing any edits and saving data if necessary.

        Args:
            action (str): The action to perform ("Save" or "Cancel").
        '''

        # Commit Currently Editing Row
        self._commitActiveRowEdits()

        self._action = action
        if action == "Save":
            try:
                self.presetData = {}
                self.presetOrder = []

                data_keys = self.headers[1:]

                for row in range(self.tw_presets.rowCount()):
                    name_item = self.tw_presets.item(row, 0)
                    if not name_item:
                        continue

                    name = name_item.text().strip()
                    if not name:
                        continue

                    self.presetOrder.append(name)

                    data = {}
                    for c, key in enumerate(data_keys, start=1):
                        if key == "LUT":
                            data[key] = self._getLutPathFromItem(row, c)
                        else:
                            item = self.tw_presets.item(row, c)
                            data[key] = item.text().strip() if item else ""

                    self.presetData[name] = data

                logger.debug("OCIO Presets data collected successfully.")

            except Exception as e:
                logger.warning(f"ERROR: Failed to Save OCIO Presets:\n{e}")

        self.accept()



############################################
#######     PLAYER SETTINGS UI      ########

class PlayerConfigPopup(QDialog):
    '''Popup dialog for configuring media player settings.
    
    Args:
    ------
    - Player (PreviewPlayer_GL): The media player instance to configure.
    - core (PrismCore): Prism Core object.
    - parent (QWidget, optional): The parent widget. Defaults to None.

    API:
    ----
    - onSaveClicked(): Handles the Save button click event.
    - onCloseClicked(): Handles the Close button click event.
    - loadSettings(data: dict) -> bool: Loads player configuration settings into the editor.
    - getSettings() -> dict: Retrieves the current player configuration settings.
    '''

    def __init__(self, Player: 'PreviewPlayer_GL', core: 'PrismCore', parent: QWidget = None):
        super().__init__(parent)

        self.Player = Player
        self.core = core

        #   Defaults
        self.cacheThreads = 4
        self.maxCacheMemPercent = 50
        self.rescanEnabled = True
        self.rescanSecs = 10
        self.check_size = 20
        self.check_color1 = (0.0, 0.0, 0.0)
        self.check_color2 = (0.1, 0.1, 0.1)
        self.result = None

        self.setWindowTitle("Media Player Configuration")

        self.loadUI()
        self.connectEvents()


    ##########################
    ########    UI    ########

    @err_catcher(name=__name__)
    def loadUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width   = screen_geometry.width() // 4
        height  = screen_geometry.height() // 2.5
        x_pos   = (screen_geometry.width() - width) // 2
        y_pos   = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        lo_main = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)


        ##   PERFORMACE SECTION
        gb_performance = QGroupBox("Performace")

        #   Layout for Margins
        lo_margins = QVBoxLayout(gb_performance)

        #   Inner Layout
        checkContainer = QWidget()
        lo_performace = QVBoxLayout(checkContainer)
        lo_performace.setContentsMargins(20, 5, 20, 5)

        #   Cache Threads
        lo_threads = QHBoxLayout()
        l_threads = QLabel("Frame Cache Threads")
        self.sp_threads = QSpinBox()
        self.sp_threads.setRange(1, 50)
        self.sp_threads.setValue(4)

        lo_threads.addWidget(l_threads)
        lo_threads.addStretch()
        lo_threads.addWidget(self.sp_threads)
        lo_performace.addLayout(lo_threads)

        #   Max RAM Percent
        lo_maxCacheMem = QHBoxLayout()
        l_maxCacheMem = QLabel("Max Cache Memory (%)")
        self.sp_maxCacheMem = QSpinBox()
        self.sp_maxCacheMem.setRange(1, 100)
        self.sp_maxCacheMem.setValue(50)

        lo_maxCacheMem.addWidget(l_maxCacheMem)
        lo_maxCacheMem.addStretch()
        lo_maxCacheMem.addWidget(self.sp_maxCacheMem)
        lo_performace.addLayout(lo_maxCacheMem)

        #   Cache Rescan
        lo_rescan = QHBoxLayout()
        self.cb_rescan = QCheckBox("Enable Cache Rescan (seconds)")
        self.cb_rescan.setChecked(self.rescanEnabled)

        self.sp_rescanSecs = QSpinBox()
        self.sp_rescanSecs.setRange(1, 3600)
        self.sp_rescanSecs.setValue(self.rescanSecs)

        lo_rescan.addWidget(self.cb_rescan)
        lo_rescan.addStretch()
        lo_rescan.addWidget(self.sp_rescanSecs)
        lo_performace.addLayout(lo_rescan)

        lo_margins.addWidget(checkContainer)
        scroll_layout.addWidget(gb_performance)


        ##  CHECKER BACKGROUND SECTION
        gb_checkerBG = QGroupBox("Checker Background")

        #   Layout for Margins
        lo_margins = QVBoxLayout(gb_checkerBG)

        #   Inner Layout
        checkContainer = QWidget()
        lo_checker = QVBoxLayout(checkContainer)
        lo_checker.setContentsMargins(20, 5, 20, 5)

        # Checker Size
        lo_checkSize = QHBoxLayout()
        l_checkSize = QLabel("Checker Size (pix)")
        self.sp_checkSize = QSpinBox()
        self.sp_checkSize.setRange(1, 100)
        self.sp_checkSize.setValue(20)

        lo_checkSize.addWidget(l_checkSize)
        lo_checkSize.addStretch()
        lo_checkSize.addWidget(self.sp_checkSize)
        lo_checker.addLayout(lo_checkSize)

        #   Color 1
        lo_row1, l_row1, self._swatch1, but_row1 = self._makeColorRow("Checker Color 1",
                                                (0, 0, 0),
                                                lambda c: setattr(self, "check_color1", c)
                                                )
        lo_checker.addLayout(lo_row1)

        #   Color 2
        lo_row2, l_row2, self._swatch2, but_row2 = self._makeColorRow("Checker Color 2",
                                                (25, 25, 25),
                                                lambda c: setattr(self, "check_color2", c)
                                                )
        lo_checker.addLayout(lo_row2)

        lo_margins.addWidget(checkContainer)
        scroll_layout.addWidget(gb_checkerBG)

        scroll_layout.addStretch(1)

        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        #   Bottom Buttons
        lo_buttons = QHBoxLayout()

        self.b_save = QPushButton("Save")
        self.b_cancel = QPushButton("Cancel")

        lo_buttons.addStretch()
        lo_buttons.addWidget(self.b_save)
        lo_buttons.addWidget(self.b_cancel)

        lo_main.addLayout(lo_buttons)

        tip = ("Number of worker threads to use for concurrent cache building.\n\n"
               "The default number will be automatically calculated based on the machine's CPU cores.")
        l_threads.setToolTip(tip)
        self.sp_threads.setToolTip(tip)

        tip = ("Maximum percentage of system RAM to use for caching frames.\n\n"
               "There is also a final safeguard at 90% of the system RAM.")
        l_maxCacheMem.setToolTip(tip)
        self.sp_maxCacheMem.setToolTip(tip)

        tip = ("Enable automatic cache rescanning for image sequences.\n\n"
               "This will periodically check the sequnce directory for additional frames\n"
               "to be added to the cache based on the specified seconds.")
        self.cb_rescan.setToolTip(tip)

        tip = "Number of seconds between automatic cache rescans (default = 10)"
        self.sp_rescanSecs.setToolTip(tip)

        tip = "Size of the Alpha Checker Background in Pixels."
        l_checkSize.setToolTip(tip)
        self.sp_checkSize.setToolTip(tip)

        tip = "Color of the first checker square."
        l_row1.setToolTip(tip)
        self._swatch1.setToolTip(tip)


        tip = "Color of the second checker square."
        l_row2.setToolTip(tip)
        self._swatch2.setToolTip(tip)

        tip = "Click to choose a color."
        but_row1.setToolTip(tip)
        but_row2.setToolTip(tip)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_save.clicked.connect(self.onSaveClicked)
        self.b_cancel.clicked.connect(self.onCloseClicked)
        self.cb_rescan.toggled.connect(self.onRescanToggled)



    ###########################
    ########    API    ########

    @err_catcher(name=__name__)
    def onSaveClicked(self):
        '''Handles the Save button click event by retrieving the current settings and accepting the dialog.'''

        self.result = self.getSettings()
        self.accept()


    @err_catcher(name=__name__)
    def onCloseClicked(self):
        '''Handles the Close button click event by rejecting the dialog.'''

        self.reject()


    @err_catcher(name=__name__)
    def loadSettings(self, data:dict) -> bool:
        '''Loads Player Config Settings into Editor

        Args:
            data (dict): The settings data to load.

        Returns:
            bool: True if settings were loaded successfully, False otherwise.
        '''

        try:
            self.sp_threads.setValue(data.get("cacheThreads", 4))
            self.sp_maxCacheMem.setValue(data.get("maxCacheMemPercent", 50))
            self.cb_rescan.setChecked(data.get("cacheRescanEnabled", True))
            self.sp_rescanSecs.setValue(data.get("cacheRescanSecs", 30))
            self.sp_checkSize.setValue(data.get("check_size", 20))

            #   Convert Lists to Tuples
            color1 = tuple(data.get("check_color1", (0.0, 0.0, 0.0)))
            color2 = tuple(data.get("check_color2", (0.1, 0.1, 0.1)))

            #   Update Vars
            self.check_color1 = color1
            self.check_color2 = color2

            #   Update Swatches
            self._setSwatchColor(self._swatch1, color1)
            self._setSwatchColor(self._swatch2, color2)

            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Load Settings: {e}")
            return False


    @err_catcher(name=__name__)
    def getSettings(self) -> dict:
        '''Retrieves the current settings from the editor.

        Returns:
            dict: A dictionary containing the current settings.
        '''

        try:
            return {
                "cacheThreads": self.sp_threads.value(),
                "maxCacheMemPercent": self.sp_maxCacheMem.value(),
                "cacheRescanEnabled": self.cb_rescan.isChecked(),
                "cacheRescanSecs": self.sp_rescanSecs.value(),
                "check_size": self.sp_checkSize.value(),
                "check_color1": self.check_color1,
                "check_color2": self.check_color2,
            }
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to get Settings: {e}")
            return {}



    ################################
    ########    INTERNAL    ########

    def onRescanToggled(self, enabled:bool):
        '''Disables seconds checkbox based on the state of the rescan checkbox.

        Args:
            enabled (bool): True if the rescan checkbox is checked, False otherwise.
        '''

        self.sp_rescanSecs.setEnabled(enabled)


    @err_catcher(name=__name__)
    def _makeColorRow(self, label_text:str, default_color:tuple, callback:callable=None) -> tuple[QHBoxLayout, QLabel, QFrame, QPushButton]:
        '''Creates a horizontal layout containing a label, a color swatch, and a button to choose a color.

        Args:
            label_text (str): The text for the label.
            default_color (tuple): The default color as an (R, G, B) tuple with values 0-255.
            callback (callable, optional): A function to call when the color is chosen. Receives the normalized color (0-1 floats).

        Returns:
            tuple[QHBoxLayout, QLabel, QFrame, QPushButton]: The layout, label, swatch, and button.
        '''

        layout = QHBoxLayout()

        #   Name Label
        lbl = QLabel(label_text)

        #   Swatch (QFrame with Background Color)
        swatch = QFrame()
        swatch.setObjectName("checkerSwatch")

        swatch.setFixedSize(40, 25)
        swatch.setFrameShape(QFrame.Box)
        swatch.setFrameShadow(QFrame.Plain)
        swatch.setStyleSheet(f"""
            QFrame#checkerSwatch {{
                background-color: rgb{default_color};
                border: 2px solid #454545;
                border-radius: 2px;
            }}
        """)
        swatch.setProperty("color", tuple(c/255 for c in default_color))

        #   Button
        btn = QPushButton("Choose...")
        btn.clicked.connect(lambda: self._pickColor(swatch, callback))

        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(swatch)
        layout.addWidget(btn)

        return layout, lbl, swatch, btn


    @err_catcher(name=__name__)
    def _pickColor(self, swatch:QFrame, callback:callable=None):
        '''Opens a color picker dialog to choose a color for the given swatch.

        Args:
            swatch (QFrame): The swatch whose color is to be changed.
            callback (callable, optional): A function to call when the color is chosen. Receives the normalized color (0-1 floats).
        '''

        initial = swatch.palette().window().color()
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            r, g, b, _ = color.getRgb()
            swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #444;")
            normalized = (round(r/255,3), round(g/255,3), round(b/255,3))
            swatch.setProperty("color", normalized)
            if callback:
                callback(normalized)


    @err_catcher(name=__name__)
    def _setSwatchColor(self, swatch:QFrame, rgb:tuple):
        '''Sets the color of the given swatch programmatically.

        Args:
            swatch (QFrame): The swatch whose color is to be set.
            rgb (tuple): The color to set, either as normalized floats (0-1) or as integers (0-255).
        '''

        if all(0 <= c <= 1 for c in rgb):
            r, g, b = [int(c*255) for c in rgb]
            #   Clamp Floats to 3 Decimal Places
            normalized = tuple(round(c, 3) for c in rgb)

        else:
            r, g, b = rgb
            normalized = tuple(round(c/255, 3) for c in rgb)

        swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #444;")
        swatch.setProperty("color", normalized)

        

#####################################
#######     FX Controls      ########

class FxControlsData(QObject):
    '''Image FX Data Storage and Emits a Signal when Changes Occur.
    
    Signals:
    ------
    - changed (Signal): Emitted when any of the FX settings change.

    API:
    ----
    - setFxEnabled(enabled: bool): Sets the FX controls active state.
    - isFxEnabled() -> bool: Gets the FX controls active state.
    - getFxControlNames() -> list[str]: Returns a list of the FX control names.
    - set_FxControlValue(name: str, value: float): Sets the value of an FX control.
    - get_FxControlValue(name: str, allowDefault: bool = True) -> int: Gets the value of an FX control.
    - set_FxControlEnabled(name: str, enabled: bool): Sets the enabled state of an FX control.
    - get_FxControlEnabled(name: str) -> bool: Gets the enabled state of an FX control.
    '''

    changed = Signal()

    def __init__(self):
        super().__init__()

        #   Global FX Enabled Flag
        self.fxEnabled = False

        self.fxControls_values = {}
        self.fxControls_enabled = {}
        
        #   FX Control Definitions
        self.fxControls = copy.deepcopy(Utils.FX_CONTROLS)

        #   Create Initial Controls State
        for name, data in self.fxControls.items():
            self.fxControls_values[name] = data["default"]
            self.fxControls_enabled[name] = True

        #   Update Throttle Timer
        self._updateTimer = QTimer(self)
        self._updateTimer.setSingleShot(True)
        self._updateTimer.timeout.connect(self.changed.emit)


    @err_catcher(name=__name__)
    def setFxEnabled(self, enabled: bool):
        '''Sets the FX Controls Active State
        
        Args:
            enabled (bool): Enabled/Disabled FX state'''
        
        self.fxEnabled = enabled
        self._queueUpdate()


    @err_catcher(name=__name__)
    def isFxEnabled(self) -> bool:
        '''Gets the FX Controls Active State
        
        Returns:
            bool: Enabled/Disabled FX state'''
        
        return self.fxEnabled
    

    @err_catcher(name=__name__)
    def getFxControlNames(self) -> list[str]:
        '''Returns a list of the FX Control Names.
        
        Returns:
            list (str): List of the Control Names.
            '''

        return [name for name in self.fxControls.keys()]


    @err_catcher(name=__name__)
    def set_FxControlValue(self, name: str, value: float):
        '''Set an FX value and queue an update.
        
        Args:
            name (str): The FX Control name.
            value (float): The value of the control.
        '''

        self.fxControls_values[name] = value
        self._queueUpdate()


    @err_catcher(name=__name__)
    def get_FxControlValue(self, name:str, allowDefault:bool=True) -> int:
        '''Get an FX value.
        
        Args:
            name (str): The FX Control name.
            allowDefault (bool): If True, returns the default value if the control is disabled. Defaults to True.

        Returns:
            float: The value of the control.
        '''

        if not self.fxControls_enabled[name] and allowDefault:
            return self.fxControls[name]["default"]

        return self.fxControls_values[name]


    @err_catcher(name=__name__)
    def set_FxControlEnabled(self, name: str, enabled: bool):
        '''Set an FX enabled state and queue an update.
        
        Args:
            name (str): The FX Control name.
            enabled (bool): The enabled state.
        '''

        self.fxControls_enabled[name] = enabled
        self._queueUpdate()


    @err_catcher(name=__name__)
    def get_FxControlEnabled(self, name: str) -> bool:
        '''Get an FX enabled state.
        
        Args:
            name (str): The FX Control name.

        Returns:
            bool: The enabled state.
        '''

        return self.fxControls_enabled[name]


    @err_catcher(name=__name__)
    def _queueUpdate(self):
        '''Queues an update to emit the changed signal after a delay.'''

        if not self._updateTimer.isActive():
            self._updateTimer.start(100)



class FxControlsDialog(QDialog):
    '''Floating FX controls dialog.
    
    Args:
    ------
    - core (PrismCore): The Prism Core object.
    - FxData (FxControlsData): The FX controls data object.
    - parent (QWidget, optional): The parent widget. Defaults to None.
    '''


    def __init__(self, core: 'PrismCore', FxData: 'FxControlsData', parent=None):
        super().__init__(parent)

        self.core = core
        self.FxData = FxData

        self.setupUI()
        self.connections()


    @err_catcher(name=__name__)
    def setupUI(self):
        '''Sets up the UI for the FX controls dialog.'''

        self.setWindowTitle("Viewer FX Controls")

        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint
        )

        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.resize(400, 250)

        ##   Main Layout
        self.lo_fxMain = QVBoxLayout(self)
        self.lo_fxMain.setContentsMargins(8, 8, 8, 8)
        self.lo_fxMain.setSpacing(8)

        ##   Title Bar
        titleBar = QWidget()
        titleBar.setObjectName("TitleBar")

        titleBar.setStyleSheet("""
            #TitleBar {
                background-color: rgb(60, 60, 60);
                border-radius: 4px;
            }

            #TitleBar QLabel {
                font-weight: bold;
                color: white;
            }

            #TitleBar QPushButton {
                font-weight: bold;
                color: white;
                border: none;
                background: transparent;
                padding: 2px;
            }

            #TitleBar QPushButton:hover {
                background: rgb(90, 90, 90);
                border-radius: 2px;
            }

            #TitleBar QPushButton:pressed {
                background: rgb(120, 120, 120);
            }
            """)

        titleLayout = QHBoxLayout(titleBar)
        titleLayout.setContentsMargins(6, 4, 6, 4)

        lblTitle = QLabel("Viewer FX Controls")
        titleLayout.addWidget(lblTitle)

        titleLayout.addStretch()

        btnClose = QPushButton("X")
        btnClose.clicked.connect(self.hide)
        btnClose.setStyleSheet("""
            QPushButton {
                padding: 0px;
                margin: 0px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 1px solid rgb(90, 90, 90);
                border-style: inset;
                border-width: 1px;
                border-color: rgb(30, 30, 30);
            }
            """)

        titleLayout.addWidget(btnClose)

        self.lo_fxMain.addWidget(titleBar)

        ##   Scene Referred Layout
        gb_sceneRef = QGroupBox()
        self.lo_fxMain.addWidget(gb_sceneRef)
        lo_sceneRef = QVBoxLayout()
        lo_sceneRef.setContentsMargins(0, 0, 0, 10)

        l_sceneRef = QLabel("Scene Referred Linear Working Space")
        l_sceneRef.setToolTip("Adjustments applied to the Float 16 Images in the OCIO Linear Working Domain.\n\n"
                              "These happen after the 'Input Colorspace' transform but before the 'Display/View' transforms.")
        l_sceneRef.setStyleSheet("font-weight: bold;")
        lo_sceneRef.addWidget(l_sceneRef)

        gb_sceneRef.setLayout(lo_sceneRef)

        ##   Display Referred Layout
        gb_displayRef = QGroupBox()
        self.lo_fxMain.addWidget(gb_displayRef)

        lo_displayRef = QVBoxLayout()
        lo_displayRef.setContentsMargins(0, 0, 0, 10)

        l_displayRef = QLabel("Display Referred Space")
        l_displayRef.setToolTip("Adjustments applied to the Displayed Images in the OCIO Display Referred Domain.\n\n"
                                "These happen after the Display/View/Look/LUT transforms.")
        l_displayRef.setStyleSheet("font-weight: bold;")
        lo_displayRef.addWidget(l_displayRef)

        gb_displayRef.setLayout(lo_displayRef)

        ##   FX Control Rows
        self.fxRows = {}

        #   Create FxControlsRow for each Control in FxData
        try:
            for fxName, cData in self.FxData.fxControls.items():
                try:
                    row = FxControlsRow(
                        self.core,
                        cData["label"],
                        fxName,
                        minimum=cData["minimum"],
                        maximum=cData["maximum"],
                        default=cData["default"],
                        mathTip=cData.get("mathTip", ""),
                    )

                    #   Add to Dict
                    self.fxRows[fxName] = row

                    #   Add to Applicable Domain Layout
                    if cData.get("domain", "scene") == "scene":
                        lo_sceneRef.addWidget(row)
                    else:
                        lo_displayRef.addWidget(row)

                except Exception as e:
                    logger.warning(f"Error creating FX Controls row for {fxName}: {e}")

        except Exception as e:
            logger.warning(f"Error creating FX Controls rows: {e}")

        self.b_resetAll = QPushButton("Reset All")
        self.lo_fxMain.addWidget(self.b_resetAll)

        self.lo_fxMain.addStretch()


    @err_catcher(name=__name__)
    def connections(self):
        #   Create Connections for Each FX Control Row
        rowsWidgets: list[FxControlsRow] = self.fxRows.values()
        for rowWidget in rowsWidgets:
            name = rowWidget.fxName

            #   Value Changed Signal
            rowWidget.valueChanged.connect(
                lambda value, fxName=name:
                    self.FxData.set_FxControlValue(fxName, value)
            )

            #   Enable Cahnged Signal
            rowWidget.enabledChanged.connect(
                lambda enabled, fxName=name:
                    self.FxData.set_FxControlEnabled(fxName, enabled)
            )

        #   Connect Reset All
        self.b_resetAll.clicked.connect(self.resetAll)


    @err_catcher(name=__name__)
    def resetAll(self):
        '''Reset all FX Controls rows to their default values.'''

        rowWidget: FxControlsRow
        for rowWidget in self.fxRows.values():
            rowWidget.reset()


    @err_catcher(name=__name__)
    def mousePressEvent(self, event: QMouseEvent):
        '''Handle mouse press events for dragging the window.
        
        Args:
            event (QMouseEvent): The mouse press event.
        '''

        if event.button() == Qt.LeftButton:
            self._dragPos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

        super().mousePressEvent(event)


    @err_catcher(name=__name__)
    def mouseMoveEvent(self, event:QMouseEvent):
        '''Handle mouse move events for dragging the window.
        
        Args:
            event (QMouseEvent): The mouse move event.
        '''

        if event.buttons() & Qt.LeftButton:
            self.move(
                event.globalPosition().toPoint()
                - self._dragPos
            )

        super().mouseMoveEvent(event)



class FxControlsRow(QWidget):
    '''A Custom FX Controls Row.

    Signals
    -------
    - valueChanged (float): Emitted whenever the value changes.
    - enabledChanged (bool): Emitted whenever the is enabled/disabled.
    - resetClicked (): Emitted after the control has been reset.

    Args:
    ------
    - core (PrismCore): The Prism Core object.
    - label (str): The label for the FX control row.
    - fxName (str): The name of the FX control.
    - minimum (float): The minimum value for the control.
    - maximum (float): The maximum value for the control.
    - default (float): The default value for the control.
    - mathTip (str, optional): User-facing explanation of the control math.
    - step (float, optional): The step size for the control. Defaults to 0.01.
    - decimals (int, optional): The number of decimal places for the control. Defaults to 2.
    - parent (QWidget, optional): The parent widget. Defaults to None.

    API:
    ----
    - value() -> float: Returns the current value of the control.
    - isFxEnabled() -> bool: Returns whether the FX control is enabled.
    - setFxEnabled(enabled: bool): Sets the enabled state of the FX control.
    - setValue(value: float): Sets the value of the FX control.
    - reset(): Resets the FX control to its default state.
    '''

    valueChanged = Signal(float)
    enabledChanged = Signal(bool)
    resetClicked = Signal()

    def __init__(
        self,
        core: 'PrismCore',
        label: str,
        fxName: str,
        minimum: float,
        maximum: float,
        default: float,
        mathTip: str = "",
        step: float = 0.01,
        decimals: int = 2,
        parent=None,
    ):
        
        super().__init__(parent)

        self.core = core
        self.fxName = fxName
        self.default = default
        self.step = step
        self.mathTip = mathTip or ""


        #   Widgets
        self.ch_enabled = QCheckBox(label)
        self.ch_enabled.setChecked(True)
        self.ch_enabled.setMinimumWidth(110)

        self.slider = QSlider(Qt.Horizontal)

        slider_min = round(minimum / step)
        slider_max = round(maximum / step)
        slider_default = round(default / step)

        self.slider.setRange(slider_min, slider_max)
        self.slider.setValue(slider_default)

        self.sp_value = QDoubleSpinBox()
        self.sp_value.setDecimals(decimals)
        self.sp_value.setRange(minimum, maximum)
        self.sp_value.setSingleStep(step)
        self.sp_value.setValue(default)
        self.sp_value.setFixedWidth(70)

        if self.mathTip:
            self.ch_enabled.setToolTip(self.mathTip)
            self.slider.setToolTip(self.mathTip)
            self.sp_value.setToolTip(self.mathTip)

        self.b_reset = QPushButton()
        self.b_reset.setToolTip("Reset")
        self.iconDir = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")
        icon_reset = Utils.getIconFromPath(os.path.join(self.iconDir, "reset.png"))
        self.b_reset.setIcon(icon_reset)
        self.b_reset.setIconSize(QSize(12,12))
        self.b_reset.setStyleSheet("""
            QPushButton {
                padding: 0px;
                margin: 0px;
                min-width: 14px;
                max-width: 14px;
                min-height: 14px;
                max-height: 14px;
            }
            """)

        #   Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        layout.addWidget(self.ch_enabled)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.sp_value)
        layout.addWidget(self.b_reset)

        #   Connections
        self.ch_enabled.toggled.connect(self._enabledChanged)
        self.slider.valueChanged.connect(self._sliderChanged)
        self.sp_value.valueChanged.connect(self._spinChanged)
        self.b_reset.clicked.connect(self.reset)


    ##########################
    ########    API   ########

    @err_catcher(name=__name__)
    def value(self) -> float:
        '''Get the current value of the control.

        Returns:
            float: The current value.
        '''

        return self.sp_value.value()


    @err_catcher(name=__name__)
    def isFxEnabled(self) -> bool:
        '''Check if the control is enabled.

        Returns:
            bool: True if the FX control is enabled, False otherwise.
        '''

        return self.ch_enabled.isChecked()


    @err_catcher(name=__name__)
    def setFxEnabled(self, enabled: bool):
        '''Set the enabled state of the control.

        Args:
            enabled (bool): True to enable the FX control, False to disable it.
        '''

        self.ch_enabled.setChecked(enabled)


    @err_catcher(name=__name__)
    def setValue(self, value: float):
        '''Set the value of the control.

        Args:
            value (float): The value to set.
        '''

        with Utils.blockSignals(self.slider, self.sp_value):
            self.slider.setValue(round(value / self.step))
            self.sp_value.setValue(value)

        self.valueChanged.emit(value)


    @err_catcher(name=__name__)
    def reset(self):
        '''Reset the control to its default state.'''

        self.setValue(self.default)
        self.ch_enabled.setChecked(True)

        self.resetClicked.emit()


    ##############################
    ########   Internal   ########

    @err_catcher(name=__name__)
    def _enabledChanged(self, enabled: bool):
        '''Handle the change in the enabled state of the control.

        Args:
            enabled (bool): True if the control is enabled, False otherwise.
        '''

        self.slider.setEnabled(enabled)
        self.sp_value.setEnabled(enabled)
        self.b_reset.setEnabled(enabled)

        self.enabledChanged.emit(enabled)

    @err_catcher(name=__name__)
    def _sliderChanged(self, sliderValue: int):
        '''Handle the change in the slider value.

        Args:
            sliderValue (int): The new value of the slider.
        '''

        value = sliderValue * self.step

        with Utils.blockSignals(self.sp_value):
            self.sp_value.setValue(value)

        self.valueChanged.emit(value)


    @err_catcher(name=__name__)
    def _spinChanged(self, value: float):
        '''Handle the change in the spin box value.

        Args:
            value (float): The new value of the spin box.
        '''

        with Utils.blockSignals(self.slider):
            self.slider.setValue(round(value / self.step))

        self.valueChanged.emit(value)



##########################################
#######   CUSTOM PLAY CONTROLS    ########

class PlayerControls(QWidget):
    '''Custom Playback Controls for the Preview Player.

    Args:
    ------
    - Player (PreviewPlayer_GL): The preview player instance.
    - parent (QWidget, optional): The parent widget. Defaults to None.

    API:
    ------
    - setRange(start: int, end: int): Sets the range of the player controls slider.
    - setFrame(frame: int): Sets the current frame number in the slider and spinbox.
    - getFrame() -> int: Gets the current frame number from the slider.
    - setPaused(paused: bool): Sets player controls playback UI for play/pause.
    - updateFpsDisplay(fps: float, refreshFps: float, direction: int): Update UI for FPS and direction.
    - refreshFrameDisplay(): Refreshes the frame display.
    - updateCacheSlider(frame: int, reset: bool = False): Updates the cache slider value and optionally resets it.
    '''


    def __init__(self, Player: 'PreviewPlayer_GL', parent=None):
        super().__init__(parent)

        self.Player = Player
        self.core: PrismCore = self.Player.core

        self._setupUI()
        self._setStyleOverrides()
        self._connections()


    @err_catcher(name=__name__)
    def _setupUI(self):
        self.playIcon = Utils.getIconFromPath(os.path.join(self.Player.iconDir, "play.png"))
        self.pauseIcon = Utils.getIconFromPath(os.path.join(self.Player.iconDir, "pause.png"))

        self.lo_main = QVBoxLayout(self)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

        ##  Timeline Line
        self.w_timeslider = QWidget()

        self.lo_timeslider = QHBoxLayout(self.w_timeslider)
        self.lo_timeslider.setContentsMargins(0, 0, 0, 0)

        #   Start and End Labels
        self.l_start = QLabel()
        self.l_end = QLabel()

        self.l_start.setContextMenuPolicy(Qt.CustomContextMenu)
        self.l_end.setContextMenuPolicy(Qt.CustomContextMenu)
        
        #   Slider
        self.sl_previewImage = QSlider(Qt.Horizontal)
        self.sl_previewImage.setRange(0, 0)
        self.sl_previewImage.setObjectName("sl_previewImage")
        self.sl_previewImage.setToolTip("Cache: Idle")
        self.sl_previewImage.setContextMenuPolicy(Qt.CustomContextMenu)

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sl_previewImage.setSizePolicy(sizePolicy)

        self.lo_timeslider.addWidget(self.l_start)
        self.lo_timeslider.addWidget(self.sl_previewImage)
        self.lo_timeslider.addWidget(self.l_end)

        self.lo_main.addWidget(self.w_timeslider)

        ##  Player Controls Line
        self.w_playerCtrls = QWidget()

        self.lo_playerCtrls = QHBoxLayout(self.w_playerCtrls)
        self.lo_playerCtrls.setContentsMargins(0, 0, 0, 0)
        self.lo_playerCtrls.setSpacing(0)

        #   Setup Playback Buttons
        for name in ("first", "prev", "play", "next", "last"):
            button = QToolButton()
            button.setIcon(
                Utils.getIconFromPath(
                    os.path.join(self.Player.iconDir, f"{name}.png")
                )
            )

            setattr(self, f"b_{name}", button)

        #   Play Button RCL Menu
        self.b_play.setContextMenuPolicy(Qt.CustomContextMenu)

        #   Get Width of Buttons
        outerButtonWidth = max(self.b_first.sizeHint().width(), self.b_last.sizeHint().width())

        #   First Frame Button
        self.w_first = QWidget()
        self.w_first.setFixedWidth(outerButtonWidth)
        self.lo_first = QHBoxLayout(self.w_first)
        self.lo_first.setContentsMargins(0, 0, 0, 0)
        self.lo_first.addWidget(self.b_first)

        #   Current Frame SpinBox
        self.w_leftInfo = QWidget()
        self.lo_leftInfo = QHBoxLayout(self.w_leftInfo)
        self.lo_leftInfo.setContentsMargins(0, 0, 0, 0)

        self.sp_current = TimeDisplaySpinBox()
        self.sp_current.sizeHint = lambda: QSize(30, 0)
        self.sp_current.setStyleSheet("min-width:30px;")
        self.sp_current.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.sp_current.setDisplayModeProvider(self._getFrameDisplayMode)
        self.sp_current.setDisplayFormatter(self._getFrameDisplayText)
        self.sp_current.setTimecodeParser(self._parseFrameInput)
        self.sp_current.setValue(self.Player.MediaData.pstart)

        self.lo_leftInfo.addStretch()
        self.lo_leftInfo.addWidget(self.sp_current)
        self.lo_leftInfo.addStretch()

        #   Center Playback Controls
        self.w_centerControls = QWidget()
        self.lo_centerControls = QHBoxLayout(self.w_centerControls)
        self.lo_centerControls.setContentsMargins(0, 0, 0, 0)
        self.lo_centerControls.addWidget(self.b_prev)
        self.lo_centerControls.addWidget(self.b_play)
        self.lo_centerControls.addWidget(self.b_next)

        #   Playback FPS Display
        self.w_rightInfo = QWidget()
        self.lo_rightInfo = QHBoxLayout(self.w_rightInfo)
        self.lo_rightInfo.setContentsMargins(0, 0, 0, 0)

        self.l_currFPS = QLabel()
        metrics = self.l_currFPS.fontMetrics()
        width = metrics.horizontalAdvance("  000.00 (000.00)  ")
        self.l_currFPS.setFixedWidth(width)

        self.lo_rightInfo.addStretch()
        self.lo_rightInfo.addWidget(self.l_currFPS)
        self.lo_rightInfo.addStretch()

        #   Last Frame Button
        self.w_last = QWidget()
        self.w_last.setFixedWidth(outerButtonWidth)
        self.lo_last = QHBoxLayout(self.w_last)
        self.lo_last.setContentsMargins(0, 0, 0, 0)
        self.lo_last.addWidget(self.b_last)

        #   Add to Layout
        self.lo_playerCtrls.addWidget(self.w_first)
        self.lo_playerCtrls.addWidget(self.w_leftInfo, 1)
        self.lo_playerCtrls.addWidget(self.w_centerControls)
        self.lo_playerCtrls.addWidget(self.w_rightInfo, 1)
        self.lo_playerCtrls.addWidget(self.w_last)

        self.lo_main.addWidget(self.w_playerCtrls)

        #   Tooltips
        tip = ("Start Frame/Timecode\n\n\n"
               "Right-click to change time display mode (Frames/Timecode).\n")
        self.l_start.setToolTip(tip)

        tip = ("End Frame/Timecode\n\n\n"
               "Right-click to change time display mode (Frames/Timecode).\n")
        self.l_end.setToolTip(tip)

        self.b_first.setToolTip("First Frame")
        self.b_prev.setToolTip("Previous Frame")
        self.b_play.setToolTip("Play / Pause")
        self.b_next.setToolTip("Next Frame")
        self.b_last.setToolTip("Last Frame")

        tip = ("Current Frame/Timecode\n\n"
               "Manually enter a frame number to jump to that frame.\n")
        self.sp_current.setToolTip(tip)

        tip = ("Selected FPS (Refresh FPS)\n\n"
               "Note: The playback rate should always\n"
               "be at the selected FPS and drop frames.")
        self.l_currFPS.setToolTip(tip)


    @err_catcher(name=__name__)
    def _connections(self):
        self.sl_previewImage.origMousePressEvent = self.sl_previewImage.mousePressEvent
        self.sl_previewImage.mousePressEvent = self.Player.sliderMousePress
        self.sl_previewImage.valueChanged.connect(self.Player.sliderChanged)
        self.sl_previewImage.sliderPressed.connect(self.Player.onSliderPressed)
        self.sl_previewImage.sliderReleased.connect(self.Player.onSliderReleased)

        self.sp_current.editingFinished.connect(
            lambda: self.Player.setCurrentFrame(self.sp_current.value(), manual=True, reset=True)
            )
        
        self.b_first.clicked.connect(self.Player.onFirstClicked)
        self.b_prev.clicked.connect(self.Player.onPrevClicked)
        self.b_play.clicked.connect(self.Player.onPlayClicked)
        self.b_next.clicked.connect(self.Player.onNextClicked)
        self.b_last.clicked.connect(self.Player.onLastClicked)

        self.b_play.customContextMenuRequested.connect(self._onPlayContextMenu)
        self.sl_previewImage.customContextMenuRequested.connect(lambda point: self._onTimeDisplayMenu(self.sl_previewImage, point))
        self.l_start.customContextMenuRequested.connect(lambda point: self._onTimeDisplayMenu(self.l_start, point))
        self.l_end.customContextMenuRequested.connect(lambda point: self._onTimeDisplayMenu(self.l_end, point))



    #############################
    #######   INTERNAL   ########

    @err_catcher(name=__name__)
    def _setStyleOverrides(self):
        '''Set custom style for the custom slider.'''

        ##   Handle
        self.sliderHandleSize = 16
        self.sliderHandleRadius = 8

        self.knob_gradCenter = "#5D7D91"
        self.knob_gradMid = "#405766"
        self.knob_gradOuter = "#1E2A30"

        self.knob_gradCenterStop = 0.00
        self.knob_gradMidStop = 0.65
        self.knob_gradRadius = 0.75

        self.knob_hoverBias = 20
        self.knob_pressedBias = 40

        #   Groove
        self.sliderGrooveHeight = 6
        self.sliderGrooveRadius = 3

        self.color_cacheFilled = "#465A78"
        self.color_sliderGrooveBorder = "#494949"
        self.color_sliderGrooveBG = "#232323"

        #   Dynamic cache gradient
        self.sliderCacheGradient = ""

        self._updateSliderStyle()


    def _biasColor(self, color: str, amount: int) -> str:
        '''Brighten (>0) or darken (<0) a hex color.
        
        Args:
            color (str): The hex color string (e.g., "#RRGGBB").
            amount (int): The amount to brighten (>0) or darken (<0) the color.

        Returns:
            str: The modified hex color string.
        '''

        color = color.lstrip("#")

        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))

        return f"#{r:02X}{g:02X}{b:02X}"


    def _buildKnobGradient(self, bias: int = 0) -> str:
        '''Builds a radial gradient for the slider knob.

        Args:
            bias (int, optional): The bias to apply to the gradient colors. Defaults to 0.

        Returns:
            str: The CSS radial gradient string.
        '''

        c0 = self._biasColor(self.knob_gradCenter, bias)
        c1 = self._biasColor(self.knob_gradMid, bias)
        c2 = self._biasColor(self.knob_gradOuter, bias)

        gradStyle = f"""
            qradialgradient(
                cx:0.5, cy:0.5,
                radius:{self.knob_gradRadius},
                fx:0.5, fy:0.5,
                stop:0 {c0},
                stop:{self.knob_gradMidStop} {c1},
                stop:1 {c2}
            )
        """

        return gradStyle


    @err_catcher(name=__name__)
    def _updateSliderStyle(self):
        '''Update the style of the slider based on the current settings.'''

        grooveBackground = (
            f"""
            qlineargradient(
                x1:0, y1:0,
                x2:1, y2:0,
                {self.sliderCacheGradient}
            )
            """
            if self.sliderCacheGradient else self.color_sliderGrooveBG
        )

        style = f"""
        QSlider::groove:horizontal {{
            border: 1px solid {self.color_sliderGrooveBorder};
            height: {self.sliderGrooveHeight}px;
            border-radius: {self.sliderGrooveRadius}px;
            background: {grooveBackground};
            margin: 0px;
        }}

        QSlider::handle:horizontal {{
            width: {self.sliderHandleSize}px;
            height: {self.sliderHandleSize}px;
            margin: -8px 0;

            border-radius: {self.sliderHandleRadius}px;
            border: 1px solid {self.knob_gradOuter};

            background: {self._buildKnobGradient()};
        }}

        QSlider::handle:horizontal:hover {{
            background: {self._buildKnobGradient(self.knob_hoverBias)};
        }}

        QSlider::handle:horizontal:pressed {{
            background: {self._buildKnobGradient(self.knob_pressedBias)};
        }}

        QSlider::handle:horizontal:disabled {{
            background: transparent;
            border: none;
        }}
        QSlider::sub-page:horizontal {{
            background: none;
        }}

        QSlider::add-page:horizontal {{
            background: none;
        }}
        """

        self.sl_previewImage.setStyleSheet(style)


    @err_catcher(name=__name__)
    def _onPlayContextMenu(self, point: QPoint):
        '''Show the playback settings popup.

        Args:
            point (QPoint): The point where the context menu should appear.
        '''

        self.Player.setTimelinePaused(True)

        #   Get Current Settings
        pData = {
            "fps_mode": self.Player.playback_fps_mode,
            "mode": self.Player.playback_mode,
            "missingFrameMode": self.Player.playback_missingFrameMode,
            "fps_custom": self.Player.playback_fps_custom
        }

        #   Create Popup Menu
        playMenu = PlaySettingsMenu(self.Player, pData, self)
        playMenu.settingsChanged.connect(self.Player.onPlaybackSettingsChanged)

        #   Get Button Position
        mousePos = self.b_play.mapToGlobal(point)

        #   Anchor to Button Position
        pos = Utils.getPopupPosition(playMenu, self, mousePos, adjustSize=True)
        playMenu.move(pos)

        #   Launch Popup
        playMenu.exec()


    @err_catcher(name=__name__)
    def _onTimeDisplayMenu(self, button: QObject, point: QPoint):
        '''Show the time display context menu.

        Args:
            button (QObject): The button that was clicked.
            point (QPoint): The point where the context menu should appear.
        '''

        self.Player.setTimelinePaused(True)

        #   Get Current Settings
        pData = {
            "frameDisplay_mode": self.Player.frameDisplay_mode
        }

        #   Create Popup Menu
        timeMenu = TimeDisplayMenu(self.Player, pData, self)
        timeMenu.settingsChanged.connect(self.Player.onFrameDisplayChanged)

        #   Get Button Position
        mousePos = button.mapToGlobal(point)

        #   Anchor to Button Position
        pos = Utils.getPopupPosition(timeMenu, self, mousePos, adjustSize=True)
        timeMenu.move(pos)

        #   Launch Popup
        timeMenu.exec()


    @err_catcher(name=__name__)
    def _getSliderWidth(self) -> int:
        '''Get the width of the preview image slider.

        Returns:
            int: The width of the slider in pixels.
        '''

        return self.sl_previewImage.width()


    @err_catcher(name=__name__)
    def _getFrameDisplayMode(self) -> str:
        '''Return the active frame display mode as a lowercase string.'''

        return str(getattr(self.Player, "frameDisplay_mode", "frames") or "frames").lower()


    @err_catcher(name=__name__)
    def _getFrameDisplayText(self, frameNumber: int) -> str:
        '''Return frame text for UI labels/spinbox based on the active display mode.

        Args:
            frameNumber (int): Source frame number.

        Returns:
            str: Frame number or formatted timecode.
        '''

        frameNumber = int(frameNumber)
        if self._getFrameDisplayMode() != "timecode":
            return str(frameNumber)

        timecode = self._frameToTimecode(frameNumber)
        return timecode if timecode else str(frameNumber)


    @err_catcher(name=__name__)
    def _parseFrameInput(self, text: str) -> int | None:
        '''Parse user-entered frame/timecode text to a source frame number.

        Args:
            text (str): User-entered text from the current-frame spinbox.

        Returns:
            int | None: Parsed source frame number, or None if parsing fails.
        '''

        if self._getFrameDisplayMode() != "timecode":
            return None

        timecodeInfo = self._getTimecodeReference()
        if not timecodeInfo:
            return None

        return Utils.timecodeToFrameNumber(text, timecodeInfo)


    @err_catcher(name=__name__)
    def _getTimecodeReference(self) -> dict[str, Any] | None:
        '''Build and return the active timecode reference for frame translations.

        Returns:
            dict[str, Any] | None: Timecode reference dictionary, or None if unavailable.
        '''

        mediaData = self.Player.MediaData
        timecodeStart = str(getattr(mediaData, "timecodeStart", "") or "").strip()
        fps = float(getattr(mediaData, "fps", 0.0) or 0.0)

        return Utils.getTimecodeReference(
            timecodeStart=timecodeStart,
            timecodeMode=str(getattr(mediaData, "timecodeMode", "") or ""),
            fps=fps,
            mediaStartFrame=int(getattr(mediaData, "pstart", 1) or 1),
        )


    @err_catcher(name=__name__)
    def _frameToTimecode(self, frameNumber: int) -> str | None:
        '''Convert a source frame number to display timecode if metadata is available.

        Args:
            frameNumber (int): Source frame number.

        Returns:
            str | None: Formatted timecode or None if conversion is unavailable.
        '''

        timecodeInfo = self._getTimecodeReference()
        if not timecodeInfo:
            return None

        return Utils.frameNumberToTimecode(frameNumber, timecodeInfo)


    #########################
    #######   API    ########

    @err_catcher(name=__name__)
    def setRange(self, start: int, end: int):
        '''Sets the range of the player controls slider.

        Args:
            start (int): The starting value of the range.
            end (int): The ending value of the range.
        '''

        self.sl_previewImage.setRange(start, end)
        self.sp_current.setMinimum(start)
        self.sp_current.setMaximum(end)
        self.refreshFrameDisplay()


    @err_catcher(name=__name__)
    def setFrame(self, frameNumber: int, blockSignals: bool = False):
        '''Sets the current frame number in the slider and spinbox.

        Args:
            frameNumber (int): The frame number to set.
            blockSignals (bool, optional): Whether to block signals during the update. Defaults to False.
        '''

        if blockSignals:
            with Utils.blockSignals(self.sl_previewImage, self.sp_current):
                self.sl_previewImage.setValue(frameNumber)
                self.sp_current.setValue(frameNumber)
        else:
            self.sl_previewImage.setValue(frameNumber)
            self.sp_current.setValue(frameNumber)


    @err_catcher(name=__name__)
    def getFrame(self) -> int:
        '''Gets the current frame number from the slider.

        Returns:
            int: The current frame number.
        '''

        return self.sl_previewImage.value()


    @err_catcher(name=__name__)
    def setPaused(self, paused: bool):
        '''Sets player controls playback UI for play/pause.

        Args:
            paused (bool): True if paused, False if playing.
        '''

        playTipText = "\n\n\nRight-click for Playback Options"

        if paused:
            self.l_currFPS.setText("")
            self.b_play.setIcon(self.playIcon)
            self.b_play.setToolTip(f"Play{playTipText}")
            
        else:
            self.b_play.setIcon(self.pauseIcon)
            self.b_play.setToolTip(f"Pause{playTipText}")


    @err_catcher(name=__name__)
    def updateFpsDisplay(self, selFPS: float, actFPS: float, direction: int):
        '''Sets the FPS display for the player controls.

        Args:
            selFPS (float): The selected FPS.
            actFPS (float): The actual FPS.
            direction (int): The playback direction. Positive for forward, negative for reverse.
        '''

        self.l_currFPS.setText(f"{selFPS:.2f} ({actFPS:.2f})")


    @err_catcher(name=__name__)
    def refreshFrameDisplay(self):
        '''Refresh start/end labels and the current spinbox text based on the active frame display mode.'''

        start = int(self.sl_previewImage.minimum())
        end = int(self.sl_previewImage.maximum())
        current = int(self.sp_current.value())

        self.l_start.setText(self._getFrameDisplayText(start))
        self.l_end.setText(self._getFrameDisplayText(end))

        with Utils.blockSignals(self.sp_current):
            self.sp_current.setValue(current)


    @err_catcher(name=__name__)
    def updateCacheSlider(self, frame=None, reset=False):
        '''Updates the cache slider based on the current cache state and optionally resets it.

        Args:
            frame (int, optional): The current frame index. Defaults to None.
            reset (bool, optional): Whether to reset the cache slider. Defaults to False.
        '''

        try:
            #   Reset and Calc Frames
            if reset or not self.Player.PreviewCache.Cache:
                total_frames = 1
                cachedFrames = [False]
                cachedFrameSet = set()
                cachedCount = 0
                cacheable_frames = 1

            else:
                total_frames = self.Player.PreviewCache.Cache.totalFrames
                cachedFrames = self.Player.PreviewCache.Cache.getCachedFrames()
                cachedFrameSet = set(cachedFrames)
                cachedCount = self.Player.PreviewCache.Cache.readyFrameCount
                cacheable_frames = getattr(self.Player.PreviewCache, "cacheableFrameCount", total_frames) or total_frames

            #   Set Sizing
            slider_width = max(1, self._getSliderWidth())
            slider_height = 6

        except Exception as e:
            logger.warning(f"ERROR: Unable to Update Cache Slider: {e}")
            return

        stops = []

        #   Build slider cache display based on frames and width
        try:
            for px in range(slider_width):
                frameIdx = min(total_frames - 1, int((px / max(1, slider_width - 1)) * total_frames))
                color = self.color_cacheFilled if frameIdx in cachedFrameSet else self.color_sliderGrooveBG
                ratio = px / slider_width
                stops.append(f"stop:{ratio} {color}")


            #   Store the cache gradient and rebuild the stylesheet
            self.sliderCacheGradient = ", ".join(stops)
            self._updateSliderStyle()

        except Exception as e:
            logger.warning(f"ERROR: Failed to Update Cache Slider Stylesheet: {e}")
        
        #   Update Tooltip

        tipSuffix = "\n\n\nRight-click to change time display (Frames/Timecode)"

        cached = max(0, cachedCount)

        if self.Player.b_cacheEnabled.isChecked():
            if self.Player.PreviewCache.Cache.cacheFull:
                status = "MAX CACHE"
            elif self.Player.PreviewCache.isRunning:
                status = "ACTIVE"
            elif cached == cacheable_frames:
                status = "COMPLETE"
            elif cached < cacheable_frames:
                status = "IDLE"
            else:
                status = "UNKNOWN"

            if status != "UNKNOWN":
                if cacheable_frames != total_frames:
                    gapCount = max(0, total_frames - cacheable_frames)
                    tip = f"{status}:  ({cached} of {cacheable_frames} source frames cached, {gapCount} gaps in range)"
                else:
                    tip = f"{status}:  ({cached} of {total_frames} frames in memory)"
            else:
                tip = "Cache: UNKNOWN"

        else:
            status = "DISABLED"
            tip = f"{status}:  ({cached} of {total_frames} frames in memory)" if cached > 0 else "Cache: DISABLED"

        tip += tipSuffix

        self.sl_previewImage.setToolTip(tip)
        self.Player.setCacheButtonStyle(status)



class TimeDisplaySpinBox(QSpinBox):
    '''Custom Spinbox for current time display in frames or timecode.
    
    Inherits from QSpinBox

    Args:
    ------
    - parent (QWidget, optional): The parent widget. Defaults to None.

    API:
    ------
    - setDisplayModeProvider(provider: callable): Set a callable that returns the current display mode ("frames" or "timecode").
    - setDisplayFormatter(formatter: callable): Set a callable that formats the display text for the current mode.
    - setTimecodeParser(parser: callable): Set a callable that parses a timecode string into an integer frame value.
    - textFromValue(value: int) -> str: Return the display text for the given value based on the current mode.
    - valueFromText(text: str) -> int: Return the integer value for the given display text based on the current mode.
    '''

    def __init__(self, parent=None):
        super().__init__(parent)

        self._modeProvider = None
        self._displayFormatter = None
        self._timecodeParser = None


    def setDisplayModeProvider(self, provider: callable):
        '''Set a callable that returns the current display mode ("frames" or "timecode").
        
        Args:
            provider (callable): A function that returns the current display mode as a string.
        '''

        self._modeProvider = provider


    def setDisplayFormatter(self, formatter: callable):
        '''Set a callable that formats the display text for the current mode.

        Args:
            formatter (callable): A function that takes an integer value and returns a formatted string.
        '''

        self._displayFormatter = formatter


    def setTimecodeParser(self, parser: callable):
        '''Set a callable that parses a timecode string into an integer frame value.

        Args:
            parser (callable): A function that takes a timecode string and returns an integer frame value.
        '''
        self._timecodeParser = parser


    def textFromValue(self, value: int) -> str:
        '''Return the display text for the given value based on the current mode.
        
        Args:
            value (int): The integer value to convert to display text.
        '''

        try:
            if callable(self._modeProvider) and self._modeProvider() == "timecode":
                if callable(self._displayFormatter):
                    text = self._displayFormatter(int(value))
                    if text:
                        return str(text)
        except Exception:
            pass

        return super().textFromValue(value)


    def valueFromText(self, text: str) -> int:
        '''Return the integer value for the given display text based on the current mode.
        
        Args:
            text (str): The display text to convert to an integer value.
        '''

        try:
            if callable(self._modeProvider) and self._modeProvider() == "timecode":
                if callable(self._timecodeParser):
                    value = self._timecodeParser(text)
                    if value is not None:
                        return int(value)
        except Exception:
            pass

        return super().valueFromText(text)



#######################################
#######     PLAY RCL MENU      ########

class PlaySettingsMenu(QDialog):
    '''Dialog for configuring playback settings of the preview player.
    
    Signals:
    ------
    - settingsChanged (dict): Emitted when the playback settings are changed.
    
    Args:
    ------
    - Player (PreviewPlayer_GL): The preview player instance.
    - pData (dict): The initial playback settings data.
    - parent (QWidget, optional): The parent widget. Defaults to None.
    '''


    settingsChanged = Signal(dict)


    def __init__(self, Player: 'PreviewPlayer_GL', pData: dict, parent=None):
        super().__init__(parent)

        self.Player = Player
        self.core: PrismCore = self.Player.core

        self.playback_fps_mode = pData.get("fps_mode", "auto")
        self.playback_fps_custom = pData.get("fps_custom", 24.0)
        self.playback_mode = pData.get("mode", "loop")
        self.playback_missingFrameMode = pData.get("missingFrameMode", "last")

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._setupUI()
        self._loadSettings()
        self._connections()


    def _setupUI(self):
        #   Main Layout
        lo_popup = QVBoxLayout(self)
        lo_popup.setContentsMargins(10, 10, 10, 10)
        lo_popup.setSpacing(10)

        ##  Playback FPS
        gb_fps = QGroupBox("Playback FPS")
        lo_fps = QGridLayout(gb_fps)
        lo_fps.setContentsMargins(6, 6, 6, 6)
        lo_fps.setHorizontalSpacing(12)
        lo_fps.setVerticalSpacing(4)

        bg_fps = QButtonGroup(gb_fps)

        self.rb_auto = QRadioButton("Auto")
        self.rb_media = QRadioButton("Media")
        self.rb_shot = QRadioButton("Shot")
        self.rb_project = QRadioButton("Project")
        self.rb_custom = QRadioButton("Custom")

        bg_fps.addButton(self.rb_auto)
        bg_fps.addButton(self.rb_media)
        bg_fps.addButton(self.rb_shot)
        bg_fps.addButton(self.rb_project)
        bg_fps.addButton(self.rb_custom)

        # FPS Labels
        l_auto = QLabel(Utils.formatFPS(self.Player.getAutoFPS()))
        l_media = QLabel(Utils.formatFPS(self.Player.getMediaFPS()))
        l_shot = QLabel(Utils.formatFPS(self.Player.getShotFPS()))
        l_project = QLabel(Utils.formatFPS(self.Player.getProjectFPS()))

        for lbl in (l_auto, l_media, l_shot, l_project):
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        #   Custom FPS Spin Box
        self.sp_fps = QDoubleSpinBox()
        self.sp_fps.setDecimals(2)
        self.sp_fps.setRange(0.10, 240.00)
        self.sp_fps.setSingleStep(0.01)
        self.sp_fps.setValue(24.00)
        self.sp_fps.setEnabled(False)
        self.sp_fps.setSuffix(" fps")

        self.rb_custom.toggled.connect(self.sp_fps.setEnabled)

        # FPS Layout
        lo_fps.addWidget(self.rb_auto, 0, 0)
        lo_fps.addWidget(l_auto, 0, 1)

        lo_fps.addWidget(self.rb_media, 1, 0)
        lo_fps.addWidget(l_media, 1, 1)

        lo_fps.addWidget(self.rb_shot, 2, 0)
        lo_fps.addWidget(l_shot, 2, 1)

        lo_fps.addWidget(self.rb_project, 3, 0)
        lo_fps.addWidget(l_project, 3, 1)

        lo_fps.addWidget(self.rb_custom, 4, 0)
        lo_fps.addWidget(self.sp_fps, 4, 1)

        lo_fps.setColumnStretch(0, 1)

        lo_popup.addWidget(gb_fps)

        ##  Playback Mode
        gb_mode = QGroupBox("Playback Mode")
        lo_mode = QVBoxLayout(gb_mode)

        bg_mode = QButtonGroup(gb_mode)

        self.rb_loop = QRadioButton("Loop")
        self.rb_once = QRadioButton("Once")
        self.rb_pingpong = QRadioButton("Ping-Pong")
        self.rb_reverse = QRadioButton("Reverse")

        bg_mode.addButton(self.rb_loop)
        bg_mode.addButton(self.rb_once)
        bg_mode.addButton(self.rb_pingpong)
        bg_mode.addButton(self.rb_reverse)

        self.rb_loop.setChecked(True)

        lo_mode.addWidget(self.rb_loop)
        lo_mode.addWidget(self.rb_once)
        lo_mode.addWidget(self.rb_pingpong)
        lo_mode.addWidget(self.rb_reverse)

        lo_popup.addWidget(gb_mode)

        ##  Missing Frame Mode
        gb_missingFrame = QGroupBox("Missing Frame Mode")
        lo_missingFrame = QVBoxLayout(gb_missingFrame)

        bg_missingFrame = QButtonGroup(gb_missingFrame)

        self.rb_hold_repeat = QRadioButton("Repeat Last Frame")
        self.rb_hold_black = QRadioButton("Black Frame")
        self.rb_hold_redX = QRadioButton("Red X Frame")

        bg_missingFrame.addButton(self.rb_hold_black)
        bg_missingFrame.addButton(self.rb_hold_redX)
        bg_missingFrame.addButton(self.rb_hold_repeat)

        self.rb_hold_repeat.setChecked(True)

        lo_missingFrame.addWidget(self.rb_hold_repeat)
        lo_missingFrame.addWidget(self.rb_hold_black)
        lo_missingFrame.addWidget(self.rb_hold_redX)

        lo_popup.addWidget(gb_missingFrame)

        ##  Bottom Buttons
        buttonLayout = QHBoxLayout()

        self.b_save = QPushButton("Save")
        self.b_cancel = QPushButton("Cancel")

        buttonLayout.addWidget(self.b_save)
        buttonLayout.addWidget(self.b_cancel)

        lo_popup.addLayout(buttonLayout)

        ##  Tooltips
        tip = "Plays Continuously in a Loop."
        self.rb_loop.setToolTip(tip)

        tip = "Plays Forward to the End and Stops."
        self.rb_once.setToolTip(tip)

        tip = "Plays Forward then Backward in a Loop."
        self.rb_pingpong.setToolTip(tip)

        tip = "Plays Reverse and Loops."
        self.rb_reverse.setToolTip(tip)

        tip = ("Automatically determines the FPS based on:\n\n"
               "Media FPS  (if able to determine)\n"
               "Shot FPS     (if set)\n"
               "Project FPS")
        self.rb_auto.setToolTip(tip)
        l_auto.setToolTip(tip)

        tip = ("Uses the Media's FPS if Video File or\n"
               "fallback to the Shot or Project FPS.")
        self.rb_media.setToolTip(tip)
        l_media.setToolTip(tip)

        tip = ("Shot's FPS set in the Shot Metadata or\n"
               "fallback to the Project FPS.")
        self.rb_shot.setToolTip(tip)
        l_shot.setToolTip(tip)

        tip = "Project's FPS set in the Prism Project Settings."
        self.rb_project.setToolTip(tip)
        l_project.setToolTip(tip)

        tip = "Select a Custom FPS for Playback."
        self.rb_custom.setToolTip(tip)
        self.sp_fps.setToolTip(tip)

        tip = "Repeats Last-Cached frame for Missing Frames."
        self.rb_hold_repeat.setToolTip(tip)

        tip = "Displays a Black Frame for Missing Frames."
        self.rb_hold_black.setToolTip(tip)

        tip = "Displays a Red X Frame for Missing Frames."
        self.rb_hold_redX.setToolTip(tip)


    def _loadSettings(self):
        '''Load the current playback settings into the UI elements.'''

        playFPS = self.playback_fps_mode
        if playFPS == "auto":
            self.rb_auto.setChecked(True)
        elif playFPS == "media":
            self.rb_media.setChecked(True)
        elif playFPS == "shot":
            self.rb_shot.setChecked(True)
        elif playFPS == "project":
            self.rb_project.setChecked(True)
        elif playFPS == "custom":
            self.rb_custom.setChecked(True)
            
        self.sp_fps.setValue(self.playback_fps_custom)

        playMode = self.playback_mode
        if playMode == "loop":
            self.rb_loop.setChecked(True)
        elif playMode == "once":
            self.rb_once.setChecked(True)
        elif playMode == "pingpong":
            self.rb_pingpong.setChecked(True)
        elif playMode == "reverse":
            self.rb_reverse.setChecked(True)

        missFrameMode = self.playback_missingFrameMode
        if missFrameMode == "last":
            self.rb_hold_repeat.setChecked(True)
        elif missFrameMode == "black":
            self.rb_hold_black.setChecked(True)
        elif missFrameMode == "redX":
            self.rb_hold_redX.setChecked(True)


    def _connections(self):
        self.b_save.clicked.connect(self._saveSettings)
        self.b_cancel.clicked.connect(self.close)


    def _saveSettings(self):
        '''Gets settings and Emits settingsChanged signal.'''

        pData = {
            "fpsMode": (
                "auto" if self.rb_auto.isChecked()
                else "media" if self.rb_media.isChecked()
                else "shot" if self.rb_shot.isChecked()
                else "project" if self.rb_project.isChecked()
                else "custom"
            ),
            "customFPS": self.sp_fps.value(),
            "playbackMode": (
                "once" if self.rb_once.isChecked()
                else "reverse" if self.rb_reverse.isChecked()
                else "pingpong" if self.rb_pingpong.isChecked()
                else "loop"
            ),
            "holdingFrameMode": (
                "black" if self.rb_hold_black.isChecked()
                else "redX" if self.rb_hold_redX.isChecked()
                else "last"
            )
        }

        self.settingsChanged.emit(pData)
        self.close()
   


#######################################
#######     PLAY RCL MENU      ########

class TimeDisplayMenu(QDialog):
    '''Dialog for configuring the time display of the preview player.
    
    Signals:
    ------
    - settingsChanged (dict): Emitted when the time display settings are changed.
    
    Args:
    ------
    - Player (PreviewPlayer_GL): The preview player instance.
    - pData (dict): The initial time display settings data.
    - parent (QWidget, optional): The parent widget. Defaults to None.
    '''


    settingsChanged = Signal(dict)


    def __init__(self, Player: 'PreviewPlayer_GL', pData: dict, parent=None):
        super().__init__(parent)

        self.Player = Player
        self.core: PrismCore = self.Player.core

        self.displayMode = pData.get("frameDisplay_mode", "frames")

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._setupUI()
        self._loadSettings()
        self._connections()


    def _setupUI(self):
        #   Main Layout
        lo_popup = QVBoxLayout(self)
        lo_popup.setContentsMargins(10, 10, 10, 10)
        lo_popup.setSpacing(10)

        ##  Time Display
        gb_timeDisp = QGroupBox("Time Display")
        lo_timeDisp = QGridLayout(gb_timeDisp)
        lo_timeDisp.setContentsMargins(6, 6, 6, 6)
        lo_timeDisp.setHorizontalSpacing(12)
        lo_timeDisp.setVerticalSpacing(4)

        bg_timeDisp = QButtonGroup(gb_timeDisp)

        self.rb_frames = QRadioButton("Frames")
        self.rb_timecode = QRadioButton("Timecode")

        bg_timeDisp.addButton(self.rb_frames)
        bg_timeDisp.addButton(self.rb_timecode)

        self.rb_frames.setChecked(True)

        lo_timeDisp.addWidget(self.rb_frames, 0, 0)
        lo_timeDisp.addWidget(self.rb_timecode, 1, 0)

        lo_popup.addWidget(gb_timeDisp)

        ##  Bottom Buttons
        buttonLayout = QHBoxLayout()

        self.b_save = QPushButton("Save")
        self.b_cancel = QPushButton("Cancel")

        buttonLayout.addWidget(self.b_save)
        buttonLayout.addWidget(self.b_cancel)

        lo_popup.addLayout(buttonLayout)

        tip = "Display Frame Numbers"
        self.rb_frames.setToolTip(tip)

        tip = "Display Timecode (if available)"
        self.rb_timecode.setToolTip(tip)


    def _loadSettings(self):
        '''Load the current playback settings into the UI elements.'''

        if self.displayMode == "timecode":
            self.rb_timecode.setChecked(True)

        else:
            self.rb_frames.setChecked(True)


    def _connections(self):
        self.b_save.clicked.connect(self._saveSettings)
        self.b_cancel.clicked.connect(self.close)


    def _saveSettings(self):
        '''Gets settings and Emits settingsChanged signal.'''

        pData = {
            "frameDisplay_mode": "frames" if self.rb_frames.isChecked() else "timecode",
        }

        self.settingsChanged.emit(pData)
        self.close()

