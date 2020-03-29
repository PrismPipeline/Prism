# Save the scene as a new version with comment

details = {
    "description": "This scene was creation through PDG",
    "username": pcore.username,
}
pcore.saveScene(comment="python executed (PDG)", versionUp=True, details=details, location="global")