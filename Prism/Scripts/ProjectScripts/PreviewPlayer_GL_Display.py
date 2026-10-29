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
import ast
import logging
import ctypes
from typing import Optional, Any, TYPE_CHECKING


import numpy as np
from OpenGL.GL import *

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


import ProjectScripts.PreviewPlayer_GL_Utils as Utils


if TYPE_CHECKING:
    from Scripts.PrismCore import PrismCore
    from ProjectScripts.PreviewPlayer_GL import PreviewPlayer_GL
    from ProjectScripts.PreviewPlayer_GL_Modules import FxControlsData



from PrismUtils.Decorators import err_catcher
logger = logging.getLogger(__name__)



class GLVideoDisplay(QOpenGLWidget):
    '''OpenGL image display widget used by the Preview Player.

    - GPU based image display
    - Reads Cached NumPy frames
    - float16/uint8/uint16 image input normalization
    - RGB and RGBA frame display
    - Customizable checkerboard background for Alpha display
    - OCIO GPU transforms (input, display/view, LUT)
    - Basic FX image color adjustments (exposure, gamma, contrast, lift/gain, etc.)

    Args:
    ------
    - player (PreviewPlayer_GL): Media player owner of this display widget.
    - core (PrismCore): Prism core instance.
    - FxData (FxControlsData): Shared FX control data/signals.
    - OcioModule (Any, optional): OCIO module wrapper used by the player.
    - parent (QWidget, optional): Parent Qt widget.

    API
    ------
    - setBackground(): Updates checkerboard size and colors.

    - setOcioTransforms(): Validates OCIO input/display/view/look/LUT selections, stages OCIO GPU
            shader resources, and marks the image shader for rebuild.

    - clearOcioTransforms(): Clears OCIO state and releases staged GPU LUT textures.

    - onFxDataChanged(): Updates internal FX state and shader-ready values when FX controls change.

    - displayLoading(): Displays a loading slide through the standard image path.

    - displayFrame(): Stores a frame for presentation and schedules a repaint.

    - clearFrame(): Clears the current frame and schedules a repaint.

    - displayError(): Builds and displays a fallback error slide through the standard image path.

    - clearError(): Clears any displayed error and resets the error state.

    Rendering lifecycle
    -------------------
    initializeGL():
        Creates GL resources (texture/programs), initializes shader state, and
        enables blending.

    resizeGL():
        Updates viewport and checkerboard sizing metadata.

    paintGL():
        Draws checkerboard first, then frame texture using the active image
        shader (with optional OCIO GPU resources and FX uniforms).

    '''

    def __init__(self, Player: 'PreviewPlayer_GL', core: 'PrismCore', FxData: 'FxControlsData', OcioModule: Any = None, parent=None):
        super().__init__(parent)

        #   Configure OpenGL Format for Alpha Display
        fmt = self.format()
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.setAutoFillBackground(False)

        self.Player = Player
        self.core = core
        self.FxData = FxData
        self.OcioModule = OcioModule

        self.frame: int = None
        self.errorData = None

        self.scale_w = 1.0
        self.scale_h = 1.0

        self.check_size = 20
        self.check_color1 = (0.0, 0.0, 0.0) # black
        self.check_color2 = (0.1, 0.1, 0.1) # grey

        self.inputSpace = ""
        self.display = ""
        self.view = ""
        self.look = None
        self.luts = None
        self.global_useOCIO = True

        self.ocioProcessor = None
        self.ocioWorkingSpace = ""
        self.ocioGpuStages = {
            "input": None,
            "display": None,
            "lut": None,
        }
        self.ocioGpuAvailable = False
        self.ocioGpuReady = False
        self.ocioGpuShaderDirty = True
        self.ocioGpuTextureIds = []

        self.texture_id = None
        self.texture_width = 0
        self.texture_height = 0
        self.texture_internal = None
        self.program_image = None
        self.program_checker = None
        self.vao = None

        #   Get Initial FX Control Values then Connect
        self.onFxDataChanged()
        self.FxData.changed.connect(self.onFxDataChanged)

        #   Add RCL Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.Player.rclPreview)



    #######################
    ######    API   #######

    #   Updates OCIO Transforms
    @err_catcher(name=__name__)
    def setBackground(self,
                      check_size:int = 20,
                      check_color1:tuple = (0.0, 0.0, 0.0),
                      check_color2:tuple = (0.1, 0.1, 0.1)
                      ) -> bool:
        
        '''Sets the checkerboard background for the GL video display.

        Args:
            check_size (int): The size of the checker squares.
            check_color1 (tuple): The first color of the checkerboard (RGB, 0-1 floats).
            check_color2 (tuple): The second color of the checkerboard (RGB, 0-1 floats).

        Returns:
            bool: True if the background was set successfully, False otherwise.
        '''

        try:
            self.check_size = check_size
            self.check_color1 = check_color1
            self.check_color2 = check_color2

            #   Refresh Viewer
            self.update()

            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Background: {e}")
            return False


    #   Updates OCIO Transforms
    @err_catcher(name=__name__)
    def setOcioTransforms(self,
                          inputSpace: str,
                          display: str,
                          view: str,
                          look: str = None,
                          luts: list = None
                          ) -> bool:
        
        '''Sets the OCIO transforms for the GL video display.

        Args:
            inputSpace (str): The input color space name.
            display (str): The display name.
            view (str): The view name.
            look (str, optional): The look name. Defaults to None.
            luts (list, optional): A list of LUT file paths. Defaults to None.

        Returns:
            bool: True if the transforms were set successfully, False otherwise.
        '''

        try:
            if not inputSpace or not display or not view:
                self.clearOcioTransforms()
                missingFields = []
                if not inputSpace:
                    missingFields.append("Color Space")
                if not display:
                    missingFields.append("Display")
                if not view:
                    missingFields.append("View")
                return f"OCIO preset is incomplete. Missing: {', '.join(missingFields)}."

            config = self.OcioModule.GetCurrentConfig()

            errors = []

            ##   Validate Passed Transforms Exist in Config

            #   Check Input Colorspace
            if inputSpace not in config.getColorSpaceNames():
                errStr = f"Invalid OCIO Input ColorSpace '{inputSpace}'"
                errors.append(errStr)

            #   Check Display
            if display not in config.getDisplays():
                errStr = f"Invalid OCIO Display '{display}'"
                errors.append(errStr)

            #   Check View
            if display in config.getDisplays():
                if view not in config.getViews(display):
                    errStr = f"Invalid OCIO View '{view}' for display '{display}'"
                    errors.append(errStr)

            #   Check LUT File
            validLuts = []

            if luts:
                for lut in luts:
                    #   Skip empty Items
                    if not lut:
                        continue

                    #   Check if LUT Path Exists
                    if not os.path.isfile(lut):
                        errStr = "LUT is not a Valid File.  Ignoring LUT"
                        errors.append(errStr)
                    
                    #   Test if LUT is Valid
                    else:
                        try:
                            if self._createLutTransform(lut):
                                validLuts.append(lut)
                            else:
                                raise Exception

                        except Exception as e:
                            errStr = f"Invalid LUT file '{lut}': {e}.\n\nIgnoring LUT."
                            logger.warning(errStr)
                            errors.append(errStr)
                            lut = None

            #   Check Look
            if look and look not in config.getLookNames():
                errStr = f"Invalid OCIO Look '{look}', ignoring."
                errors.append(errStr)
                look = None

            self.inputSpace = inputSpace
            self.display = display
            self.view = view
            self.look = look
            self.luts = validLuts


            if not self._buildOCIOProcessor():
                errStr = "Failed to Build GL OCIO Processor"
                errors.append(errStr)

            if errors:
                errorsStr = "There are Errors with the Selected OCIO Transforms:\n\n"
                errorsStr += "\n".join(f"- {err}\n" for err in errors)
                return errorsStr
            
            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set OCIO Transforms: {e}")
            self.clearOcioTransforms()

            return f"OCIO Error:\n\n- {e}"


    @err_catcher(name=__name__)
    def clearOcioTransforms(self) -> None:
        '''Disable OCIO transforms and release any cached OCIO resources.'''

        self.inputSpace = ""
        self.display = ""
        self.view = ""
        self.look = None
        self.luts = []
        self.ocioProcessor = None
        self.ocioWorkingSpace = ""
        self.ocioGpuStages = {
            "input": None,
            "display": None,
            "lut": None,
        }
        self.ocioGpuAvailable = False
        self.ocioGpuReady = False
        self.ocioGpuShaderDirty = True

        try:
            self._releaseOcioGpuTextures()
        except Exception:
            pass

        try:
            self.update()
        except Exception:
            pass
        

    @err_catcher(name=__name__)
    def onFxDataChanged(self):
        '''Handles changes in the FX Data. Updates internal state and shader-ready values.'''

        self.fxEnabled = self.FxData.fxEnabled

        #   Get Current Values Dict and Get Shader Uniforms
        self.fxValues = {
            name: self.FxData.get_FxControlValue(name)
            for name in self.FxData.getFxControlNames()
        }

        #   Get Shader Uniform Values from Current FX Control Values
        self.fxUniformValues = self._buildFxUniformValues(self.fxValues)

        self.update()


    @err_catcher(name=__name__)
    def displayLoading(self, enabled:bool):
        '''Displays a loading slide through the standard image path.'''

        frame = Utils.buildLoadingImage(player=self.Player)
        self.displayFrame(-1, frame, useOCIO=False)
        return True


    @err_catcher(name=__name__)
    def displayFrame(self, frameIdx: int, frame: np.ndarray, useOCIO: bool=True) -> bool:
        '''Displays a frame in the GL video viewer.

        Args:
            frameIdx (int): The index of the frame to display.
            frame (np.ndarray): The frame data as a numpy array.
            useOCIO (bool, optional): Whether to apply OCIO color transforms. Defaults to True.

        Returns:
            bool: True if the frame was displayed successfully, False otherwise.
        '''

        try:
            self.frame = frame
            self.global_useOCIO = bool(useOCIO and getattr(self.Player, "global_useOCIO", True))

            self.update()
            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Image Frame: {e}")
            return False


    @err_catcher(name=__name__)
    def clearFrame(self) -> None:
        '''Clear the current frame and repaint the checkerboard only.'''

        self.frame = None
        self.update()


    @err_catcher(name=__name__)
    def displayError(self, title: str, msg: str = "", error: Optional[str] = None, details: str = "") -> bool:
        '''Build and display a fallback slide through the standard image path.'''

        self.errorData = {
            "title": title,
            "msg": msg,
            "message": msg,
            "error": error,
            "details": details,
        }

        frame = Utils.buildFallbackImg(
            player=self.Player,
            msg=msg,
            error=error,
            details=details,
        )

        if frame is None:
            self.frame = None
            self.update()
            return False

        self.displayFrame(-1, frame, useOCIO=False)
        return True


    @err_catcher(name=__name__)
    def clearError(self):
        '''Clears any displayed error and resets the error state.'''

        self.errorData = None
        self.update()



    ##########################
    ######    QT API   #######

    @err_catcher(name=__name__)
    def resizeGL(self, w: int, h: int):
        '''Called by Qt when the OpenGL widget is resized.
        
        Args:
            w (int): The new width of the OpenGL widget.
            h (int): The new height of the OpenGL widget.
        '''

        self._resizeGL(w, h)


    @err_catcher(name=__name__)
    def initializeGL(self):
        '''Called by Qt to Initialize the OpenGL context, generate textures, and compile shaders.'''

        self._initializeGL()

        #   Setup Quad Geo Buffers/VAO (uses fixed locations 0-1)
        self._setupQuad()
        

    @err_catcher(name=__name__)
    def paintGL(self):
        '''Called by Qt to paint the OpenGL widget. Clears the window, draws the checkerboard, and then draws the image if available.'''

        self._paintGL()



    ###########################
    ######   INTERNAL   #######

    ####    OCIO    ####

    @err_catcher(name=__name__)
    def _resolveOcioWorkingSpace(self, config: Any) -> str:
        '''Resolve the scene-linear working space from the OCIO config.
        
        Args:
            config (Any): The OCIO configuration object.

        Returns:
            str: The name of the scene-linear working space, or an empty string if not found.
        '''

        try:
            if config.hasRole(self.OcioModule.ROLE_SCENE_LINEAR):
                workingSpace = config.getRoleColorSpace(self.OcioModule.ROLE_SCENE_LINEAR)
                if workingSpace:
                    return workingSpace

        except Exception:
            logger.warning("Failed to resolve OCIO working space. Using default.")

        return ""


    @err_catcher(name=__name__)
    def _isSceneReferredColorSpace(self, config: Any, colorSpaceName: str) -> bool:
        '''Return True when the given color space is scene-referred in the OCIO config.

        Args:
            config (Any): The OCIO configuration object.
            colorSpaceName (str): The name of the color space to check.

        Returns:
            bool: True if the color space is scene-referred, False otherwise.
        '''

        if not colorSpaceName:
            return False

        try:
            colorSpace = config.getColorSpace(colorSpaceName)
            if not colorSpace:
                return False

            refType = colorSpace.getReferenceSpaceType()
            return refType == self.OcioModule.REFERENCE_SPACE_SCENE

        except Exception:
            return False


    @err_catcher(name=__name__)
    def _appendLutTransforms(self, transformGroup: Any) -> None:
        '''Append validated LUT transforms to an OCIO group transform.

        Args:
            transformGroup (Any): The OCIO group transform to which LUT transforms will be appended.
        '''

        if not self.luts:
            return

        #   Append Validated LUT Transforms
        for lutPath in self.luts:
            transform_lut = self._createLutTransform(lutPath)

            if transform_lut:
                transformGroup.appendTransform(transform_lut)


    @err_catcher(name=__name__)
    def _createOcioGpuStage(self,
                            processor: Any,
                            functionName: str,
                            resourcePrefix: str
                            ) -> dict | None:
        
        '''Create a shader-ready OCIO GPU stage description from a processor.

        Args:
            processor (Any): The OCIO processor object.
            functionName (str): The name of the shader function.
            resourcePrefix (str): The prefix for GPU resources.

        Returns:
            dict | None: A dictionary describing the GPU stage, or None if the processor is a no-op.
        '''

        if not processor or processor.isNoOp():
            return None

        gpuProcessor = processor.getDefaultGPUProcessor()

        #   Create Shader Description
        shaderDesc = self.OcioModule.GpuShaderDesc.CreateShaderDesc(
            self.OcioModule.GPU_LANGUAGE_GLSL_4_0,
            functionName,
            "outColor",
            resourcePrefix,
            ""
        )

        #   Skip 1D Textures
        shaderDesc.setAllowTexture1D(False)

        #   Get Shader information
        gpuProcessor.extractGpuShaderInfo(shaderDesc)

        stage = {
            "functionName": functionName,
            "shaderText": shaderDesc.getShaderText(),
            "textures2D": [],
            "textures3D": [],
            "uniforms": [],
        }

        #   Populate 2D Textures
        for texture in shaderDesc.getTextures():
            stage["textures2D"].append({
                "textureName": texture.textureName,
                "samplerName": texture.samplerName,
                "width": int(texture.width),
                "height": int(texture.height),
                "channel": texture.channel,
                "dimensions": texture.dimensions,
                "interpolation": texture.interpolation,
                "values": np.ascontiguousarray(texture.getValues(), dtype=np.float32),
                "unit": None,
                "location": -1,
                "glId": None,
            })

        #   Populate 3D Textures
        for texture in shaderDesc.get3DTextures():
            stage["textures3D"].append({
                "textureName": texture.textureName,
                "samplerName": texture.samplerName,
                "edgeLen": int(texture.edgeLen),
                "interpolation": texture.interpolation,
                "values": np.ascontiguousarray(texture.getValues(), dtype=np.float32),
                "unit": None,
                "location": -1,
                "glId": None,
            })

        #   Populate Uniforms
        for uniformName, uniformData in shaderDesc.getUniforms():
            uniformEntry = {
                "name": uniformName,
                "type": uniformData.type,
                "location": -1,
                "value": None,
            }

            #   Populate Uniform Values Based on Image Type
            if uniformData.type == self.OcioModule.UNIFORM_BOOL:
                uniformEntry["value"] = bool(uniformData.getBool())

            elif uniformData.type == self.OcioModule.UNIFORM_DOUBLE:
                uniformEntry["value"] = float(uniformData.getDouble())

            elif uniformData.type == self.OcioModule.UNIFORM_FLOAT3:
                uniformEntry["value"] = tuple(float(v) for v in uniformData.getFloat3())

            elif uniformData.type == self.OcioModule.UNIFORM_VECTOR_FLOAT:
                uniformEntry["value"] = np.ascontiguousarray(uniformData.getVectorFloat(), dtype=np.float32)

            elif uniformData.type == self.OcioModule.UNIFORM_VECTOR_INT:
                uniformEntry["value"] = np.ascontiguousarray(uniformData.getVectorInt(), dtype=np.int32)

            stage["uniforms"].append(uniformEntry)

        return stage


    @err_catcher(name=__name__)
    def _iterOcioGpuStages(self) -> list[dict]:
        '''Return the OCIO GPU stages in execution order.

        Returns:
            list[dict]: A list of OCIO GPU stage dictionaries in execution order.
        '''

        return [
            stage
            for stage in (
                self.ocioGpuStages.get("input"),
                self.ocioGpuStages.get("display"),
                self.ocioGpuStages.get("lut"),
            )
            if stage
        ]


    ####    FX ADJUSTMENTS  ####

    @err_catcher(name=__name__)
    def _evalFxMathAst(self, node: ast.AST, context: dict[str, float]) -> float:
        '''Evaluate a restricted math AST for FX formulas.

        Args:
            node (ast.AST): The AST node representing the math expression.
            context (dict[str, float]): A dictionary mapping variable names to their values.

        Returns:
            float: The evaluated result of the math expression.
        '''

        #   Expression Nodes
        if isinstance(node, ast.Expression):
            return self._evalFxMathAst(node.body, context)

        #   Constant Nodes
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            logger.warning("Unsupported constant in FX math.")
            return 0.0

        #   Name Nodes (Variables)
        if isinstance(node, ast.Name):
            if node.id in context:
                return float(context[node.id])
            logger.warning(f"Unknown symbol in FX math: {node.id}")
            return 0.0

        #   Binary Operation Nodes
        if isinstance(node, ast.BinOp):
            left = self._evalFxMathAst(node.left, context)
            right = self._evalFxMathAst(node.right, context)

            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right

            logger.warning("Unsupported operator in FX math.")
            return 0.0

        #   Unary Operation Nodes
        if isinstance(node, ast.UnaryOp):
            value = self._evalFxMathAst(node.operand, context)

            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.USub):
                return -value

            logger.warning("Unsupported unary operator in FX math.")
            return 0.0

        #   Function Call Nodes
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                logger.warning("Only direct function calls are allowed in FX math.")
                return 0.0

            fnName = node.func.id
            fn = Utils.FX_MATH_ALLOWED_FUNCS.get(fnName)

            if not fn:
                logger.warning(f"Unsupported function in FX math: {fnName}")
                return 0.0

            args = [self._evalFxMathAst(arg, context) for arg in node.args]
            return float(fn(*args))

        logger.warning("Unsupported expression in FX math.")
        return 0.0


    @err_catcher(name=__name__)
    def _evaluateFxMath(self, mathExpr: str, value: float, fxValues: dict[str, float]) -> float:
        '''Evaluate a formula from FX_CONTROLS.

        Args:
            mathExpr (str): The math expression to evaluate.
            value (float): The current value of the control.
            fxValues (dict[str, float]): A dictionary of all FX control values.

        Returns:
            float: The evaluated result of the math expression.
        '''

        #   If No Math
        if not mathExpr:
            return float(value)

        context = {"value": float(value)}
        context.update({name: float(v) for name, v in fxValues.items()})

        #   Process AST
        try:
            tree = ast.parse(mathExpr, mode="eval")
            return float(self._evalFxMathAst(tree, context))

        except Exception as e:
            logger.warning(f"Invalid FX math expression '{mathExpr}'. Using raw value. {e}")
            return float(value)


    @err_catcher(name=__name__)
    def _getFxUniformSpecs(self) -> list[tuple[str, dict[str, Any]]]:
        '''Return all shader uniform specs in control order.

        Returns:
            list[tuple[str, dict[str, Any]]]: A list of tuples containing control names and their corresponding uniform specifications.
        '''

        uniformSpecs: list[tuple[str, dict[str, Any]]] = []

        for controlName, controlData in Utils.FX_CONTROLS.items():
            for uniformSpec in controlData.get("uniforms", []):
                uniformSpecs.append((controlName, uniformSpec))

        return uniformSpecs


    @err_catcher(name=__name__)
    def _getFxUniformNames(self) -> list[str]:
        '''Return ordered shader uniform names used by FX controls.

        Returns:
            list[str]: A list of shader uniform names in the order they are defined in FX controls.
        '''

        return [spec["name"] for _, spec in self._getFxUniformSpecs() if "name" in spec]


    @err_catcher(name=__name__)
    def _buildFxUniformValues(self, fxValues: dict[str, float]) -> dict[str, float]:
        '''Build shader uniform values from current control values.

        Args:
            fxValues (dict[str, float]): A dictionary of all FX control values.

        Returns:
            dict[str, float]: A dictionary mapping uniform names to their evaluated values.
        '''

        uniformValues: dict[str, float] = {}

        for controlName, uniformSpec in self._getFxUniformSpecs():
            uniformName = uniformSpec.get("name")

            if not uniformName:
                continue

            sourceName = uniformSpec.get("source", controlName)
            controlData = Utils.FX_CONTROLS.get(controlName, {})
            sourceValue = fxValues.get(sourceName, Utils.FX_CONTROLS.get(sourceName, {}).get("default", 0.0))
            mathExpr = uniformSpec.get("math", controlData.get("math", "value"))
            uniformValues[uniformName] = self._evaluateFxMath(mathExpr, sourceValue, fxValues)

        return uniformValues


    ####    IMAGE SHADERS  ####

    @err_catcher(name=__name__)
    def _getImageVertexShaderSource(self) -> str:
        '''Return the shared vertex shader source used by the image pass.

        Returns:
            str: The GLSL source code for the vertex shader.
        '''

        return """
        #version 330
        layout(location = 0) in vec2 position;
        layout(location = 1) in vec2 texcoord;
        out vec2 vTexCoord;
        uniform vec2 uScale;
        void main() {
            vTexCoord = texcoord;
            gl_Position = vec4(position * uScale, 0.0, 1.0);
        }
        """


    @err_catcher(name=__name__)
    def _getImageFragmentShaderSource(self, useGpuOcio: bool) -> str:
        '''Return the image fragment shader source with optional OCIO GPU stages embedded.

        Args:
            useGpuOcio (bool): Whether to include OCIO GPU stages in the shader.

        Returns:
            str: The GLSL source code for the fragment shader.
        '''

        #   Initialize Shader
        shaderParts = [
            "#version 330",
            "",
            "uniform sampler2D uTex;",
            "uniform bool uUseOcioInput;",
            "uniform bool uUseOcioDisplay;",
            "uniform bool uUseOcioLut;",
            "uniform bool uEnableLinearFx;",
            "uniform bool uEnableDisplayFx;",
            "",
            "in vec2 vTexCoord;",
            "out vec4 fragColor;",
            "",
        ]

        #   Add FX Uniforms
        for uniformName in self._getFxUniformNames():
            shaderParts.append(f"uniform float {uniformName};")

        shaderParts.append("")

        #   Add OCIO GPU Stages if Enabled
        if useGpuOcio:
            for stage in self._iterOcioGpuStages():
                shaderParts.extend([stage["shaderText"], ""])

        #   Add FX Functions
        shaderParts.extend([
            "vec3 applyLinearFx(vec3 color)",
            "{",
            "    color *= uExposureGain;",
            "",
            "    float temp = clamp(uTemperature, -1.0, 1.0);",
            "    vec3 wb = vec3(",
            "        1.0 + max(temp, 0.0),",
            "        1.0,",
            "        1.0 + max(-temp, 0.0)",
            "    );",
            "    color *= wb;",
            "    color.g *= max(0.0, 1.0 + uTint);",
            "",
            "    color += vec3(uLift) * (vec3(1.0) - color);",
            "    color *= vec3(uGain);",
            "",
            "    const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);",
            "    float luma = dot(color, LUMA);",
            "    color = mix(vec3(luma), color, uSaturation);",
            "",
            "    color = pow(max(color, vec3(0.0)), vec3(uInvGamma));",
            "    return color;",
            "}",
            "",
            "vec3 applyDisplayFx(vec3 color)",
            "{",
            "    color += vec3(uBrightness);",
            "    color = (color - vec3(uBlackPoint)) / max(vec3(0.0001), vec3(1.0 - uBlackPoint));",
            "    color = clamp(color, vec3(0.0), vec3(1.0));",
            "    color *= 1.0 / max(0.0001, uWhitePoint);",
            "    color = clamp(color, vec3(0.0), vec3(1.0));",
            "    color = (color - vec3(uContrastPivot)) * uContrast + vec3(uContrastPivot);",
            "    return color;",
            "}",
            "",
            "void main()",
            "{",
            "    vec4 color = texture(uTex, vTexCoord);",
        ])

        #   Add OCIO GPU Stage Calls
        inputStage = self.ocioGpuStages.get("input") if useGpuOcio else None
        displayStage = self.ocioGpuStages.get("display") if useGpuOcio else None
        lutStage = self.ocioGpuStages.get("lut") if useGpuOcio else None

        #   Apply OCIO Input Transform
        if inputStage:
            shaderParts.extend([
                "",
                f"    vec4 ocioInputColor = {inputStage['functionName']}(color);",
                "    if (uUseOcioInput)",
                "    {",
                "        color = ocioInputColor;",
                "    }",
            ])

        #   Apply FX Adjustments
        shaderParts.extend([
            "",
            "    if (uEnableLinearFx)",
            "    {",
            "        color.rgb = applyLinearFx(color.rgb);",
            "    }",
        ])

        if displayStage:
            shaderParts.extend([
                "",
                f"    vec4 ocioDisplayColor = {displayStage['functionName']}(color);",
                "    if (uUseOcioDisplay)",
                "    {",
                "        color = ocioDisplayColor;",
                "    }",
            ])

        if lutStage:
            shaderParts.extend([
                "",
                f"    vec4 ocioLutColor = {lutStage['functionName']}(color);",
                "    if (uUseOcioLut)",
                "    {",
                "        color = ocioLutColor;",
                "    }",
            ])

        shaderParts.extend([
            "",
            "    if (uEnableDisplayFx)",
            "    {",
            "        color.rgb = applyDisplayFx(color.rgb);",
            "    }",
            "",
            "    fragColor = color;",
            "}",
        ])

        return "\n".join(shaderParts)


    @err_catcher(name=__name__)
    def _releaseOcioGpuTextures(self):
        '''Release any currently allocated OCIO GPU textures.'''

        if self.ocioGpuTextureIds:
            glDeleteTextures(self.ocioGpuTextureIds)

        self.ocioGpuTextureIds = []

        for stage in self._iterOcioGpuStages():
            for texture in stage["textures2D"] + stage["textures3D"]:
                texture["glId"] = None
                texture["unit"] = None


    @err_catcher(name=__name__)
    def _cacheImageProgramUniforms(self):
        '''Cache uniform locations for the current image shader program.'''

        glUseProgram(self.program_image)

        # Cache Uniform Locations
        self.linearFxEnableLoc = glGetUniformLocation(self.program_image, "uEnableLinearFx")
        self.displayFxEnableLoc = glGetUniformLocation(self.program_image, "uEnableDisplayFx")
        self.ocioInputEnableLoc = glGetUniformLocation(self.program_image, "uUseOcioInput")
        self.ocioDisplayEnableLoc = glGetUniformLocation(self.program_image, "uUseOcioDisplay")
        self.ocioLutEnableLoc = glGetUniformLocation(self.program_image, "uUseOcioLut")
        self.fxUniformLocs = {
            uniformName: glGetUniformLocation(self.program_image, uniformName)
            for uniformName in self._getFxUniformNames()
        }
        self.scaleLoc = glGetUniformLocation(self.program_image, "uScale")
        self.texLoc = glGetUniformLocation(self.program_image, "uTex")

        for stage in self._iterOcioGpuStages():
            for texture in stage["textures2D"] + stage["textures3D"]:
                texture["location"] = glGetUniformLocation(self.program_image, texture["samplerName"])

            for uniform in stage["uniforms"]:
                uniform["location"] = glGetUniformLocation(self.program_image, uniform["name"])


    @err_catcher(name=__name__)
    def _rebuildImageShaderProgram(self, useGpuOcio: bool) -> bool:
        '''Compile and cache the image shader program for the current OCIO pipeline state.

        Args:
            useGpuOcio (bool): Whether to include OCIO GPU stages in the shader.

        Returns:
            bool: True if the shader program was successfully compiled and cached, False otherwise.
        '''

        #   Compile Shader Program
        fragmentShaderSrc = self._getImageFragmentShaderSource(useGpuOcio)
        program = self._compileShaderProgram(self._getImageVertexShaderSource(), fragmentShaderSrc)

        if not program:
            return False

        #   Release Previous Program
        if self.program_image:
            glDeleteProgram(self.program_image)

        #   Cache New Program and Uniform Locations
        self.program_image = program
        self._cacheImageProgramUniforms()
        return True


    @err_catcher(name=__name__)
    def _uploadOcioGpuTextures(self):
        '''Upload OCIO LUT textures to the current OpenGL context.'''

        #   Release Previous OCIO GPU Textures
        self._releaseOcioGpuTextures()

        textureUnit = 1
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        #   Upload 2D and 3D Textures for Each OCIO GPU Stage
        for stage in self._iterOcioGpuStages():
            #   Upload 2D Textures
            for texture in stage["textures2D"]:
                texture["unit"] = textureUnit
                textureUnit += 1
                texture["glId"] = glGenTextures(1)
                self.ocioGpuTextureIds.append(texture["glId"])

                glTarget = GL_TEXTURE_1D if texture["dimensions"] == self.OcioModule.GpuShaderDesc.TEXTURE_1D else GL_TEXTURE_2D
                glActiveTexture(GL_TEXTURE0 + texture["unit"])
                glBindTexture(glTarget, texture["glId"])

                glTexParameteri(glTarget, GL_TEXTURE_MIN_FILTER,
                                GL_NEAREST if texture["interpolation"] == self.OcioModule.Interpolation.INTERP_NEAREST else GL_LINEAR)
                
                glTexParameteri(glTarget, GL_TEXTURE_MAG_FILTER,
                                GL_NEAREST if texture["interpolation"] == self.OcioModule.Interpolation.INTERP_NEAREST else GL_LINEAR)
                
                glTexParameteri(glTarget, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)

                if glTarget == GL_TEXTURE_2D:
                    glTexParameteri(glTarget, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

                if texture["channel"] == self.OcioModule.GpuShaderDesc.TEXTURE_RED_CHANNEL:
                    glFormat = GL_RED
                    glInternal = GL_R32F

                else:
                    glFormat = GL_RGB
                    glInternal = GL_RGB32F

                if glTarget == GL_TEXTURE_1D:
                    glTexImage1D(
                        GL_TEXTURE_1D,
                        0,
                        glInternal,
                        texture["width"],
                        0,
                        glFormat,
                        GL_FLOAT,
                        texture["values"]
                    )

                else:
                    glTexImage2D(
                        GL_TEXTURE_2D,
                        0,
                        glInternal,
                        texture["width"],
                        texture["height"],
                        0,
                        glFormat,
                        GL_FLOAT,
                        texture["values"]
                    )

            #   Upload 3D Textures
            for texture in stage["textures3D"]:
                texture["unit"] = textureUnit
                textureUnit += 1
                texture["glId"] = glGenTextures(1)
                self.ocioGpuTextureIds.append(texture["glId"])

                glActiveTexture(GL_TEXTURE0 + texture["unit"])
                glBindTexture(GL_TEXTURE_3D, texture["glId"])
                glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER,
                                GL_NEAREST if texture["interpolation"] == self.OcioModule.Interpolation.INTERP_NEAREST else GL_LINEAR)
                
                glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER,
                                GL_NEAREST if texture["interpolation"] == self.OcioModule.Interpolation.INTERP_NEAREST else GL_LINEAR)
                
                glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)

                glTexImage3D(
                    GL_TEXTURE_3D,
                    0,
                    GL_RGB32F,
                    texture["edgeLen"],
                    texture["edgeLen"],
                    texture["edgeLen"],
                    0,
                    GL_RGB,
                    GL_FLOAT,
                    texture["values"]
                )

        glActiveTexture(GL_TEXTURE0)


    @err_catcher(name=__name__)
    def _setOcioGpuUniform(self, uniform: dict):
        '''Upload a cached OCIO-generated uniform value to the current shader program.

        Args:
            uniform (dict): The uniform dictionary containing type, value, and location.
        '''

        location = uniform["location"]

        if location < 0:
            return

        #   Set Uniform Value Based on Type
        if uniform["type"] == self.OcioModule.UNIFORM_BOOL:
            glUniform1i(location, int(uniform["value"]))

        elif uniform["type"] == self.OcioModule.UNIFORM_DOUBLE:
            glUniform1f(location, uniform["value"])

        elif uniform["type"] == self.OcioModule.UNIFORM_FLOAT3:
            glUniform3f(location, *uniform["value"])

        elif uniform["type"] == self.OcioModule.UNIFORM_VECTOR_FLOAT:
            values = uniform["value"]
            if len(values):
                glUniform1fv(location, len(values), values)

        elif uniform["type"] == self.OcioModule.UNIFORM_VECTOR_INT:
            values = uniform["value"]
            if len(values):
                glUniform1iv(location, len(values), values)


    @err_catcher(name=__name__)
    def _bindOcioGpuResources(self):
        '''Bind the OCIO GPU textures and uniforms for the current image shader program.'''

        for stage in self._iterOcioGpuStages():
            for texture in stage["textures2D"]:
                if texture["location"] >= 0 and texture["unit"] is not None and texture["glId"]:
                    glUniform1i(texture["location"], texture["unit"])
                    glActiveTexture(GL_TEXTURE0 + texture["unit"])
                    glTarget = GL_TEXTURE_1D if texture["dimensions"] == self.OcioModule.GpuShaderDesc.TEXTURE_1D else GL_TEXTURE_2D
                    glBindTexture(glTarget, texture["glId"])

            for texture in stage["textures3D"]:
                if texture["location"] >= 0 and texture["unit"] is not None and texture["glId"]:
                    glUniform1i(texture["location"], texture["unit"])
                    glActiveTexture(GL_TEXTURE0 + texture["unit"])
                    glBindTexture(GL_TEXTURE_3D, texture["glId"])

            for uniform in stage["uniforms"]:
                self._setOcioGpuUniform(uniform)

        glActiveTexture(GL_TEXTURE0)


    @err_catcher(name=__name__)
    def _syncOcioGpuPipeline(self) -> bool:
        '''Compile the image shader and upload OCIO textures for the current staged GPU pipeline.

        Returns:
            bool: True if the pipeline was successfully synchronized, False otherwise.
        '''

        #   Check for Valid OCIO Context
        if not self.context() or not self.context().isValid():
            return False

        #   Return True if Already Synced and Not Dirty
        if not self.ocioGpuShaderDirty and self.program_image:
            return True

        #   Get Ordered OCIO GPU Stages
        stages = self._iterOcioGpuStages()

        if stages:
            try:
                #   Rebuild Image Shader Program with OCIO GPU Stages
                if self._rebuildImageShaderProgram(useGpuOcio=True):
                    self._uploadOcioGpuTextures()
                    self.ocioGpuReady = True
                    self.ocioGpuShaderDirty = False
                    return True

            except Exception as e:
                logger.warning(f"ERROR: Failed to build OCIO GPU pipeline: {e}")

        #   If No Stages or Failed, Release Textures and Rebuild Shader Without OCIO
        self._releaseOcioGpuTextures()
        self.ocioGpuReady = False

        if not self._rebuildImageShaderProgram(useGpuOcio=False):
            self.program_image = None
            return False

        self.ocioGpuShaderDirty = False
        return True


    @err_catcher(name=__name__)
    def _compileShaderProgram(self, vert_src: str, frag_src: str) -> int:
        '''Compiles a GLSL shader program from vertex and fragment shader code.

        Args:
            vert_src (str): The source code for the vertex shader.
            frag_src (str): The source code for the fragment shader.

        Returns:
            int: The OpenGL program ID if compilation and linking succeed, None otherwise.
        '''

        #   Compile the Shaders
        vs = self._compileShader(vert_src, GL_VERTEX_SHADER)
        fs = self._compileShader(frag_src, GL_FRAGMENT_SHADER)

        #   Create a GL Progrm and Add Shaders
        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        #   Check for Link Errors
        if not glGetProgramiv(program, GL_LINK_STATUS):
            err = glGetProgramInfoLog(program).decode()
            logger.warning(f"ERROR: GLSL link error: {err}")

            glDeleteProgram(program)
            return None
             
        return program
    

    @err_catcher(name=__name__)
    def _compileShader(self, src: str, shader_type: int) -> int:
        '''Compiles a GLSL shader from source code.

        Args:
            src (str): The source code for the shader.
            shader_type (int): The type of shader (e.g., GL_VERTEX_SHADER or GL_FRAGMENT_SHADER).

        Returns:
            int: The OpenGL shader ID if compilation succeeds, None otherwise.
        '''

        #   Create Empty Shader
        shader = glCreateShader(shader_type)

        #   Compile Using Shader Code
        glShaderSource(shader, src)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            err = glGetShaderInfoLog(shader).decode()
            logger.warning(f"ERROR: GLSL compile: [{shader_type}]: {err}")

            glDeleteShader(shader)
            return None
        
        return shader
    

    @err_catcher(name=__name__)
    def _initializeGL(self):
        '''Initializes the OpenGL context, generates textures, and compiles shaders.'''

        #   Generate Texture ID
        self.texture_id = glGenTextures(1)

        #    Shader Code for Checkboard
        checker_frag_src = """
        #version 330

        in vec2 vTexCoord;
        out vec4 fragColor;

        uniform float uCheckerCount;
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        uniform float uAspect; // width / height

        void main() {
            float cx = floor(vTexCoord.x * uCheckerCount * uAspect);
            float cy = floor(vTexCoord.y * uCheckerCount);

            if (mod(cx + cy, 2.0) < 1.0)
                fragColor = vec4(uColor1, 1.0);
            else
                fragColor = vec4(uColor2, 1.0);
        }
        """

        vertex_shader_src = self._getImageVertexShaderSource()

        #   Compile/link Programs
        self.program_checker = self._compileShaderProgram(vertex_shader_src, checker_frag_src)

        if not self.program_checker:
            logger.error("ERROR: Failed to Compile/Link Shaders")
            self.program_image = None
            return

        #   Checker BG Uniform Locations
        glUseProgram(self.program_checker)
        self.checkCountLoc = glGetUniformLocation(self.program_checker, "uCheckerCount")
        self.checkColor1Loc = glGetUniformLocation(self.program_checker, "uColor1")
        self.checkColor2Loc = glGetUniformLocation(self.program_checker, "uColor2")
        self.checkAspectLoc = glGetUniformLocation(self.program_checker, "uAspect")
        self.checkScaleLoc = glGetUniformLocation(self.program_checker, "uScale")

        if not self._syncOcioGpuPipeline():
            logger.error("ERROR: Failed to Compile/Link Image Shader")
            self.program_image = None
            return

        #   Enable Alpha Blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


    @err_catcher(name=__name__)
    def _setupQuad(self):
        '''Sets up the vertex array object (VAO), vertex buffer object (VBO), and element buffer object (EBO) for rendering a quad.'''
        
        #   Sets Verts for Quad
        verts = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 1.0,
        ], dtype=np.float32)

        #   Create Two Tris for the Quad
        indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

        #   Generate GL Objects
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)

        #   Bind VAO and Upload Vertex Data
        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)

        #   Upload EBO
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        #   Set Vertex Pointers
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))

        #   Unbind VAO
        glBindVertexArray(0)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)  # bypass EBO
        glBindVertexArray(0)


    @err_catcher(name=__name__)
    def _resizeGL(self, w: int, h: int):
        '''Resizes the OpenGL viewport and updates the checkerboard size.
        
        Args:
            w (int): The new width of the OpenGL viewport.
            h (int): The new height of the OpenGL viewport.
        '''

        glViewport(0, 0, max(1, w), max(1, h))


    @err_catcher(name=__name__)
    def _createLutTransform(self, lut_path: str) -> Any:
        '''Creates an OCIO FileTransform for the given LUT path if it exists and is valid.

        Args:
            lut_path (str): Path to the LUT file.

        Returns:
            Any | None: The created FileTransform if valid, None otherwise.
        '''

        if not os.path.isfile(lut_path):
            logger.warning(f"LUT path not found: {lut_path}")
            return None

        #   Create OCIO FileTransform
        try:
            lutTransform = self.OcioModule.FileTransform(
                lut_path,
                interpolation=self.OcioModule.Interpolation.INTERP_LINEAR,
                direction=self.OcioModule.TransformDirection.TRANSFORM_DIR_FORWARD
            )

            #   Quick Validation by Creating Temp Processor
            self.OcioModule.GetCurrentConfig().getProcessor(lutTransform)
            return lutTransform

        except Exception as e:
            logger.warning(f"Invalid LUT file '{lut_path}': {e}")
            return None


    @err_catcher(name=__name__)
    def _buildOCIOProcessor(self) -> bool:
        '''Builds the OCIO processor based on the current input space, display, view, look, and LUTs.

        Returns:
            bool: True if the processor was successfully built, False otherwise.
        '''

        #   Reset OCIO State
        self.ocioProcessor = None
        self.ocioWorkingSpace = ""
        self.ocioGpuStages = {
            "input": None,
            "display": None,
            "lut": None,
        }
        self.ocioGpuAvailable = False
        self.ocioGpuReady = False
        self.ocioGpuShaderDirty = True

        try:
            #   Get Current OCIO Config
            config = self.OcioModule.GetCurrentConfig()

            #   Get Working Space and Determine if Input is Scene-Referred
            self.ocioWorkingSpace = self._resolveOcioWorkingSpace(config)
            inputIsSceneReferred = self._isSceneReferredColorSpace(config, self.inputSpace)
            workingSpace = self.ocioWorkingSpace if (inputIsSceneReferred and self.ocioWorkingSpace) else self.inputSpace

            #   Build Input Transform if Needed
            if self.inputSpace and workingSpace and self.inputSpace != workingSpace:
                transform_input = self.OcioModule.ColorSpaceTransform(src=self.inputSpace, dst=workingSpace)
                processor_input = config.getProcessor(transform_input)
                self.ocioGpuStages["input"] = self._createOcioGpuStage(
                    processor_input,
                    "OCIO_InputToLinear",
                    "ocio_input_"
                )

            #   Build Display Transform
            elif inputIsSceneReferred and not self.ocioWorkingSpace:
                logger.warning("OCIO scene_linear role not found; skipping dedicated input-to-linear stage.")

            transform_display = self.OcioModule.GroupTransform()

            #   Append Look Transform if Applicable
            if self.look:
                transform_look = self.OcioModule.LookTransform()
                transform_look.setSrc(workingSpace)
                transform_look.setDst(workingSpace)
                transform_look.setLooks(self.look)
                transform_display.appendTransform(transform_look)

            #   Append Display/View Transform
            transform_dispView = self.OcioModule.DisplayViewTransform(
                src=workingSpace,
                display=self.display,
                view=self.view,
                looksBypass=True,
                dataBypass=True
            )

            transform_display.appendTransform(transform_dispView)
            processor_display = config.getProcessor(transform_display)
            self.ocioGpuStages["display"] = self._createOcioGpuStage(
                processor_display,
                "OCIO_DisplayView",
                "ocio_display_"
            )

            #   Build LUT Transform if Applicable
            if self.luts:
                transform_luts = self.OcioModule.GroupTransform()
                self._appendLutTransforms(transform_luts)
                processor_luts = config.getProcessor(transform_luts)
                self.ocioGpuStages["lut"] = self._createOcioGpuStage(
                    processor_luts,
                    "OCIO_DisplayLut",
                    "ocio_lut_"
                )

            self.ocioGpuAvailable = bool(self._iterOcioGpuStages())

            return bool(self.ocioGpuAvailable)

        except Exception as e:
            logger.warning(f"ERROR: Failed to build OCIO Processor: {e}")
            self.clearOcioTransforms()
            return False


    @err_catcher(name=__name__)
    def _prepareTextureData(self, frameData: np.ndarray) -> np.ndarray | None:
        '''Normalize image data into a contiguous float16 RGB/RGBA array suitable for OpenGL texture upload.

        Args:
            frameData (np.ndarray): The input image data to normalize.

        Returns:
            np.ndarray | None: Contiguous RGB or RGBA float16 image or None
        '''

        ##   Validate Input
        if frameData is None:
            return None
        if not isinstance(frameData, np.ndarray):
            return None
        if frameData.size == 0:
            return None

        ##   Convert Input to Numpy Array
        img_source = np.asarray(frameData)

        #   Return Early if Already Float16 and RGBA
        if (
            img_source.dtype == np.float16
            and img_source.ndim == 3
            and img_source.shape[2] in (3, 4)
            and img_source.flags.c_contiguous
        ):
            return img_source

        #   Convert to Float16 if Needed
        if img_source.dtype == np.float16:
            img_normalized = img_source

        elif np.issubdtype(img_source.dtype, np.floating):
            img_normalized = img_source.astype(np.float16)

        elif img_source.dtype == np.uint16:
            img_normalized = (img_source.astype(np.float32) / 65535.0).astype(np.float16)

        elif img_source.dtype == np.uint8:
            img_normalized = (img_source.astype(np.float32) / 255.0).astype(np.float16)

        #   Fallback (Clip to 0-255, convert to float16 in 0-1 range)
        else:
            img_normalized = (np.clip(img_source, 0, 255).astype(np.float32) / 255.0).astype(np.float16)

        #   Convert Grayscale Image (H, W) to RGB Array (H, W, 3)
        if img_normalized.ndim == 2:
            img_channels = np.repeat(img_normalized[..., None], 3, axis=2)

        #   Normalize Multi-Channel Image Layout (H, W, C)
        elif img_normalized.ndim == 3:
            channel_count = img_normalized.shape[2]

            #   Convert Single Channel Image (H, W, 1) to RGB Array (H, W, 3)
            if channel_count == 1:
                img_channels = np.repeat(img_normalized, 3, axis=2)

            #   Convert Two Channel Image (H, W, 2) to RGB Array (H, W, 3)
            elif channel_count == 2:
                img_channels = np.repeat(img_normalized[..., :1], 3, axis=2)

            #   Keep RGB Image (H, W, 3) As Is
            elif channel_count == 3:
                img_channels = img_normalized

            #   Convert RGBA (H, W, 4+) to RGBA Array (H, W, 4) - discards additional channels
            elif channel_count >= 4:
                img_channels = img_normalized[..., :4]

            else:
                return None

        else:
            return None

        #   Validate Dimensions
        if img_channels.shape[0] <= 0 or img_channels.shape[1] <= 0:
            return None

        return np.ascontiguousarray(img_channels)



    @err_catcher(name=__name__)
    def _paintGL(self):
        '''Clears the window, draws the checkerboard, and then draws the image if available.'''

        #   Clear Window
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        #   Bind VAO Quad
        glBindVertexArray(self.vao)

        ### CHECKERBOARD
        glUseProgram(self.program_checker)
        glUniform3f(self.checkColor1Loc, *self.check_color1)
        glUniform3f(self.checkColor2Loc, *self.check_color2)

        #   Checker Sizing
        glUniform2f(self.checkScaleLoc, self.scale_w, self.scale_h)
        draw_w = max(1.0, self.width() * float(self.scale_w))
        draw_h = max(1.0, self.height() * float(self.scale_h))
        aspect = draw_w / draw_h
        glUniform1f(self.checkAspectLoc, aspect)
        glUniform1f(self.checkCountLoc, max(1.0, draw_h / max(1.0, float(self.check_size))))

        #   Draw Checkerboard Quad
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

        ### FRAME IMAGE

        if self.ocioGpuShaderDirty or not self.program_image:
            self._syncOcioGpuPipeline()

        if not self.program_image:
            return

        # Draw image
        if self.frame is None:
            return

        #   Prepare Image Data
        img_source = self._prepareTextureData(self.frame)

        if img_source is None:
            glBindVertexArray(0)
            return

        #   Apply OCIO Transform
        try:
            img_upload = img_source
            ocioActive = bool(self.global_useOCIO and self.Player.ocioEnabled)
            ocioGpuActive = bool(ocioActive and self.ocioGpuAvailable and self.ocioGpuReady)

            #   RGBA Image
            if img_source.shape[2] == 4:
                img_rgb = img_source[..., :3]
                img_alpha = img_source[..., 3:4]

                img_upload = np.concatenate(
                    [img_rgb, img_alpha],
                    axis=-1
                )

            #   RGB Image
            else:
                if ocioActive and not ocioGpuActive:
                    img_upload = img_source

        except Exception as e:
            logger.warning(f"ERROR: Unable to Apply OCIO transform: {e}")
            self.Player.setOcioStatus(f"OCIO is disabled or invalid: {e}")
            img_upload = img_source

        #   Ensure OpenGL Compatible Buffer
        img_upload = np.ascontiguousarray(img_upload)

        #   Texture Upload
        height, width = img_upload.shape[:2]
        channels = img_upload.shape[2]

        #   Bind Texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        #   Set Pixel Alignment
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        try:
            #   Determine Texture Format
            if channels == 4:
                gl_format = GL_RGBA
                internal = GL_RGBA16F
            else:
                gl_format = GL_RGB
                internal = GL_RGB16F

            if (
                width != self.texture_width
                or height != self.texture_height
                or internal != self.texture_internal
            ):
                # Allocate new texture storage
                glTexImage2D(
                    GL_TEXTURE_2D,
                    0,
                    internal,
                    width,
                    height,
                    0,
                    gl_format,
                    GL_HALF_FLOAT,
                    img_upload
                )

                self.texture_width = width
                self.texture_height = height
                self.texture_internal = internal

            else:
                # Update existing texture
                glTexSubImage2D(
                    GL_TEXTURE_2D,
                    0,
                    0,
                    0,
                    width,
                    height,
                    gl_format,
                    GL_HALF_FLOAT,
                    img_upload
                )


            #   Configure Alpha Blending
            if channels == 4:
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            else:
                glBlendFunc(GL_ONE, GL_ZERO)

        except Exception as e:
            logger.warning(f"GL texture upload failed. Falling back to black frame: {e}")
            self.frame = self.Player.makeBlackFrame()
            glBindVertexArray(0)
            return

        #   Enable Linear Filtering for Texture Scaling
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        ##   Draw Image Quad

        #   Activate Image Shader
        glUseProgram(self.program_image)

        ocioGpuActive = bool(self.global_useOCIO and self.Player.ocioEnabled and self.ocioGpuAvailable and self.ocioGpuReady)

        #   Pass Viewer FX Adjustments to Shader
        glUniform1i(self.linearFxEnableLoc, int(self.fxEnabled))
        glUniform1i(self.displayFxEnableLoc, int(self.fxEnabled))
        glUniform1i(self.ocioInputEnableLoc, int(ocioGpuActive and self.ocioGpuStages.get("input") is not None))
        glUniform1i(self.ocioDisplayEnableLoc, int(ocioGpuActive and self.ocioGpuStages.get("display") is not None))
        glUniform1i(self.ocioLutEnableLoc, int(ocioGpuActive and self.ocioGpuStages.get("lut") is not None))

        for uniformName, location in self.fxUniformLocs.items():
            if location >= 0:
                glUniform1f(location, self.fxUniformValues.get(uniformName, 0.0))

        #   Set Image Scale
        glUniform2f(self.scaleLoc, self.scale_w, self.scale_h)

        #   Bind Image Texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        #   Pass Texture Unit to Shader
        glUniform1i(self.texLoc,0)

        if ocioGpuActive:
            self._bindOcioGpuResources()

        #   Draw Image Geometry
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        #   Unbind Index Buffer
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

