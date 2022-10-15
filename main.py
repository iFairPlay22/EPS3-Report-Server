from flask import Flask, redirect, url_for, request, render_template
from datetime import datetime
import uuid
import glob
import os
import shutil
import io
import json
import torch 
from PIL import Image
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

TEMPLATES_FOLDER                = os.path.join("templates", "html")
ASSETS_FOLDER                   = "assets"
STORAGE_FOLDER                  = "storage"
STORAGE_INITIAL_IMAGE_FILE_NAME = "initial-image"
STORAGE_RESULT_IMAGE_FILE_NAME  = "result-image"
STORAGE_RESULT_DATA_FILE_NAME   = "result-data"

def createFolderIfNotExists(path):
	if not os.path.exists(path):
		os.makedirs(path)

def createFoldersIfNotExists(paths):
	for path in paths:
		createFolderIfNotExists(path)

createFoldersIfNotExists([
	STORAGE_FOLDER,
	TEMPLATES_FOLDER, 
	ASSETS_FOLDER
])

app = Flask(__name__, template_folder=TEMPLATES_FOLDER)

def sanitizeFileName(string: str):
	return "".join(char for char in str(string) if char.isalnum())

# Upload the report files in the STORAGE_FOLDER
# Paths:
# 	> "STORAGE_INITIAL_IMAGE_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.EXTENSION"	
# 	> "STORAGE_RESULT_IMAGE_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.EXTENSION"
# 	> "STORAGE_RESULT_DATA_FOLDER/YEARy-MONTHm-DAYd/YEARy-MONTHm-DAYd-HOURh-MINUTEm-SECONDs-ID.json"
def uploadReportFiles(building_id : str, initial_file):

	date_time   = datetime.now()
	date        = sanitizeFileName(date_time.strftime('%Y-%m-%d'))
	time        = sanitizeFileName(date_time.strftime('%H-%M-%S'))
	building_id = sanitizeFileName(building_id)
	analysis_id = sanitizeFileName(uuid.uuid4())

	# File structure
	extension = initial_file.filename.split(".")[-1]

	initial_image_time_analysis_folder_path     = os.path.join(STORAGE_FOLDER, building_id, date, analysis_id) 
	result_image_time_analysis_folder_path      = os.path.join(STORAGE_FOLDER, building_id, date, analysis_id) 
	result_data_time_analysis_folder_path       = os.path.join(STORAGE_FOLDER, building_id, date, analysis_id) 
	initial_image_full_path   		   = os.path.join(initial_image_time_analysis_folder_path, STORAGE_INITIAL_IMAGE_FILE_NAME + "." + extension) 
	result_image_full_path    		   = os.path.join(result_image_time_analysis_folder_path,  STORAGE_RESULT_IMAGE_FILE_NAME  + "." + extension) 
	result_data_full_path     		   = os.path.join(result_data_time_analysis_folder_path,   STORAGE_RESULT_DATA_FILE_NAME   + "." + "json") 

	createFoldersIfNotExists([
		initial_image_time_analysis_folder_path,
		result_image_time_analysis_folder_path, 
		result_data_time_analysis_folder_path
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
			"building_id": str(building_id),
			"day":         str(date),
			"time":        str(time),
			"analysis_id": str(analysis_id)
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
		f.write(json.dumps(predictions_json, indent=4))

	# Image
	result_img   = results.render()[0]
	result_file  = Image.fromarray(result_img)
	result_file.save(result_image_full_path)

	# Return full paths
	return getAnalysis(building_id, date, analysis_id)

def getAnalysis(building_id, day_string, analysis_id):
    	
	analysis_folder_full_path = os.path.join(STORAGE_FOLDER, sanitizeFileName(building_id), sanitizeFileName(day_string), sanitizeFileName(analysis_id))    	
	
	# Result data
	result_data_full_path = os.path.join(analysis_folder_full_path, STORAGE_RESULT_DATA_FILE_NAME + ".json")
	with open(result_data_full_path, "r") as f:
		analysys_data = json.load(f)

	# Images
	for analysis_file_path in os.listdir(analysis_folder_full_path):
		analysis_file_full_path = os.path.join(analysis_folder_full_path, analysis_file_path)
		if os.path.isfile(analysis_file_full_path):
			
			if analysis_file_path.startswith(STORAGE_INITIAL_IMAGE_FILE_NAME):
				analysys_data[STORAGE_INITIAL_IMAGE_FILE_NAME] = analysis_file_full_path
					
			if analysis_file_path.startswith(STORAGE_RESULT_IMAGE_FILE_NAME):
				analysys_data[STORAGE_RESULT_IMAGE_FILE_NAME]  = analysis_file_full_path

	return analysys_data

@app.route('/api/analyse/<building_id>')
def apiAnalyse(building_id : str):

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

@app.route('/api/view/<building_id>/<day_string>')
def apiView(building_id : str, day_string : str):

	analysis_results = []

	# Foreach analysis
	main_directory = os.path.join(STORAGE_FOLDER, sanitizeFileName(building_id), sanitizeFileName(day_string))
	for analysis_folder_path in os.listdir(main_directory):
		analysis_folder_full_path = os.path.join(main_directory, analysis_folder_path)
		if os.path.isdir(analysis_folder_full_path):
			
			# One analysis
			analysis_id = analysis_folder_path
			analysys_data = getAnalysis(building_id, day_string, analysis_id)
			analysis_results.append(analysys_data)
						
	return analysis_results

@app.route('/api/clear')
def apiClear():
    shutil.rmtree(STORAGE_FOLDER)
    createFolderIfNotExists(STORAGE_FOLDER)

    return "Done"

@app.route('/')
def home():
	return render_template("pages/home.html")

if __name__ == '__main__':
	
	model = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best.pt")) # , force_reload=True
	app.run(debug=True)
