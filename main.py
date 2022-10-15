from flask import Flask, redirect, url_for, request, render_template
from datetime import datetime
import uuid
import glob
import os
import io
import json
import torch 
from PIL import Image
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

STORAGE_FOLDER               = "storage"
STORAGE_INITIAL_IMAGE_FOLDER = os.path.join(STORAGE_FOLDER, "initial-image")
STORAGE_RESULT_IMAGE_FOLDER  = os.path.join(STORAGE_FOLDER, "result-image")
STORAGE_RESULT_DATA_FOLDER   = os.path.join(STORAGE_FOLDER, "result-data")
TEMPLATES_FOLDER             = os.path.join("templates", "html")
ASSETS_FOLDER                = "assets"

def createFolderIfNotExists(path):
	if not os.path.exists(path):
		os.makedirs(path)

def createFoldersIfNotExists(paths):
	for path in paths:
		createFolderIfNotExists(path)

createFoldersIfNotExists([
	STORAGE_FOLDER,
	STORAGE_INITIAL_IMAGE_FOLDER, 
	STORAGE_RESULT_IMAGE_FOLDER,
	STORAGE_RESULT_DATA_FOLDER,
	TEMPLATES_FOLDER, 
	ASSETS_FOLDER
])

app = Flask(__name__, template_folder=TEMPLATES_FOLDER)

# Upload the report files in the STORAGE_FOLDER
# Paths:
# 	> "STORAGE_INITIAL_IMAGE_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.EXTENSION"	
# 	> "STORAGE_RESULT_IMAGE_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.EXTENSION"
# 	> "STORAGE_RESULT_DATA_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.json"
def uploadReportFiles(building_id, initial_file):

	building_id = str(building_id)

	# Time
	dt  = datetime.now()
	d   = dt.strftime('%dd-%mm-%Yy')
	t   = dt.strftime('%Hh-%Mm-%Ss')

	# File structure
	extension = initial_file.filename.split(".")[-1]
	file_name = building_id + "-" + d + "-" + t

	initial_image_building_folder_path = os.path.join(STORAGE_INITIAL_IMAGE_FOLDER, building_id) 
	result_image_building_folder_path  = os.path.join(STORAGE_RESULT_IMAGE_FOLDER,  building_id) 
	result_data_building_folder_path   = os.path.join(STORAGE_RESULT_DATA_FOLDER,   building_id) 
	initial_image_time_folder_path     = os.path.join(initial_image_building_folder_path, d) 
	result_image_time_folder_path      = os.path.join(result_image_building_folder_path,  d) 
	result_data_time_folder_path       = os.path.join(result_data_building_folder_path,   d) 
	initial_image_full_path   		   = os.path.join(initial_image_time_folder_path, file_name + "." + extension) 
	result_image_full_path    		   = os.path.join(result_image_time_folder_path,  file_name + "." + extension) 
	result_data_full_path     		   = os.path.join(result_data_time_folder_path,   file_name + ".json") 

	createFoldersIfNotExists([
		initial_image_building_folder_path,
		result_image_building_folder_path, 
		result_data_building_folder_path,
		initial_image_time_folder_path,
		result_image_time_folder_path, 
		result_data_time_folder_path
	])

	# Save original file
	initial_file.save(initial_image_full_path)

	# Make prediction
	img          = Image.open(initial_image_full_path)
	results      = model([img])

	# Box info
	results_data    = results.pandas().xyxy[0]
	predictions_nb  = results_data.shape[0]
	predictions_json = {
		"metadata": {
			"id": id,
			"time": dt.strftime('%d/%m/%Y %H:%M:%S'),
		},
		"predictions": [
			{
				"confidence": float(results_data.confidence[i]),
				"class": {
					"id"  : int(results_data["class"][i]),
					"name": str(results_data.name[i]),
				},
				"box": {
					"xmin": float(results_data.xmin[i]),
					"ymin": float(results_data.ymin[i]),
					"xmax": float(results_data.xmax[i]),
					"ymax": float(results_data.ymax[i]),
				}
			}
			for i in range(predictions_nb)
		]
	}
	
	with open(result_data_full_path, 'w') as f:
		f.write(json.dumps(predictions_json))

	# Image
	result_img   = results.render()[0]
	result_file  = Image.fromarray(result_img)
	result_file.save(result_image_full_path)

	# Return full paths
	return predictions_json

@app.route('/api/analyse/<building_id>')
def apiAnalysisDetection(building_id):

	# Requests
	files = list(request.files.items())
	if len(files) == 0:
		return "No file found..."

	# Upload files
	results = dict()
	for file_name, file_content in files:
		result = uploadReportFiles(building_id, file_content)
		results[file_name] = result

	return results

@app.route('/api/get/<building_id>/<day_string>')
def apiAnalysisDetection(building_id, day_string):

	for f in glob.glob(f"")


@app.route('/')
def home():
	return render_template("pages/home.html")

if __name__ == '__main__':
	
	model = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best.pt"), force_reload=True)
	app.run(debug=True)
