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
# Copyright (C) 2023-2026 Prism Software GmbH
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


from .prism import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .config import get_comfy_config_path, get_user_pref_dir
import os
import json
import sys
import subprocess
import time
import threading
import tempfile
import glob
import shutil
import asyncio
import signal
import atexit
import urllib.error
import urllib.request
from aiohttp import ClientConnectorError, ClientError, ClientSession, ClientTimeout, web
from server import PromptServer

WEB_DIRECTORY = "./js"
_PIPE_DRAIN_THREADS = []
_SETUP_PROCESSES = {}
_SETUP_JOBS = {}
_SETUP_LOCK = threading.RLock()
_CONTEXT_PROCESS = None
_CONTEXT_LOCK = threading.RLock()
_CONTEXT_SHUTDOWN = threading.Event()
PRISM_SETUP_SCRIPT_URL = "https://service.prism-pipeline.com/api/service/setup_comfy"


def _get_comfyui_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_comfy_config_path():
    return get_comfy_config_path()


def _read_comfy_config():
    try:
        with open(_get_comfy_config_path(), "r") as config_file:
            data = json.load(config_file)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _find_plugin_root(prism_root, configured_plugin_root=""):
    candidates = [
        configured_plugin_root,
        os.getenv("PRISM_COMFYUI_PLUGIN_ROOT", ""),
        os.path.join(prism_root, "Plugins", "Apps", "ComfyUI"),
        os.path.join(prism_root, "Plugins", "ComfyUI"),
        "C:/ProgramData/Prism2/plugins/ComfyUI",
    ]
    for candidate in candidates:
        script_path = os.path.join(candidate, "Scripts", "Prism_ComfyUI_MenuTools.py")
        if candidate and os.path.isfile(script_path):
            return os.path.normpath(candidate)

    return ""


def _get_prism_python_executable(prism_root):
    executables = ("Prism.exe", "python.exe") if sys.platform == "win32" else (
        "bin/python", "bin/python3"
    )
    for executable in executables:
        candidate = os.path.join(prism_root, "Python313", executable)
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


def _is_prism_root(prism_root):
    return (
        prism_root
        and os.path.isabs(prism_root)
        and os.path.isdir(prism_root)
        and os.path.isfile(os.path.join(prism_root, "Scripts", "PrismCore.py"))
    )


def _get_downloaded_prism_folders():
    return sorted(
        glob.glob(os.path.join(get_user_pref_dir(), "versions", "v*")), reverse=True
    )


def _find_prism_root(configured_root=""):
    candidates = [
        os.getenv("PRISM_ROOT", ""),
        configured_root,
        "C:/Program Files/Prism2",
    ]
    candidates += sorted(
        glob.glob("C:/Program Files/Prism Pipeline/v*"), reverse=True
    )
    candidates += _get_downloaded_prism_folders()

    for candidate in candidates:
        prism_root = os.path.normpath(os.path.expandvars(os.path.expanduser(candidate)))
        if _is_prism_root(prism_root):
            return prism_root
    return ""


def _find_downloaded_prism_root():
    for candidate in _get_downloaded_prism_folders():
        prism_root = os.path.normpath(candidate)
        if _is_prism_root(prism_root):
            return prism_root
    return ""


def _get_latest_downloaded_prism_folder():
    candidates = _get_downloaded_prism_folders()
    return os.path.normpath(candidates[0]) if candidates else ""


def _get_prism_launch_config():
    config = _read_comfy_config()
    prism_root = _find_prism_root(config.get("prism_root", ""))
    if not prism_root:
        return None

    python_executable = _get_prism_python_executable(prism_root)
    plugin_root = _find_plugin_root(prism_root, config.get("plugin_root", ""))
    if not python_executable or not plugin_root:
        return None

    script_path = os.path.join(plugin_root, "Scripts", "Prism_ComfyUI_MenuTools.py")

    return {
        "python_executable": python_executable,
        "script_path": script_path,
        "script_args": [prism_root],
        "cwd": prism_root,
    }


def _save_prism_root(prism_root):
    prism_root = os.path.normpath(os.path.expandvars(os.path.expanduser(str(prism_root or "").strip())))
    print(f"[Prism] Validating selected Prism root: {prism_root}")
    if not _is_prism_root(prism_root):
        return False, "Select a Prism installation folder containing Scripts/PrismCore.py."

    plugin_root = _find_plugin_root(prism_root, _read_comfy_config().get("plugin_root", ""))
    if not plugin_root:
        print("[Prism] Prism ComfyUI plugin was not found for the selected root.")
        return False, "The Prism ComfyUI plugin could not be found for this installation."

    config_path = _get_comfy_config_path()
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)

    config = _read_comfy_config()
    config["prism_root"] = prism_root
    config["plugin_root"] = plugin_root
    with open(config_path, "w") as config_file:
        json.dump(config, config_file, indent=4)

    print(f"[Prism] Saved Prism configuration to {config_path}: root={prism_root}, plugin={plugin_root}")

    return True, ""


def _browse_for_prism_root():
    if os.name != "nt":
        print("[Prism] Folder picker is only available on Windows.")
        return ""

    print("[Prism] Opening modern Prism installation folder picker.")
    command = r'''
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace PrismFolderPicker {
    [Flags]
    enum FileOpenOptions : uint {
        PickFolders = 0x00000020,
        ForceFileSystem = 0x00000040
    }

    enum ShellDisplayName : uint {
        FileSystemPath = 0x80058000
    }

    [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IShellItem {
        void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
        void GetParent(out IShellItem ppsi);
        void GetDisplayName(ShellDisplayName sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);
        void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
        void Compare(IShellItem psi, uint hint, out int piOrder);
    }

    [ComImport, Guid("42F85136-DB7E-439C-85F1-E4075D135FC8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IFileDialog {
        [PreserveSig] int Show(IntPtr parent);
        void SetFileTypes(uint count, IntPtr filters);
        void SetFileTypeIndex(uint index);
        void GetFileTypeIndex(out uint index);
        void Advise(IntPtr events, out uint cookie);
        void Unadvise(uint cookie);
        void SetOptions(FileOpenOptions options);
        void GetOptions(out FileOpenOptions options);
        void SetDefaultFolder(IShellItem folder);
        void SetFolder(IShellItem folder);
        void GetFolder(out IShellItem folder);
        void GetCurrentSelection(out IShellItem item);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string name);
        void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string name);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string title);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string text);
        void GetResult(out IShellItem item);
        void AddPlace(IShellItem item, int location);
        void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string extension);
        void Close(int result);
        void SetClientGuid(ref Guid guid);
        void ClearClientData();
        void SetFilter(IntPtr filter);
    }

    [ComImport, Guid("D57C7288-D4AD-4768-BE02-9D969532D960"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IFileOpenDialog : IFileDialog { }

    [ComImport, Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    class FileOpenDialog { }

    public static class Picker {
        public static string SelectFolder() {
            IFileOpenDialog dialog = (IFileOpenDialog)new FileOpenDialog();
            try {
                FileOpenOptions options;
                dialog.GetOptions(out options);
                dialog.SetOptions(options | FileOpenOptions.PickFolders | FileOpenOptions.ForceFileSystem);
                dialog.SetTitle("Select your Prism installation folder");
                if (dialog.Show(IntPtr.Zero) != 0) return "";

                IShellItem item;
                dialog.GetResult(out item);
                try {
                    string path;
                    item.GetDisplayName(ShellDisplayName.FileSystemPath, out path);
                    return path ?? "";
                } finally {
                    Marshal.ReleaseComObject(item);
                }
            } finally {
                Marshal.ReleaseComObject(dialog);
            }
        }
    }
}
'@
[PrismFolderPicker.Picker]::SelectFolder()
'''
    result = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    prism_root = result.stdout.strip() if result.returncode == 0 else ""
    print(
        "[Prism] Folder picker finished: returncode=%s, selected=%s, stderr=%s"
        % (result.returncode, bool(prism_root), result.stderr.strip())
    )
    return prism_root


def _download_and_run_prism_setup(setup_job=None):
    if setup_job and setup_job["cancelled"].is_set():
        raise InterruptedError("Prism setup was cancelled.")
    print(f"[Prism] Downloading ComfyUI setup script from {PRISM_SETUP_SCRIPT_URL}")
    request = urllib.request.Request(
        PRISM_SETUP_SCRIPT_URL, headers={"User-Agent": "Prism-ComfyUI"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise RuntimeError("Setup service returned HTTP %s." % status)
        content = response.read()
    if not content:
        raise RuntimeError("Setup service returned an empty script.")
    setup_dir = tempfile.mkdtemp(prefix="prism-comfy-setup-")
    setup_path = os.path.join(setup_dir, "PrismSetup.py")
    result_path = os.path.join(setup_dir, "result.json")
    try:
        with open(setup_path, "wb") as setup_file:
            setup_file.write(content)
        with _SETUP_LOCK:
            if setup_job and setup_job["cancelled"].is_set():
                raise InterruptedError("Prism setup was cancelled.")
            result = _run_python_script(
                sys.executable, setup_path, cwd=setup_dir, track_setup=True,
                setup_result_path=result_path,
            )
            if setup_job:
                setup_job["pid"] = result["pid"]
                _SETUP_PROCESSES[result["pid"]]["job"] = setup_job
            return result
    except Exception:
        shutil.rmtree(setup_dir, ignore_errors=True)
        raise


def _cleanup_setup_process(setup_pid):
    with _SETUP_LOCK:
        setup_process = _SETUP_PROCESSES.pop(setup_pid, None)
        if not setup_process:
            return
        job = setup_process.get("job")
        if job:
            _SETUP_JOBS.pop(job["id"], None)
    result_path = setup_process.get("result_path")
    if result_path:
        shutil.rmtree(os.path.dirname(result_path), ignore_errors=True)


def _cancel_prism_setup(setup_id=None, setup_pid=None):
    with _SETUP_LOCK:
        if setup_id:
            job = _SETUP_JOBS.setdefault(setup_id, {
                "id": setup_id, "cancelled": threading.Event(), "pid": None,
            })
            job["cancelled"].set()
            setup_pid = job["pid"]
        setup_process = _SETUP_PROCESSES.get(setup_pid)
        if not setup_process:
            return
        setup_process["cancelled"] = True
        if setup_process.get("job"):
            setup_process["job"]["cancelled"].set()
    process = setup_process["process"]
    if process.poll() is None:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True, text=True, check=False, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode and process.poll() is None:
                raise RuntimeError("Unable to stop Prism setup.")
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=30)
    _cleanup_setup_process(setup_pid)


def _drain_pipe_to_console(pipe, label, setup_process=None):
    try:
        for line in iter(pipe.readline, ""):
            line = line.rstrip()
            if line:
                print(f"[Prism:{label}] {line}")
                if setup_process is not None:
                    setup_process["messages"] = (setup_process["messages"] + [line])[-20:]
                    if setup_process.get("context"):
                        startup_error = _get_context_startup_error(line)
                        if startup_error:
                            setup_process["error"] = startup_error
                    progress = _get_setup_progress(line)
                    if progress:
                        setup_process["progress"] = progress
    except Exception as e:
        print(f"[Prism] Failed to drain {label}: {e}")
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _get_context_startup_error(line):
    message = line.lower()
    if "10048" in message or "address already in use" in message or "errno 98" in message:
        return "Port 8765 is already in use. Close other Prism ComfyUI sessions, then try again."
    if "error calling python override" in message or "fatal python error" in message:
        return "Prism encountered an error during startup. Check the ComfyUI console for details."
    return None


def _get_setup_progress(line):
    message = line.lower()
    if "dependencies" in message or "pip install" in message or "installing packages" in message or "collecting " in message:
        return "Installing Python dependencies..."
    if "setting up" in message and "python" in message or "python.org/ftp/python" in message or "portable python" in message:
        return "Installing Python 3.13..."
    if "downloading prism" in message or "downloading repository" in message:
        return "Downloading Prism..."
    if "extraction complete" in message or "moving prism" in message:
        return "Installing Prism..."
    if "shortcut" in message:
        return "Finishing Prism setup..."
    if "completed successfully" in message or "already installed" in message:
        return "Checking the Prism installation..."
    return None


def _start_process_pipe_drainers(process, setup_process=None):
    global _PIPE_DRAIN_THREADS
    _PIPE_DRAIN_THREADS = [t for t in _PIPE_DRAIN_THREADS if t.is_alive()]

    for label, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
        if pipe is None:
            continue

        thread = threading.Thread(
            target=_drain_pipe_to_console,
            args=(pipe, label, setup_process),
            daemon=True,
        )
        thread.start()
        _PIPE_DRAIN_THREADS.append(thread)


def _run_python_script(python_executable, script_path, script_args=None, cwd=None, track_setup=False, setup_result_path=None, track_context=False):
    global _CONTEXT_PROCESS
    if not python_executable:
        raise ValueError("Missing python_executable")

    if not script_path:
        raise ValueError("Missing script_path")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    args = [python_executable, script_path]
    if script_args:
        args.extend([str(arg) for arg in script_args])

    popen_kwargs = {"cwd": cwd or None}
    if track_setup or track_context:
        popen_kwargs["stdin"] = subprocess.DEVNULL
        popen_kwargs["env"] = dict(os.environ, PYTHONUNBUFFERED="1")
        if track_context:
            popen_kwargs["env"]["PRISM_COMFYUI_ROOT"] = _get_comfyui_root()
        if setup_result_path:
            popen_kwargs["env"]["PRISM_COMFYUI_SETUP_RESULT"] = setup_result_path
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    elif track_setup or track_context:
        popen_kwargs["start_new_session"] = True

    print(f"[Prism] Running Python script: {args} with cwd={cwd}")
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **popen_kwargs,
    )
    setup_process = None
    if track_setup:
        setup_process = {
            "process": process, "messages": [], "result_path": setup_result_path,
            "progress": "Downloading Prism...",
        }
        _SETUP_PROCESSES[process.pid] = setup_process
    elif track_context:
        setup_process = {
            "process": process, "messages": [], "context": True, "error": "",
            "prism_root": str(script_args[0]) if script_args else cwd or "",
            "plugin_root": os.path.dirname(os.path.dirname(script_path)),
        }
        _CONTEXT_PROCESS = setup_process
    _start_process_pipe_drainers(process, setup_process=setup_process)
    if process.poll() is not None:  # Check if the process has terminated
        print(f"[Prism] Process terminated immediately: {args}")

    return {"pid": process.pid, "command": args}


async def _probe_prism_context(prism_root):
    try:
        async with ClientSession(timeout=ClientTimeout(total=5)) as session:
            async with session.ws_connect("ws://localhost:8765") as socket:
                await socket.send_json({"action": "get_context_identity"})
                identity = await socket.receive_json(timeout=1)
    except ClientConnectorError:
        return None
    except asyncio.TimeoutError:
        return {"error": "Timed out checking the local Prism context on port 8765. The port may be unavailable or blocked."}
    except (ClientError, ValueError, TypeError):
        return {"error": "Port 8765 is already in use by a service that did not identify itself as Prism."}
    if not isinstance(identity, dict) or identity.get("protocol") != "prism-comfyui-context-v1":
        return {"error": "Port 8765 is already in use by an unidentified service."}
    normalize = lambda path: os.path.normcase(os.path.realpath(path)) if isinstance(path, str) and path else ""
    if (
        normalize(identity.get("prism_root")) != normalize(prism_root)
        or normalize(identity.get("comfyui_root")) != normalize(_get_comfyui_root())
    ):
        raise RuntimeError("Port 8765 belongs to a different Prism or ComfyUI installation. Close that session before starting this one.")
    pid = identity.get("pid")
    if type(pid) is not int or pid <= 0:
        return {"error": "The existing Prism context returned an invalid process ID."}
    return {"pid": pid, "already_running": True, "reused": True, "closing": bool(identity.get("closing"))}


def _find_existing_prism_context(prism_root):
    deadline = time.monotonic() + 20
    while not _CONTEXT_SHUTDOWN.is_set():
        context = asyncio.run(_probe_prism_context(prism_root))
        if context is None:
            return None
        if context.get("pid") and not context.get("closing"):
            return context
        if time.monotonic() >= deadline:
            raise RuntimeError(context.get("error") or "The previous Prism context is still shutting down. Try again shortly.")
        delay = min(16, max(0, deadline - time.monotonic())) if context.get("error") else 0.25
        _CONTEXT_SHUTDOWN.wait(delay)
    raise RuntimeError("ComfyUI is shutting down.")


def _launch_prism_context(python_executable, script_path, script_args=None, cwd=None):
    with _CONTEXT_LOCK:
        if _CONTEXT_SHUTDOWN.is_set():
            raise RuntimeError("ComfyUI is shutting down.")
        if _CONTEXT_PROCESS and _CONTEXT_PROCESS["process"].poll() is None:
            if _CONTEXT_PROCESS.get("error"):
                raise RuntimeError(_CONTEXT_PROCESS["error"])
            return {"pid": _CONTEXT_PROCESS["process"].pid, "already_running": True}
        existing = _find_existing_prism_context(str(script_args[0]) if script_args else cwd or "")
        if existing:
            return existing
        if _CONTEXT_SHUTDOWN.is_set():
            raise RuntimeError("ComfyUI is shutting down.")
        return _run_python_script(
            python_executable, script_path, script_args, cwd, track_context=True,
        )


def _stop_prism_context():
    global _CONTEXT_PROCESS
    state = _CONTEXT_PROCESS
    if not state:
        return
    process = state["process"]
    if process.poll() is None:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True, text=True, check=False, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode and process.poll() is None:
                raise RuntimeError("Unable to stop Prism.")
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                raise RuntimeError("Prism did not stop in time.")
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
    _CONTEXT_PROCESS = None


def _control_prism_context(restart=False):
    with _CONTEXT_LOCK:
        config = _get_prism_launch_config() if restart else None
        if restart and not config:
            raise RuntimeError("Prism is not configured on this machine.")
        _stop_prism_context()
        if restart:
            return _launch_prism_context(**config)
        return {"stopped": True}


def _shutdown_prism_context():
    _CONTEXT_SHUTDOWN.set()
    try:
        with _CONTEXT_LOCK:
            _stop_prism_context()
    except Exception as error:
        print(f"[Prism] Unable to stop Prism during ComfyUI shutdown: {error}")


async def _on_comfyui_shutdown(app):
    await asyncio.to_thread(_shutdown_prism_context)


atexit.register(_shutdown_prism_context)
_comfyui_app = getattr(PromptServer.instance, "app", None)
if _comfyui_app is not None:
    _comfyui_app.on_shutdown.append(_on_comfyui_shutdown)


def _get_prism_status_data():
    with _CONTEXT_LOCK:
        state = _CONTEXT_PROCESS
        running = bool(state and state["process"].poll() is None)
        config = _read_comfy_config()
        prism_root = state.get("prism_root", "") if running else ""
        if not _is_prism_root(prism_root):
            prism_root = _find_prism_root(config.get("prism_root", ""))
        plugin_root = _find_plugin_root(
            prism_root,
            state.get("plugin_root", "") if running else config.get("plugin_root", ""),
        )
        result = {
            "success": True, "running": running, "managed": running,
            "pid": state["process"].pid if running else None,
            "prism_root": prism_root, "plugin_root": plugin_root,
            "error": state.get("error", "") if state else "",
        }
    return result


@PromptServer.instance.routes.get("/prism/get_status")
async def get_prism_status(request):
    return web.json_response(await asyncio.to_thread(_get_prism_status_data))


@PromptServer.instance.routes.post("/prism/stop_context")
async def stop_prism_context(request):
    try:
        result = await asyncio.to_thread(_control_prism_context)
        return web.json_response({"success": True, **result})
    except Exception as error:
        return web.json_response({"success": False, "error": str(error)}, status=500)


@PromptServer.instance.routes.post("/prism/restart_context")
async def restart_prism_context(request):
    try:
        result = await asyncio.to_thread(_control_prism_context, True)
        return web.json_response({"success": True, **result})
    except Exception as error:
        return web.json_response({"success": False, "error": str(error)}, status=500)


@PromptServer.instance.routes.get("/prism/get_context_status")
async def get_context_status(request):
    state = _CONTEXT_PROCESS
    try:
        requested_pid = int(request.query.get("pid"))
    except (TypeError, ValueError):
        return web.json_response({"success": False, "error": "Invalid Prism process ID."}, status=400)
    if not state or state["process"].pid != requested_pid:
        config = _get_prism_launch_config()
        if config:
            try:
                context = await _probe_prism_context(config["cwd"])
                if context and context.get("pid") == requested_pid and not context.get("closing"):
                    return web.json_response({"success": True, "running": True, "error": "", "reused": True})
            except RuntimeError as error:
                return web.json_response({"success": False, "running": False, "error": str(error)})
        return web.json_response({"success": False, "running": False, "error": "The Prism startup process could not be found. Please try again."})
    running = state["process"].poll() is None
    error = state.get("error", "")
    if not running and not error:
        error = "Prism closed before it could connect. Check the ComfyUI console for details."
    return web.json_response({"success": not bool(error), "running": running, "error": error})


@PromptServer.instance.routes.get("/prism/get_comfyui_root")
async def get_comfyui_root(request):
    try:
        return web.json_response({
            "success": True,
            "comfyui_root": _get_comfyui_root()
        })
    except Exception as e:
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


@PromptServer.instance.routes.get("/prism/get_launch_config")
async def get_launch_config(request):
    config = _get_prism_launch_config()
    if not config:
        return web.json_response({
            "success": False,
            "requires_prism_path": True,
            "error": "Prism is not configured on this machine.",
        })

    return web.json_response({
        "success": True,
        **config,
    })


@PromptServer.instance.routes.post("/prism/configure_prism_root")
async def configure_prism_root(request):
    try:
        data = await request.json()
    except (ValueError, json.JSONDecodeError):
        print("[Prism] Prism configuration request contained invalid JSON.")
        return web.json_response({"success": False, "error": "Invalid request data."}, status=400)

    print(f"[Prism] Received Prism configuration request: {data.get('prism_root')}")
    success, error = _save_prism_root(data.get("prism_root"))
    print(f"[Prism] Prism configuration request completed: success={success}, error={error}")
    return web.json_response({"success": success, "error": error}, status=200 if success else 400)


@PromptServer.instance.routes.post("/prism/browse_prism_root")
async def browse_prism_root(request):
    print("[Prism] Received folder picker request.")
    prism_root = _browse_for_prism_root()
    print("[Prism] Folder picker request completed: selected=%s" % bool(prism_root))
    return web.json_response({"success": bool(prism_root), "prism_root": prism_root})


@PromptServer.instance.routes.post("/prism/download_prism_setup")
async def download_prism_setup(request):
    setup_job = None
    try:
        data = await request.json()
        setup_id = str(data.get("setup_id") or "")
        if not setup_id or len(setup_id) > 128:
            return web.json_response({"success": False, "error": "Invalid setup request."}, status=400)
        with _SETUP_LOCK:
            setup_job = _SETUP_JOBS.setdefault(setup_id, {
                "id": setup_id, "cancelled": threading.Event(), "pid": None,
            })
        print("[Prism] Received ComfyUI setup download request.")
        result = await asyncio.to_thread(_download_and_run_prism_setup, setup_job)
        print(f"[Prism] Started ComfyUI setup process: pid={result['pid']}")
        return web.json_response({"success": True, **result})
    except InterruptedError:
        return web.json_response({"success": False, "cancelled": True})
    except Exception as error:
        print(f"[Prism] Failed to download or start ComfyUI setup: {error}")
        return web.json_response({"success": False, "error": "Unable to start Prism setup. Check the ComfyUI console and try again."}, status=500)
    finally:
        if setup_job and setup_job["pid"] is None:
            with _SETUP_LOCK:
                _SETUP_JOBS.pop(setup_job["id"], None)


@PromptServer.instance.routes.post("/prism/cancel_prism_setup")
async def cancel_prism_setup(request):
    try:
        data = await request.json()
        setup_id = str(data.get("setup_id") or "")
        setup_pid = int(data["pid"]) if data.get("pid") is not None else None
        if (not setup_id and setup_pid is None) or len(setup_id) > 128:
            raise ValueError("Invalid setup request.")
    except (TypeError, ValueError, json.JSONDecodeError):
        return web.json_response({"success": False, "error": "Invalid setup request."}, status=400)
    try:
        await asyncio.to_thread(_cancel_prism_setup, setup_id, setup_pid)
        return web.json_response({"success": True, "cancelled": True})
    except Exception as error:
        print(f"[Prism] Could not stop setup: {error}")
        return web.json_response({"success": False, "error": "Unable to stop setup. Check the ComfyUI console."}, status=500)


@PromptServer.instance.routes.post("/prism/complete_prism_setup")
async def complete_prism_setup(request):
    try:
        data = await request.json()
        setup_pid = int(data.get("pid"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return web.json_response({"success": False, "error": "Invalid setup process ID."}, status=400)

    setup_process = _SETUP_PROCESSES.get(setup_pid)
    if not setup_process:
        return web.json_response({"success": False, "error": "Prism setup process was not found."}, status=404)

    process = setup_process["process"]
    if setup_process.get("cancelled"):
        return web.json_response({"success": False, "installed": False, "cancelled": True})
    message = setup_process.get("progress", "Installing Prism...")
    return_code = process.poll()
    if return_code is None:
        return web.json_response({"success": False, "installed": False, "running": True, "message": message})
    if return_code != 0:
        _cleanup_setup_process(setup_pid)
        return web.json_response({
            "success": False,
            "installed": False,
            "error": "Prism setup failed. Check the ComfyUI console for details, then try again.",
        }, status=500)

    prism_root = ""
    result_path = setup_process.get("result_path")
    try:
        if not result_path:
            raise RuntimeError("Prism setup did not provide an installation result.")
        with open(result_path, encoding="utf-8") as result_file:
            prism_root = json.load(result_file)["prism_root"]
        success, error = _save_prism_root(prism_root)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exception:
        print(f"[Prism] Setup completion failed: {exception}")
        success, error = False, "Prism setup could not be completed. Check the ComfyUI console and try again."
    finally:
        _cleanup_setup_process(setup_pid)
    print(f"[Prism] Setup completion check: root={prism_root}, success={success}")
    return web.json_response({
        "success": success,
        "installed": success,
        "prism_root": prism_root,
        "error": error,
    }, status=200 if success else 500)


@PromptServer.instance.routes.post("/prism/run_python_script")
async def run_python_script(request):
    data = None
    try:
        data = await request.json()
        python_executable = data.get("python_executable")
        script_path = data.get("script_path")
        script_args = data.get("script_args") or []
        cwd = data.get("cwd")

        launcher = _launch_prism_context if os.path.basename(script_path or "") == "Prism_ComfyUI_MenuTools.py" else _run_python_script
        result = await asyncio.to_thread(
            launcher,
            python_executable=python_executable,
            script_path=script_path,
            script_args=script_args,
            cwd=cwd,
        )

        return web.json_response({
            "success": True,
            **result,
        })
    except Exception as e:
        return web.json_response({
            "success": False,
            "error": str(e),
            "data": data
        }, status=500)

@PromptServer.instance.routes.get("/prism/verify_context")
async def verify_context(request):
    try:
        config = _get_prism_launch_config()
        if not config:
            raise RuntimeError("Prism is not configured on this machine.")
        context = await _probe_prism_context(config["cwd"])
        if not context or context.get("error") or context.get("closing"):
            raise RuntimeError((context or {}).get("error") or "The Prism context is unavailable or shutting down.")
        return web.json_response({"success": True, "pid": context["pid"]})
    except RuntimeError as error:
        return web.json_response({"success": False, "error": str(error)})

# Custom endpoint to save workflows to absolute paths
@PromptServer.instance.routes.post("/prism/save_workflow_absolute")
async def save_workflow_absolute(request):
    """
    Custom endpoint to save workflows to absolute paths.
    This bypasses ComfyUI's normal user directory restrictions.
    """
    try:
        data = await request.json()
        filepath = data.get('filepath')
        workflow_content = data.get('workflow')
        
        if not filepath or not workflow_content:
            return web.json_response({
                'success': False, 
                'error': 'Missing filepath or workflow'
            }, status=400)
        
        # Ensure directory exists
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # Save the workflow
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(workflow_content, f, indent=2)
        
        print(f"[Prism] Workflow saved to: {filepath}")
        
        return web.json_response({
            'success': True, 
            'filepath': filepath
        })
        
    except Exception as e:
        print(f"[Prism] Error saving workflow: {e}")
        return web.json_response({
            'success': False, 
            'error': str(e)
        }, status=500)

# Custom endpoint to load workflows from absolute paths
@PromptServer.instance.routes.post("/prism/load_workflow_absolute")
async def load_workflow_absolute(request):
    """
    Custom endpoint to load workflows from absolute paths.
    Returns the workflow JSON content.
    """
    try:
        data = await request.json()
        filepath = data.get('filepath')
        
        if not filepath:
            return web.json_response({
                'success': False, 
                'error': 'Missing filepath'
            }, status=400)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return web.json_response({
                'success': False, 
                'error': f'File not found: {filepath}'
            }, status=404)
        
        # Read the workflow file
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
        
        print(f"[Prism] Workflow loaded from: {filepath}")
        
        return web.Response(
            text=workflow_content,
            content_type='application/json'
        )
        
    except Exception as e:
        print(f"[Prism] Error loading workflow: {e}")
        return web.json_response({
            'success': False, 
            'error': str(e)
        }, status=500)

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']