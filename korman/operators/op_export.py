#    This file is part of Korman.
#
#    Korman is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Korman is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Korman.  If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.props import *
import os, os.path

from .. import exporter
from ..properties.prop_world import PlasmaAge


class ExportOperator(bpy.types.Operator):
    """Exports ages for Cyan Worlds' Plasma Engine"""

    bl_idname = "export.plasma_age"
    bl_label = "Export Age"

    # Here's the rub: we define the properties in this dict. We're going to register them as a seekrit
    # over on the PlasmaAge world properties. We've got a helper so we can access them like they're actually on us...
    # If you want a volatile property, register it directly on this operator!
    _properties = {
        "version": (EnumProperty, {"name": "Version",
                                   "description": "Version of the Plasma Engine to target",
                                   "default": "pvPots",  # This should be changed when moul is easier to target!
                                   "items": [("pvPrime", "Ages Beyond Myst (63.11)", "Targets the original Uru (Live) game", 2),
                                             ("pvPots", "Path of the Shell (63.12)", "Targets the most recent offline expansion pack", 1),
                                             ("pvMoul", "Myst Online: Uru Live (70)", "Targets the most recent online game", 0)]}),

        "use_texture_page": (BoolProperty, {"name": "Use Textures Page",
                                            "description": "Exports all textures to a dedicated Textures page",
                                            "default": True}),
    }

    # This wigs out and very bad things happen if it's not directly on the operator...
    filepath = StringProperty(subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout
        age = context.scene.world.plasma_age

        # The crazy mess we're doing with props on the fly means we have to explicitly draw them :(
        layout.prop(age, "version")
        layout.prop(age, "use_texture_page")

    def __getattr__(self, attr):
        if attr in self._properties:
            return getattr(bpy.context.scene.world.plasma_age, attr)
        raise AttributeError(attr)

    @property
    def has_reports(self):
        return hasattr(self.report)

    @classmethod
    def poll(cls, context):
        if context.object is not None:
            return context.scene.render.engine == "PLASMA_GAME"

    def execute(self, context):
        # Before we begin, do some basic sanity checking...
        if not self.filepath:
            self.error = "No file specified"
            return {"CANCELLED"}
        else:
            dir = os.path.split(self.filepath)[0]
            if not os.path.exists(dir):
                try:
                    os.mkdirs(dir)
                except os.error:
                    self.report({"ERROR"}, "Failed to create export directory")
                    return {"CANCELLED"}

        # We need to back out of edit mode--this ensures that all changes are committed
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Separate blender operator and actual export logic for my sanity
        with _UiHelper() as _ui:
            e = exporter.Exporter(self)
            try:
                e.run()
            except exporter.ExportError as error:
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
            else:
                return {"FINISHED"}

    def invoke(self, context, event):
        # Called when a user hits "export" from the menu
        # We will prompt them for the export info, then call execute()
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    @classmethod
    def register(cls):
        # BEGIN MAJICK
        # Register the exporter properties such that they will persist
        for name, (prop, options) in cls._properties.items():
            # Hide these settings from being seen on the age properties
            age_options = dict(options)
            age_options["options"] = {"HIDDEN"}

            # Now do the majick
            setattr(PlasmaAge, name, prop(**age_options))


class _UiHelper:
    """This fun little helper makes sure that we don't wreck the UI"""
    def __enter__(self):
        self.active_object = bpy.context.object
        self.selected_objects = bpy.context.selected_objects

    def __exit__(self, type, value, traceback):
        for i in bpy.data.objects:
            i.select = (i in self.selected_objects)
        bpy.context.scene.objects.active = self.active_object


# Add the export operator to the Export menu :)
def menu_cb(self, context):
    if context.scene.render.engine == "PLASMA_GAME":
        self.layout.operator_context = "INVOKE_DEFAULT"
        self.layout.operator(ExportOperator.bl_idname, text="Plasma Age (.age)")


def register():
    bpy.types.INFO_MT_file_export.append(menu_cb)

def unregister():
    bpy.types.INFO_MT_file_export.remove(menu_cb)
