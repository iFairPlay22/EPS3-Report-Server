import torch 
from PIL import Image
from python.images_management import getPilImage

class StructuralIssuesDetector:

    def __init__(self, model_path: str):
        self.__model  = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
        self.__model.conf = 0.4
        
    def detectFromArray(self, arr: list):
        
        initial_img = getPilImage(arr)
        return self.detectFromImage(initial_img)

    def detectFromImage(self, initial_img : Image):
    	
        # Make prediction
        results         = self.__model([initial_img])
        results_data    = results.pandas().xyxy[0]
        result_img_arr  = results.render()[0]
        result_image    = Image.fromarray(result_img_arr)

        # Json
        result_predictions = [
            {
                "confidence": round(float(results_data.confidence[i]) * 100),
                "class": str(results_data.name[i]),
                "box": {
                    "xmin": float(results_data.xmin[i]),
                    "ymin": float(results_data.ymin[i]),
                    "xmax": float(results_data.xmax[i]),
                    "ymax": float(results_data.ymax[i]),
                }
            }
            for i in range(results_data.shape[0])
        ]

        return initial_img, result_image, result_predictions