from flask import Flask, redirect, url_for, request, render_template, send_file
from datetime import datetime
import io
import os
from collections import Counter
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

STORAGE_NORMAL_INITIAL_IMAGE_FILE_NAME = "normal-initial-image"
STORAGE_NORMAL_RESULT_IMAGE_FILE_NAME  = "normal-result-image"
STORAGE_THERMAL_INITIAL_IMAGE_FILE_NAME = "thermal-initial-image"
STORAGE_THERMAL_RESULT_IMAGE_FILE_NAME  = "thermal-result-image"
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
normal_model  = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best_normal.pt" )) # , force_reload=True
thermal_model = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best_thermal.pt")) # , force_reload=True
	

################################################################################################
#####> UTIL METHODS
################################################################################################

# Make a prediction of an image thanks to a model
def makePrediction(model, img : Image):
    	
    # Make prediction
	results         = model([img])
	results_data    = results.pandas().xyxy[0]
	result_img_arr  = results.render()[0]
	result_image    = Image.fromarray(result_img_arr)

	# Json
	result_predictions = [
		{
			"confidence": round(float(results_data.confidence[i]) * 100),
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
		for i in range(results_data.shape[0])
	]

	return result_image, result_predictions

# Upload the report files in the STORAGE_FOLDER
def uploadReportFiles(data : dict, initial_normal_file : Image, initial_thermal_file : Image):

	date_time             = datetime.now()
	data["date"]          = u.sanitizeFileName(date_time.strftime('%Y-%m-%d'))
	data["time"]          = u.sanitizeFileName(date_time.strftime('%H-%M-%S'))
	data["building_name"] = u.sanitizeFileName(data["building_name"])
	data["row"] 		  = u.sanitizeFileName(int(data["row"]))
	data["column"] 		  = u.sanitizeFileName(int(data["column"]))

	# Base folder
	base_folder_path = os.path.join(STORAGE_FOLDER, data["building_name"], data["date"], data["row"], data["column"]) 
	if u.folderExists(base_folder_path):
		raise Exception("Data already exists for the id (building_name, time, row, column)")
	u.createFolderIfNotExists(base_folder_path)

	# File names
	normal_initial_image_full_path  = os.path.join(base_folder_path, STORAGE_NORMAL_INITIAL_IMAGE_FILE_NAME + "." + initial_normal_file.format) 
	normal_result_image_full_path   = os.path.join(base_folder_path, STORAGE_NORMAL_RESULT_IMAGE_FILE_NAME  + "." + initial_normal_file.format)
	thermal_initial_image_full_path = os.path.join(base_folder_path, STORAGE_THERMAL_INITIAL_IMAGE_FILE_NAME + "." + initial_thermal_file.format)
	thermal_result_image_full_path  = os.path.join(base_folder_path, STORAGE_THERMAL_RESULT_IMAGE_FILE_NAME  + "." + initial_thermal_file.format)
	result_data_full_path                  = os.path.join(base_folder_path, STORAGE_RESULT_DATA_FILE_NAME   + "." + "json")
	
	# Save original images
	initial_normal_file.save(normal_initial_image_full_path)
	initial_thermal_file.save(thermal_initial_image_full_path)

	# Make prediction
	normal_result_image,  normal_predictions  = makePrediction(normal_model,  initial_normal_file)
	thermal_result_image, thermal_predictions = makePrediction(thermal_model, initial_thermal_file)
	
	# Merge predictions for json
	all_predictions = normal_predictions + thermal_predictions
	all_predictions_class_name = map(lambda pred: pred["class"]["name"], all_predictions)
	result_json = {
		"metadata": {
			"building_name": str(data["building_name"]),
			"day"          : str(data["date"]),
			"time"         : str(data["time"]),
			"column"       : str(data["column"]),
			"row"          : str(data["row"])
		},
		"images": {
			"normal": {
				"initial": normal_initial_image_full_path,
				"result" : normal_result_image_full_path
			},
			"thermal": {
				"initial": thermal_initial_image_full_path,
				"result" : thermal_result_image_full_path
			}
		},
		"predictions": all_predictions,
		"issues_nb": dict(Counter(all_predictions_class_name))
	}

	# Save result images
	normal_result_image.save(normal_result_image_full_path)
	thermal_result_image.save(thermal_result_image_full_path)

	# Save result data
	with open(result_data_full_path, 'w') as f:
		f.write(json.dumps(result_json, indent=4))

	# Return full paths
	return getPartialAnalysis(data["building_name"], data["date"], data["row"], data["column"])

# Get the report data for a wall cell of a building at a time
def getPartialAnalysis(building_name : str, day_string : str, row : int, column : int):
		
	# Get JSON data
	analysis_json = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string), u.sanitizeFileName(row), u.sanitizeFileName(column), STORAGE_RESULT_DATA_FILE_NAME + ".json")
	with open(analysis_json, "r") as f:
		analysis_data = json.load(f)

	return analysis_data

# Get the report data for a building at a time
def getCompleteAnalysis(building_name : str, day_string : str):

	result = {}

	# All analysis results
	analysis_results = []
	main_directory = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string))
	for (row_folder_name, row_folder_full_path) in u.subFolders(main_directory):
		for (col_folder_name, col_folder_full_path) in u.subFolders(row_folder_full_path):
			# An analysis result
			analysis_results.append(getPartialAnalysis(building_name, day_string, row_folder_name, col_folder_name))
	result["analysis_results"] = analysis_results

	# Building issues counter
	class_name_predictions = [ prediction_data["class"]["name"] for analysis_data in analysis_results for prediction_data in analysis_data["predictions"] ]
	class_name_counter     = Counter(class_name_predictions)
	result["class_name_count"] = class_name_counter
	
	# Building big image
	max_column      = max([ int(analysis_data["metadata"]["column"]) for analysis_data in analysis_results  ])
	max_row         = max([ int(analysis_data["metadata"]["row"])    for analysis_data in analysis_results  ])
	big_original_image_matrix  = [ [ None for j in range(max_column + 1) ]  for i in range(max_row + 1) ]
	for analysis_data in analysis_results:
		col = int(analysis_data["metadata"]["column"])
		row = int(analysis_data["metadata"]["row"])

		big_original_image_matrix[max_row-row][col] = {
			"normal_initial_image_path"  : str(analysis_data["images"]["normal"]["initial"]),
			"normal_result_image_path"   : str(analysis_data["images"]["normal"]["result"]),
			"thermal_initial_image_path" : str(analysis_data["images"]["thermal"]["initial"]),
			"thermal_result_image_path"  : str(analysis_data["images"]["thermal"]["result"]),
		}
	result["big_original_image_matrix"] = big_original_image_matrix

	return result

# Get all the analysis dates of a bulding 
def getAllAnalysisDatesOfBuilding(building_name : str):
    return [ 
		{
			"human"    : getReadableDate(date_file_path),
			"program" : date_file_path
		}
		for (date_file_path, date_file_full_path) 
		in u.subFolders(os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name)))
	]

# Get a readable data from the storage date
def getReadableDate(storageDate : str):
    return datetime.strptime(storageDate, '%Y%m%d').date().strftime('%d/%m/%Y')

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

# Upload images from HTTP
@app.route('/api/upload/from-body/<building_name>', methods=['POST'])
def apiUploadFromBody(building_name : str):

	# Requests
	if not("normal-image" in request.files):
		return 'No normal image file found... Missing parameter "normal-image"'

	if not("thermal-image" in request.files):
		return 'No thermal image file found... Missing parameter "thermal-image"'

	if not("row" in request.form):
		return 'Missing parameter "row"'

	if not("column" in request.form):
		return 'Missing parameter "column"'

	# Result
	# We assume that:
	# > each "row"     match the serie "0", "1", "2", "3", ..., "r"
	# > each "column"  match the serie "0", "1", "2", "3", ..., "r"
	# > ("0", "0") is the bottom left corner of the wall
	# > ("r", "c") is the top right corner of the wall
	return uploadReportFiles(
		{
			"building_name": str(building_name),
			"row"          : int(request.form["row"]),
			"column"       : int(request.form["column"])
		}, 
		Image.open(request.files["normal-image"].stream), 
		Image.open(request.files["thermal-image"].stream)
	) 

# Upload images from FILE STORAGE
@app.route('/api/upload/from-storage/<building_name>', methods=['POST'])
def apiUploadFromStorage(building_name : str):

	# Requests
	if not("folder_path" in request.form):
		return "No args folder_path found..."

	folder_path = request.form["folder_path"]
	if not(os.path.isdir(folder_path)):
		return f'"{folder_path}" is not a folder...'

	sub_folders = u.subFolders(folder_path)
	if len(sub_folders) == 0:
		return "No file found..."

	# Result
	# We assume that:
	# > each subfolder(1) named "0", "1", "2", "3", ..., "r" corresponds to the row    "0", "1", "2", "3", ..., "r"
	# > each subfolder(2) named "0", "1", "2", "3", ..., "c" corresponds to the column "0", "1", "2", "3", ..., "c"
	# > /(1)/(2)/normal.*  corresponds to the image taken with a normal camera 
	# > /(1)/(2)/thermal.* corresponds to the image taken with a thermal camera
	# > ("0", "0") is the bottom left corner of the wall
	# > ("r", "c") is the top right corner of the wall
	result = {}

	row = 0
	for (row_folder_path, row_folder_full_path) in sub_folders:
		
		column = 0
		for (col_folder_path, col_folder_full_path) in u.subFolders(row_folder_full_path):
    			
			thermalImage = None
			normalImage  = None
			for (col_image_path, col_image_full_path) in u.subFiles(col_folder_full_path):
				if (col_image_path.startswith("normal")):
					normalImage = col_image_full_path
				if (col_image_path.startswith("thermal")):
					thermalImage = col_image_full_path

			if normalImage is None:
				raise Exception('Missing normal image named "normal.*" in folder ' + col_folder_full_path);

			if thermalImage is None:
				raise Exception('Missing thermal image named "thermal.*" in folder ' + col_folder_full_path);

			result[col_image_full_path] = uploadReportFiles(
				{
					"building_name": str(building_name),
					"row"          : row,
					"column"       : column
				}, 
				Image.open(normalImage),
				Image.open(thermalImage),
			)
		
			column += 1
		row += 1
		
	return result

# TODO
# See the result image of a manual prediction
@app.route('/api/manual-prediction', methods=['POST'])
def manualPrediction():

	# Requests
	if not("file" in request.files):
		return 'No file "file" found...'
    
	results_data, result_image = makePrediction(Image.open(request.files["file"].stream))

	img_io = io.BytesIO()
	result_image.save(img_io, 'JPEG', quality=70)
	img_io.seek(0)
	return send_file(img_io, mimetype='image/jpeg')

################################################################################################
#####> GET REQUESTS
################################################################################################

# TODO
# Manual prediction view
@app.route('/manual-upload', methods=['GET'])
def manualUpload():
	return render_template("pages/manual_upload.html")

# Historic report (historic evolution of a wall cell)
@app.route('/historic-report/<building_name>/<row>/<column>', methods=['GET'])
def historic_report(building_name : str, row : int, column : int):
    	
	day_analysis = {}
	day_predictions_count = []

	building_folder_full_path = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name))
	for (date_file_path, date_file_full_path) in u.subFolders(building_folder_full_path):		
		day_string = date_file_path
		analysis = getPartialAnalysis(building_name, day_string, row, column);
		day_analysis[getReadableDate(day_string)] = analysis

		predictions_count = dict(Counter([ prediction["class"]["name"] for prediction in analysis["predictions"] ]))
		predictions_count["date"] = getReadableDate(day_string)
		day_predictions_count.append(predictions_count)
	
	return render_template("part/historic_report.html", day_analysis=day_analysis, day_predictions_count=day_predictions_count)

# Report page (report of a wall)
@app.route('/report/<building_name>/<day_string>', methods=['GET'])
def report(building_name : str, day_string : str = "_"):
    	
	analysis_dates = getAllAnalysisDatesOfBuilding(building_name)

	# Last report date by default
	if day_string == "_":
		day_string = analysis_dates[-1]["program"]

	analysis = getCompleteAnalysis(building_name, day_string)
		
	return render_template(
		"pages/report.html",
  		building_name=building_name,
		analysis_date=day_string,
		analysis_dates=analysis_dates,
		analysis=analysis
	)

# Home page (company info + all reports links)
@app.route('/', methods=['GET'])
def home():
		
	reports = []

	# For each buildings
	main_directory = STORAGE_FOLDER
	for (building_path, building_full_path) in u.subFolders(main_directory):
		building_name = building_path

		# Add an entry
		reports.append({
			"building_name" : building_name,
			"link"          : url_for("report", building_name=building_name, day_string="_")
		})

	return render_template(
		"pages/home.html",
		reports=reports
	)

################################################################################################
#####> LAUNCH SERVER
################################################################################################

if __name__ == '__main__':
	app.run(debug=True)
