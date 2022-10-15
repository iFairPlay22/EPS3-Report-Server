import os
import shutil

def subWithPredicate(folder: str, predicate: callable):
    return [ 
		(
			f_name,
			os.path.join(folder, f_name)
		)
		for f_name in os.listdir(folder)
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

# Delete non alpha numeric characters in a string
def sanitizeFileName(string: str):
	return "".join(char for char in str(string) if char.isalnum())