# >>>PrismStart
class TOPBAR_MT_prism(Menu):
    bl_label = "Prism"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.prism_save")

        row = layout.row()
        row.operator("object.prism_savecomment")

        row = layout.row()
        row.operator("object.prism_browser")

        row = layout.row()
        row.operator("object.prism_manager")

        row = layout.row()
        row.operator("object.prism_settings")


# <<<PrismEnd
