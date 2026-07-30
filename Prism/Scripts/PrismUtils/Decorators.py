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


import sys
import traceback
import time
import logging
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


logger = logging.getLogger(__name__)

T = TypeVar('T')


def err_handler(func: Callable[..., T], name: str = "", plugin: bool = False) -> Callable[..., T]:
    """Wrap a function with error handling and logging capabilities.
    
    Creates a wrapper that catches exceptions and logs them through the Prism
    error reporting system. Collects version information from the core, app plugin,
    and regular plugins to include in error reports. Prevents duplicate error
    popups within 1-second intervals.
    
    Args:
        func: The function to wrap with error handling
        name: Name identifier for the error logs
        plugin: Whether this is a plugin function (affects error handling)
        
    Returns:
        Wrapped function that catches and logs exceptions
    """
    @wraps(func)
    def func_wrapper(*args, **kwargs) -> Any:
        """Wrapper function that executes the decorated function with error handling.
        
        Args:
            *args: Variable positional arguments passed to wrapped function
            **kwargs: Variable keyword arguments passed to wrapped function
            
        Returns:
            Return value from the wrapped function
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            if hasattr(args[0], "core"):
                core = args[0].core
            else:
                core = None
                logger.warning("object %s has no core" % args[0])

            data = {}
            versionStr = ""
            if core:
                versionStr += "\nCore: %s" % core.version
                data["version"] = core.version

            if core and getattr(args[0].core, "appPlugin", None):
                data["appPlugin"] = args[0].core.appPlugin.pluginName
                data["appPluginVersion"] = args[0].core.appPlugin.version
                versionStr += "\nApp plugin: %s %s" % (
                    data["appPlugin"],
                    data["appPluginVersion"],
                )
            if getattr(args[0], "plugin", None):
                data["plugin"] = args[0].plugin.pluginName
                data["pluginVersion"] = args[0].plugin.version
                versionStr += "\nPlugin: %s %s" % (
                    data["plugin"],
                    data["pluginVersion"],
                )

            erStr = "%s ERROR - %s\n%s\n\n%s\n\n%s" % (
                time.strftime("%d/%m/%y %X"),
                name,
                versionStr,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )

            if not core:
                raise Exception(erStr)

            ltime = getattr(args[0].core, "lastErrorTime", 0)
            if (time.time() - ltime) > 1:
                isGuiThread = (
                    QApplication.instance()
                    and QApplication.instance().thread() == QThread.currentThread()
                )
                if isGuiThread:
                    args[0].core.writeErrorLog(erStr, data=data)
                else:
                    raise Exception(erStr)

    return func_wrapper


def err_catcher(name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory for standard error catching.
    
    Creates an error catching decorator with the specified name identifier.
    
    Args:
        name: Name identifier for error logs
        
    Returns:
        Decorator function that wraps functions with error handling
    """
    return lambda x, y=name, z=False: err_handler(x, name=y, plugin=z)


def err_catcher_plugin(name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory for plugin error catching.
    
    Creates an error catching decorator specifically for plugin functions.
    
    Args:
        name: Name identifier for error logs
        
    Returns:
        Decorator function that wraps plugin functions with error handling
    """
    return lambda x, y=name, z=True: err_handler(x, name=y, plugin=z)


def err_catcher_standalone(name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory for standalone error catching without core dependency.
    
    Creates an error catching decorator for standalone scripts that don't have
    access to the Prism core. Errors are logged to console and displayed in
    a message box.
    
    Args:
        name: Name identifier for error logs
        
    Returns:
        Decorator function that wraps standalone functions with error handling
    """
    def err_decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Inner decorator that wraps the target function.
        
        Args:
            func: Function to wrap with error handling
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        def func_wrapper(*args, **kwargs) -> Any:
            """Wrapper that executes function with error handling.
            
            Args:
                *args: Variable positional arguments
                **kwargs: Variable keyword arguments
                
            Returns:
                Return value from wrapped function
            """
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - %s %s:\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    name,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                print(erStr)
                QMessageBox.warning(None, "Prism", erStr)

        return func_wrapper

    return err_decorator


def timmer(name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory for timing function execution.
    
    Creates a decorator that logs the start time, end time, and total duration
    of function execution. Useful for performance profiling.
    
    Args:
        name: Name identifier for timing logs
        
    Returns:
        Decorator function that wraps functions with execution timing
    """
    def timer_decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Inner decorator that wraps the target function.
        
        Args:
            func: Function to wrap with timing
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        def func_wrapper(*args, **kwargs) -> None:
            """Wrapper that times function execution.
            
            Args:
                *args: Variable positional arguments
                **kwargs: Variable keyword arguments
            """
            startTime = datetime.now()
            logger.info("starttime: %s" % startTime.strftime("%Y-%m-%d %H:%M:%S"))
            func(*args, **kwargs)
            endTime = datetime.now()
            logger.info("endtime: %s" % endTime.strftime("%Y-%m-%d %H:%M:%S"))
            logger.info("duration: %s" % (endTime - startTime))

        return func_wrapper

    return timer_decorator
