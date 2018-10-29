import os
userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
os.system("launchctl load /Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName)