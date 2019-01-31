# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CreateItem.ui'
#
# Created: Thu Oct 25 18:02:26 2018
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_CreateItem(object):
    def setupUi(self, dlg_CreateItem):
        dlg_CreateItem.setObjectName("dlg_CreateItem")
        dlg_CreateItem.resize(317, 182)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_CreateItem)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_type = QtWidgets.QWidget(dlg_CreateItem)
        self.w_type.setObjectName("w_type")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.w_type)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(self.w_type)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        spacerItem = QtWidgets.QSpacerItem(40, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.rb_asset = QtWidgets.QRadioButton(self.w_type)
        self.rb_asset.setChecked(True)
        self.rb_asset.setObjectName("rb_asset")
        self.horizontalLayout_2.addWidget(self.rb_asset)
        self.rb_folder = QtWidgets.QRadioButton(self.w_type)
        self.rb_folder.setObjectName("rb_folder")
        self.horizontalLayout_2.addWidget(self.rb_folder)
        self.verticalLayout.addWidget(self.w_type)
        self.w_item = QtWidgets.QWidget(dlg_CreateItem)
        self.w_item.setObjectName("w_item")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.w_item)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_item = QtWidgets.QLabel(self.w_item)
        self.l_item.setObjectName("l_item")
        self.horizontalLayout.addWidget(self.l_item)
        self.e_item = QtWidgets.QLineEdit(self.w_item)
        self.e_item.setObjectName("e_item")
        self.horizontalLayout.addWidget(self.e_item)
        self.b_showTasks = QtWidgets.QPushButton(self.w_item)
        self.b_showTasks.setMaximumSize(QtCore.QSize(25, 16777215))
        self.b_showTasks.setObjectName("b_showTasks")
        self.horizontalLayout.addWidget(self.b_showTasks)
        self.verticalLayout.addWidget(self.w_item)
        self.w_options = QtWidgets.QWidget(dlg_CreateItem)
        self.w_options.setObjectName("w_options")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.w_options)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.verticalLayout.addWidget(self.w_options)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_CreateItem)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_CreateItem)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_CreateItem.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_CreateItem.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_CreateItem)
        dlg_CreateItem.setTabOrder(self.e_item, self.b_showTasks)
        dlg_CreateItem.setTabOrder(self.b_showTasks, self.buttonBox)
        dlg_CreateItem.setTabOrder(self.buttonBox, self.rb_asset)
        dlg_CreateItem.setTabOrder(self.rb_asset, self.rb_folder)

    def retranslateUi(self, dlg_CreateItem):
        dlg_CreateItem.setWindowTitle(QtWidgets.QApplication.translate("dlg_CreateItem", "Create Category", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("dlg_CreateItem", "Type:", None, -1))
        self.rb_asset.setText(QtWidgets.QApplication.translate("dlg_CreateItem", "Asset", None, -1))
        self.rb_folder.setText(QtWidgets.QApplication.translate("dlg_CreateItem", "Folder", None, -1))
        self.l_item.setText(QtWidgets.QApplication.translate("dlg_CreateItem", "Category Name:", None, -1))
        self.b_showTasks.setToolTip(QtWidgets.QApplication.translate("dlg_CreateItem", "existing tasks", None, -1))
        self.b_showTasks.setText(QtWidgets.QApplication.translate("dlg_CreateItem", "▼", None, -1))

