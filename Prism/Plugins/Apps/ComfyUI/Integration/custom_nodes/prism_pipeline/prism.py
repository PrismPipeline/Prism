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


import os
import sys
import shutil
import glob
import re
import uuid
import importlib
from .config import get_comfy_config_path, get_user_pref_dir

import folder_paths
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import json
import asyncio
import torch
import comfy.model_management

import numpy as np

from comfy.cli_args import args

try:
    from comfy_api.latest import Types, InputImpl
except Exception:
    Types = None
    InputImpl = None

try:
    from comfy_api.input_impl.video_types import VideoFromFile as LegacyVideoFromFile
except Exception:
    LegacyVideoFromFile = None


def _normalize_root_path(path):
    if not path:
        return ""

    return os.path.normpath(os.path.expandvars(os.path.expanduser(str(path).strip())))


def _get_default_comfy_config_path():
    return os.path.join(get_user_pref_dir(), "comfy.json")


def _get_comfy_config_path():
    return get_comfy_config_path()


def _load_comfy_config():
    configPath = _get_comfy_config_path()
    if not os.path.isfile(configPath):
        return {}

    try:
        with open(configPath, "r") as configFile:
            configData = json.load(configFile)
    except Exception:
        return {}

    return configData if isinstance(configData, dict) else {}


def _pick_valid_root_path(*paths):
    for path in paths:
        normalized = _normalize_root_path(path)
        if normalized and os.path.isdir(normalized):
            return normalized

    return ""


_comfyConfig = _load_comfy_config()

defaultPrismRoot = "C:/Program Files/Prism2"
defaultPluginRoot = "C:/ProgramData/Prism2/plugins/ComfyUI"

prismRoot = _pick_valid_root_path(
    os.getenv("PRISM_ROOT", ""),
    _comfyConfig.get("prism_root", ""),
    defaultPrismRoot,
)
pluginRoot = _pick_valid_root_path(
    os.getenv("PRISM_COMFYUI_PLUGIN_ROOT", ""),
    _comfyConfig.get("plugin_root", ""),
    defaultPluginRoot,
)

print(f"[Prism] prismRoot: {prismRoot}")
print(f"[Prism] pluginRoot: {pluginRoot}")

crossPlatformPath = os.path.join(pluginRoot, "ExternalModules", "CrossPlatform") if pluginRoot else ""
if crossPlatformPath and os.path.isdir(crossPlatformPath):
    sys.path.append(crossPlatformPath)

try:
    import websockets
except ImportError:
    websockets = None

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif", ".m4v"}


def _request_prism_configuration():
    _refresh_prism_configuration()
    if prismRoot and pluginRoot:
        return

    try:
        from server import PromptServer
        PromptServer.instance.send_sync("prism_missing_configuration", {})
    except Exception:
        pass


def _refresh_prism_configuration():
    global prismRoot, pluginRoot, crossPlatformPath, websockets

    configData = _load_comfy_config()
    prismRoot = _pick_valid_root_path(
        os.getenv("PRISM_ROOT", ""),
        configData.get("prism_root", ""),
        defaultPrismRoot,
    )
    pluginRoot = _pick_valid_root_path(
        os.getenv("PRISM_COMFYUI_PLUGIN_ROOT", ""),
        configData.get("plugin_root", ""),
        defaultPluginRoot,
    )
    crossPlatformPath = os.path.join(pluginRoot, "ExternalModules", "CrossPlatform") if pluginRoot else ""
    if crossPlatformPath and os.path.isdir(crossPlatformPath) and crossPlatformPath not in sys.path:
        sys.path.append(crossPlatformPath)

    if websockets is None and crossPlatformPath:
        try:
            websockets = importlib.import_module("websockets")
        except ImportError:
            pass


def _is_prism_available():
    _refresh_prism_configuration()
    return bool(prismRoot and pluginRoot and websockets is not None)


async def _get_output_filepath_async(asset, episode, sequence, shot, identifier, version, extension):
    """
    Connects to Prism standalone app and requests an output filepath.
    
    Args:
        asset: Asset name
        episode: Episode name
        sequence: Sequence name
        shot: Shot name
        identifier: File identifier
        version: Version string
        extension: File extension
        
    Returns:
        str: The filepath from Prism, or a default path if connection fails
    """
    if not _is_prism_available():
        _request_prism_configuration()
        return get_default_filepath(asset, episode, sequence, shot, identifier, version, extension)

    try:
        # Connect to Prism ComfyUI on port 8765
        async with websockets.connect("ws://localhost:8765", open_timeout=2) as websocket:
            # Send request for output filepath
            request = {
                "action": "get_output_filepath",
                "asset": asset,
                "episode": episode,
                "sequence": sequence,
                "shot": shot,
                "identifier": identifier,
                "version": version,
                "extension": extension
            }
            print(f"[Prism] Requesting output filepath from Prism app with: {request}")
            await websocket.send(json.dumps(request))
            
            # Wait for response (with timeout)
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)
            
            if response.get("status") == "success" and "filepath" in response:
                return response["filepath"]
            else:
                error_msg = response.get("message", "Unknown error")
                print(f"[Prism] Error getting filepath: {error_msg}")
                return get_default_filepath(asset, episode, sequence, shot, identifier, version, extension)
                
    except asyncio.TimeoutError:
        _request_prism_configuration()
        print("[Prism] Timeout waiting for filepath response from Prism app")
        return get_default_filepath(asset, episode, sequence, shot, identifier, version, extension)
    except Exception as e:
        _request_prism_configuration()
        print(f"[Prism] Could not connect to Prism app: {e}")
        return get_default_filepath(asset, episode, sequence, shot, identifier, version, extension)


def get_default_filepath(asset, episode, sequence, shot, identifier, version, extension):
    """Generate a default filepath when Prism is not available."""
    if asset:
        filename = f"{asset}_{identifier}_{version}{extension}" if all([asset, identifier, version]) else f"{asset}_output{extension}"
    else:
        if all([sequence, shot, identifier, version]):
            if episode:
                filename = f"{episode}_{sequence}_{shot}_{identifier}_{version}{extension}"
            else:
                filename = f"{sequence}_{shot}_{identifier}_{version}{extension}"
        else:
            filename = f"prism_output{extension}"

    return os.path.join("output", filename)


async def getOutputFilepath(asset, episode, sequence, shot, identifier, version, extension):
    """
    Async function for getting output filepath from Prism.
    
    Args:
        asset: Asset name
        episode: Episode name
        sequence: Sequence name
        shot: Shot name
        identifier: File identifier
        version: Version string
        extension: File extension
        
    Returns:
        str: The filepath from Prism
    """
    return await _get_output_filepath_async(asset, episode, sequence, shot, identifier, version, extension)


def _normalize_input_value(value):
    if value is None:
        return ""

    text = str(value).strip()
    if text.lower() in ["none", "null"]:
        return ""

    return text


async def _resolve_media_filepath_async(
    filepath,
    asset,
    episode,
    sequence,
    shot,
    identifier,
    version,
    aov,
    source,
):
    filepath = _normalize_input_value(filepath)
    if filepath:
        return os.path.normpath(os.path.expandvars(os.path.expanduser(filepath)))

    if not _is_prism_available():
        _request_prism_configuration()
        return ""

    request_id = uuid.uuid4().hex
    try:
        async with websockets.connect("ws://localhost:8765", open_timeout=2) as websocket:
            request = {
                "action": "resolve_media_filepath",
                "request_id": request_id,
                "filepath": filepath,
                "asset": asset,
                "episode": episode,
                "sequence": sequence,
                "shot": shot,
                "identifier": identifier,
                "version": version,
                "aov": aov,
                "source": source,
                "location": "global",
            }
            print(f"[Prism] Resolving media filepath with: {request}")
            await websocket.send(json.dumps(request))

            while True:
                response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_text)
                response_action = response.get("action")
                response_request_id = response.get("request_id")

                if response_action and response_action != "resolve_media_filepath":
                    continue

                if response_request_id and response_request_id != request_id:
                    continue

                if response.get("status") == "success" and response.get("filepath"):
                    return os.path.normpath(response["filepath"])

                print(f"[Prism] Failed to resolve media filepath: {response.get('message', 'Unknown error')}")
                return ""

    except asyncio.TimeoutError:
        _request_prism_configuration()
        print("[Prism] Timeout waiting for media filepath response from Prism app")
        return ""
    except Exception as e:
        _request_prism_configuration()
        print(f"[Prism] Could not resolve media filepath from Prism app: {e}")
        return ""


async def resolveMediaFilepath(
    filepath,
    asset,
    episode,
    sequence,
    shot,
    identifier,
    version,
    aov,
    source,
):
    return await _resolve_media_filepath_async(
        filepath=filepath,
        asset=asset,
        episode=episode,
        sequence=sequence,
        shot=shot,
        identifier=identifier,
        version=version,
        aov=aov,
        source=source,
    )


def _is_video_extension(extension):
    return extension.lower() in VIDEO_EXTENSIONS


def _looks_like_sequence_pattern(path):
    if any(char in path for char in ["#", "*", "?"]):
        return True

    return re.search(r"%0?\d*d", path) is not None


def _sequence_pattern_to_glob(path_pattern):
    def _replace_printf(match):
        width_text = match.group(1)
        if width_text:
            try:
                width = int(width_text)
                if width > 0:
                    return "?" * width
            except Exception:
                pass

        return "*"

    pattern = re.sub(r"%0?(\d*)d", _replace_printf, path_pattern)
    pattern = re.sub(r"#+", lambda m: "?" * len(m.group(0)), pattern)
    return pattern


def _detect_neighbor_sequence_files(filepath):
    if not os.path.isfile(filepath):
        return []

    base, ext = os.path.splitext(filepath)
    if _is_video_extension(ext):
        return []

    match = re.search(r"(.*?)(\d+)$", base)
    if not match:
        return []

    pattern = f"{match.group(1)}{'?' * len(match.group(2))}{ext}"
    files = sorted(glob.glob(pattern))
    return files if len(files) > 1 else []


def _get_video_from_file(filepath):
    if InputImpl is not None and hasattr(InputImpl, "VideoFromFile"):
        return InputImpl.VideoFromFile(filepath)

    if LegacyVideoFromFile is not None:
        return LegacyVideoFromFile(filepath)

    raise RuntimeError("ComfyUI video input API is unavailable (VideoFromFile not found).")


def _mask_from_components(components, dtype, device):
    if components.alpha is not None:
        return (1.0 - components.alpha[..., -1]).to(device=device, dtype=dtype)

    frame_count = int(components.images.shape[0]) if components.images is not None else 0
    if frame_count > 0:
        height = int(components.images.shape[1])
        width = int(components.images.shape[2])
    else:
        height, width = 64, 64

    return torch.zeros((frame_count, height, width), dtype=dtype, device=device)


def _load_sequence_images(sequence_files, dtype, device):
    image_batches = []
    mask_batches = []
    width = None
    height = None

    for sequence_file in sequence_files:
        components = _get_video_from_file(sequence_file).get_components()
        images = components.images
        if images is None or images.shape[0] == 0:
            continue

        cur_height = int(images.shape[1])
        cur_width = int(images.shape[2])
        if width is None:
            width = cur_width
            height = cur_height
        elif cur_width != width or cur_height != height:
            print(f"[Prism] Skipping mismatched sequence frame size: {sequence_file}")
            continue

        batch_images = images.to(device=device, dtype=dtype)
        batch_mask = _mask_from_components(components, dtype=dtype, device=device)
        image_batches.append(batch_images)
        mask_batches.append(batch_mask)

    if not image_batches:
        raise ValueError("Sequence pattern matched files, but none could be decoded as images.")

    return torch.cat(image_batches, dim=0), torch.cat(mask_batches, dim=0)


def _load_media_images_and_mask(filepath):
    normalized_path = os.path.normpath(os.path.expandvars(os.path.expanduser(filepath)))
    if not os.path.isabs(normalized_path):
        input_path = os.path.join(folder_paths.get_input_directory(), normalized_path)
        if os.path.isfile(input_path):
            normalized_path = input_path
    dtype = comfy.model_management.intermediate_dtype()
    device = comfy.model_management.intermediate_device()

    extension = os.path.splitext(normalized_path)[1].lower()
    if not _is_video_extension(extension):
        sequence_files = []
        if _looks_like_sequence_pattern(normalized_path):
            sequence_files = sorted(glob.glob(_sequence_pattern_to_glob(normalized_path)))
        else:
            sequence_files = _detect_neighbor_sequence_files(normalized_path)

        if sequence_files:
            return _load_sequence_images(sequence_files, dtype=dtype, device=device)

    components = _get_video_from_file(normalized_path).get_components()
    if components.images is None or components.images.shape[0] == 0:
        raise ValueError(f"No image frames could be decoded from '{normalized_path}'.")

    images = components.images.to(device=device, dtype=dtype)
    mask = _mask_from_components(components, dtype=dtype, device=device)
    return images, mask


class PrismSaveMedia:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        video_formats = ["auto", "mp4"]
        video_codecs = ["auto", "h264"]
        if Types is not None:
            video_formats = Types.VideoContainer.as_input()
            video_codecs = Types.VideoCodec.as_input()

        return {
            "required": {
                "asset": ("STRING", {"default": ""}),
                "episode": ("STRING", {"default": ""}),
                "sequence": ("STRING", {"default": ""}),
                "shot": ("STRING", {"default": ""}),
                "identifier": ("STRING", {"default": "comfy"}),
                "version": ("STRING", {"default": ""}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video": ("VIDEO",),
                "video_format": (video_formats, {"default": "auto"}),
                "video_codec": (video_codecs, {"default": "auto"}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()

    FUNCTION = "save_media"

    OUTPUT_NODE = True
    CATEGORY = "Prism"
    DESCRIPTION = "Saves images (single/frame sequence) or video to your Prism Pipeline project."
    SEARCH_ALIASES = ["save", "save image", "save media", "save video", "export image", "export video", "output image", "write image", "download", "prism"]

    def _build_png_metadata(self, prompt=None, extra_pnginfo=None):
        if args.disable_metadata:
            return None

        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for key in extra_pnginfo:
                metadata.add_text(key, json.dumps(extra_pnginfo[key]))

        return metadata

    def _build_video_metadata(self, prompt=None, extra_pnginfo=None):
        if args.disable_metadata:
            return None

        metadata = {}
        if extra_pnginfo is not None:
            metadata.update(extra_pnginfo)
        if prompt is not None:
            metadata["prompt"] = prompt

        return metadata or None

    def _ensure_parent_dir(self, path):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _save_images_to_paths(self, images, target_paths, metadata):
        results = []
        for idx, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            target_path = target_paths[idx]
            self._ensure_parent_dir(target_path)
            print(f"[Prism] Saving image to {target_path} with metadata: {metadata}")
            img.save(target_path, pnginfo=metadata, compress_level=self.compress_level)

            user_output_file = os.path.join(self.output_dir, os.path.basename(target_path))
            if os.path.normcase(os.path.normpath(target_path)) != os.path.normcase(os.path.normpath(user_output_file)):
                shutil.copy2(target_path, user_output_file)

            results.append({
                "filename": os.path.basename(user_output_file),
                "subfolder": "",
                "type": self.type,
            })

        return results

    def _save_video_to_path(self, video, target_path, video_format="auto", video_codec="auto", metadata=None):
        self._ensure_parent_dir(target_path)

        print(f"[Prism] Saving video to {target_path} with format: {video_format}, codec: {video_codec}, metadata: {metadata}")
        if Types is not None:
            format_value = Types.VideoContainer(video_format)
            codec_value = Types.VideoCodec(video_codec)
            video.save_to(target_path, format=format_value, codec=codec_value, metadata=metadata)
        else:
            video.save_to(target_path, metadata=metadata)

        user_output_file = os.path.join(self.output_dir, os.path.basename(target_path))
        if os.path.normcase(os.path.normpath(target_path)) != os.path.normcase(os.path.normpath(user_output_file)):
            shutil.copy2(target_path, user_output_file)

        return {
            "filename": os.path.basename(user_output_file),
            "subfolder": "",
            "type": self.type,
        }

    async def save_media(
        self,
        asset,
        episode,
        sequence,
        shot,
        identifier,
        version,
        images=None,
        video=None,
        video_format="auto",
        video_codec="auto",
        prompt=None,
        extra_pnginfo=None,
    ):
        if images is None and video is None:
            raise ValueError("Prism Save Media requires at least one valid input: images or video.")

        ui_payload = {}

        if images is not None:
            extension = ".png"  # Default extension for images
            base_output_file = await getOutputFilepath(asset, episode, sequence, shot, identifier, version, extension)
            base_root, base_ext = os.path.splitext(base_output_file)
            image_metadata = self._build_png_metadata(prompt=prompt, extra_pnginfo=extra_pnginfo)
            frame_count = int(images.shape[0]) if hasattr(images, "shape") and len(images.shape) > 0 else len(images)

            if frame_count <= 1:
                image_paths = [base_output_file]
            else:
                image_paths = [f"{base_root}_{idx + 1:05d}{extension}" for idx in range(frame_count)]

            ui_payload["images"] = self._save_images_to_paths(images, image_paths, image_metadata)

        if video is not None:
            video_identifier = identifier
            if images is not None and identifier:
                video_identifier = f"{identifier}_video"

            if Types is not None:
                extension = "." + Types.VideoContainer.get_extension(video_format)
            else:
                extension = ".mp4"

            video_output_file = await getOutputFilepath(asset, episode, sequence, shot, video_identifier, version, extension)
            video_metadata = self._build_video_metadata(prompt=prompt, extra_pnginfo=extra_pnginfo)
            video_result = self._save_video_to_path(
                video,
                video_output_file,
                video_format=video_format,
                video_codec=video_codec,
                metadata=video_metadata,
            )
            ui_payload["videos"] = [video_result]

        result = {"result": (images,), "ui": ui_payload}
        return result

    async def save_image(self, images, asset, sequence, shot, identifier, version, prompt=None, extra_pnginfo=None, episode=""):
        # Backward-compatible wrapper for older workflows.
        return await self.save_media(
            asset=asset,
            episode=episode,
            sequence=sequence,
            shot=shot,
            identifier=identifier,
            version=version,
            images=images,
            prompt=prompt,
            extra_pnginfo=extra_pnginfo,
        )


class PrismLoadMedia:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filepath": ("STRING", {"default": ""}),
                "asset": ("STRING", {"default": ""}),
                "episode": ("STRING", {"default": ""}),
                "sequence": ("STRING", {"default": ""}),
                "shot": ("STRING", {"default": ""}),
                "identifier": ("STRING", {"default": ""}),
                "version": ("STRING", {"default": "latest"}),
                "aov": ("STRING", {"default": ""}),
                "source": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "VIDEO", "STRING")
    RETURN_NAMES = ("images", "mask", "video", "resolved_filepath")
    FUNCTION = "load_media"
    CATEGORY = "Prism"
    DESCRIPTION = "Loads image/video media from a direct filepath or from Prism context fields."
    SEARCH_ALIASES = [
        "load",
        "load image",
        "load media",
        "load sequence",
        "load video",
        "read image",
        "read exr",
        "prism",
    ]

    async def load_media(
        self,
        filepath,
        asset,
        episode,
        sequence,
        shot,
        identifier,
        version,
        aov,
        source,
    ):
        resolved_filepath = await resolveMediaFilepath(
            filepath=filepath,
            asset=asset,
            episode=episode,
            sequence=sequence,
            shot=shot,
            identifier=identifier,
            version=version,
            aov=aov,
            source=source,
        )

        if not resolved_filepath:
            raise ValueError("Prism Load Media could not resolve a valid filepath from the provided inputs.")

        images, mask = _load_media_images_and_mask(resolved_filepath)
        normalized_path = os.path.normpath(os.path.expandvars(os.path.expanduser(resolved_filepath)))
        extension = os.path.splitext(normalized_path)[1].lower()
        video = _get_video_from_file(normalized_path) if _is_video_extension(extension) else None
        return {"result": (images, mask, video, resolved_filepath)}

NODE_CLASS_MAPPINGS = {
    "PrismLoadMedia": PrismLoadMedia,
    "PrismSaveMedia": PrismSaveMedia,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PrismLoadMedia": "Prism Load Media",
    "PrismSaveMedia": "Prism Save Media",
}
