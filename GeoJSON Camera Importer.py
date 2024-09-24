bl_info = {
    "name": "GeoJSON Camera Importer",
    "description": "Import cameras from a GeoJSON file",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "author": "Kjetil Haughom",
    "location": "View3D > UI > Camera Import",
    "category": "Import-Export",
}

import bpy, json, os, math
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
    )

    sensor_width: bpy.props.FloatProperty(
        name="Sensor Width",
        description="Camera sensor width in mm",
        default=36.0,
    )

    translation_offset_x: bpy.props.FloatProperty(
        name="Translation Offset X",
        description="Offset for the X axis",
        default=0.0,
    )
    
    translation_offset_y: bpy.props.FloatProperty(
        name="Translation Offset Y",
        description="Offset for the Y axis",
        default=0.0,
    )
    
    translation_offset_z: bpy.props.FloatProperty(
        name="Translation Offset Z",
        description="Offset for the Z axis",
        default=0.0,
    )

    def calculate_translation_offset(self, features):
        translations = [feature['properties']['translation'] for feature in features]
        min_x = min(translations, key=lambda t: t[0])[0]
        min_y = min(translations, key=lambda t: t[1])[1]
        max_x = max(translations, key=lambda t: t[0])[0]
        max_y = max(translations, key=lambda t: t[1])[1]
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.translation_offset_x = center_x
        self.translation_offset_y = center_y

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
        
        #print(f"Generated matrix: {final_matrix}")
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
        
        fov = 2 * math.degrees(math.atan(sensor_width / (2 * (sensor_width * focal)))) #not used but nice to keep around
        
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
        self.calculate_translation_offset(features)
        
        for feature in features:
            self.create_camera_from_feature(feature, self.sensor_width, camera_collection, base_path)
        
        return {'FINISHED'}

class GeoJSONCameraImportPanel(bpy.types.Panel):
    bl_label = "Import Camera Data"
    bl_idname = "VIEW3D_PT_camera_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Camera Import'

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.operator(
            ImportGeoJSONCameraOperator.bl_idname,
            text="Import GeoJSON Cameras",
            icon='IMPORT')
        
        col = layout.column(align=True)
        col.prop(context.scene, "geojson_camera_sensor_width", text="Sensor Width")
        col.separator()
        col.label(text="Translation Offset:")
        
        row = col.row(align=True)
        row.prop(context.scene, "geojson_camera_translation_x", text="X")
        row.prop(context.scene, "geojson_camera_translation_y", text="Y")
        row.prop(context.scene, "geojson_camera_translation_z", text="Z")

def register():
    bpy.utils.register_class(ImportGeoJSONCameraOperator)
    bpy.utils.register_class(GeoJSONCameraImportPanel)
    
    bpy.types.Scene.geojson_camera_sensor_width = bpy.props.FloatProperty(
        name="Sensor Width",
        description="Camera sensor width in mm. Default: 36.0)",
        default=36.0,
    )
    
    bpy.types.Scene.geojson_camera_translation_x = bpy.props.FloatProperty(
        name="Translation Offset X",
        description="Offset for the X axis",
        default=0.0,
    )
    
    bpy.types.Scene.geojson_camera_translation_y = bpy.props.FloatProperty(
        name="Translation Offset Y",
        description="Offset for the Y axis",
        default=0.0,
    )
    
    bpy.types.Scene.geojson_camera_translation_z = bpy.props.FloatProperty(
        name="Translation Offset Z",
        description="Offset for the Z axis",
        default=0.0,
    )

def unregister():
    bpy.utils.unregister_class(ImportGeoJSONCameraOperator)
    bpy.utils.unregister_class(GeoJSONCameraImportPanel)
    del bpy.types.Scene.geojson_camera_sensor_width
    del bpy.types.Scene.geojson_camera_translation_x
    del bpy.types.Scene.geojson_camera_translation_y
    del bpy.types.Scene.geojson_camera_translation_z

if __name__ == "__main__":
    register()
