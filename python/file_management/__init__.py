import os
import shutil

class FileManagement:
    
    @staticmethod
    def folderExists(folder):
        return os.path.isdir(folder)

    @staticmethod
    def fileExists(file):
        return os.path.isfile(file)

    @staticmethod
    def subWithPredicate(folder: str, predicate: callable):
        return [ 
            (
                f_name,
                os.path.join(folder, f_name)
            )
            for f_name in sorted(os.listdir(folder))
            if predicate(os.path.join(folder, f_name))
        ]

    @staticmethod
    def subFiles(folder: str):
        return FileManagement.subWithPredicate(folder, lambda full_path: FileManagement.fileExists(full_path))

    @staticmethod
    def subFolders(folder: str):
        return FileManagement.subWithPredicate(folder, lambda full_path: FileManagement.folderExists(full_path))

    @staticmethod
    def createFolderIfNotExists(path):
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def createFoldersIfNotExists(paths):
        for path in paths:
            FileManagement.createFolderIfNotExists(path)

    def deleteFoldersRecursively(folder):
        if FileManagement.folderExists(folder):
            shutil.rmtree(folder)

    def copyPasteFolder(src_dir, dest_dir):
        if FileManagement.folderExists(src_dir):
            shutil.copytree(src_dir, dest_dir)

    def deleteFile(file_full_path):
        if FileManagement.fileExists(file_full_path):
            os.remove(file_full_path) 

    @staticmethod
    def deleteFiles(file_full_paths):
        for file_full_path in file_full_paths:
            FileManagement.deleteFile(file_full_path) 

    @staticmethod
    def sanitizeFileName(string: str):
        # Remove non alpha numeric characters
        return "".join(char for char in str(string) if char.isalnum())