from .prism import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
import os
import json
import sys
import subprocess
import time
import threading
import tempfile
import glob
import urllib.error
import urllib.request
from aiohttp import web
from server import PromptServer

WEB_DIRECTORY = "./js"
_PIPE_DRAIN_THREADS = []
_SETUP_PROCESSES = {}
PRISM_SETUP_SCRIPT_URL = "https://service.prism-pipeline.com/api/service/setup_comfy"


def _get_comfyui_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_comfy_config_path():
    override_path = os.getenv("PRISM_COMFYUI_CONFIG_PATH", "")
    if override_path:
        return os.path.normpath(os.path.expandvars(os.path.expanduser(override_path)))

    user_profile = os.getenv("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(user_profile, "Documents", "Prism2", "comfy.json")


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
    for executable in ("Prism.exe", "python.exe"):
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


def _find_prism_root(configured_root=""):
    candidates = [
        os.getenv("PRISM_ROOT", ""),
        configured_root,
        "C:/Program Files/Prism2",
    ]
    candidates += sorted(
        glob.glob("C:/Program Files/Prism Pipeline/v*"), reverse=True
    )
    candidates += sorted(
        glob.glob(os.path.join(
            os.path.expanduser("~"), "Documents", "Prism2", "versions", "v*"
        )),
        reverse=True,
    )

    for candidate in candidates:
        prism_root = os.path.normpath(os.path.expandvars(os.path.expanduser(candidate)))
        if _is_prism_root(prism_root):
            return prism_root
    return ""


def _find_downloaded_prism_root():
    pattern = os.path.join(
        os.path.expanduser("~"), "Documents", "Prism2", "versions", "v*"
    )
    for candidate in sorted(glob.glob(pattern), reverse=True):
        prism_root = os.path.normpath(candidate)
        if _is_prism_root(prism_root):
            return prism_root
    return ""


def _get_latest_downloaded_prism_folder():
    pattern = os.path.join(
        os.path.expanduser("~"), "Documents", "Prism2", "versions", "v*"
    )
    candidates = sorted(glob.glob(pattern), reverse=True)
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


def _download_and_run_prism_setup():
    setup_path = os.path.join(tempfile.gettempdir(), "PrismSetup.py")
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
    with open(setup_path, "wb") as setup_file:
        setup_file.write(content)
    print(f"[Prism] Downloaded {len(content)} bytes to {setup_path}")
    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    setup_python = pythonw_path if os.path.isfile(pythonw_path) else sys.executable
    return _run_python_script(
        setup_python, setup_path, cwd=os.path.dirname(setup_path), track_setup=True
    )


def _drain_pipe_to_console(pipe, label, setup_process=None):
    try:
        for line in iter(pipe.readline, ""):
            line = line.rstrip()
            if line:
                print(f"[Prism:{label}] {line}")
                if setup_process is not None:
                    setup_process["messages"] = (setup_process["messages"] + [line])[-20:]
    except Exception as e:
        print(f"[Prism] Failed to drain {label}: {e}")
    finally:
        try:
            pipe.close()
        except Exception:
            pass


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


def _run_python_script(python_executable, script_path, script_args=None, cwd=None, track_setup=False):
    if not python_executable:
        raise ValueError("Missing python_executable")

    if not script_path:
        raise ValueError("Missing script_path")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    args = [python_executable, script_path]
    if script_args:
        args.extend([str(arg) for arg in script_args])

    popen_kwargs = {}
    popen_kwargs = {"cwd": cwd or None}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

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
        setup_process = {"process": process, "messages": []}
        _SETUP_PROCESSES[process.pid] = setup_process
    _start_process_pipe_drainers(process, setup_process=setup_process)
    if process.poll() is not None:  # Check if the process has terminated
        print(f"[Prism] Process terminated immediately: {args}")

    return {"pid": process.pid, "command": args}


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
    try:
        print("[Prism] Received ComfyUI setup download request.")
        result = _download_and_run_prism_setup()
        print(f"[Prism] Started ComfyUI setup process: pid={result['pid']}")
        return web.json_response({"success": True, **result})
    except Exception as error:
        print(f"[Prism] Failed to download or start ComfyUI setup: {error}")
        return web.json_response({"success": False, "error": str(error)}, status=500)


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
    message = setup_process["messages"][-1] if setup_process["messages"] else "Installing Prism..."
    return_code = process.poll()
    if return_code is None:
        return web.json_response({"success": False, "installed": False, "running": True, "message": message})
    if return_code != 0:
        _SETUP_PROCESSES.pop(setup_pid, None)
        return web.json_response({
            "success": False,
            "installed": True,
            "error": "Prism setup failed (exit code %s): %s" % (return_code, message),
        }, status=500)

    prism_root = _get_latest_downloaded_prism_folder()
    if not prism_root:
        print("[Prism] Setup completion check: no Prism installation found yet.")
        return web.json_response({"success": False, "installed": False})

    success, error = _save_prism_root(prism_root)
    _SETUP_PROCESSES.pop(setup_pid, None)
    print(f"[Prism] Setup completion check: root={prism_root}, success={success}")
    return web.json_response({
        "success": success,
        "installed": True,
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

        result = _run_python_script(
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