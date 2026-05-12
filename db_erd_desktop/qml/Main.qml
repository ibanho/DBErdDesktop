import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1450
    height: 900
    minimumWidth: 1100
    minimumHeight: 720
    visible: true
    title: backend.currentSessionName ? "DB ERD Desktop - " + backend.currentSessionName : "DB ERD Desktop"
    color: bg
    font.family: "Segoe UI"
    font.pixelSize: 13

    property real zoom: 1.0
    property string selectedSessionName: ""
    property bool createSessionFromStartup: false
    readonly property bool startupDialogBlocked: createSessionFromStartup && createSessionDialog.visible

    readonly property color bg: "#101419"
    readonly property color side: "#151a21"
    readonly property color panel: "#1b222b"
    readonly property color panelRaised: "#202832"
    readonly property color panelSoft: "#18202a"
    readonly property color rowEven: "#1c242d"
    readonly property color rowOdd: "#18202a"
    readonly property color canvas: "#121820"
    readonly property color border: "#34404d"
    readonly property color borderStrong: "#465465"
    readonly property color text: "#f3f7fb"
    readonly property color muted: "#9ca9b7"
    readonly property color accent: "#4f9cff"
    readonly property color accentHover: "#6eaeff"
    readonly property color accentSoft: "#203b5f"
    readonly property color disabled: "#2b333e"

    function defaultPort(dbms) {
        if (dbms === "PostgreSQL") return "5432"
        if (dbms === "MSSQL") return "1433"
        if (dbms === "Oracle") return "1521"
        return "3306"
    }

    function readConnectionSettings() {
        var s = backend.connectionSettings
        dbmsCombo.currentIndex = Math.max(0, dbmsCombo.model.indexOf(s.dbms))
        dbHostField.text = s.host
        dbPortField.text = String(s.port)
        databaseField.text = s.database
        dbUserField.text = s.username
        dbPasswordField.text = s.password
        mssqlDriverField.text = s.mssqlDriver
        oracleModeCombo.currentIndex = s.oracleMode === "sid" ? 1 : 0
        trustCertCheck.checked = s.trustServerCertificate
        sshEnabledCheck.checked = s.sshEnabled
        sshHostField.text = s.sshHost
        sshPortField.text = String(s.sshPort)
        sshUserField.text = s.sshUsername
        sshPasswordField.text = s.sshPassword
        sshKeyField.text = s.sshKeyFile
        sshKeyPassphraseField.text = s.sshKeyPassphrase
    }

    function openConnectionDialog() {
        readConnectionSettings()
        connectionDialog.open()
    }

    function openCreateSessionDialog(fromStartup) {
        createSessionFromStartup = fromStartup
        newSessionNameField.text = ""
        newSessionDescriptionField.text = ""
        createSessionDialog.open()
        newSessionNameField.forceActiveFocus()
    }

    function createSessionFromDialog() {
        if (backend.createSession(newSessionNameField.text, newSessionDescriptionField.text)) {
            newSessionNameField.text = ""
            newSessionDescriptionField.text = ""
            createSessionDialog.close()
            if (createSessionFromStartup)
                startupDialog.close()
            root.openConnectionDialog()
        }
    }

    Component.onCompleted: {
        backend.reloadSessions()
        startupDialog.open()
    }

    onClosing: backend.shutdown()

    menuBar: MenuBar {
        background: Rectangle {
            color: root.side
            border.color: root.border
        }

        Menu {
            title: "File"
            Action {
                text: "Save..."
                enabled: backend.hasErd
                onTriggered: saveFileDialog.open()
            }
            MenuSeparator {}
            Action {
                text: "Exit"
                onTriggered: Qt.quit()
            }
        }
        Menu {
            title: "Session"
            Action {
                text: "Create Session"
                enabled: !backend.connected && !backend.isBusy
                onTriggered: root.openCreateSessionDialog(false)
            }
            MenuSeparator {}
            Action {
                text: "Edit Connection Settings..."
                enabled: backend.currentSessionName.length > 0 && !backend.connected
                onTriggered: root.openConnectionDialog()
            }
            Action {
                text: "Save Current Session"
                enabled: backend.currentSessionName.length > 0
                onTriggered: backend.saveCurrentSession()
            }
            MenuSeparator {}
            Action {
                text: "Disconnect"
                enabled: backend.connected && !backend.isBusy
                onTriggered: backend.disconnectCurrentSession()
            }
        }
    }

    header: Rectangle {
        height: 52
        color: root.side
        border.color: root.border

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 10

            Label {
                text: "DB ERD Desktop"
                color: root.text
                font.pixelSize: 15
                font.bold: true
                Layout.rightMargin: 8
            }

            ActionButton {
                text: "+"
                compact: true
                Layout.preferredWidth: 38
                onClicked: root.zoom = Math.min(root.zoom + 0.15, 3.0)
            }
            ActionButton {
                text: "-"
                compact: true
                Layout.preferredWidth: 38
                onClicked: root.zoom = Math.max(root.zoom - 0.15, 0.35)
            }
            ActionButton {
                text: "100%"
                compact: true
                Layout.preferredWidth: 58
                onClicked: root.zoom = 1.0
            }

            Item { Layout.fillWidth: true }

            BusyIndicator {
                running: backend.isBusy
                visible: backend.isBusy
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
            }

            Rectangle {
                visible: backend.currentSessionName.length > 0
                Layout.maximumWidth: 360
                Layout.preferredHeight: 30
                implicitWidth: sessionLabel.implicitWidth + 28
                radius: 15
                color: root.accentSoft
                border.color: Qt.rgba(0.31, 0.61, 1.0, 0.45)

                Label {
                    id: sessionLabel
                    anchors.centerIn: parent
                    text: backend.currentSessionName
                    color: root.text
                    elide: Text.ElideRight
                    width: Math.min(320, implicitWidth)
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            SplitView.preferredWidth: 410
            SplitView.minimumWidth: 340
            color: root.side
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: backend.connected ? 120 : 132
                    radius: 8
                    color: root.panel
                    border.color: root.border

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: backend.connected ? "Connected Session" : "Session"
                            color: root.muted
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Label {
                            text: backend.currentSessionName.length > 0 ? backend.currentSessionName : "No session selected"
                            color: root.text
                            font.pixelSize: 16
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            visible: !backend.connected
                            Layout.fillWidth: true
                            spacing: 8
                            ActionButton {
                                text: "Connection Settings"
                                Layout.fillWidth: true
                                enabled: backend.currentSessionName.length > 0
                                onClicked: root.openConnectionDialog()
                            }
                            ActionButton {
                                text: "Connect"
                                primary: true
                                Layout.preferredWidth: 104
                                enabled: backend.currentSessionName.length > 0 && !backend.isBusy
                                onClicked: backend.connectCurrentSession()
                            }
                        }
                        RowLayout {
                            visible: backend.connected
                            Layout.fillWidth: true
                            spacing: 8
                            ActionButton {
                                text: "Disconnect"
                                Layout.fillWidth: true
                                enabled: backend.connected && !backend.isBusy
                                onClicked: backend.disconnectCurrentSession()
                            }
                        }
                    }
                }

                SectionPanel {
                    title: "Database Info"
                    Layout.fillWidth: true
                    Label {
                        text: backend.databaseInfo
                        color: root.text
                        wrapMode: Text.WordWrap
                        lineHeight: 1.18
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: root.panel
                    border.color: root.border
                    visible: backend.connected

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            color: root.panelRaised
                            radius: 8

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 8
                                color: root.panelRaised
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 10
                                spacing: 8
                                Label {
                                    text: "Database / Schema / Tables / Views"
                                    color: root.text
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                ActionButton {
                                    text: "Reload"
                                    compact: true
                                    Layout.preferredWidth: 76
                                    enabled: !backend.isBusy
                                    onClicked: backend.reloadTree()
                                }
                            }
                        }

                        ListView {
                            id: tableList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: backend.tableRowsModel
                            boundsBehavior: Flickable.StopAtBounds

                            delegate: Rectangle {
                                property bool rowCheckable: modelData.checkable === false ? false : true
                                property bool groupRow: modelData.type === "table_group" || modelData.type === "view_group"
                                property bool viewRow: modelData.type === "view" || modelData.type === "view_group"

                                width: tableList.width
                                height: groupRow ? 30 : 34
                                color: tableMouse.containsMouse ? root.panelRaised : (index % 2 === 0 ? root.rowEven : root.rowOdd)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10 + ((modelData.level || 0) * 24)
                                    anchors.rightMargin: 10
                                    spacing: 8

                                    Item {
                                        Layout.preferredWidth: 20
                                        Layout.preferredHeight: 20
                                        StyledCheckBox {
                                            anchors.centerIn: parent
                                            visible: rowCheckable
                                            enabled: rowCheckable
                                            checked: modelData.checked
                                            text: ""
                                            width: 20
                                            height: 20
                                            onToggled: backend.setRowChecked(index, checked)
                                        }
                                    }

                                    Rectangle {
                                        Layout.preferredWidth: modelData.type === "namespace" ? 28 : 24
                                        Layout.preferredHeight: 18
                                        radius: 4
                                        color: modelData.type === "namespace" ? root.accentSoft : (viewRow ? root.disabled : root.panelRaised)
                                        border.color: viewRow ? root.border : root.borderStrong

                                        Label {
                                            anchors.centerIn: parent
                                            text: modelData.badge || ""
                                            color: modelData.type === "namespace" ? root.text : (viewRow ? root.muted : "#dbe5ee")
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }

                                    Label {
                                        text: modelData.label
                                        color: viewRow ? root.muted : (modelData.type === "namespace" ? root.text : "#dbe5ee")
                                        font.bold: modelData.type === "namespace" || groupRow
                                        font.pixelSize: groupRow ? 12 : 13
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }

                                MouseArea {
                                    id: tableMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: backend.connected
                    spacing: 8

                    ActionButton {
                        text: "Generate ERD"
                        primary: true
                        Layout.fillWidth: true
                        enabled: backend.connected && !backend.isBusy
                        onClicked: backend.generateErd()
                    }
                    ActionButton {
                        text: "Save..."
                        Layout.preferredWidth: 104
                        enabled: backend.hasErd && !backend.isBusy
                        onClicked: saveFileDialog.open()
                    }
                }
            }
        }

        Rectangle {
            SplitView.fillWidth: true
            color: root.canvas
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    color: root.panel
                    radius: 8
                    border.color: root.border

                    TabBar {
                        id: erdTabs
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        anchors.topMargin: 6
                        anchors.bottomMargin: 6
                        background: Item {}

                        StyledTabButton { text: "Logical ERD" }
                        StyledTabButton { text: "Physical ERD" }
                    }
                }

                StackLayout {
                    currentIndex: erdTabs.currentIndex
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ErdImagePane {
                        imageSource: backend.logicalImageUrl
                        zoom: root.zoom
                        emptyText: "Generate ERD to preview the logical diagram."
                    }
                    ErdImagePane {
                        imageSource: backend.physicalImageUrl
                        zoom: root.zoom
                        emptyText: "Generate ERD to preview the physical diagram."
                    }
                }
            }
        }
    }

    footer: Rectangle {
        height: 30
        color: root.side
        border.color: root.border

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 14
            text: backend.statusMessage
            color: root.muted
            elide: Text.ElideRight
            width: parent.width - 28
        }
    }

    Dialog {
        id: startupDialog
        title: "Open or Create Session"
        modal: true
        dim: true
        enabled: !root.startupDialogBlocked
        opacity: root.startupDialogBlocked ? 0.54 : 1.0
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: 540
        height: 430
        padding: 0

        background: DialogBackground {}
        header: DialogHeader { title: startupDialog.title }

        contentItem: Item {
            enabled: !root.startupDialogBlocked
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10

                Label {
                    text: "저장된 세션을 열거나 새 세션을 생성합니다."
                    color: root.muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: root.panelSoft
                    border.color: root.border

                    ListView {
                        id: sessionList
                        anchors.fill: parent
                        anchors.margins: 6
                        clip: true
                        model: backend.sessionList
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Rectangle {
                            width: sessionList.width
                            height: 52
                            radius: 6
                            color: sessionList.currentIndex === index ? root.accentSoft : (sessionMouse.containsMouse ? root.panelRaised : "transparent")

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 2

                                Label {
                                    text: modelData.name
                                    color: root.text
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: modelData.description || "No description"
                                    color: root.muted
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    font.pixelSize: 12
                                }
                            }

                            MouseArea {
                                id: sessionMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    sessionList.currentIndex = index
                                    root.selectedSessionName = modelData.name
                                }
                                onDoubleClicked: {
                                    sessionList.currentIndex = index
                                    root.selectedSessionName = modelData.name
                                    if (backend.openSession(root.selectedSessionName))
                                        startupDialog.close()
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            text: "No saved sessions"
                            visible: sessionList.count === 0
                            color: root.muted
                        }

                        onCountChanged: {
                            if (count > 0 && currentIndex < 0) {
                                currentIndex = 0
                                root.selectedSessionName = backend.sessionList[0].name
                            }
                        }
                    }
                }
            }
        }

        footer: DialogFooter {
            enabled: !root.startupDialogBlocked
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                ActionButton {
                    text: "Exit"
                    Layout.preferredWidth: 92
                    onClicked: Qt.quit()
                }
                Item { Layout.fillWidth: true }
                ActionButton {
                    text: "Create Session"
                    Layout.preferredWidth: 132
                    onClicked: root.openCreateSessionDialog(true)
                }
                ActionButton {
                    text: "Open Session"
                    primary: true
                    Layout.preferredWidth: 122
                    enabled: sessionList.count > 0
                    onClicked: {
                        var name = root.selectedSessionName || (backend.sessionList.length > 0 ? backend.sessionList[sessionList.currentIndex].name : "")
                        if (backend.openSession(name))
                            startupDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: createSessionDialog
        title: "Create Session"
        modal: true
        dim: true
        anchors.centerIn: parent
        width: Math.min(680, root.width - 96)
        height: Math.min(500, root.height - 96)
        implicitWidth: 680
        implicitHeight: 500
        contentWidth: width
        contentHeight: 330
        padding: 0
        standardButtons: Dialog.NoButton

        background: DialogBackground {}
        header: DialogHeader { title: createSessionDialog.title }

        contentItem: Item {
            implicitWidth: createSessionDialog.width
            implicitHeight: 330

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label {
                    text: "세션 이름을 먼저 만든 뒤 연결 정보를 설정합니다."
                    color: root.muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                FieldInput {
                    id: newSessionNameField
                    placeholderText: "Session name"
                    Layout.fillWidth: true
                }
                FieldArea {
                    id: newSessionDescriptionField
                    placeholderText: "Description"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 150
                }
            }
        }

        footer: DialogFooter {
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Item { Layout.fillWidth: true }
                ActionButton {
                    text: root.createSessionFromStartup ? "Back" : "Cancel"
                    Layout.preferredWidth: 92
                    onClicked: createSessionDialog.close()
                }
                ActionButton {
                    text: "Create"
                    primary: true
                    Layout.preferredWidth: 104
                    onClicked: root.createSessionFromDialog()
                }
            }
        }
    }

    Dialog {
        id: connectionDialog
        title: "Connection Settings"
        modal: true
        dim: true
        anchors.centerIn: parent
        width: 680
        height: 720
        padding: 0
        standardButtons: Dialog.NoButton

        background: DialogBackground {}
        header: DialogHeader { title: connectionDialog.title }

        contentItem: ScrollView {
            id: connectionScroll
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: Math.max(1, connectionScroll.availableWidth - 36)
                x: 18
                y: 18
                spacing: 14

                SectionPanel {
                    title: "SSH Server"
                    Layout.fillWidth: true
                    StyledCheckBox { id: sshEnabledCheck; text: "Use SSH tunnel" }
                    FormRow { label: "SSH Host"; FieldInput { id: sshHostField; Layout.fillWidth: true; enabled: sshEnabledCheck.checked } }
                    FormRow { label: "SSH Port"; FieldInput { id: sshPortField; Layout.fillWidth: true; enabled: sshEnabledCheck.checked } }
                    FormRow { label: "SSH User"; FieldInput { id: sshUserField; Layout.fillWidth: true; enabled: sshEnabledCheck.checked } }
                    FormRow {
                        label: "SSH Password"
                        FieldInput {
                            id: sshPasswordField
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            enabled: sshEnabledCheck.checked
                        }
                    }
                    FormRow { label: "Private Key"; FieldInput { id: sshKeyField; Layout.fillWidth: true; enabled: sshEnabledCheck.checked } }
                    FormRow {
                        label: "Key Passphrase"
                        FieldInput {
                            id: sshKeyPassphraseField
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            enabled: sshEnabledCheck.checked
                        }
                    }
                }

                SectionPanel {
                    title: "Database"
                    Layout.fillWidth: true
                    FormRow {
                        label: "DBMS"
                        FieldCombo {
                            id: dbmsCombo
                            model: ["MySQL", "PostgreSQL", "MSSQL", "Oracle"]
                            Layout.fillWidth: true
                            onActivated: dbPortField.text = root.defaultPort(currentText)
                        }
                    }
                    FormRow { label: "DB Host"; FieldInput { id: dbHostField; Layout.fillWidth: true } }
                    FormRow { label: "DB Port"; FieldInput { id: dbPortField; Layout.fillWidth: true } }
                    FormRow { label: "DB/Service"; FieldInput { id: databaseField; Layout.fillWidth: true } }
                    FormRow { label: "DB User"; FieldInput { id: dbUserField; Layout.fillWidth: true } }
                    FormRow {
                        label: "DB Password"
                        FieldInput {
                            id: dbPasswordField
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                        }
                    }
                    FormRow { label: "MSSQL Driver"; FieldInput { id: mssqlDriverField; Layout.fillWidth: true; enabled: dbmsCombo.currentText === "MSSQL" } }
                    StyledCheckBox { id: trustCertCheck; text: "Trust server certificate"; enabled: dbmsCombo.currentText === "MSSQL" }
                    FormRow {
                        label: "Oracle Mode"
                        FieldCombo {
                            id: oracleModeCombo
                            model: ["service", "sid"]
                            Layout.fillWidth: true
                            enabled: dbmsCombo.currentText === "Oracle"
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                }
            }
        }

        footer: DialogFooter {
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Item { Layout.fillWidth: true }
                ActionButton {
                    text: "Cancel"
                    Layout.preferredWidth: 96
                    onClicked: connectionDialog.close()
                }
                ActionButton {
                    text: "Apply"
                    primary: true
                    Layout.preferredWidth: 104
                    onClicked: {
                        backend.updateConnectionSettings({
                            dbms: dbmsCombo.currentText,
                            host: dbHostField.text,
                            port: parseInt(dbPortField.text),
                            database: databaseField.text,
                            username: dbUserField.text,
                            password: dbPasswordField.text,
                            mssqlDriver: mssqlDriverField.text,
                            oracleMode: oracleModeCombo.currentText,
                            trustServerCertificate: trustCertCheck.checked,
                            sshEnabled: sshEnabledCheck.checked,
                            sshHost: sshHostField.text,
                            sshPort: parseInt(sshPortField.text),
                            sshUsername: sshUserField.text,
                            sshPassword: sshPasswordField.text,
                            sshKeyFile: sshKeyField.text,
                            sshKeyPassphrase: sshKeyPassphraseField.text
                        })
                        connectionDialog.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: saveFileDialog
        title: "Save ERD Documentation"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Word Document (*.docx)", "Hancom HWPX (*.hwpx)", "PowerPoint (*.pptx)", "Draw.io Diagram (*.drawio)"]
        currentFile: "erd_documentation.docx"
        onAccepted: backend.saveDocumentation(selectedFile)
    }

    component ActionButton: Button {
        id: control
        property bool primary: false
        property bool compact: false

        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        implicitHeight: compact ? 30 : 36
        implicitWidth: compact ? 64 : 120
        padding: compact ? 8 : 12

        contentItem: Text {
            text: control.text
            color: !control.enabled ? root.muted : (control.primary ? "#ffffff" : root.text)
            font.pixelSize: control.compact ? 13 : 14
            font.bold: control.primary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 7
            color: !control.enabled ? root.disabled
                   : control.primary ? (control.hovered ? root.accentHover : root.accent)
                   : control.hovered ? root.panelRaised : root.panelSoft
            border.color: !control.enabled ? root.border
                        : control.primary ? Qt.rgba(1, 1, 1, 0.18)
                        : control.hovered ? root.borderStrong : root.border
        }
    }

    component StyledTabButton: TabButton {
        id: control
        height: 32
        padding: 0

        contentItem: Text {
            text: control.text
            color: control.checked ? root.text : root.muted
            font.bold: control.checked
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 6
            color: control.checked ? root.accentSoft : (control.hovered ? root.panelRaised : "transparent")
            border.color: control.checked ? Qt.rgba(0.31, 0.61, 1.0, 0.35) : "transparent"
        }
    }

    component DialogBackground: Rectangle {
        color: root.panel
        radius: 10
        border.color: root.borderStrong
    }

    component DialogHeader: Rectangle {
        id: headerRoot
        property string title: ""
        height: 54
        color: root.panelRaised
        radius: 10

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 10
            color: root.panelRaised
        }

        Label {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 18
            text: headerRoot.title
            color: root.text
            font.pixelSize: 16
            font.bold: true
        }
    }

    component DialogFooter: Rectangle {
        height: 60
        color: root.panelRaised
        radius: 10

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 10
            color: root.panelRaised
        }
    }

    component SectionPanel: Rectangle {
        id: panelRoot
        property string title: ""
        default property alias content: contentColumn.data

        color: root.panel
        radius: 8
        border.color: root.border
        implicitHeight: contentColumn.implicitHeight + 24

        ColumnLayout {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Label {
                visible: panelRoot.title.length > 0
                text: panelRoot.title
                color: root.muted
                font.pixelSize: 12
                font.bold: true
                Layout.fillWidth: true
            }
        }
    }

    component FormRow: RowLayout {
        property alias label: rowLabel.text
        Layout.fillWidth: true
        spacing: 12

        Label {
            id: rowLabel
            Layout.preferredWidth: 132
            Layout.alignment: Qt.AlignVCenter
            color: root.muted
            font.pixelSize: 13
            elide: Text.ElideRight
        }
    }

    component FieldInput: TextField {
        id: control
        selectByMouse: true
        color: enabled ? root.text : root.muted
        placeholderTextColor: Qt.rgba(0.61, 0.66, 0.72, 0.72)
        selectionColor: root.accent
        selectedTextColor: "#ffffff"
        implicitHeight: 34
        leftPadding: 10
        rightPadding: 10
        opacity: enabled ? 1.0 : 0.62

        background: Rectangle {
            radius: 6
            color: control.enabled ? root.panelSoft : root.disabled
            border.color: control.activeFocus ? root.accent : root.border
        }
    }

    component FieldArea: TextArea {
        id: control
        selectByMouse: true
        wrapMode: TextArea.WordWrap
        color: root.text
        placeholderTextColor: Qt.rgba(0.61, 0.66, 0.72, 0.72)
        selectionColor: root.accent
        selectedTextColor: "#ffffff"
        leftPadding: 10
        rightPadding: 10
        topPadding: 8
        bottomPadding: 8

        background: Rectangle {
            radius: 6
            color: root.panelSoft
            border.color: control.activeFocus ? root.accent : root.border
        }
    }

    component FieldCombo: ComboBox {
        id: control
        implicitHeight: 34
        leftPadding: 10
        rightPadding: 30
        opacity: enabled ? 1.0 : 0.62

        contentItem: Text {
            text: control.displayText
            color: control.enabled ? root.text : root.muted
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        indicator: Text {
            text: "v"
            color: control.enabled ? root.muted : root.borderStrong
            x: control.width - width - 12
            y: Math.round((control.height - height) / 2)
        }

        background: Rectangle {
            radius: 6
            color: control.enabled ? root.panelSoft : root.disabled
            border.color: control.activeFocus ? root.accent : root.border
        }

        delegate: ItemDelegate {
            width: control.width
            height: 34
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: modelData
                color: root.text
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: highlighted ? root.accentSoft : root.panel
            }
        }

        popup: Popup {
            y: control.height + 4
            width: control.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 240)
            padding: 4

            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
            }

            background: Rectangle {
                color: root.panel
                border.color: root.borderStrong
                radius: 7
            }
        }
    }

    component StyledCheckBox: CheckBox {
        id: control
        spacing: 8
        hoverEnabled: true
        implicitHeight: 28

        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: control.leftPadding
            y: Math.round((control.height - height) / 2)
            radius: 5
            color: control.checked ? root.accent : root.panelSoft
            border.color: control.checked ? root.accentHover : (control.hovered ? root.borderStrong : root.border)

            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: "#ffffff"
                font.pixelSize: 13
                font.bold: true
            }
        }

        contentItem: Text {
            text: control.text
            color: control.enabled ? root.text : root.muted
            verticalAlignment: Text.AlignVCenter
            leftPadding: control.indicator.width + control.spacing
            elide: Text.ElideRight
        }
    }

    component ErdImagePane: Rectangle {
        property string imageSource: ""
        property real zoom: 1.0
        property string emptyText: ""

        color: root.panel
        radius: 8
        border.color: root.border
        clip: true

        ScrollView {
            anchors.fill: parent
            anchors.margins: 10
            clip: true

            Image {
                source: imageSource
                visible: imageSource.length > 0
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                width: Math.max(sourceSize.width * zoom, parent.width)
                height: Math.max(sourceSize.height * zoom, parent.height)
            }
        }

        Label {
            anchors.centerIn: parent
            text: emptyText
            color: root.muted
            visible: imageSource.length === 0
        }
    }
}
