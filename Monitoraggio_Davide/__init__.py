def classFactory(iface):
    from .monitoraggio_plugin import MonitoraggioPlugin
    return MonitoraggioPlugin(iface)
