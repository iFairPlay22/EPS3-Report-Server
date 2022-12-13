from flask import Flask, url_for, request, render_template
from python.structural_issues import StructuralIssuesDetector
from python.thermal_issues import ThermalIssuesDetector, RgbImage
from python.file_management import FileManagement
from PIL import Image
from datetime import datetime
from tqdm import tqdm
import os
from collections import Counter
import json
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

################################################################################################
#####> GLOBAL VARIABLES
################################################################################################

# Folders
TEMPLATES_FOLDER                		= os.path.join("templates", "html")
STATIC_FOLDER                   		= "static"
ASSETS_FOLDER                   		= "assets"
STORAGE_FOLDER							= os.path.join(STATIC_FOLDER, "storage")

# Files
STORAGE_NORMAL_INITIAL_IMAGE_FILE_NAME 	= "normal-initial-image"
STORAGE_NORMAL_RESULT_IMAGE_FILE_NAME  	= "normal-result-image"
STORAGE_THERMAL_INITIAL_IMAGE_FILE_NAME = "thermal-initial-image"
STORAGE_THERMAL_RESULT_IMAGE_FILE_NAME  = "thermal-result-image"
STORAGE_RESULT_DATA_FILE_NAME   		= "result-data"

# Structural issues detector
STRUCTURAL_ISSUES_MODEL_WEIGHTS_PATH 	= os.path.join(ASSETS_FOLDER, "weights/best_weights.pt")
STRUCTURAL_ISSUES_DETECTOR  			= StructuralIssuesDetector(STRUCTURAL_ISSUES_MODEL_WEIGHTS_PATH)

# initial_img, result_image, result_predictions = STRUCTURAL_ISSUES_DETECTOR.detectFromImage(Image.open("_.jpeg"))
# initial_img.show()
# exit()


# Thermal issues detector
THERMAL_ISSUES_DETECTOR					= ThermalIssuesDetector()

# Launch app
FileManagement.createFoldersIfNotExists([ TEMPLATES_FOLDER, STATIC_FOLDER, ASSETS_FOLDER, STORAGE_FOLDER ])
app = Flask(__name__, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)

################################################################################################
#####> UTIL METHODS
################################################################################################

# Upload the report files in the STORAGE_FOLDER
def uploadReportFiles(data : dict, normal_arr : list, thermal_arr : list):

	# Sanitize data
	date_time             = datetime.now()
	data["date"]          = FileManagement.sanitizeFileName(date_time.strftime('%Y-%m-%d'))
	data["time"]          = FileManagement.sanitizeFileName(date_time.strftime('%H-%M-%S'))
	data["building_name"] = FileManagement.sanitizeFileName(data["building_name"])
	data["row"] 		  = FileManagement.sanitizeFileName(int(data["row"]))
	data["column"] 		  = FileManagement.sanitizeFileName(int(data["column"]))

	# Create base folder
	base_folder_path = os.path.join(STORAGE_FOLDER, data["building_name"], data["date"], data["row"], data["column"]) 
	if FileManagement.folderExists(base_folder_path):
		raise Exception("Data already exists for the id (building_name, time, row, column)")
	FileManagement.createFolderIfNotExists(base_folder_path)

	# Create paths
	normal_initial_image_full_path  = os.path.join(base_folder_path, STORAGE_NORMAL_INITIAL_IMAGE_FILE_NAME  + ".png") 
	normal_result_image_full_path   = os.path.join(base_folder_path, STORAGE_NORMAL_RESULT_IMAGE_FILE_NAME   + ".png")
	thermal_initial_image_full_path = os.path.join(base_folder_path, STORAGE_THERMAL_INITIAL_IMAGE_FILE_NAME + ".png")
	thermal_result_image_full_path  = os.path.join(base_folder_path, STORAGE_THERMAL_RESULT_IMAGE_FILE_NAME  + ".png")
	result_data_full_path           = os.path.join(base_folder_path, STORAGE_RESULT_DATA_FILE_NAME   + "." + "json")
	
	# Make detections
	normal_initial_img, normal_result_image, normal_result_predictions = STRUCTURAL_ISSUES_DETECTOR.detectFromArray(normal_arr)
	thermal_initial_img, thermal_result_image, thermal_result_predictions = THERMAL_ISSUES_DETECTOR.detectFromArray(thermal_arr)

	# Save result images
	normal_initial_img.save(normal_initial_image_full_path)
	thermal_initial_img.save(thermal_initial_image_full_path)
	normal_result_image.save(normal_result_image_full_path)
	thermal_result_image.save(thermal_result_image_full_path)

	# Merge predictions for json
	all_predictions = normal_result_predictions + thermal_result_predictions
	all_predictions_class_name = map(lambda pred: pred["class"], all_predictions)
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

	# Save result data
	with open(result_data_full_path, 'w') as f:
		f.write(json.dumps(result_json, indent=4))

	# Return full paths
	return getPartialAnalysis(data["building_name"], data["date"], data["row"], data["column"])

# Get the report data for a wall cell of a building at a time
def getPartialAnalysis(building_name : str, day_string : str, row : int, column : int):
		
	# Get JSON data
	analysis_json = os.path.join(STORAGE_FOLDER, FileManagement.sanitizeFileName(building_name), FileManagement.sanitizeFileName(day_string), FileManagement.sanitizeFileName(row), FileManagement.sanitizeFileName(column), STORAGE_RESULT_DATA_FILE_NAME + ".json")
	with open(analysis_json, "r") as f:
		analysis_data = json.load(f)

	return analysis_data

# Get the report data for a building at a time
def getCompleteAnalysis(building_name : str, day_string : str):

	result = {}

	# All analysis results
	analysis_results = []
	main_directory = os.path.join(STORAGE_FOLDER, FileManagement.sanitizeFileName(building_name), FileManagement.sanitizeFileName(day_string))
	for (row_folder_name, row_folder_full_path) in FileManagement.subFolders(main_directory):
		for (col_folder_name, col_folder_full_path) in FileManagement.subFolders(row_folder_full_path):
			# An analysis result
			analysis_results.append(getPartialAnalysis(building_name, day_string, row_folder_name, col_folder_name))
	result["analysis_results"] = analysis_results

	# Building issues counter
	class_name_predictions = [ prediction_data["class"] for analysis_data in analysis_results for prediction_data in analysis_data["predictions"] ]
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
		in FileManagement.subFolders(os.path.join(STORAGE_FOLDER, FileManagement.sanitizeFileName(building_name)))
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
	FileManagement.deleteFoldersRecursively(STORAGE_FOLDER)
	FileManagement.createFolderIfNotExists(STORAGE_FOLDER)

	return "Cleared"
		
################################################################################################
#####> POST REQUESTS
################################################################################################

# Upload images
@app.route('/api/upload', methods=['POST'])
def apiUpload():
    
	json_data = request.json
	building_name = json_data["building_name"]
	images = json_data["images"]
 
	for image_data in images:
     
		row, col, normal_arr, thermal_arr = image_data["row"], image_data["col"], image_data["normal_array"], image_data["thermal_array"]
     
		uploadReportFiles(
			{
				"building_name": building_name,
				"row"          : row,
				"column"       : col
			}, 
			normal_arr,
			thermal_arr
		)

	# TODO: return the link		
	return ""

################################################################################################
#####> GET REQUESTS
################################################################################################

# Historic report (historic evolution of a wall cell)
@app.route('/historic-report/<building_name>/<row>/<column>', methods=['GET'])
def historic_report(building_name : str, row : int, column : int):
    
	day_analysis = {}
	day_predictions_count = []

	building_folder_full_path = os.path.join(STORAGE_FOLDER, FileManagement.sanitizeFileName(building_name))
	for (date_file_path, date_file_full_path) in FileManagement.subFolders(building_folder_full_path):		
		day_string = date_file_path
		analysis = getPartialAnalysis(building_name, day_string, row, column)
		day_analysis[getReadableDate(day_string)] = analysis

		predictions_count = dict(Counter([ prediction["class"] for prediction in analysis["predictions"] ]))
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
	for (building_path, building_full_path) in FileManagement.subFolders(main_directory):
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

# Test structural defects AI
@app.route('/test/structural_defects', methods=['GET'])
def test_structural_defects_ai():

	search_folder = "/Users/ewenbouquet/Downloads/initial"
	insert_folder = "/Users/ewenbouquet/Downloads/result"
 
	FileManagement.createFoldersIfNotExists([search_folder, insert_folder])

	for (file_name, file_full_path) in tqdm(FileManagement.subFiles(search_folder)):
		img = Image.open(file_full_path)
		init_img, result_img, result_arr = STRUCTURAL_ISSUES_DETECTOR.detectFromImage(img)
		result_img.save(os.path.join(insert_folder, file_name))
  
	return "Done"
  
  
################################################################################################
#####> LAUNCH SERVER
################################################################################################

if __name__ == '__main__':
	app.run(debug=True)
