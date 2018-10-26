You can add custom plugins to this folder (Plugins/Custom in your Prism folder) to extend or change the features of Prism.

To create a new plugin duplicate the "PluginEmpty" folder. Then replace "PluginEmpty" with your pluginname in all filenames in this folder and in the content of all .py files.

You can use the various callback functions in the Prism_<PluginName>_Functions.py file to execute your custom python code at specific events.
Then save the file and restart your Prism app to reload the plugin.

You can also use the "reloadCustomPlugins" function of the Prism core object to reload your plugin without the need to restart your 3d app.
For example in Maya you can execute this in the Python script editor:
pcore.reloadCustomPlugins()

If you need additional callback functions for your, contact me at contact@prism-pipeline.com and I'll add the callbacks as soon as possible to the official Prism version.