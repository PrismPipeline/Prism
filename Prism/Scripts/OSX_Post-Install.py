import os

userName = os.environ["SUDO_USER"] if "SUDO_USER" in os.environ else os.environ["USER"]
path = "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
if os.path.exists(path):
    os.system("launchctl load %s" % path)
