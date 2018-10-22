if menuMan.findMenu "Prism" != undefined then
(
menuMan.unRegisterMenu (menuMan.findMenu "Prism")
)
(
local mainMenuBar = menuMan.getMainMenuBar()
local subMenu = menuMan.createMenu "Prism"
local psaveItem = menuMan.createActionItem "PrismSave" "Prism"
subMenu.addItem psaveItem -1
local pcommentsaveItem = menuMan.createActionItem "PrismCommentsave" "Prism"
subMenu.addItem pcommentsaveItem -1
local browserItem = menuMan.createActionItem "OpenProjectBrowser" "Prism"
subMenu.addItem browserItem -1
local pmanagerItem = menuMan.createActionItem "PrismStateManager" "Prism"
subMenu.addItem pmanagerItem -1
local settingsItem = menuMan.createActionItem "PrismSettings" "Prism"
subMenu.addItem settingsItem -1
local subMenuItem = menuMan.createSubMenuItem "Prism" subMenu
local subMenuIndex = mainMenuBar.numItems()
mainMenuBar.addItem subMenuItem subMenuIndex
menuMan.updateMenuBar()
menuMan.saveMenuFile (menuMan.getMenuFile())
--menuMan.unRegisterMenu (menuMan.findMenu "Prism")
)