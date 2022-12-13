from PIL import Image
from python.images_management import Matrix, RgbImage, ThermalImage, LeakMask

class ThermalIssuesDetector:

    def __init__(self):
        
        self.image_size = (250, 200)
        self.color_palette = [
            { "rgb": (15, 16, 19),      "color": "Rich Black FOGRA 39",     "temperature": 0},
            { "rgb": (40, 15, 87),      "color": "Russian Violet",          "temperature": 1},
            { "rgb": (71, 12, 119),     "color": "Indigo",                  "temperature": 2},
            { "rgb": (95, 16, 144),     "color": "Blue Violet Color Wheel", "temperature": 3},
            { "rgb": (121, 12, 156),    "color": "Violet RYB",              "temperature": 4},
            { "rgb": (147, 16, 167),    "color": "Violet RYB",              "temperature": 5},
            { "rgb": (188, 18, 161),    "color": "Byzantine",               "temperature": 6},
            { "rgb": (216, 39, 135),    "color": "Barbie Pink",             "temperature": 7},
            { "rgb": (238, 58, 107),    "color": "Paradise Pink",           "temperature": 8},
            { "rgb": (230, 82, 62),     "color": "Fire Opal",               "temperature": 9},
            { "rgb": (228, 129, 18),    "color": "Fulvous",                 "temperature": 10},
            { "rgb": (230, 168, 15),    "color": "Goldenrod",               "temperature": 11},
            { "rgb": (231, 193, 11),    "color": "Jonquil",                 "temperature": 12},
            { "rgb": (231, 221, 52),    "color": "Titanium Yellow",         "temperature": 13},
            { "rgb": (223, 229, 149),   "color": "Green Yellow Crayola",    "temperature": 14},
            { "rgb": (227, 230, 202),   "color": "Beige",                   "temperature": 15}
        ]
        self.leak_offset = 5

    def detectFromImage(self, img: Image, show=False):
        
        # Load RGB image
        rgb_img = RgbImage.fromPilImage(img, self.image_size)
        
        # Transform RGB image to thermal image
        thermal_img_view, thermal_img_data = ThermalImage.FromRgbImage(rgb_img, self.color_palette)
        
        # Transform thermal image to relative thermal image
        temperature_average, min_temperature, max_temperature = thermal_img_data.getTemperatureInfo()
        relative_thermal_image_data = thermal_img_data.toRelativeThermalImage(temperature_average)
        
        # Reperate thermal leaks
        leaks_mask_view, leaks_mask_data, leaks_results_arr = LeakMask.FromData(rgb_img, relative_thermal_image_data, self.leak_offset)

        if show:
            print(" > Image size: {}".format((rgb_img.matrix().rows(), rgb_img.matrix().cols())))
            print(" > Average: {:.2f}°C, Min: {:.2f}°C, Max: {:.2f}°C".format(temperature_average, min_temperature, max_temperature))
            print(" > Leaks founded: {}".format(len(leaks_results_arr)))
            rgb_img.matrix().create_figure("Initial image")
            thermal_img_view.matrix().create_figure(
                "Thermal image", 
                lambda c:  "aT: {:.2f}°C rT: {:.2f}°C".format(
                    thermal_img_data.matrix().get(c),
                    relative_thermal_image_data.matrix().get(c)
                )
            )
            leaks_mask_view.matrix().create_figure(
                "Leak mask", 
                lambda c:  "aT: {:.2f}°C rT: {:.2f}°C".format(
                    thermal_img_data.matrix().get(c),
                    relative_thermal_image_data.matrix().get(c)
                )
            )
            Matrix.show()

        return leaks_mask_view.toPilImage(), leaks_results_arr
    
    def detectFromArray(self, img_arr: list, show=False):
        
        # Load RGB image
        thermal_img_view, thermal_img_data = ThermalImage.FromThermalArray(img_arr)
        
        # Transform thermal image to relative thermal image
        temperature_average, min_temperature, max_temperature = thermal_img_data.getTemperatureInfo()
        relative_thermal_image_data = thermal_img_data.toRelativeThermalImage(temperature_average)
        
        # Reperate thermal leaks
        leaks_mask_view, leaks_mask_data, leaks_results_arr = LeakMask.FromData(thermal_img_view, relative_thermal_image_data, self.leak_offset)

        if show:
            print(" > Image size: {}".format((thermal_img_view.matrix().rows(), thermal_img_view.matrix().cols())))
            print(" > Average: {:.2f}°C, Min: {:.2f}°C, Max: {:.2f}°C".format(temperature_average, min_temperature, max_temperature))
            print(" > Leaks founded: {}".format(len(leaks_results_arr)))
            thermal_img_view.matrix().create_figure(
                "Thermal image", 
                lambda c:  "aT: {:.2f}°C rT: {:.2f}°C".format(
                    thermal_img_data.matrix().get(c),
                    relative_thermal_image_data.matrix().get(c)
                )
            )
            leaks_mask_view.matrix().create_figure(
                "Leak mask", 
                lambda c:  "aT: {:.2f}°C rT: {:.2f}°C".format(
                    thermal_img_data.matrix().get(c),
                    relative_thermal_image_data.matrix().get(c)
                )
            )
            Matrix.show()

        return thermal_img_view.toPilImage(), leaks_mask_view.toPilImage(), leaks_results_arr
    
if __name__ == "__main__":

    path =  "test.png"
    
    detector = ThermalIssuesDetector()
    detector.detectFromImage(img=Image.open(path), show=True)
    