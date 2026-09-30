import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class MonitoraggioPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def tr(self, text):
        return QCoreApplication.translate("MonitoraggioDavide", text)

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icons", "monitoraggio.svg"))
        self.action = QAction(icon, self.tr("Monitoraggio Davide"), self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr("&Monitoraggio Davide"), self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(self.tr("&Monitoraggio Davide"), self.action)
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        if self.dialog is None:
            from .monitoraggio_dialog import MonitoraggioDialog
            self.dialog = MonitoraggioDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
