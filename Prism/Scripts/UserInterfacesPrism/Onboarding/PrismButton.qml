import QtQuick 2.12
import QtQuick.Controls 2.5

Button {
    id: control

    property string kind: "secondary"
    property url iconSource: ""
    property int iconSize: 18
    readonly property bool pointerHovered: control.enabled && (control.hovered || pointerArea.containsMouse)

    implicitWidth: Math.max(128, contentItem.implicitWidth + 38)
    implicitHeight: 42
    leftPadding: 19
    rightPadding: 19

    contentItem: Row {
        spacing: control.iconSource.toString() ? 8 : 0

        Image {
            width: control.iconSource.toString() ? control.iconSize : 0
            height: control.iconSource.toString() ? control.iconSize : 0
            anchors.verticalCenter: parent.verticalCenter
            source: control.iconSource
            fillMode: Image.PreserveAspectFit
            opacity: control.enabled ? 1 : control.kind === "primary" ? 0.72 : 0.48
            visible: control.iconSource.toString() !== ""
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: control.text
                 color: !control.enabled && control.kind === "primary" ? "#d2d7d8" :
                     !control.enabled ? "#687477" :
                   control.kind === "primary" ? "#ffffff" :
                   control.kind === "ghost" ? "#c5cecf" : "#edf3f3"
            font.pixelSize: 14
            font.bold: control.kind === "primary"
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: 5
         color: !control.enabled && control.kind === "primary" ? "#513644" :
             control.kind === "primary" ? "#AF326D" :
               control.kind === "ghost" ? (control.pointerHovered ? "#ff30313e" : "#0030313e") :
             control.down ? "#30313e" : control.pointerHovered ? "#343644" : "#292b36"
        border.width: control.kind === "primary" || control.kind === "ghost" ? 0 : 1
         border.color: control.pointerHovered ? "#555766" : "#41434f"
        opacity: control.enabled || control.kind === "primary" ? 1 : 0.58

         Behavior on color { ColorAnimation { duration: 140 } }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: control.kind === "primary" && control.enabled
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: control.down ? "#9821AB" : control.pointerHovered ? "#AC26C0" : "#A423B7"
                }
                GradientStop {
                    position: 1.0
                    color: control.down ? "#B93136" : control.pointerHovered ? "#CF363B" : "#C63237"
                }
            }
        }
    }

    MouseArea {
        id: pointerArea
        anchors.fill: parent
        hoverEnabled: control.enabled
        acceptedButtons: Qt.NoButton
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}