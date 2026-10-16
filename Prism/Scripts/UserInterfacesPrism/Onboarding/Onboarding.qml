import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.12

Rectangle {
    id: root
    color: "#182023"
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#1a1c25" }
        GradientStop { position: 1.0; color: "#15171e" }
    }

    readonly property color accentColor: "#AF326D"
    readonly property bool pluginPageAvailable: onboarding.accountAvailable && onboarding.hubAvailable
    property int pendingStep: -1
    property int pluginSelectionRevision: 0
    property string selectedPluginBundle: onboarding.defaultPluginBundleTitle
    property string selectedProjectManager: ""

    function activePluginNames() {
        if (!pluginPageAvailable)
            return []

        var revision = pluginSelectionRevision
        var names = onboarding.usingManualPluginSelection
                    ? onboarding.manualPluginNames.slice(0)
                    : selectedBundlePluginNames()

        for (var managerIndex = 0; managerIndex < onboarding.projectManagerBundles.length; ++managerIndex) {
            var manager = onboarding.projectManagerBundles[managerIndex]
            if (manager.title !== selectedProjectManager)
                continue

            for (var managerPluginIndex = 0; managerPluginIndex < manager.plugins.length; ++managerPluginIndex) {
                if (names.indexOf(manager.plugins[managerPluginIndex]) === -1)
                    names.push(manager.plugins[managerPluginIndex])
            }
            break
        }
        return names
    }

    function selectedBundlePluginNames() {
        for (var bundleIndex = 0; bundleIndex < onboarding.pluginBundles.length; ++bundleIndex) {
            var bundle = onboarding.pluginBundles[bundleIndex]
            if (bundle.title === selectedPluginBundle)
                return bundle.plugins.slice(0)
        }
        return []
    }

    function manualPluginSeedNames() {
        return onboarding.usingManualPluginSelection
                ? onboarding.manualPluginNames : selectedBundlePluginNames()
    }

    function pluginSummary() {
        var names = activePluginDisplayNames()
        if (!names.length)
            return "No plugins selected"

        var summary = names.slice(0, 3).join(", ")
        return names.length > 3 ? summary + "  +" + (names.length - 3) + " more" : summary
    }

    function pluginDisplayName(pluginName) {
        for (var index = 0; index < onboarding.availablePlugins.length; ++index) {
            var plugin = onboarding.availablePlugins[index]
            if (plugin.pluginName === pluginName)
                return plugin.name
        }

        var predefinedDisplayNames = {
            "AfterEffects": "After Effects",
            "ExecutionGraph": "Execution Graph",
            "MediaExtension": "Media Extension",
            "ProjectManagement": "Project Management",
            "Unreal": "Unreal Engine"
        }
        return predefinedDisplayNames[pluginName] || pluginName
    }

    function activePluginDisplayNames() {
        return pluginDisplayNames(activePluginNames())
    }

    function pluginDisplayNames(pluginNames) {
        var displayNames = []
        for (var index = 0; index < pluginNames.length; ++index)
            displayNames.push(pluginDisplayName(pluginNames[index]))
        return displayNames
    }

    function installablePluginNames() {
        var selectedNames = activePluginNames()
        var installableNames = []
        for (var index = 0; index < selectedNames.length; ++index) {
            if (!onboarding.isPluginInstalled(selectedNames[index]))
                installableNames.push(selectedNames[index])
        }
        return installableNames
    }

    function newPluginSummary() {
        var names = pluginDisplayNames(installablePluginNames())
        if (!names.length)
            return "No new plugins"

        var summary = names.slice(0, 3).join(", ")
        return names.length > 3 ? summary + "  +" + (names.length - 3) + " more" : summary
    }

    function pluginActionText() {
        var count = installablePluginNames().length
        if (!count)
            return "Continue"

        return count === 1 ? "Install 1 Plugin" : "Install " + count + " Plugins"
    }

    function navigateTo(step) {
        if (step === onboarding.step || pageTransition.running)
            return

        pendingStep = step
        pageTransition.start()
    }

    readonly property var titles: [
        "Welcome to Prism Pipeline",
        "Your Prism Account",
        "Add more features",
        "Set up your project",
        "Ready to create"
    ]
    readonly property var descriptions: [
        "Let's get you started in a few simple steps.",
        "Sign in to access more features and additional plugins (optional).",
        "Install the plugins that fit your workflow (optional).",
        "Create a new production or open an existing project.",
        "You've completed the onboarding successfully."
    ]

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 292
            Layout.fillHeight: true
            color: "#20212b"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#292b38" }
                GradientStop { position: 1.0; color: "#1b1d27" }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 34
                spacing: 18

                Image {
                    Layout.preferredWidth: 224
                    Layout.preferredHeight: 84
                    fillMode: Image.PreserveAspectFit
                    source: prismLogoUrl
                    sourceSize.width: 488
                    sourceSize.height: 268
                }

                Item { Layout.preferredHeight: 18 }

                Repeater {
                    model: ["Welcome", "Account", "Plugins", "Project", "Ready"]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        radius: 5
                        color: index === onboarding.step ? "#2a2028" :
                               navigationMouse.containsMouse ? "#292b38" : "transparent"
                        opacity: index <= onboarding.step ? 1 : 0.42
                        Behavior on opacity { NumberAnimation { duration: 640 } }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 7
                            anchors.rightMargin: 7
                            spacing: 13

                            Rectangle {
                                Layout.preferredWidth: 30
                                Layout.preferredHeight: 30
                                radius: 5
                                color: index === onboarding.step ? root.accentColor : "#292b36"
                                border.color: index < onboarding.step ? root.accentColor : "transparent"

                                Text {
                                    anchors.centerIn: parent
                                    text: index < onboarding.step ? "\u2713" : index + 1
                                    color: index === onboarding.step ? "#ffffff" : "#d7e1e1"
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData
                                color: "#edf4f3"
                                font.pixelSize: 15
                                font.bold: index === onboarding.step
                            }
                        }

                        MouseArea {
                            id: navigationMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.navigateTo(index)
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                PrismButton {
                    id: helpButton
                    Layout.preferredWidth: 96
                    text: "Help"
                    kind: "ghost"
                    iconSource: "icons/circle-question-mark.svg"
                    onClicked: onboarding.openHelp()

                    ToolTip.visible: helpButton.hovered || helpButton.pointerHovered
                    ToolTip.delay: 400
                    ToolTip.text: onboarding.helpUrl
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#222b2f" }
                GradientStop { position: 0.55; color: "#192124" }
                GradientStop { position: 1.0; color: "#13191b" }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 68
                anchors.rightMargin: 68
                anchors.topMargin: 58
                anchors.bottomMargin: 42
                spacing: 20

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "STEP " + (onboarding.step + 1) + " OF 5"
                    color: root.accentColor
                    font.pixelSize: 12
                    font.bold: true
                    font.letterSpacing: 0
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Column {
                        id: content
                        width: Math.min(parent.width, 610)
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 22

                        Text {
                            width: parent.width
                            text: root.titles[onboarding.step]
                            color: "#f5f8f7"
                            font.pixelSize: 40
                            font.bold: true
                            wrapMode: Text.WordWrap
                            visible: onboarding.step !== 4
                        }

                        Text {
                            width: Math.min(parent.width, 610)
                            text: onboarding.step === 1 && onboarding.loggedIn ?
                                  "You're signed in and ready to access additional features and plugins." :
                                    onboarding.step === 2 && !pluginPageAvailable ?
                                    "Plugin installation is unavailable because the Prism Hub plugin is not loaded." :
                                  root.descriptions[onboarding.step]
                            color: "#aebdbd"
                            font.pixelSize: 17
                            lineHeight: 1.45
                            wrapMode: Text.WordWrap
                            visible: onboarding.step !== 4
                        }

                        RowLayout {
                            width: Math.min(parent.width, 610)
                            spacing: 18
                            visible: onboarding.step === 4

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 5

                                Text {
                                    Layout.fillWidth: true
                                    text: root.titles[onboarding.step]
                                    color: "#f5f8f7"
                                    font.pixelSize: 40
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.descriptions[onboarding.step]
                                    color: "#aebdbd"
                                    font.pixelSize: 17
                                    lineHeight: 1.45
                                    wrapMode: Text.WordWrap
                                }
                            }

                            Image {
                                Layout.preferredWidth: 44
                                Layout.preferredHeight: 44
                                Layout.alignment: Qt.AlignVCenter
                                source: "icons/check-green.svg"
                                fillMode: Image.PreserveAspectFit
                            }
                        }

                        RowLayout {
                            width: Math.min(parent.width, 610)
                            spacing: 12
                            visible: onboarding.step === 1 && !onboarding.loggedIn &&
                                     !onboarding.acquiringLicense

                            PrismButton {
                                visible: onboarding.accountAvailable
                                text: "Sign in"
                                iconSource: "icons/log-in.svg"
                                onClicked: onboarding.openLogin()
                            }

                            PrismButton {
                                visible: !onboarding.accountAvailable
                                text: "Install PrismInternals"
                                iconSource: "icons/download.svg"
                                onClicked: onboarding.installHubDependencies()
                            }

                            Text {
                                Layout.fillWidth: true
                                text: onboarding.accountAvailable ? "Optional" : "Login is unavailable (PrismInternals plugin is not loaded)"
                                color: "#829194"
                                font.pixelSize: 14
                                wrapMode: Text.WordWrap
                            }
                        }

                        Item {
                            width: Math.min(parent.width, 610)
                            height: 52
                            visible: onboarding.step === 1 && onboarding.acquiringLicense

                            AnimatedImage {
                                id: accountLoadingAnimation
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 52
                                height: 52
                                source: "../prism-loading-dark.gif"
                                fillMode: Image.PreserveAspectFit
                                playing: visible
                            }

                            Text {
                                anchors.left: accountLoadingAnimation.right
                                anchors.leftMargin: 4
                                anchors.verticalCenter: accountLoadingAnimation.verticalCenter
                                text: "Signing in..."
                                color: "#aebdbd"
                                font.pixelSize: 14
                            }
                        }

                        Rectangle {
                            width: Math.min(parent.width, 610)
                            height: 82
                            radius: 6
                            visible: onboarding.step === 1 && onboarding.loggedIn
                            color: "#252631"
                            border.color: "#484957"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 14

                                Rectangle {
                                    Layout.preferredWidth: 48
                                    Layout.preferredHeight: 48
                                    radius: 5
                                    color: root.accentColor

                                    Text {
                                        anchors.centerIn: parent
                                        text: onboarding.accountName ? onboarding.accountName.charAt(0).toUpperCase() : "\u2713"
                                        color: "#ffffff"
                                        font.pixelSize: 20
                                        font.bold: true
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        text: "SIGNED IN AS"
                                        color: "#829194"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.letterSpacing: 0
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: onboarding.accountName || "Prism account"
                                        color: "#f5f8f7"
                                        font.pixelSize: 17
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: onboarding.licenseType ? "License: " + onboarding.licenseType : "License unavailable"
                                        color: "#9da5ad"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                PrismButton {
                                    Layout.preferredWidth: 132
                                    text: "Switch user"
                                    iconSource: "icons/log-in.svg"
                                    onClicked: onboarding.switchUser()
                                }
                            }
                        }

                        Column {
                            width: Math.min(parent.width, 608)
                            spacing: 10
                            visible: onboarding.step === 2

                            Row {
                                width: parent.width
                                spacing: 5

                                Text {
                                    text: "PLUGIN BUNDLES"
                                    color: root.accentColor
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Rectangle {
                                    id: bundleInfo
                                    width: 16
                                    height: 16
                                    radius: 8
                                    color: "#3b3d48"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "i"
                                        color: "#c5ced0"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        ToolTip.visible: containsMouse
                                        ToolTip.delay: 350
                                        ToolTip.text: "Choose a bundle to install it's plugins. See the bundles tooltip for details."
                                    }
                                }
                            }

                            Grid {
                                width: parent.width
                                columns: 3
                                columnSpacing: 10

                                Repeater {
                                    id: pluginBundleRepeater
                                    model: onboarding.pluginBundles

                                    delegate: Rectangle {
                                        id: pluginTile
                                        readonly property bool selected: root.selectedPluginBundle === modelData.title
                                        readonly property bool bundleEnabled: root.pluginPageAvailable
                                        width: 196
                                        height: 58
                                        radius: 6
                                        color: !bundleEnabled ? "#22232b" : selected ? "#332631" : tileMouse.containsMouse ? "#2d2e39" : "#252631"
                                        border.width: selected ? 2 : 1
                                        border.color: !bundleEnabled ? "#3a3b45" : selected ? root.accentColor : "#484957"
                                        opacity: bundleEnabled ? 1.0 : 0.48

                                        Row {
                                            anchors.centerIn: parent
                                            spacing: 9

                                            Image {
                                                width: 30
                                                height: 30
                                                source: modelData.thumbnail || ""
                                                fillMode: Image.PreserveAspectFit
                                                visible: source.toString() !== ""
                                            }

                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: modelData.title
                                                color: !pluginTile.bundleEnabled ? "#7d8588" : "#edf3f3"
                                                font.pixelSize: 14
                                                font.bold: pluginTile.selected
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: tileMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            enabled: pluginTile.bundleEnabled
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: {
                                                onboarding.clearManualPluginSelection()
                                                root.selectedPluginBundle = pluginTile.selected ? "" : modelData.title
                                                root.pluginSelectionRevision++
                                            }

                                            ToolTip.visible: containsMouse
                                            ToolTip.delay: 450
                                            ToolTip.text: root.pluginDisplayNames(modelData.plugins).join("\n")
                                        }
                                    }
                                }
                            }

                            Item {
                                width: parent.width
                                height: 6
                            }

                            Row {
                                width: parent.width
                                spacing: 5

                                Text {
                                    text: "PROJECT MANAGER"
                                    color: root.accentColor
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Rectangle {
                                    id: projectManagerInfo
                                    width: 16
                                    height: 16
                                    radius: 8
                                    color: "#3b3d48"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "i"
                                        color: "#c5ced0"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        ToolTip.visible: containsMouse
                                        ToolTip.delay: 350
                                        ToolTip.text: "Choose a project manager, which you want to connect to Prism."
                                    }
                                }
                            }

                            Grid {
                                width: parent.width
                                columns: 3
                                columnSpacing: 10

                                Repeater {
                                    id: projectManagerRepeater
                                    model: onboarding.projectManagerBundles

                                    delegate: Rectangle {
                                        id: projectManagerTile
                                        readonly property bool selected: root.selectedProjectManager === modelData.title
                                        readonly property bool bundleEnabled: root.pluginPageAvailable
                                        width: 196
                                        height: 52
                                        radius: 6
                                        color: !bundleEnabled ? "#22232b" : selected ? "#332631" : projectManagerMouse.containsMouse ? "#2d2e39" : "#252631"
                                        border.width: selected ? 2 : 1
                                        border.color: !bundleEnabled ? "#3a3b45" : selected ? root.accentColor : "#484957"
                                        opacity: bundleEnabled ? 1.0 : 0.48

                                        Row {
                                            anchors.centerIn: parent
                                            spacing: 7

                                            Image {
                                                width: 24
                                                height: 24
                                                source: modelData.thumbnail || ""
                                                fillMode: Image.PreserveAspectFit
                                                visible: source.toString() !== ""
                                            }

                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: modelData.title
                                                color: !projectManagerTile.bundleEnabled ? "#7d8588" : "#edf3f3"
                                                font.pixelSize: 13
                                                font.bold: projectManagerTile.selected
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: projectManagerMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            enabled: projectManagerTile.bundleEnabled
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: {
                                                onboarding.clearManualPluginSelection()
                                                root.selectedProjectManager = projectManagerTile.selected ? "" : modelData.title
                                                root.pluginSelectionRevision++
                                            }

                                            ToolTip.visible: containsMouse
                                            ToolTip.delay: 450
                                            ToolTip.text: modelData.description || root.pluginDisplayNames(modelData.plugins).join("\n")
                                        }
                                    }
                                }
                            }
                        }

                        Column {
                            width: Math.min(parent.width, 608)
                            visible: onboarding.step === 2
                            spacing: 14

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: "#3e414c"
                                }

                                Text {
                                    text: "OR"
                                    color: "#858f94"
                                    font.pixelSize: 10
                                    font.bold: true
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: "#3e414c"
                                }
                            }

                            Item {
                                width: parent.width
                                height: onboarding.usingManualPluginSelection ? 62 : 42

                                PrismButton {
                                    id: manualChoiceButton
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.top: parent.top
                                    text: "Choose Individually..."
                                    iconSource: hubIconUrl
                                    enabled: root.pluginPageAvailable
                                    onClicked: {
                                        manualPluginPopup.openForSelection(root.manualPluginSeedNames())
                                        onboarding.loadAvailablePlugins()
                                    }
                                }

                                Text {
                                    anchors.top: manualChoiceButton.bottom
                                    anchors.topMargin: 4
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    visible: onboarding.usingManualPluginSelection
                                    text: "Individual selection active"
                                    color: root.accentColor
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            PrismButton {
                                anchors.horizontalCenter: parent.horizontalCenter
                                visible: !onboarding.hubAvailable
                                text: "Install Hub"
                                iconSource: "icons/download.svg"
                                onClicked: onboarding.installHubDependencies()
                            }
                        }

                        Connections {
                            target: onboarding
                            function onManualPluginsChanged() {
                                if (onboarding.usingManualPluginSelection) {
                                    root.selectedPluginBundle = ""
                                    root.selectedProjectManager = ""
                                }
                                root.pluginSelectionRevision++
                            }
                        }

                        Column {
                            width: Math.min(parent.width, 610)
                            spacing: 14
                            visible: onboarding.step === 3

                            Row {
                                width: parent.width
                                spacing: 10

                                Repeater {
                                    model: [
                                        {
                                            "title": "Create Empty Project",
                                            "description": "Start a new production with a clean Prism project.",
                                            "icon": "icons/folder-plus.svg",
                                            "action": "create",
                                            "enabled": true
                                        },
                                        {
                                            "title": "Open Existing Project",
                                            "description": "Connect to a Prism project already on this computer.",
                                            "icon": "icons/folder-open.svg",
                                            "action": "open",
                                            "enabled": true
                                        },
                                        {
                                            "title": "Download Demo Project",
                                            "description": "Explore Prism with a ready-made example production.",
                                            "icon": "icons/play-square.svg",
                                            "action": "demo",
                                            "enabled": true
                                        }
                                    ]

                                    delegate: Rectangle {
                                        id: projectTile
                                        property bool tileEnabled: modelData.enabled
                                        width: 196
                                        height: 126
                                        radius: 6
                                        color: !tileEnabled ? "#20222a" :
                                               projectTileMouse.containsMouse ? "#302b35" : "#252631"
                                        border.width: 1
                                        border.color: tileEnabled && projectTileMouse.containsMouse ?
                                                      root.accentColor : "#484957"
                                        opacity: tileEnabled ? 1 : 0.62

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 13
                                            spacing: 6

                                            RowLayout {
                                                Layout.fillWidth: true

                                                Rectangle {
                                                    Layout.preferredWidth: 34
                                                    Layout.preferredHeight: 34
                                                    radius: 5
                                                    color: tileEnabled ? "#363944" : "#30323b"

                                                    Image {
                                                        anchors.centerIn: parent
                                                        width: 19
                                                        height: 19
                                                        source: modelData.icon
                                                        fillMode: Image.PreserveAspectFit
                                                    }
                                                }

                                                Item { Layout.fillWidth: true }

                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.title
                                                color: "#edf3f3"
                                                font.pixelSize: 13
                                                font.bold: true
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 2
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                text: modelData.description
                                                color: "#8f999e"
                                                font.pixelSize: 10
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 2
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: projectTileMouse
                                            anchors.fill: parent
                                            enabled: projectTile.tileEnabled
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: modelData.action === "create" ?
                                                       onboarding.createProject() :
                                                       modelData.action === "open" ? onboarding.openProject() :
                                                       demoProjectPopup.openForSelection()
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                width: parent.width
                                visible: onboarding.projectName !== ""
                                spacing: 10

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: "#3e414c"
                                }

                                Text {
                                    text: "OR CONTINUE WITH CURRENT PROJECT"
                                    color: "#858f94"
                                    font.pixelSize: 9
                                    font.bold: true
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: "#3e414c"
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 94
                                radius: 6
                                visible: onboarding.projectName !== ""
                                color: "#332631"
                                border.width: 2
                                border.color: root.accentColor
                                clip: true

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 14

                                    Rectangle {
                                        Layout.preferredWidth: 112
                                        Layout.fillHeight: true
                                        radius: 5
                                        color: "#30323d"
                                        clip: true

                                        Image {
                                            anchors.fill: parent
                                            source: onboarding.projectImageUrl
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            visible: status === Image.Ready
                                        }

                                        Image {
                                            anchors.centerIn: parent
                                            width: 28
                                            height: 28
                                            source: "icons/box.svg"
                                            fillMode: Image.PreserveAspectFit
                                            opacity: 0.55
                                            visible: onboarding.projectImageUrl.toString() === ""
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        Text {
                                            text: "CURRENT PROJECT"
                                            color: root.accentColor
                                            font.pixelSize: 10
                                            font.bold: true
                                            font.letterSpacing: 0
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: onboarding.projectName
                                            color: "#f5f8f7"
                                            font.pixelSize: 18
                                            font.bold: true
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: onboarding.projectPath
                                            color: "#8f999e"
                                            font.pixelSize: 11
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    Image {
                                        Layout.preferredWidth: 20
                                        Layout.preferredHeight: 20
                                        source: "icons/check.svg"
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }
                            }
                        }

                        Column {
                            width: Math.min(parent.width, 610)
                            spacing: 12
                            visible: onboarding.step === 4

                            Text {
                                text: "OPTIONAL NEXT STEPS"
                                color: "#8f999e"
                                font.pixelSize: 10
                                font.bold: true
                                font.letterSpacing: 0
                            }

                            Repeater {
                                model: [
                                    {
                                        "icon": "icons/circle-play.svg",
                                        "title": "Watch our Getting Started video guides",
                                        "description": "Learn the essential Prism workflows with step-by-step videos.",
                                        "url": "https://prism-pipeline.com/docs/latest/guides"
                                    },
                                    {
                                        "icon": "icons/user-round.svg",
                                        "title": "Manage your Prism Account",
                                        "description": "Review your profile, subscriptions, and account settings.",
                                        "url": "https://prism-pipeline.com/my-subscriptions"
                                    },
                                    {
                                        "icon": "icons/discord.svg",
                                        "title": "Join the Prism Community on Discord",
                                        "description": "Meet other artists, share workflows, and get community help.",
                                        "url": "https://prism-pipeline.com/discord"
                                    }
                                ]

                                delegate: Item {
                                    width: 610
                                    height: 62

                                    RowLayout {
                                        anchors.fill: parent
                                        spacing: 12

                                        Rectangle {
                                            Layout.preferredWidth: 40
                                            Layout.preferredHeight: 40
                                            radius: 5
                                            color: "#30323d"

                                            Image {
                                                anchors.centerIn: parent
                                                width: 21
                                                height: 21
                                                source: modelData.icon
                                                fillMode: Image.PreserveAspectFit
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            spacing: 2

                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.title
                                                color: "#edf3f3"
                                                font.pixelSize: 13
                                                font.bold: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.description
                                                color: "#8f999e"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Button {
                                            id: externalLinkButton
                                            Layout.preferredWidth: 40
                                            Layout.preferredHeight: 40
                                            padding: 0
                                            onClicked: onboarding.openUrl(modelData.url)

                                            contentItem: Item {
                                                Image {
                                                    anchors.centerIn: parent
                                                    width: 20
                                                    height: 20
                                                    source: "icons/external-link.svg"
                                                    fillMode: Image.PreserveAspectFit
                                                }
                                            }

                                            background: Rectangle {
                                                radius: 5
                                                color: externalLinkButton.down ? "#393b48" :
                                                       externalLinkButton.hovered ? "#343644" : "#292b36"
                                                border.width: 1
                                                border.color: externalLinkButton.hovered ? root.accentColor : "#484a56"
                                            }

                                            ToolTip.visible: hovered
                                            ToolTip.delay: 400
                                            ToolTip.text: "Open external link"
                                        }
                                    }

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 1
                                        color: "#343942"
                                    }
                                }
                            }
                        }
                    }

                    SequentialAnimation {
                        id: pageTransition

                        NumberAnimation {
                            target: content
                            property: "opacity"
                            to: 0
                            duration: 240
                            easing.type: Easing.InOutSine
                        }

                        ScriptAction {
                            script: onboarding.goToStep(root.pendingStep)
                        }

                        NumberAnimation {
                            target: content
                            property: "opacity"
                            to: 1
                            duration: 360
                            easing.type: Easing.InOutSine
                        }
                    }

                    Connections {
                        target: onboarding
                        function onPluginInstallChanged() {
                            if (onboarding.installingPlugins && !pluginInstallPopup.visible)
                                pluginInstallPopup.open()
                            else if (!onboarding.installingPlugins && pluginInstallPopup.visible)
                                pluginInstallPopup.close()
                        }

                        function onPluginInstallFinished() {
                            root.navigateTo(3)
                        }

                        function onStepChanged() {
                            if (!pageTransition.running) {
                                content.opacity = 1
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    PrismButton {
                        text: "Skip onboarding"
                        kind: "ghost"
                        visible: onboarding.step === 0
                        onClicked: onboarding.skip()
                    }

                    PrismButton {
                        text: "Back"
                        iconSource: "icons/arrow-left.svg"
                        visible: onboarding.step > 0
                        onClicked: root.navigateTo(onboarding.step - 1)
                    }

                    Item { Layout.fillWidth: true }

                    ColumnLayout {
                        visible: onboarding.step === 2
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter

                        Text {
                            Layout.alignment: Qt.AlignRight
                            text: "SUMMARY"
                            color: root.accentColor
                            font.pixelSize: 10
                            font.bold: true
                        }

                        Text {
                            Layout.alignment: Qt.AlignRight
                            text: onboarding.installingPlugins ? onboarding.pluginInstallStatus :
                                  root.newPluginSummary()
                            color: "#aebdbd"
                            font.pixelSize: 12

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: root.installablePluginNames().length > 0
                                ToolTip.visible: containsMouse
                                ToolTip.delay: 350
                                ToolTip.text: root.pluginDisplayNames(root.installablePluginNames()).join("\n")
                            }
                        }
                    }

                    PrismButton {
                        id: primaryButton
                        kind: "primary"
                        text: onboarding.installingPlugins ? "Installing..." :
                            onboarding.step === 2 ? root.pluginActionText() :
                              onboarding.step === 4 ? "Finish" : (onboarding.step === 0 ? "Get started" : "Continue")
                        iconSource: onboarding.step === 4 ? "icons/check.svg" : "icons/arrow-right.svg"
                                                enabled: !onboarding.installingPlugins
                        onClicked: onboarding.step === 4 ? onboarding.finish() :
                                   onboarding.step === 2 ? onboarding.installPlugins(root.activePluginNames()) :
                                   root.navigateTo(onboarding.step + 1)
                    }
                }
            }
        }
    }

    Popup {
        id: pluginInstallPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 100, 460)
        padding: 26
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose

        Overlay.modal: Rectangle {
            color: "#a00b0d12"
        }

        background: Rectangle {
            radius: 8
            color: "#242630"
            border.width: 1
            border.color: "#505260"
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    radius: 5
                    color: "#343843"

                    Image {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        source: "icons/download.svg"
                        fillMode: Image.PreserveAspectFit
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: "Installing plugins"
                        color: "#f5f8f7"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        Layout.fillWidth: true
                        text: onboarding.pluginInstallStatus
                        color: "#9da5ad"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }

            ProgressBar {
                id: pluginInstallProgressBar
                Layout.fillWidth: true
                Layout.preferredHeight: 8
                from: 0
                to: Math.max(1, onboarding.pluginInstallTotal)
                value: onboarding.pluginInstallCompleted

                background: Rectangle {
                    implicitHeight: 8
                    radius: 4
                    color: "#343641"
                }

                contentItem: Item {
                    implicitHeight: 8

                    Rectangle {
                        width: pluginInstallProgressBar.visualPosition * parent.width
                        height: parent.height
                        radius: 4
                        color: root.accentColor
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: onboarding.pluginInstallCompleted + " of " +
                      onboarding.pluginInstallTotal + " plugins installed"
                color: "#c6d0d1"
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Popup {
        id: demoProjectPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 64, 760)
        height: Math.min(root.height - 48, 620)
        padding: 24
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape

        property string selectedProjectId: ""
        property string projectName: ""
        property string projectPath: ""
        property bool pathManuallyEdited: false
        readonly property var loadingProjectPlaceholders: [
            {"id": "loading-1", "name": "", "description": "", "thumbnail": "", "thumbnailReady": false, "thumbnailColor": "#343640", "loading": true},
            {"id": "loading-2", "name": "", "description": "", "thumbnail": "", "thumbnailReady": false, "thumbnailColor": "#343640", "loading": true},
            {"id": "loading-3", "name": "", "description": "", "thumbnail": "", "thumbnailReady": false, "thumbnailColor": "#343640", "loading": true}
        ]

        function selectProject(project) {
            if (!project || project.enabled === false)
                return

            selectedProjectId = project.id
            projectName = project.name
            pathManuallyEdited = false
            projectPath = onboarding.defaultDemoProjectPath(project.name)
        }

        function selectFirstAvailableProject() {
            for (var index = 0; index < onboarding.demoProjects.length; ++index) {
                if (onboarding.demoProjects[index].enabled !== false) {
                    selectProject(onboarding.demoProjects[index])
                    return
                }
            }
        }

        function openForSelection() {
            selectedProjectId = ""
            projectName = ""
            projectPath = ""
            pathManuallyEdited = false
            onboarding.loadDemoProjects()
            if (onboarding.demoProjects.length > 0)
                selectFirstAvailableProject()
            open()
        }

        Overlay.modal: Rectangle {
            color: "#a00b0d12"
        }

        background: Rectangle {
            radius: 8
            color: "#242630"
            border.width: 1
            border.color: "#505260"
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Create a Demo Project"
                        color: "#f5f8f7"
                        font.pixelSize: 22
                        font.bold: true
                    }

                    Text {
                        text: "Choose an example production, then set where Prism should create it."
                        color: "#9da5ad"
                        font.pixelSize: 13
                    }
                }

            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 312
                visible: onboarding.demoProjectsError === ""

                ListView {
                    id: demoProjectList
                    anchors.fill: parent
                    anchors.bottomMargin: -8
                    orientation: ListView.Horizontal
                    spacing: 10
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: onboarding.loadingDemoProjects
                           ? demoProjectPopup.loadingProjectPlaceholders
                           : onboarding.demoProjects
                    ScrollBar.horizontal: ScrollBar {
                        policy: !onboarding.loadingDemoProjects && onboarding.demoProjects.length > 3
                                ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
                    }

                    delegate: Rectangle {
                    id: demoChoice
                    readonly property bool loadingPlaceholder: modelData.loading === true
                    readonly property bool projectEnabled: !loadingPlaceholder && modelData.enabled !== false
                    readonly property string detailsUrl: modelData.detailsUrl || modelData.moreDetailsUrl || modelData.url || ""
                    readonly property bool selected: projectEnabled && demoProjectPopup.selectedProjectId === modelData.id
                    width: 230
                    height: 302
                    radius: 6
                    color: !projectEnabled ? "#24252b" : selected ? "#352832" : demoChoiceMouse.containsMouse ? "#2d2f39" : "#292b34"
                    border.width: selected ? 2 : 1
                    border.color: !projectEnabled ? "#3b3d46" : selected ? root.accentColor : "#484a56"
                    opacity: loadingPlaceholder || projectEnabled ? 1.0 : 0.52
                    clip: true

                    ColumnLayout {
                        z: 1
                        anchors.fill: parent
                        anchors.margins: demoChoice.selected ? 2 : 1
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 112
                            radius: demoChoice.selected ? 4 : 5
                            color: demoChoice.loadingPlaceholder ? "#343640" : modelData.thumbnailColor
                            clip: true

                            Rectangle {
                                anchors.centerIn: parent
                                width: 52
                                height: 52
                                radius: 5
                                color: "#41434e"
                                visible: demoChoice.loadingPlaceholder

                                SequentialAnimation on opacity {
                                    running: demoChoice.loadingPlaceholder
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 0.45; to: 0.9; duration: 650 }
                                    NumberAnimation { from: 0.9; to: 0.45; duration: 650 }
                                }
                            }

                            Image {
                                anchors.fill: parent
                                source: !demoChoice.loadingPlaceholder && modelData.thumbnailReady ? modelData.thumbnail : ""
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                visible: !demoChoice.loadingPlaceholder && modelData.thumbnailReady && status === Image.Ready
                            }

                            Image {
                                anchors.centerIn: parent
                                width: 52
                                height: 52
                                source: modelData.thumbnail
                                fillMode: Image.PreserveAspectFit
                                opacity: 0.9
                                visible: !demoChoice.loadingPlaceholder && !modelData.thumbnailReady
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.leftMargin: 13
                            Layout.rightMargin: 13
                            Layout.topMargin: 10
                            Layout.bottomMargin: 11
                            spacing: 5

                            Rectangle {
                                Layout.preferredWidth: 132
                                Layout.preferredHeight: 14
                                radius: 3
                                color: "#41434e"
                                visible: demoChoice.loadingPlaceholder
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 9
                                radius: 3
                                color: "#3a3c46"
                                visible: demoChoice.loadingPlaceholder
                            }

                            Rectangle {
                                Layout.preferredWidth: 165
                                Layout.preferredHeight: 9
                                radius: 3
                                color: "#3a3c46"
                                visible: demoChoice.loadingPlaceholder
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: demoChoice.projectEnabled ? "#f1f5f4" : "#92999b"
                                font.pixelSize: 14
                                font.bold: true
                                elide: Text.ElideRight
                                visible: !demoChoice.loadingPlaceholder
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: modelData.description
                                color: demoChoice.projectEnabled ? "#929ca1" : "#70787c"
                                font.pixelSize: 11
                                lineHeight: 1.15
                                wrapMode: Text.WordWrap
                                maximumLineCount: 6
                                elide: Text.ElideRight
                                visible: !demoChoice.loadingPlaceholder
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 14
                                spacing: 8
                                visible: !demoChoice.loadingPlaceholder &&
                                         (!!modelData.size || demoChoice.detailsUrl !== "")

                                Text {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    text: modelData.size || ""
                                    color: "#929ca1"
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }

                                Item {
                                    Layout.preferredWidth: demoDetailsContent.implicitWidth
                                    Layout.preferredHeight: 14
                                    visible: demoChoice.detailsUrl !== ""

                                    Row {
                                        id: demoDetailsContent
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 5

                                        Text {
                                            text: "More details"
                                            color: root.accentColor
                                            font.pixelSize: 11
                                            font.bold: true
                                        }

                                        Image {
                                            width: 13
                                            height: 13
                                            source: "icons/external-link-accent.svg"
                                            fillMode: Image.PreserveAspectFit
                                        }
                                    }

                                    MouseArea {
                                        id: demoDetailsMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: onboarding.openUrl(demoChoice.detailsUrl)
                                    }
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: demoChoiceMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: demoChoice.projectEnabled
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: demoProjectPopup.selectProject(modelData)
                    }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 10
                    anchors.bottomMargin: 10
                    width: loadingProjectsText.implicitWidth + 18
                    height: 26
                    radius: 4
                    color: "#e6292b34"
                    border.width: 1
                    border.color: "#505260"
                    visible: onboarding.loadingDemoProjects

                    Text {
                        id: loadingProjectsText
                        anchors.centerIn: parent
                        text: "LOADING PROJECTS..."
                        color: "#c2cbcd"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 230
                visible: onboarding.demoProjectsError !== ""
                radius: 6
                color: "#292b34"
                border.width: 1
                border.color: "#484a56"

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 48, 430)
                    spacing: 12

                    Text {
                        Layout.fillWidth: true
                        text: onboarding.demoProjectsError
                        color: "#d6dcde"
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    PrismButton {
                        Layout.alignment: Qt.AlignHCenter
                        visible: onboarding.accountAvailable
                        text: "Retry"
                        iconSource: "icons/refresh-cw.svg"
                        onClicked: onboarding.loadDemoProjects()
                    }

                    PrismButton {
                        Layout.alignment: Qt.AlignHCenter
                        visible: !onboarding.accountAvailable
                        text: "Install PrismInternals"
                        iconSource: "icons/download.svg"
                        onClicked: onboarding.installHubDependencies()
                    }
                }
            }

            Connections {
                target: onboarding
                function onDemoProjectsChanged() {
                    if (!demoProjectPopup.visible || onboarding.demoProjects.length === 0)
                        return

                    var selectionExists = false
                    for (var index = 0; index < onboarding.demoProjects.length; ++index) {
                        if (onboarding.demoProjects[index].id === demoProjectPopup.selectedProjectId &&
                            onboarding.demoProjects[index].enabled !== false) {
                            selectionExists = true
                            break
                        }
                    }
                    if (!selectionExists)
                        demoProjectPopup.selectFirstAvailableProject()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.preferredWidth: 250
                    Layout.minimumWidth: 250
                    Layout.maximumWidth: 250
                    spacing: 6

                    Text {
                        text: "PROJECT NAME"
                        color: "#a3adb1"
                        font.pixelSize: 10
                        font.bold: true
                    }

                    TextField {
                        id: demoProjectNameField
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        enabled: demoProjectPopup.selectedProjectId !== "" && onboarding.demoProjectsError === ""
                        text: demoProjectPopup.projectName
                        color: enabled ? "#edf3f3" : "#788286"
                        selectionColor: "#7f2d55"
                        selectedTextColor: "#ffffff"
                        selectByMouse: true
                        leftPadding: 13
                        rightPadding: 13
                        onTextEdited: {
                            demoProjectPopup.projectName = text
                            if (!demoProjectPopup.pathManuallyEdited)
                                demoProjectPopup.projectPath = onboarding.defaultDemoProjectPath(text)
                        }

                        background: Rectangle {
                            radius: 5
                            color: demoProjectNameField.activeFocus ? "#30323d" : "#292b34"
                            border.width: 1
                            border.color: demoProjectNameField.activeFocus ? root.accentColor : "#484a56"
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 6

                    Text {
                        text: "PROJECT PATH"
                        color: "#a3adb1"
                        font.pixelSize: 10
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TextField {
                            id: demoProjectPathField
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredHeight: 42
                            enabled: demoProjectPopup.selectedProjectId !== "" && onboarding.demoProjectsError === ""
                            text: demoProjectPopup.projectPath
                            color: enabled ? "#edf3f3" : "#788286"
                            selectionColor: "#7f2d55"
                            selectedTextColor: "#ffffff"
                            selectByMouse: true
                            leftPadding: 13
                            rightPadding: 13
                            onTextEdited: {
                                demoProjectPopup.projectPath = text
                                demoProjectPopup.pathManuallyEdited = true
                            }

                            background: Rectangle {
                                radius: 5
                                color: demoProjectPathField.activeFocus ? "#30323d" : "#292b34"
                                border.width: 1
                                border.color: demoProjectPathField.activeFocus ? root.accentColor : "#484a56"
                            }
                        }

                        PrismButton {
                            Layout.preferredWidth: 112
                            text: "Browse"
                            iconSource: "icons/folder-open.svg"
                            enabled: demoProjectPopup.selectedProjectId !== "" && onboarding.demoProjectsError === ""
                            onClicked: {
                                var selectedPath = onboarding.browseDemoProjectPath(demoProjectPopup.projectPath)
                                if (selectedPath) {
                                    demoProjectPopup.projectPath = selectedPath
                                    demoProjectPopup.pathManuallyEdited = true
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Item { Layout.fillWidth: true }

                PrismButton {
                    text: "Cancel"
                    kind: "ghost"
                    iconSource: "icons/x.svg"
                    onClicked: demoProjectPopup.close()
                }

                PrismButton {
                    Layout.preferredWidth: 220
                    text: "Download Demo Project"
                    kind: "primary"
                    iconSource: "icons/play-square.svg"
                    enabled: demoProjectPopup.selectedProjectId !== "" &&
                             demoProjectPopup.projectName.trim() !== "" &&
                             demoProjectPopup.projectPath.trim() !== ""
                    onClicked: {
                        var started = onboarding.createDemoProject(
                            demoProjectPopup.selectedProjectId,
                            demoProjectPopup.projectName,
                            demoProjectPopup.projectPath
                        )
                        if (started) {
                            demoProjectPopup.close()
                            demoProjectProgressPopup.open()
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: demoProjectProgressPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 100, 480)
        padding: 26
        modal: true
        focus: true
        closePolicy: onboarding.creatingDemoProject ? Popup.NoAutoClose : Popup.CloseOnEscape

        Overlay.modal: Rectangle {
            color: "#a00b0d12"
        }

        background: Rectangle {
            radius: 8
            color: "#242630"
            border.width: 1
            border.color: "#505260"
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    radius: 5
                    color: onboarding.demoProjectError ? "#463039" : "#343843"

                    Image {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        source: onboarding.demoProjectError ? "icons/x.svg" : "icons/play-square.svg"
                        fillMode: Image.PreserveAspectFit
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        Layout.fillWidth: true
                        text: onboarding.demoProjectError ? "Could not create demo project" : "Creating demo project"
                        color: "#f5f8f7"
                        font.pixelSize: 18
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: onboarding.demoProjectError || onboarding.demoProjectStatus
                        color: onboarding.demoProjectError ? "#d9a9b6" : "#9da5ad"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }

            ProgressBar {
                id: demoProjectProgressBar
                Layout.fillWidth: true
                Layout.preferredHeight: 8
                from: 0
                to: 100
                value: onboarding.demoProjectProgress
                visible: !onboarding.demoProjectError

                background: Rectangle {
                    implicitHeight: 8
                    radius: 4
                    color: "#343641"
                }

                contentItem: Item {
                    implicitHeight: 8

                    Rectangle {
                        width: demoProjectProgressBar.visualPosition * parent.width
                        height: parent.height
                        radius: 4
                        color: root.accentColor
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: onboarding.demoProjectDownloadedSize + " / " +
                      (onboarding.demoProjectTotalSize || "total unknown")
                color: "#9da5ad"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                visible: onboarding.demoProjectDownloadedSize !== ""
            }

            RowLayout {
                Layout.fillWidth: true

                Item { Layout.fillWidth: true }

                PrismButton {
                    visible: onboarding.creatingDemoProject
                    text: "Cancel download"
                    kind: "ghost"
                    iconSource: "icons/x.svg"
                    onClicked: onboarding.cancelDemoProject()
                }

                PrismButton {
                    visible: !onboarding.creatingDemoProject
                    text: "Close"
                    kind: onboarding.demoProjectError ? "secondary" : "primary"
                    iconSource: onboarding.demoProjectError ? "icons/x.svg" : "icons/check.svg"
                    onClicked: demoProjectProgressPopup.close()
                }
            }
        }

        Connections {
            target: onboarding
            function onDemoProjectProgressChanged() {
                if (!onboarding.creatingDemoProject && !onboarding.demoProjectError)
                    demoProjectProgressPopup.close()
            }
        }
    }

    Popup {
        id: manualPluginPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(root.width - 80, 620)
        height: Math.min(root.height - 64, 610)
        padding: 24
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape

        property var draftPluginNames: []

        function openForSelection(pluginNames) {
            var names = []
            for (var index = 0; index < pluginNames.length; ++index)
                names.push(pluginNames[index])

            draftPluginNames = names
            open()
        }

        function selectedPluginNames() {
            var names = []
            for (var index = 0; index < draftPluginNames.length; ++index) {
                var pluginName = draftPluginNames[index]
                var installed = false
                for (var pluginIndex = 0; pluginIndex < onboarding.availablePlugins.length; ++pluginIndex) {
                    var plugin = onboarding.availablePlugins[pluginIndex]
                    if (plugin.pluginName === pluginName) {
                        installed = plugin.installed
                        break
                    }
                }
                if (!installed)
                    names.push(pluginName)
            }
            return names
        }

        function isSelected(pluginName) {
            return draftPluginNames.indexOf(pluginName) !== -1
        }

        function togglePlugin(pluginName) {
            for (var pluginIndex = 0; pluginIndex < onboarding.availablePlugins.length; ++pluginIndex) {
                var plugin = onboarding.availablePlugins[pluginIndex]
                if (plugin.pluginName === pluginName && plugin.installed)
                    return
            }

            var names = draftPluginNames.slice(0)
            var index = names.indexOf(pluginName)
            if (index === -1)
                names.push(pluginName)
            else
                names.splice(index, 1)

            draftPluginNames = names
        }

        Overlay.modal: Rectangle {
            color: "#a00b0d12"
        }

        background: Rectangle {
            radius: 8
            color: "#242630"
            border.width: 1
            border.color: "#505260"
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Choose Plugins"
                        color: "#f5f8f7"
                        font.pixelSize: 22
                        font.bold: true
                    }

                    Text {
                        text: "Select individual plugins for this Prism installation."
                        color: "#9da5ad"
                        font.pixelSize: 13
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 6
                color: "#1e2028"
                border.width: 1
                border.color: "#3c3e49"

                ListView {
                    id: manualPluginList
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    model: onboarding.availablePlugins
                    visible: !onboarding.loadingAvailablePlugins
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Item {
                        id: pluginRow
                        readonly property bool selected: modelData.installed || manualPluginPopup.isSelected(modelData.pluginName)
                        readonly property bool hovered: rowMouse.containsMouse
                        width: manualPluginList.width
                        height: 54

                        Rectangle {
                            anchors.fill: parent
                            anchors.topMargin: 3
                            anchors.bottomMargin: 3
                            radius: 5
                            color: modelData.installed ? "#292b34" : pluginRow.selected ? "#352832" : pluginRow.hovered ? "#2d2f39" : "transparent"
                            border.width: pluginRow.selected ? 1 : 0
                            border.color: modelData.installed ? "#50535e" : root.accentColor
                            opacity: modelData.installed ? 0.58 : 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 12

                                Rectangle {
                                    Layout.preferredWidth: 22
                                    Layout.preferredHeight: 22
                                    radius: 4
                                    color: modelData.installed ? "#454853" : pluginRow.selected ? root.accentColor : "#252731"
                                    border.width: 1
                                    border.color: modelData.installed ? "#666a74" : pluginRow.selected ? root.accentColor : "#666875"

                                    Text {
                                        anchors.centerIn: parent
                                        text: pluginRow.selected ? "\u2713" : ""
                                        color: "#ffffff"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 4
                                    color: modelData.thumbnailColor || "#353842"

                                    Image {
                                        id: pluginIcon
                                        anchors.fill: parent
                                        anchors.margins: 3
                                        source: onboarding.pluginIcons[modelData.pluginName] || ""
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                        smooth: true
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        visible: !onboarding.pluginIcons[modelData.pluginName] || pluginIcon.status === Image.Error
                                        text: modelData.name ? modelData.name.charAt(0).toUpperCase() : ""
                                        color: "#aeb8bd"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: "#edf3f3"
                                    font.pixelSize: 14
                                    font.bold: pluginRow.selected
                                    elide: Text.ElideRight
                                }

                                Text {
                                    visible: modelData.installed
                                    text: "INSTALLED"
                                    color: "#8fc7ad"
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: !modelData.installed
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: manualPluginPopup.togglePlugin(modelData.pluginName)
                            }
                        }
                    }
                }

                AnimatedImage {
                    anchors.centerIn: parent
                    width: 200
                    height: 200
                    source: "../prism-loading-dark.gif"
                    fillMode: Image.PreserveAspectFit
                    playing: visible
                    visible: onboarding.loadingAvailablePlugins
                }

                Text {
                    anchors.centerIn: parent
                    visible: !onboarding.loadingAvailablePlugins && manualPluginList.count === 0
                    text: onboarding.availablePluginsError || "No plugins available"
                    color: "#818991"
                    font.pixelSize: 13
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    Layout.fillWidth: true
                      readonly property int selectedCount: manualPluginPopup.selectedPluginNames().length
                      text: selectedCount === 1 ?
                          "1 plugin selected" : selectedCount + " Plugins Selected"
                    color: "#aeb8bd"
                    font.pixelSize: 12
                    font.bold: true
                }

                PrismButton {
                    text: "Cancel"
                    kind: "ghost"
                    iconSource: "icons/x.svg"
                    onClicked: manualPluginPopup.close()
                }

                PrismButton {
                    Layout.preferredWidth: 210
                    text: "Use Selected Plugins"
                    kind: "primary"
                    iconSource: "icons/check.svg"
                    enabled: !onboarding.loadingAvailablePlugins && onboarding.availablePlugins.length > 0
                    onClicked: {
                        onboarding.applyManualPluginSelection(manualPluginPopup.selectedPluginNames())
                        manualPluginPopup.close()
                    }
                }
            }
        }
    }
}