from PIL import Image
from matplotlib import pyplot as plt
import cv2
import numpy as np

class Matrix:
    
    def __init__(self, data: list, rows: int, cols: int):
        self.__data = data
        self.__rows, self.__cols = rows, cols
        self.__avoidGarbage = []
     
    @staticmethod
    def FromData(matrix):
        return Matrix(matrix, len(matrix), len(matrix[0]))
    
    @staticmethod
    def FromValue(rows, cols, value):
        return Matrix([ [ value for c in range(cols) ] for r in range(rows) ], rows, cols)
        
    @staticmethod
    def FromPredicate(rows, cols, predicate: callable):
        return Matrix([ [ predicate((r,c)) for c in range(cols) ] for r in range(rows) ], rows, cols)

    def copy(self):
        return Matrix.FromPredicate(self.__rows, self.__cols, lambda c: self.__data[c[0]][c[1]])
        
    def rows(self):
        return self.__rows
        
    def cols(self):
        return self.__cols
    
    def length(self):
        return self.__rows * self.__cols
    
    def exists(self, coords):
        return 0 <= coords[0] < self.__rows and 0 <= coords[1] < self.__cols
    
    def indexOf(self, predicate : callable = lambda c: True):
        
        for r in range(self.__rows):
            for c in range(self.__cols):
                if predicate((r, c)):
                    return (r, c)
                
        return None
    
    def get(self, coords):
        return self.__data[coords[0]][coords[1]]
    
    def set(self, coords, value):
        self.__data[coords[0]][coords[1]] = value

    def apply(self, value_function: callable):
        for r in range(self.__rows):
            for c in range(self.__cols):
                self.__data[r][c] = value_function((r,c)) 

    def contains(self, value):

        for r in range(self.__rows):
            for c in range(self.__cols):
                if self.__data[r][c] == value:
                    return True

        return False
    
    def count(self, value):
        
        occurences = 0
        
        for r in range(self.__rows):
            for c in range(self.__cols):
                if self.__data[r][c] == value:
                    occurences += 1

        return occurences

    def toCoordsList(self, predicate: callable = lambda c: True):
        return [ (r, c) for r in range(self.__rows) for c in range(self.__cols) if predicate((r, c))]

    def toValuesList(self, predicate: callable = lambda c: True):
        return [ self.__data[r][c] for r in range(self.__rows) for c in range(self.__cols) if predicate((r, c))]

    def toMatrix(self):
        return [ [ self.__data[r][c] for r in range(self.__rows) ] for c in range(self.__cols) ]

    def print(self):
        print("[")

        for row in self.__data:
            print("  " + str(row))

        print("]")

    def create_figure(self, title, text_function: callable = None):
        
        fig = plt.figure(title)
        ax = fig.add_subplot()
        
        if text_function is not None:
            
            cursor  = LabelizedCursor(ax, text_function)
            conn = plt.connect('motion_notify_event', cursor.mouse_event)
            self.__avoidGarbage.append(cursor)
            self.__avoidGarbage.append(conn)
            
        ax.imshow(self.__data, interpolation='nearest')
        
        return fig, ax
        
    @staticmethod
    def show():
        plt.show()

class RgbImage:
    
    def __init__(self, matrix: Matrix):
        self.__rows, self.__cols = matrix.rows(), matrix.cols()
        self.__rgb_image = matrix.copy()

    @staticmethod
    def fromPilImage(img : Image, size : tuple = None):

        new_img = img.convert('RGB')
        if size is not None:
            new_img = new_img.resize(size)
            
        matrix = Matrix.FromPredicate(new_img.size[1], new_img.size[0], lambda c: new_img.getpixel((c[1], c[0])))
        return RgbImage(matrix)

    @staticmethod
    def FromFilePath(img_path: str, size : tuple = None):
        
        return RgbImage.fromPilImage(Image.open(img_path), size)
        
    @staticmethod
    def FromPixelMatrix(matrix: Matrix):
        
        return RgbImage(matrix)    
      
    def matrix(self):
        return self.__rgb_image

    def toPilImage(self):
        
        img = Image.new('RGB', [self.__rows, self.__cols], 255)
        data = img.load()

        for x in range(img.size[0]):
            for y in range(img.size[1]):
                data[x,y] = self.__rgb_image.get((x,y))

        return img
    
class LabelizedCursor:
    def __init__(self, ax, label_function: callable):
        self.__ax = ax
        self.__label_function = label_function
        self.txt = ax.text(0,0,'', { "color": "black", "fontsize": "x-large"})

    def mouse_event(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.txt.set_text(self.__label_function((int(x), int(y))))
            self.txt.set_position((x, y))
            self.__ax.figure.canvas.draw_idle()

class ThermalImage:
    
    def __init__(self, matrix: Matrix):
            
        self.__rows, self.__cols = matrix.rows(), matrix.cols()
        self.__thermal_image = matrix.copy()
        
    def matrix(self):
        return self.__thermal_image
    
    def getTemperatureInfo(self):
        
        all_temperatures = self.__thermal_image.toValuesList()
        temperature_average = sum(all_temperatures) / len(all_temperatures)
        min_temperature     = min(all_temperatures)
        max_temperature     = max(all_temperatures)
        return temperature_average, min_temperature, max_temperature
      
    def toRgbImage(self):
        
        np_old_img  = np.array(self.__thermal_image.toMatrix())
        np_new_arr  = np.zeros((self.__rows, self.__cols), dtype=np.uint8)
        np_new_img  = np.uint8(cv2.normalize(np_old_img, np_new_arr, 0, 255, cv2.NORM_MINMAX))
        colored_img = cv2.applyColorMap(np_new_img, cv2.COLORMAP_MAGMA).tolist()
        
        return RgbImage.FromPixelMatrix(Matrix.FromPredicate(len(colored_img[0]), len(colored_img), lambda c: tuple(colored_img[c[1]][c[0]])))
    
    def toRelativeThermalImage(self, offset: float):
          
        return ThermalImage(Matrix.FromPredicate(self.__rows, self.__cols, lambda c: self.__thermal_image.get(c) - offset))
    
    @staticmethod
    def get_closest_color_from_rgb(color_palette, rgb_triplet: tuple):
        min_colours = {}

        for color_data in color_palette:
            r_c, g_c, b_c = color_data["rgb"]
            r_s, g_s, b_s = rgb_triplet
            key=0.299*abs(r_c - r_s)+0.587*abs(g_c - g_s)+0.114*abs(b_c - b_s)
            min_colours[key] = color_data
            
        return min_colours[min(min_colours.keys())]
            
    @staticmethod
    def get_closest_color_from_temperature(color_palette, temperature: float):
        min_colours = {}

        for color_data in color_palette:
            temperature_c = color_data["temperature"]
            temperature_s = temperature
            key=abs(temperature_c - temperature_s)
            min_colours[key] = color_data
            
        return min_colours[min(min_colours.keys())]
               
    @staticmethod
    def FromRgbImage(rgb_image: RgbImage, color_palette : list):
        
        matrix = rgb_image.matrix()
        
        return (
            RgbImage(Matrix.FromPredicate(matrix.rows(), matrix.cols(), lambda c: 
                ThermalImage.get_closest_color_from_rgb(color_palette, matrix.get(c))["rgb"]    
            )),
            ThermalImage(Matrix.FromPredicate(matrix.rows(), matrix.cols(), lambda c: 
                ThermalImage.get_closest_color_from_rgb(color_palette, matrix.get(c))["temperature"]    
            ))
        )

    @staticmethod
    def FromThermalArray(thermal_array : Matrix):
        
        thermal_image = ThermalImage(Matrix.FromPredicate(len(thermal_array), len(thermal_array[0]), lambda c: int(thermal_array[c[0]][c[1]])))
        
        return (
            thermal_image.toRgbImage(),
            thermal_image
        )

class LeakMask:
    
    def __init__(self, mask_matrix: Matrix):
            
        self.__rows, self.__cols = mask_matrix.rows(), mask_matrix.cols()
        self.__mask_matrix = mask_matrix.copy()

    @staticmethod
    def __getSmallestRectangle(data: list):

        all_x = [ coord[0] for coord in data ]
        all_y = [ coord[1] for coord in data ]

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        return ((min_x, min_y), (max_x, max_y))

    @staticmethod
    def __firstIndividualPixel(pixels_data):

        for pixel, pixel_data in pixels_data.items():
            if pixel_data["group"] is None:
                return pixel_data["index"]

        return None

    @staticmethod
    def tuple2ToStr(t: tuple):
        return "{}_{}".format(int(t[0]), int(t[1]))

    @staticmethod
    def tuple2FromStr(s: str):
        v1, v2 = s.split("_")
        return (int(v1), int(v2))

    @staticmethod
    def __makeGroups(data: list, start_group_id):

        pixels_nb_categ     = 0
        pixels_nb_to_categ  = len(data)
        pixels_data         = { LeakMask.tuple2ToStr(data[i]) : { "group": None, "index": i } for i in range(len(data)) }

        group_id = start_group_id

        # while individual pixels
        while pixels_nb_to_categ != pixels_nb_categ:
                
            # pick the first individual pixel
            start_pos     = LeakMask.__firstIndividualPixel(pixels_data)
            all_pos_to_check  = [ start_pos ]

            # while pixels to check
            while len(all_pos_to_check) != 0:

                # pick the pixel to check
                pos_to_check    = all_pos_to_check.pop()
                pixel_to_check  = data[pos_to_check]
                str_to_check    = LeakMask.tuple2ToStr(pixel_to_check)
                
                # if individual pixel
                if pixels_data[str_to_check]["group"] is None:
                    
                    # add group to individual pixel 
                    pixels_data[str_to_check]["group"] = group_id
                    pixels_nb_categ += 1

                    # if pixels_nb_categ % 100 == 0:                
                    #     print("> {}% ".format(int(pixels_nb_categ * 100 / pixels_nb_to_categ)), end="\r")

                    # check neighboors
                    x,y = pixel_to_check
                    for t in [i for i in range(1, 10)]:
                        for o_x, o_y in [ (0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,-1),(1,-1),(-1,1) ]:

                            # if pixel exists
                            next_pixel_to_check = (x + o_x * t, y + o_y * t)                
                            newt_str_to_check   = LeakMask.tuple2ToStr(next_pixel_to_check)
                            if newt_str_to_check in pixels_data:
                                
                                # if not already added and individual
                                next_pos_to_check = pixels_data[newt_str_to_check]["index"]                    
                                
                                if not(next_pos_to_check in all_pos_to_check) and pixels_data[newt_str_to_check]["group"] is None:

                                    # check it
                                    all_pos_to_check.append(next_pos_to_check)

            # next group
            group_id += 1

        # print("> 100%", end="\r")

        result = {}
        for pixel_str, pixel_data in pixels_data.items():
            if not pixel_data["group"] in result:
                result[pixel_data["group"]] = []
            result[pixel_data["group"]].append(LeakMask.tuple2FromStr(pixel_str))
    
        return result
        
    @staticmethod
    def FromData(image_view: RgbImage, relative_thermal_image: ThermalImage, leak_offset: float):
        
        # Leak detection
        matrix = relative_thermal_image.matrix()
        too_hot_coords  = matrix.toCoordsList(lambda c: leak_offset <= matrix.get(c))
        too_cold_coords = matrix.toCoordsList(lambda c: matrix.get(c) <= -leak_offset)
        
        # Leak analysis
        too_hot_groups  = LeakMask.__makeGroups(too_hot_coords, 0)
        id_limit = len(too_hot_groups)
        too_cold_groups = LeakMask.__makeGroups(too_cold_coords, id_limit)
        
        results = []
        for leak_group_id, leak_group_coords in list(too_hot_groups.items()) + list(too_cold_groups.items()):
            (min_x, min_y), (max_x, max_y) = LeakMask.__getSmallestRectangle(leak_group_coords)
            results.append({
                "confidence": 100,
                "class": "hot leak" if leak_group_id < id_limit else "cold leak",
                "box": {
                    "xmin": float(min_x), "ymin": float(min_y),
                    "xmax": float(max_x), "ymax": float(max_y),
                }
            })

        return (
            RgbImage.FromPixelMatrix(Matrix.FromPredicate(matrix.rows(), matrix.cols(), lambda c: (255, 0, 0) if c in too_hot_coords else ((0, 0, 255) if c in too_cold_coords else image_view.matrix().get(c)))),
            LeakMask(Matrix.FromPredicate(matrix.rows(), matrix.cols(), lambda c: c in too_hot_coords or c in too_cold_coords)),
            results
        )
    
    def matrix(self):
        return self.__mask_matrix
    
def getPilImage(mat: list):
    
    img = Image.new('RGB', [len(mat), len(mat[0])], 255)
    data = img.load()

    for x in range(img.size[0]):
        for y in range(img.size[1]):
            data[x,y] = tuple(mat[x][y])

    return img