import PrismInit


def dropAccept(fileList):
    return PrismInit.pcore.appPlugin.handleNetworkDrop(fileList)
