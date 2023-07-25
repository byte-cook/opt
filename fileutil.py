#!/usr/bin/env python3

import os
import stat
import shutil
import tarfile
import zipfile
import logging

###################################################
## chmod
## https://www.tutorialspoint.com/python/os_chmod.htm
###################################################

def chmod_add(file, stat):
    fileStat = os.stat(file)
    os.chmod(file, fileStat.st_mode | stat)

def chmod_remove(file, stat):
    fileStat = os.stat(file)
    os.chmod(file, fileStat.st_mode & ~stat)

###################################################
## copy
###################################################

def copyFileOrFolder(file, targetDir):
    """Copy file/folder to targetDir and create targetDir if needed."""
    logging.debug(f'Copy {file} to {targetDir}')
    os.makedirs(targetDir, exist_ok=True)
    if os.path.isdir(file):
        shutil.copytree(file, targetDir, dirs_exist_ok=True)
    else:
        shutil.copy2(file, targetDir)

def getAllSubFiles(dir):
    files = []
    for (root, dirnames, filenames) in os.walk(dir):
        files.extend(filenames)
    return files

def skipContainerDirs(dir):
    """Return dir without single folders."""
    resultDir = dir
    files = os.listdir(resultDir)
    while len(files) == 1:
        fileOrDir = os.path.join(resultDir, files[0])
        if not os.path.isdir(fileOrDir):
            break
        # skip single container dirs
        resultDir = fileOrDir
        files = os.listdir(resultDir)
    return resultDir

###################################################
## archives
###################################################

def isArchiveFile(file):
    """Indicate if file in an archive."""
    return file.endswith('.zip') or file.endswith('.tar.bz2') or file.endswith(".tar") or file.endswith(".tar.gz") or file.endswith(".tgz") or file.endswith(".tar.xz")

def getArchiveFiles(file):
    """Return files in archive or empty list if file is no archive."""
    if file.endswith('.zip'):
        with zipfile.ZipFile(file) as zip:
            return zip.namelist()
    elif file.endswith('.tar.bz2') or file.endswith(".tar") or file.endswith(".tar.gz") or file.endswith(".tgz") or file.endswith(".tar.xz"):
        with tarfile.open(file, 'r') as tar:
            return tar.getnames()
    return []

def extractArchive(file, targetDir):
    """Copy file to dir or extract the file if it is an archive."""
    if file.endswith('.zip'):
        with zipfile.ZipFile(file) as zip:
            zip.extractall(targetDir)
    elif file.endswith('.tar.bz2') or file.endswith(".tar") or file.endswith(".tar.gz") or file.endswith(".tgz") or file.endswith(".tar.xz"):
        with tarfile.open(file, 'r') as tar:
            tar.extractall(targetDir)

###################################################
## chown
###################################################

def chown_recursively(dir, uid=0, gid=0, follow_symlinks=False):
    """Set owner of complete dir to the given value."""
    # Change permissions for the top-level folder
    #os.chmod(path, 502, 20)
    os.chown(dir, uid, gid, follow_symlinks)

    for root, dirs, files in os.walk(path):
      for dir in dirs:
        os.chown(os.path.join(root, dir), uid, gid, follow_symlinks)
      for file in files:
        os.chown(os.path.join(root, file), uid, gid, follow_symlinks)

