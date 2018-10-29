Overview
*****************

Introduction
===================

Prism is a software aimed at animation and VFX projects. Its goal is to automate organizational tasks and simplify different steps of the workflow, when creating digital images. One key aspect of Prism is that it is very artist friendly and easy to use. No programming skills are required to setup and to use Prism, which make it the perfect tools for teams and individuals, who want to focus on the creative parts of a project.

The images in this documentation were mostly taken from Prism Standalone, Houdini- or Maya- integration of Prism, but the Prism user interface in other DCC applications is almost identical. The features described in this documentation can be applied to the integration of all supported programs.


What's New in v1.1.1
=====================

This version makes Prism more customizable and more flexible to use.

Prism now supports "custom" plugins, which can be used to develop customizations of various features in Prism, while staying compatible with the official Prism updates.

It is possible now to choose an installation directory for Prism. This makes it possible to use a single central installation of Prism on a server for the whole team. The prefences are now saved at a different location:

Windows: %userprofile%/Documents/Prism

Linux: $HOME/Prism

Mac: ~Library/Preferences/Prism

It is now possible to update Prism from GitHub or from a .zip file, which makes it easier and faster to get the latest changes.

Besides that there are many small usability improvements, like setting the FPS in a scene on a FPS mismatch or an option to show additional import options during the import of an object. Tools from the Tray icon start a lot faster now and there are many bugfixes added in this release.

Lastely it is now possible to use the official Pixar USD plugin for Houdini with Prism. Right now the USD integration allows to export and import USD files in Houdini if you have the USD plugin installed, but in the future there will be more Prism features, which will make use of more features that USD offers.


What's New in v1.1.0
=====================

This version of Prism includes some massive internal restructuring. The result is that each DCC integration is now a plugin and not hardcoded in the core Prism code. You can remove the complete support for a DCC app simply by removing the corresponding folder in the plugin directory. This makes it also a lot easier to develop support for additional DCC apps.
The biggest features include:


**Linux and MacOSX**

Prism is now available for Linux and MacOSX (previously Windows only). However, not all features of Prism are available on Linux and Mac yet.


**Adobe Photoshop**

You can use Prism to save your PSD files in the Prism project and export your image into different image formats. You can access Prism from the File/Scripts menu in Photoshop or connect your standalone Project Browser to an open Photoshop instance from the options menu of the Project Browser.


**Blackmagic Fusion**

You can use Prism in Fusion to manage your compositions and render them to the Prism project with the WritePrism macro.


**Natron**

The Natron integration of Prism is similar to the Nuke integration. From the main menubar you can access the Prism tools to manage your Natron project and you can use the WritePrism node to render your comp to your Prism project.


**Add and remove Prism integrations**

In the new DCC apps tab in the Prism settings it is now possible to add and remove the Prism integratio for your DCC app versions. You don't need to run the Prism installer for that anymore.


**Hooks**

Prism allows you to add your own python code at specific events. You can use this to customize Prism to your needs. For example you could clean up your scene before rendering or communicate with external pipeline tools after a Prism export.
The hooks are located in your Prism project in this folder: 00_Pipeline/Hooks
Prism comes with some preset scripts in that folder and you can add your custom python code into these existing files. The individual presets contain detailed information when they will be executed.


**Combine media files**

A new button in the Prism Project Browser allows you to combine multiple media sources into one video file as a sequence. This allows you to easily play multiple shots in sequence or create a video file with different versions of a shot for your client.


**Support for Maya renderlayers**

When starting a rendering or submitting a renderjob in Maya, you can select which renderlayer should be rendered. This allows to work with more complex scenes as before.


**New Maya export options**

When exporting objects from Maya there are now additional options:

* Import references
* Delete unknown nodes
* Delete display layers

Additionally you can export your objects to the .mb (Maya Binary) format now.


**Support for additional Houdini export nodes**

Prism can use now the "Filecache" node and the "Geometry" and "Alembic" node in the "out" context to export objects.

|

This Prism version contains more minor features, changes and bugfixes.
For a detailed list of new features go to the `Changelog <https://prism-pipeline.com/changelog/>`_


Supported Software
===================

Prism can be used as a separate software (standalone), but most of the time you will use Prism inside some DDC apps (Digital Content Creation Application).
In the list below you can see, which DCC integrations are available on which OS and which versions are supported. Additional versions can work but are untested and not officially supported. The goal is always to support the latest version of a DCC app.

============  ==========  ======  ========   ============================================
Integration     Windows   Linux   Mac OSX    Supported Versions
------------  ----------  ------  --------   --------------------------------------------
============  ==========  ======  ========   ============================================
3dsMax             X                           2017-2019
Blender            X                           2.79
Fusion             X                           9.02
Houdini            X        X        X         16.0-17.0
Maya               X        X        X         2016-2018 (earlier versions untested)
Natron             X        X                  2.13-2.14  (earlier versions untested)
Nuke               X        X        X         >10.0 (earlier versions unstable)
Photoshop          X                           CS6, CC (earlier versions untested)
Standalone         X        X        X
============  ==========  ======  ========   ============================================

Additional integrations can be developed by 3rd parties and can be used in combination with the official Prism software.