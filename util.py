from genericpath import isfile
import os
import shutil
from difPy import dif

def subWithPredicate(folder: str, predicate: callable):
    return [ 
		(
			f_name,
			os.path.join(folder, f_name)
		)
		for f_name in sorted(os.listdir(folder))
		if predicate(os.path.join(folder, f_name))
	]

def subFiles(folder: str):
    return subWithPredicate(folder, lambda full_path: os.path.isfile(full_path))

def subFolders(folder: str):
    return subWithPredicate(folder, lambda full_path: os.path.isdir(full_path))

def createFolderIfNotExists(path):
	if not os.path.exists(path):
		os.makedirs(path)

def createFoldersIfNotExists(paths):
	for path in paths:
		createFolderIfNotExists(path)

def deleteFoldersRecursively(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder)

def copyPasteFolder(src_dir, dest_dir):
    if os.path.isdir(src_dir):
        shutil.copytree(src_dir, dest_dir)

def deleteFile(file_full_path):
    if os.path.isfile(file_full_path):
        os.remove(file_full_path) 

def deleteFiles(file_full_paths):
    for file_full_path in file_full_paths:
        deleteFile(file_full_path) 

def getDuplicatedFilesInFolder(folder):
    	
	duplicate_file_full_paths = []
    	
	all_duplications = dif(folder).result
	for duplication in all_duplications.values():
		for duplicate_file_full_path in duplication["duplicates"]:
			duplicate_file_full_paths.append(duplicate_file_full_path)

	return duplicate_file_full_paths

def getFilesInF2ThatAlsoAreInF1(folder1, folder2):

	f2_duplicates_files_full_path = []
	all_duplications = dif(folder1, folder2).result
	
	for duplication in all_duplications.values():
		duplicates = duplication["duplicates"] + [duplication["location"]]
		for file_full_path in duplicates:
			if file_full_path.startswith(folder2):
				f2_duplicates_files_full_path.append(file_full_path)

	return f2_duplicates_files_full_path
	
# Delete non alpha numeric characters in a string
def sanitizeFileName(string: str):
	return "".join(char for char in str(string) if char.isalnum())