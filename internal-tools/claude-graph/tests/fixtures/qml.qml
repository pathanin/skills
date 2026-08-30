import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property real contentHeight: content.implicitHeight
    property bool isFocusable: true
    readonly property string serverName: ServersModel.name
    default property alias contentData: inner.data

    signal configPrepared(string config)

    function reloadServers() {
        ServersModel.reload()
    }

    // Property bindings and signal handlers are not declarations.
    visible: ServersUiController.isAdVisible
    Keys.onTabPressed: {
        FocusController.nextKeyTabItem()
    }
}
