macroScript PrismStateManager category:"Prism" tooltip:"Open the State Manager" buttontext:"State Manager"
(
	python.Execute "pcore.stateManager()"
)

macroScript PrismSave category:"Prism" tooltip:"Save the current file to a new version" buttontext:"Save Version"
(
	python.Execute "pcore.saveScene()"
)

macroScript PrismCommentsave category:"Prism" tooltip:"Save the current file to a new version with a comment" buttontext:"Save Comment"
(
	python.Execute "pcore.saveWithComment()"
)

macroScript OpenProjectBrowser category:"Prism" tooltip:"Open Project Browser" buttontext:"Project Browser"
(
	python.Execute "pcore.projectBrowser()"
)

macroScript PrismSettings category:"Prism" tooltip:"Open Prism settings" buttontext:"Settings"
(
	python.Execute "pcore.prismSettings()"
)