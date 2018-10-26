# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CreateItem.ui'
#
# Created: Thu Oct 25 18:02:26 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_CreateItem(object):
    def setupUi(self, dlg_CreateItem):
        dlg_CreateItem.setObjectName("dlg_CreateItem")
        dlg_CreateItem.resize(317, 182)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_CreateItem)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_type = QtGui.QWidget(dlg_CreateItem)
        self.w_type.setObjectName("w_type")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.w_type)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtGui.QLabel(self.w_type)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        spacerItem = QtGui.QSpacerItem(40, 10, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.rb_asset = QtGui.QRadioButton(self.w_type)
        self.rb_asset.setChecked(True)
        self.rb_asset.setObjectName("rb_asset")
        self.horizontalLayout_2.addWidget(self.rb_asset)
        self.rb_folder = QtGui.QRadioButton(self.w_type)
        self.rb_folder.setObjectName("rb_folder")
        self.horizontalLayout_2.addWidget(self.rb_folder)
        self.verticalLayout.addWidget(self.w_type)
        self.w_item = QtGui.QWidget(dlg_CreateItem)
        self.w_item.setObjectName("w_item")
        self.horizontalLayout = QtGui.QHBoxLayout(self.w_item)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_item = QtGui.QLabel(self.w_item)
        self.l_item.setObjectName("l_item")
        self.horizontalLayout.addWidget(self.l_item)
        self.e_item = QtGui.QLineEdit(self.w_item)
        self.e_item.setObjectName("e_item")
        self.horizontalLayout.addWidget(self.e_item)
        self.b_showTasks = QtGui.QPushButton(self.w_item)
        self.b_showTasks.setMaximumSize(QtCore.QSize(25, 16777215))
        self.b_showTasks.setObjectName("b_showTasks")
        self.horizontalLayout.addWidget(self.b_showTasks)
        self.verticalLayout.addWidget(self.w_item)
        self.w_options = QtGui.QWidget(dlg_CreateItem)
        self.w_options.setObjectName("w_options")
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.w_options)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.verticalLayout.addWidget(self.w_options)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_CreateItem)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
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
        dlg_CreateItem.setWindowTitle(QtGui.QApplication.translate("dlg_CreateItem", "Create Category", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("dlg_CreateItem", "Type:", None, QtGui.QApplication.UnicodeUTF8))
        self.rb_asset.setText(QtGui.QApplication.translate("dlg_CreateItem", "Asset", None, QtGui.QApplication.UnicodeUTF8))
        self.rb_folder.setText(QtGui.QApplication.translate("dlg_CreateItem", "Folder", None, QtGui.QApplication.UnicodeUTF8))
        self.l_item.setText(QtGui.QApplication.translate("dlg_CreateItem", "Category Name:", None, QtGui.QApplication.UnicodeUTF8))
        self.b_showTasks.setToolTip(QtGui.QApplication.translate("dlg_CreateItem", "existing tasks", None, QtGui.QApplication.UnicodeUTF8))
        self.b_showTasks.setText(QtGui.QApplication.translate("dlg_CreateItem", "▼", None, QtGui.QApplication.UnicodeUTF8))

