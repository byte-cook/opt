#!/usr/bin/env python3

import unittest
import os
import sys
import shutil
#from pathlib import Path

# import from parent dir
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(PROJECT_DIR))
import opt
APP_NAME = 'app-v1'
ROOT_DIR = os.path.join(PROJECT_DIR, 'root')

# Usage:
# > test_opt.py
# > test_opt.py TestOpt.test_remove_unmanaged_forced

# TODOs
# set owner wenn nötig

class TestOpt(unittest.TestCase):
    def setUp(self):
        os.makedirs(ROOT_DIR, exist_ok=True)
        shutil.rmtree(ROOT_DIR)
        
        opt.OPT_DIR = os.path.abspath(os.path.join(ROOT_DIR, 'opt'))
        opt.BIN_DIR = os.path.abspath(os.path.join(ROOT_DIR, 'usr-local-bin'))
        opt.DESKTOP_DIR = os.path.join(ROOT_DIR, 'usr-share-applications')
        opt.ICON_DIR = os.path.join(ROOT_DIR, 'usr-share-piximage')
        opt.INSTALL_DIR = os.path.join(opt.OPT_DIR, '.installer')
        os.makedirs(opt.OPT_DIR, exist_ok=True)
        os.makedirs(opt.BIN_DIR, exist_ok=True)
        os.makedirs(opt.DESKTOP_DIR, exist_ok=True)
        os.makedirs(opt.ICON_DIR, exist_ok=True)
    
    def tearDown(self):
        #shutil.rmtree(ROOT_DIR)
        pass

    def test_install_tar(self):
        print('+++++++++++ TEST INSTALL TAR')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_zip(self):
        print('+++++++++++ TEST INSTALL ZIP')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.zip'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_bz2(self):
        print('+++++++++++ TEST INSTALL TAR BZ2')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.bz2'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_gz(self):
        print('+++++++++++ TEST INSTALL TAR GZ')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.gz'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_xz(self):
        print('+++++++++++ TEST INSTALL TAR xz')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.xz'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_zip_with_folder(self):
        print('+++++++++++ TEST INSTALL ZIP')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_folder1_test_file1.zip'), ['test_file1.txt'], skipFolder='folder1')
    def test_install_twice(self):
        print('++++++++++ TEST INSTALL TWICE ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'), ['test_file1.txt'])
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file1.txt'])
    def test_install_wrong_file(self):
        print('++++++++++ TEST INSTALL WRONG FILE ++++++++++')
        opt.main(['--debug', '-y', 'install', APP_NAME, 'resources/__not_exists1__.txt', 'resources/__not_exists2__.txt'])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
    def test_install_unmanaged(self):
        print('++++++++++ TEST INSTALL UNMANAGED ++++++++++')
        os.makedirs(os.path.join(opt.OPT_DIR, APP_NAME), exist_ok=True)
        opt.main(['--debug', '-y', 'install', APP_NAME, 'resources/test_file1.txt'])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
    def test_install_folder(self):
        print('++++++++++ TEST INSTALL FOLDER ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources'), ['test_file1.txt', 'test_folder1_test_file1.zip'])

    def test_update(self):
        print('++++++++++ TEST update ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'), ['test_file1.txt'])
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file2.txt'], update=True)
    
    def test_path(self):
        print('++++++++++ TEST PATH ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._path(APP_NAME, 'test_file1.txt')

    def test_path_wrong_file(self):
        print('++++++++++ TEST PATH WRONG FILE ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._remove(APP_NAME, pathOnly=True, desktopOnly=False)
        opt.main(['--debug', '-y', 'path', APP_NAME, 'resources/test_file1.txt'])
        self.assertTrue(self._isDirEmpty(opt.BIN_DIR))

    def test_alias(self):
        print('++++++++++ TEST ALIAS ++++++++++')
        APP_ALIAS = 'app-alias'
        APP_NAME_2 = 'app-v2'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._installOrUpdate(APP_NAME_2, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'))
        print('+++++ alias')
        opt.main(['--debug', '-y', 'alias', APP_ALIAS, APP_NAME])
        expectedFile = os.path.join(self._getInstallDir(APP_ALIAS), 'test_file1.txt')
        self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
        print('+++++ alias')
        opt.main(['--debug', '-y', 'alias', APP_ALIAS, APP_NAME_2])
        expectedFile = os.path.join(self._getInstallDir(APP_ALIAS), 'test_file2.txt')
        self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
        self._remove(APP_ALIAS)
        self._remove(APP_NAME)
        self._remove(APP_NAME_2)
        self.assertTrue(self._isDirEmpty(opt.INSTALL_DIR))
    
    def test_remove(self):
        print('++++++++++ TEST REMOVE ++++++++++')
        executable = 'test_file1.txt'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'))
        self._path(APP_NAME, executable)
        self._remove(APP_NAME)
        self.assertFalse(os.path.exists(os.path.join(opt.BIN_DIR, executable)))
        self.assertTrue(self._isDirEmpty(opt.BIN_DIR))
        self.assertTrue(self._isDirEmpty(opt.INSTALL_DIR))
        self.assertTrue(self._isDirEmpty(opt.DESKTOP_DIR))
        self.assertTrue(self._isDirEmpty(opt.ICON_DIR))
    def test_remove_unmanaged(self):
        print('++++++++++ TEST REMOVE UNMANAGED ++++++++++')
        appDir = os.path.join(opt.OPT_DIR, APP_NAME)
        os.makedirs(appDir, exist_ok=True)
        opt.main(['--debug', '-y', 'remove', APP_NAME])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
        self.assertTrue(os.path.exists(appDir))
    def test_remove_unmanaged_forced(self):
        print('++++++++++ TEST REMOVE UNMANAGED ++++++++++')
        appDir = os.path.join(opt.OPT_DIR, APP_NAME)
        os.makedirs(appDir, exist_ok=True)
        opt.main(['--debug', '-y', 'remove', '-f', APP_NAME])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
        self.assertFalse(os.path.exists(appDir), appDir)
    
    def test_clean(self):
        shutil.rmtree(ROOT_DIR)
    
    # Helper methods
    def _installOrUpdate(self, name, installFile, expectedFiles=[], skipFolder=None, update=False):
        print('+++++ install')
        cmd = ['-y', '--debug']
        cmd.append('update' if update else 'install') 
        cmd.append(name)
        cmd.append(installFile)
        opt.main(cmd)
        self.assertTrue(os.path.exists(self._getAppDir(name)))
        self.assertTrue(os.path.islink(self._getAppDir(name)))
        if skipFolder:
            self.assertTrue(os.path.realpath(self._getAppDir(name)) == os.path.join(self._getInstallDir(name), skipFolder))
        else:
            self.assertTrue(os.path.realpath(self._getAppDir(name)) == self._getInstallDir(name))
        self.assertTrue(os.path.exists(self._getInstallDir(name)))
        for f in expectedFiles:
            if skipFolder:
                expectedFile = os.path.join(self._getInstallDir(name), skipFolder, f) 
            else:
                expectedFile = os.path.join(self._getInstallDir(name), f)
            self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
    
    def _path(self, name, executable):
        print('+++++ path')
        opt.main(['--debug', '-y', 'path', name, os.path.join(self._getAppDir(APP_NAME), executable)])
        self.assertTrue(os.path.islink(os.path.join(opt.BIN_DIR, executable)))

    def _remove(self, name, pathOnly=False, desktopOnly=False):
        print('+++++ remove')
        cmd = ['-y', '--debug', 'remove']
        if pathOnly:
            cmd.append('--path-only')
        if desktopOnly:
            cmd.append('--desktop-only')
        cmd.append(name)
        opt.main(cmd)
        if not pathOnly and not desktopOnly:
            self.assertFalse(os.path.exists(self._getAppDir(name)))
            self.assertFalse(os.path.exists(self._getInstallDir(name)))
    
    def _isDirEmpty(self, dir):
        files = os.listdir(dir)
        return len(files) == 0

    def _getAppDir(self, name):
        return os.path.join(opt.OPT_DIR, name)

    def _getInstallDir(self, name):
        return os.path.join(opt.INSTALL_DIR, name)

if __name__ == '__main__':
    unittest.main()
    