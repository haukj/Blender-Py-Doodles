bl_info = {
    "name": "GeoJSON Camera Importer",
    "description": "Import cameras from a GeoJSON file",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "author": "Kjetil Haughom",
    "location": "File > Import > GeoJSON Camera (.geojson)",
    "category": "Import-Export",
}

import bpy
import json
import os
import math
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Vector
from math import radians, tan


class ImportGeoJSONCameraOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.geojson_camera"
    bl_label = "Import GeoJSON Cameras"
    bl_description = "Imports cameras from geojson files exported from OpenDroneMap (ODM), adds matching images if present. The correct geojson file usually ends with \"...projectname...-shots.geojson\""
    bl_options = {'PRESET', 'UNDO'}
    
    filename_ext = ".geojson"
    filter_glob: bpy.props.StringProperty(
        default="*.geojson",
        options={'HIDDEN'},
        maxlen=255,
    ) # type: ignore

    sensor_width: bpy.props.FloatProperty(
        name="Sensor Width",
        description="Camera sensor width in mm",
        default=36.0,
    ) # type: ignore

    use_mean_midpoint: bpy.props.BoolProperty(
        name="Calculate Mean Midpoint",
        description="Calculate the mean midpoint of all cameras and use as offset",
        default=False,
    ) # type: ignore

    translation_offset_x: bpy.props.FloatProperty(
        name="Translation Offset X",
        description="Offset for the X axis",
        default=0.0,
    ) # type: ignore
    
    translation_offset_y: bpy.props.FloatProperty(
        name="Translation Offset Y",
        description="Offset for the Y axis",
        default=0.0,
    ) # type: ignore
    
    translation_offset_z: bpy.props.FloatProperty(
        name="Translation Offset Z",
        description="Offset for the Z axis",
        default=0.0,
    ) # type: ignore

    def create_offset_text_object(self):
        # Create a formatted text string with the offset values
        offset_text = f"X:{self.translation_offset_x:.2f}\nY:{self.translation_offset_y:.2f}\nZ:{self.translation_offset_z:.2f}".upper()
        
        # Create a new text object in Blender at the origin
        bpy.ops.object.text_add(location=(0, 0, 0))
        text_object = bpy.context.object
        text_object.data.body = offset_text  # Set the text content
        text_object.name = "Offset Values"
        text_object.data.align_x = 'CENTER'
        text_object.data.size = 10
        
        # Print to console for debug purposes
        print(f"Created text object with offset: {offset_text}")

    def calculate_translation_offset(self, features):
        # Only calculate the mean midpoint if the user enabled it
        if self.use_mean_midpoint:
            print("Calculating mean midpoint for offset...")
            translations = [feature['properties']['translation'] for feature in features]
            
            avg_x = sum(t[0] for t in translations) / len(translations)
            avg_y = sum(t[1] for t in translations) / len(translations)

            self.translation_offset_x = avg_x
            self.translation_offset_y = avg_y

            print(f"Mean midpoint calculated: X={avg_x}, Y={avg_y}")
        else:
            print("Using manual offset...")

        # Check if any offset is applied
        if (self.translation_offset_x == 0.0 and 
            self.translation_offset_y == 0.0):
            # If no offset applied, do not create the text object
            print("No offset applied, skipping text object creation.")
            return
        else:
            # Create the text object with the offset values
            self.create_offset_text_object()

    def get_matrix(self, translation, rotation, scale=1.0):
        axis = Vector((-rotation[0], -rotation[1], -rotation[2]))
        angle = axis.length
        
        if angle > 0:
            axis.normalize()
            rotation_matrix = Matrix.Rotation(angle, 4, axis)
        else:
            rotation_matrix = Matrix.Identity(4)
        
        adjusted_translation = [
            translation[0] - self.translation_offset_x,
            translation[1] - self.translation_offset_y,
            translation[2] - self.translation_offset_z
        ]
        
        translation_matrix = Matrix.Translation(Vector(adjusted_translation))
        
        if scale != 1.0:
            scale_matrix = Matrix.Scale(scale, 4)
            rotation_matrix = scale_matrix @ rotation_matrix
        
        correction_matrix = Matrix.Rotation(radians(180), 4, 'X')
        final_matrix = translation_matrix @ rotation_matrix @ correction_matrix
        
        return final_matrix

    def find_corresponding_images(self, base_path, camera_name):
        image_extensions = {'.jpg', '.jpeg', '.png'}
        matching_images = []
        image_folders = {'drone', 'jpg', 'jpeg', 'img', 'image', 'images', 'photo', 'photos', 'dji', 'dcim'}
        
        for root, dirs, files in os.walk(base_path):
            normalized_root = os.path.normpath(root)
            
            if any(folder in normalized_root.lower() for folder in image_folders):
                for file in files:
                    if file.lower().endswith(tuple(image_extensions)) and camera_name in file:
                        image_path = os.path.join(normalized_root, file)
                        matching_images.append(image_path)
        
        return matching_images

    def set_camera_background_image(self, camera, image_path):
        img = bpy.data.images.load(os.path.normpath(image_path))
        
        if img:
            camera.data.show_background_images = True
            bg = camera.data.background_images.new()
            bg.image = img
            bg.display_depth = 'BACK'
        
        return img

    def set_scene_resolution(self, image):
        width = image.size[0]
        height = image.size[1]
        bpy.context.scene.render.resolution_x = width
        bpy.context.scene.render.resolution_y = height

    def create_camera_from_feature(self, feature, sensor_width, collection, base_path):
        properties = feature['properties']
        filename = properties['filename']
        translation = properties['translation']
        rotation = properties['rotation']
        focal = properties['focal']
        
        fov = 2 * math.degrees(math.atan(sensor_width / (2 * (sensor_width * focal))))  # Not used but useful to keep
        
        focal_length = sensor_width * focal
        
        cam_data = bpy.data.cameras.new(name=filename)
        cam_data.lens = focal_length
        cam_data.sensor_width = sensor_width
        cam_object = bpy.data.objects.new(name=filename, object_data=cam_data)
        
        bpy.context.collection.objects.link(cam_object)
        collection.objects.link(cam_object)
        bpy.context.collection.objects.unlink(cam_object)
        
        transform_matrix = self.get_matrix(translation, rotation)
        cam_object.matrix_world = transform_matrix
        images = self.find_corresponding_images(base_path, filename)
        
        if images:
            image_path = images[0]
            print(f"Found image for camera {filename}: {image_path}")
            img = self.set_camera_background_image(cam_object, image_path)
            self.set_scene_resolution(img)
        else:
            print(f"No images found for camera {filename}.")

    def execute(self, context):
        file_path = os.path.abspath(self.filepath)
        base_path = os.path.dirname(file_path)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read the file: {str(e)}")
            return {'CANCELLED'}
        
        features = data.get('features', [])
        
        if not features:
            self.report({'ERROR'}, "No 'features' key found in the JSON file.")
            return {'CANCELLED'}
        
        camera_collection = bpy.data.collections.new(name="Imported Cameras")
        bpy.context.scene.collection.children.link(camera_collection)
        self.calculate_translation_offset(features)  # Calculate the offset here
        
        for feature in features:
            self.create_camera_from_feature(feature, self.sensor_width, camera_collection, base_path)
        
        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportGeoJSONCameraOperator.bl_idname, text="GeoJSON Camera (.geojson)")

def register():
    bpy.utils.register_class(ImportGeoJSONCameraOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportGeoJSONCameraOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
