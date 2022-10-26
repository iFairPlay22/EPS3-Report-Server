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
def getAnalysisForPart(building_name : str, day_string : str, row : int, column : int):
		
	analysis_folder_full_path = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string), u.sanitizeFileName(row), u.sanitizeFileName(column))

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

def getAnalysis(building_name : str, day_string : str):
    	
	analysis_results = []

	# Foreach analysis
	main_directory = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name), u.sanitizeFileName(day_string))
	
	for (row_folder_name, row_folder_full_path) in u.subFolders(main_directory):
		for (col_folder_name, col_folder_full_path) in u.subFolders(row_folder_full_path):
			
			# One analysis
			analysis_data = getAnalysisForPart(building_name, day_string, row_folder_name, col_folder_name)
			analysis_results.append(analysis_data)

	# Building issues frequency
	class_name_predictions = [ prediction_data["class"]["name"] for analysis_data in analysis_results for prediction_data in analysis_data["predictions"] ]
	class_name_counter     = Counter(class_name_predictions)
	class_name_frequency   = { class_name : float(iterations / len(class_name_predictions)) for class_name, iterations in class_name_counter.items() }
	
	# Building big image
	column_row_image_list = [
		{
			"column"              : int(analysis_data["metadata"]["column"]),
			"row"                 : int(analysis_data["metadata"]["row"]),
			"original_image_path" : str(analysis_data["original_image"]),
			"result_image_path"   : str(analysis_data["result_image"])
		}
		for analysis_data in analysis_results 
	]
	max_row         = max([ el["row"]    for el in column_row_image_list ]) 
	max_column      = max([ el["column"] for el in column_row_image_list ])
	big_original_image_matrix  = [ [ None for j in range(max_column + 1) ]  for i in range(max_row + 1) ]
	big_result_image_matrix    = [ [ None for j in range(max_column + 1) ]  for i in range(max_row + 1) ]
	for el in column_row_image_list:
		big_original_image_matrix[max_row-el["row"]][el["column"]] = el["original_image_path"]
	for el in column_row_image_list:
		big_result_image_matrix[max_row-el["row"]][el["column"]]   = el["result_image_path"]

	return analysis_results, class_name_frequency, big_original_image_matrix, big_result_image_matrix

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

def makePrediction(initial_image : Image):
    	
    # Make prediction
	results         = model([initial_image])
	results_data    = results.pandas().xyxy[0]
	result_img_arr  = results.render()[0]
	result_image    = Image.fromarray(result_img_arr)

	return results_data, result_image

# Upload the report files in the STORAGE_FOLDER
def uploadReportFiles(data : str, initial_file : Image):

	date_time     = datetime.now()
	date          = u.sanitizeFileName(date_time.strftime('%Y-%m-%d'))
	time          = u.sanitizeFileName(date_time.strftime('%H-%M-%S'))
	building_name = u.sanitizeFileName(data["building_name"])
	row 		  = u.sanitizeFileName(int(data["row"]))
	column 		  = u.sanitizeFileName(int(data["column"]))

	# Folder management
	base_folder_path = os.path.join(STORAGE_FOLDER, building_name, date, row, column) 
	if u.folderExists(base_folder_path):
		raise Exception("Data already exists for the id (building_name, time, row, column)")
	u.createFolderIfNotExists(base_folder_path)

	# Create files
	initial_image_full_path = os.path.join(base_folder_path, STORAGE_INITIAL_IMAGE_FILE_NAME + "." + initial_file.format) 
	result_image_full_path  = os.path.join(base_folder_path,  STORAGE_RESULT_IMAGE_FILE_NAME  + "." + initial_file.format) 
	result_data_full_path   = os.path.join(base_folder_path,   STORAGE_RESULT_DATA_FILE_NAME   + "." + "json") 

	# Save original image
	initial_file.save(initial_image_full_path)

	# Make prediction
	results_data, result_image = makePrediction(initial_file)
	predictions_nb  = results_data.shape[0]
	predictions_json = {
		"metadata": {
			"building_name": str(building_name),
			"day"          : str(date),
			"time"         : str(time),
			"column"       : str(column),
			"row"          : str(row)
		},
		"predictions": [
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
			for i in range(predictions_nb)
		],
		"issues_nb": dict(Counter(results_data.name))
	}
	
	# Save result data
	with open(result_data_full_path, 'w') as f:
		f.write(json.dumps(predictions_json, indent=4))

	# Save result image
	result_image.save(result_image_full_path)

	# Return full paths
	return getAnalysisForPart(building_name, date, row, column)

# Do a building analysis concerning an image
@app.route('/api/upload/from-body/<building_name>', methods=['POST'])
def apiUploadFromBody(building_name : str):

	# Requests
	files = list(request.files.items())
	if len(files) == 0:
		return "No file found..."

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
	result = {}

	for upload_body_name, upload_image_content in files:
		result[upload_body_name] = uploadReportFiles(
			{
				"building_name": str(building_name),
				"row"          : int(request.form["row"]),
				"column"       : int(request.form["column"])
			}, 
			Image.open(upload_image_content.stream)
		) 

	return result

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
	# > each subfolder named "0", "1", "2", "3", ..., "r" corresponds to the row    "0", "1", "2", "3", ..., "r"
	# > each file      named "0", "1", "2", "3", ..., "c" corresponds to the column "0", "1", "2", "3", ..., "c"
	# > ("0", "0") is the bottom left corner of the wall
	# > ("r", "c") is the top right corner of the wall
	result = {}

	row = 0
	for (row_folder_path, row_folder_full_path) in sub_folders:
		column = 0
		for (col_image_path, col_image_full_path) in u.subFiles(row_folder_full_path):
    			
			result[col_image_full_path] = uploadReportFiles(
				{
					"building_name": str(building_name),
					"row"          : row,
					"column"       : column
				}, 
				Image.open(col_image_full_path)
			) 
			column += 1
		row += 1
		

	return result

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

def getReadableDate(storageDate):
    return datetime.strptime(storageDate, '%Y%m%d').date().strftime('%d/%m/%Y')

# Manual prediction view
@app.route('/manual-upload', methods=['GET'])
def manualUpload():
	return render_template("pages/manual_upload.html")


# See the results of a previous analysis
@app.route('/report/<building_name>', methods=['GET'])
def report(building_name : str):
    	
	time_analysis = {}

	building_folder_full_path = os.path.join(STORAGE_FOLDER, u.sanitizeFileName(building_name))
	for (date_file_path, date_file_full_path) in u.subFolders(building_folder_full_path):		
		day_string = date_file_path
		analysis_results, class_name_frequency, big_original_image_matrix, big_result_image_matrix = getAnalysis(building_name, day_string)
		time_analysis[day_string] = {
			"readable_date"				: getReadableDate(day_string),
			"analysis_results"          : analysis_results,
			"class_name_frequency"      : class_name_frequency,
			"big_original_image_matrix" : big_original_image_matrix,
			"big_result_image_matrix"   : big_result_image_matrix,
		}
		
	selected_time = list(time_analysis.keys())[-1]

	return render_template(
		"pages/report.html",
		time_analysis=time_analysis,
		time_chosen=selected_time,
  		building_name=building_name
	)

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
			"link"          : url_for("report", building_name=building_name)
		})

	return render_template(
		"pages/home.html",
		reports=reports
	)
 
@app.route('/api/duplicates/folder', methods=['GET'])
def apiGetDuplicatesOfFolder():
		
	return u.getDuplicatedFilesInFolder(request.form["folder"])

@app.route('/api/duplicates/folders', methods=['GET'])
def apiGetDuplicatesOfFolders():
		
	return u.getFilesInF2ThatAlsoAreInF1(request.form["folder1"], request.form["folder2"])


################################################################################################
#####> LAUNCH SERVER
################################################################################################

if __name__ == '__main__':
	
	model = torch.hub.load('ultralytics/yolov5', 'custom', path=os.path.join(ASSETS_FOLDER, "weights/best.pt")) # , force_reload=True
	app.run(debug=True)
