from flask import Flask, redirect, url_for, request, render_template
from datetime import datetime
import uuid
import glob
import os
from collections import Counter
import io
import json
import torch 
from PIL import Image
import util as u
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

################################################################################################
#####> FOLDER MANAGEMENT
################################################################################################

TEMPLATES_FOLDER                = os.path.join("templates", "html")
ASSETS_FOLDER                   = "assets"
STATIC_FOLDER                   = "static"
STORAGE_FOLDER					= os.path.join(STATIC_FOLDER, "storage")
STORAGE_INITIAL_IMAGE_FILE_NAME = "initial-image"
STORAGE_RESULT_IMAGE_FILE_NAME  = "result-image"
STORAGE_RESULT_DATA_FILE_NAME   = "result-data"

u.createFoldersIfNotExists([
	TEMPLATES_FOLDER, 
	ASSETS_FOLDER,
	STATIC_FOLDER,
	STORAGE_FOLDER
])

################################################################################################
#####> LAUNCH APP
################################################################################################

app = Flask(__name__, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)

################################################################################################
#####> UTIL METHODS
################################################################################################

# Get the report data
def getAnalysis(building_name : str, day_string : str, analysis_id : str):
    	
	analysis_folder_full_path = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string), u.sanitizeFileName(analysis_id))    	
	
	# Result data
	result_data_full_path = os.path.join(analysis_folder_full_path, STORAGE_RESULT_DATA_FILE_NAME + ".json")
	with open(result_data_full_path, "r") as f:
		analysis_data = json.load(f)

	# Original & result images
	for (analysis_file_path, analysis_file_full_path) in u.subFiles(analysis_folder_full_path):		
		if analysis_file_path.startswith(STORAGE_INITIAL_IMAGE_FILE_NAME):
			analysis_data["original_image"] = analysis_file_full_path
				
		if analysis_file_path.startswith(STORAGE_RESULT_IMAGE_FILE_NAME):
			analysis_data["result_image"]  = analysis_file_full_path

	return analysis_data

################################################################################################
#####> DELETE REQUESTS
################################################################################################

# Delete completely the file storage
@app.route('/api/clear', methods=['DELETE'])
def apiClear():
    u.deleteFoldersRecursively(STORAGE_FOLDER)
    u.createFolderIfNotExists(STORAGE_FOLDER)

    return "Cleared"
    	
################################################################################################
#####> POST REQUESTS
################################################################################################

# Upload the report files in the STORAGE_FOLDER
def uploadReportFiles(building_name : str, initial_file : Image):

	date_time     = datetime.now()
	date          = u.sanitizeFileName(date_time.strftime('%Y-%m-%d'))
	time          = u.sanitizeFileName(date_time.strftime('%H-%M-%S'))
	building_name = u.sanitizeFileName(building_name)
	analysis_id   = u.sanitizeFileName(uuid.uuid4())

	# Create folders
	initial_image_time_analysis_folder_path = os.path.join(STORAGE_FOLDER, building_name, date, analysis_id) 
	result_image_time_analysis_folder_path  = os.path.join(STORAGE_FOLDER, building_name, date, analysis_id) 
	result_data_time_analysis_folder_path   = os.path.join(STORAGE_FOLDER, building_name, date, analysis_id) 

	u.createFoldersIfNotExists([
		initial_image_time_analysis_folder_path,
		result_image_time_analysis_folder_path, 
		result_data_time_analysis_folder_path
	])

	# Create files
	initial_image_full_path = os.path.join(initial_image_time_analysis_folder_path, STORAGE_INITIAL_IMAGE_FILE_NAME + "." + initial_file.format) 
	result_image_full_path  = os.path.join(result_image_time_analysis_folder_path,  STORAGE_RESULT_IMAGE_FILE_NAME  + "." + initial_file.format) 
	result_data_full_path   = os.path.join(result_data_time_analysis_folder_path,   STORAGE_RESULT_DATA_FILE_NAME   + "." + "json") 

	# Save original image
	initial_file.save(initial_image_full_path)

	# Make prediction
	results         = model([initial_file])
	results_data    = results.pandas().xyxy[0]
	predictions_nb  = results_data.shape[0]
	predictions_json = {
		"metadata": {
			"building_name": str(building_name),
			"day":           str(date),
			"time":          str(time),
			"analysis_id":   str(analysis_id)
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
	
	# Save result data
	with open(result_data_full_path, 'w') as f:
		f.write(json.dumps(predictions_json, indent=4))

	# Save result image
	result_img   = results.render()[0]
	result_file  = Image.fromarray(result_img)
	result_file.save(result_image_full_path)

	# Return full paths
	return getAnalysis(building_name, date, analysis_id)

# Do a building analysis concerning an image
@app.route('/api/upload/from-body/<building_name>', methods=['POST'])
def apiUploadFromBody(building_name : str):

	# Requests
	files = list(request.files.items())
	if len(files) == 0:
		return "No file found..."

	# Upload files
	return { upload_body_name: uploadReportFiles(building_name, Image.open(upload_image_content.stream)) for upload_body_name, upload_image_content in files }

@app.route('/api/upload/from-storage/<building_name>', methods=['POST'])
def apiUploadFromStorage(building_name : str):

	# Requests

	if not("folder_path" in request.form):
		return "No args folder_path found..."

	folder_path = request.form["folder_path"]
	if not(os.path.isdir(folder_path)):
		return f'"{folder_path}" is not a folder...'

	files = u.subFiles(folder_path)
	if len(files) == 0:
		return "No file found..."

	# Upload files
	return { upload_image_path: uploadReportFiles(building_name, Image.open(upload_image_full_path)) for (upload_image_path, upload_image_full_path) in u.subFiles(folder_path) }	

################################################################################################
#####> GET REQUESTS
################################################################################################

# See the results of a previous analysis
@app.route('/report/<building_name>/<day_string>', methods=['GET'])
def report(building_name : str, day_string : str):

	analysis_results = []

	# Foreach analysis
	main_directory = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string))
	
	for (analysis_folder_name, analysis_folder_full_path) in u.subFolders(main_directory):
			
		# One analysis
		analysis_id = analysis_folder_name
		analysis_data = getAnalysis(building_name, day_string, analysis_id)
		analysis_results.append(analysis_data)

	class_name_predictions = [ prediction_data["class"]["name"] for analysis_data in analysis_results for prediction_data in analysis_data["predictions"] ]
	class_name_counter     = Counter(class_name_predictions)
	class_name_frequency   = { class_name : float(iterations / len(class_name_predictions)) for class_name, iterations in class_name_counter.items() }
	
	return render_template(
		"pages/report.html",
		building=building_name,
		date=day_string,
		analysis=analysis_results,
		class_name_frequency=class_name_frequency
	)

@app.route('/', methods=['GET'])
def home():
    	
	reports = []

	# For each buildings
	main_directory = STORAGE_FOLDER

	for (building_path, building_full_path) in u.subFolders(main_directory):
		building_name = building_path

		# For each dates
		for (date_path, date_full_path) in u.subFolders(building_full_path):
			day_string = date_path

			# Add an entry
			reports.append({
				"building_name" : building_name,
				"date"          : day_string,
				"link"          : url_for("apiReportView", building_name=building_name, day_string=day_string)
			})

	return render_template(
		"pages/home.html",
		reports=reports
	)

################################################################################################
#####> LAUNCH SERVER
################################################################################################

if __name__ == '__main__':
	
	model = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best.pt")) # , force_reload=True
	app.run(debug=True)
