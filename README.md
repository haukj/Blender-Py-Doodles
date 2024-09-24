# GeoJSON Camera Importer

### Description

The **GeoJSON Camera Importer** is a Blender add-on that allows users to import camera data from GeoJSON files exported from OpenDroneMap (ODM). The add-on also supports adding matching background images if they are located in the same directory or relevant subfolders. Additionally, it can calculate an offset based on the mean midpoint of the camera locations.

### Features
- Import cameras from a `.geojson` file.
- Match and load corresponding background images (e.g., `.jpg`, `.jpeg`, `.png`).
- Option to calculate the mean midpoint of all cameras and apply it as a translation offset.
- Add a text object in the 3D viewport showing the applied offset values.

### Installation

1. Download the `GeoJSON Camera Importer` add-on as a `.zip` file.
2. Open Blender and navigate to `Edit > Preferences > Add-ons`.
3. Click on `Install...` and locate the downloaded `.zip` file.
4. Enable the add-on by checking the box next to `GeoJSON Camera Importer`.
5. The add-on will now be available under `File > Import > GeoJSON Camera (.geojson)`.

### Usage

1. Go to `File > Import > GeoJSON Camera (.geojson)` in Blender's top menu.
2. A file browser will open. Navigate to the desired `.geojson` file and select it.
3. In the lower-left corner of the file browser, you will see import options:
   - **Sensor Width**: Specify the sensor width of the camera (default is 36.0 mm).
   - **Translation Offset X, Y, Z**: Set manual translation offsets for the camera data.
   - **Calculate Mean Midpoint**: If enabled, the add-on will calculate the mean midpoint of all the camera locations and apply it as the offset.

4. After importing:
   - The cameras will be added to the scene.
   - Any matching background images (if present) will be loaded as camera backgrounds.
   - A text object will be created at the origin `(0, 0, 0)` showing the applied offsets (X, Y, Z) if any offset is applied (manual or calculated).

### Options Explained

- **Sensor Width**: This refers to the physical width of the camera sensor in millimeters. If you're not sure, 36mm is the standard full-frame camera width.
- **Translation Offset**: These fields allow you to manually enter translation offsets (in X, Y, Z coordinates) to reposition the cameras. 
- **Calculate Mean Midpoint**: This option computes the average (mean) location of all the cameras and uses that as the translation offset. This is useful if the camera coordinates are large and you need to center them in the scene.

### Example Workflow

1. Enable the add-on in Blender.
2. Import a `.geojson` file via `File > Import > GeoJSON Camera (.geojson)`.
3. Enable **Calculate Mean Midpoint** if you want the importer to calculate and apply the center point as an offset.
4. If you have background images in the same folder or subfolders, the add-on will automatically match and add these to the cameras.

### Folder Structure for Image Matching

To ensure that background images are correctly matched, the images should be in the same folder as the `.geojson` file or in subfolders such as:
- `drone`
- `image`, `images`
- `photo`, `photos`
- `dji`, `dcim`

### Known Issues

- Ensure that the camera names in the `.geojson` file match the image file names for the correct images to be loaded as camera backgrounds.
- Blender's file browser does not support relative paths; ensure all paths to background images are correct.

### License

This add-on is licensed under the [GPL-3.0](https://opensource.org/licenses/GPL-3.0) License.
