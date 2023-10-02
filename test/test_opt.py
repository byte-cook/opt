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
        opt.AUTOCOMPLETE_DIR = os.path.join(ROOT_DIR, 'etc-bash_completion.d')
        opt.ICON_DIR = os.path.join(ROOT_DIR, 'usr-share-piximage')
        opt.INSTALL_DIR = os.path.join(opt.OPT_DIR, '.installer')
        os.makedirs(opt.OPT_DIR, exist_ok=True)
        os.makedirs(opt.BIN_DIR, exist_ok=True)
        os.makedirs(opt.DESKTOP_DIR, exist_ok=True)
        os.makedirs(opt.AUTOCOMPLETE_DIR, exist_ok=True)
        os.makedirs(opt.ICON_DIR, exist_ok=True)
    
    def tearDown(self):
        #shutil.rmtree(ROOT_DIR)
        pass

    def test_install_tar(self):
        print('+++++++++++ test_install_tar ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_zip(self):
        print('+++++++++++ test_install_zip ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.zip'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_bz2(self):
        print('+++++++++++ test_install_tar_bz2 ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.bz2'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_gz(self):
        print('+++++++++++ test_install_tar_gz ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.gz'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_tar_xz(self):
        print('+++++++++++ test_install_tar_xz ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar.xz'), ['test_file1.txt', 'test_file2.txt'])
    def test_install_zip_with_folder(self):
        print('+++++++++++ test_install_zip_with_folder ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_folder1_test_file1.zip'), ['test_file1.txt'], skipFolder='folder1')
    def test_install_twice(self):
        print('++++++++++ test_install_twice ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'), ['test_file1.txt'])
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file1.txt'])
    def test_install_wrong_file(self):
        print('++++++++++ test_install_wrong_file ++++++++++')
        opt.main(['--debug', '-y', 'install', APP_NAME, 'resources/__not_exists1__.txt', 'resources/__not_exists2__.txt'])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
    def test_install_unmanaged(self):
        print('++++++++++ test_install_unmanaged ++++++++++')
        os.makedirs(os.path.join(opt.OPT_DIR, APP_NAME), exist_ok=True)
        opt.main(['--debug', '-y', 'install', APP_NAME, 'resources/test_file1.txt'])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
    def test_install_folder(self):
        print('++++++++++ test_install_folder ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources'), ['test_file1.txt', 'test_folder1_test_file1.zip'])
    def test_install_path_noexec(self):
        print('++++++++++ test_install_path_noexec ++++++++++')
        if os.name == 'nt':
            print('skipped on Windows')
            return
        execFile = os.path.join(PROJECT_DIR, 'resources/exec-app.bin')
        nonExecFile = os.path.join(PROJECT_DIR, 'resources/exec.xml')
        os.chmod(execFile, 0o666) # rw
        os.chmod(nonExecFile, 0o666) # rw
        opt.main(['--debug', '-y', 'install', APP_NAME, execFile, nonExecFile])
        self.assertTrue(self._isDirEmpty(opt.BIN_DIR), msg='No executable file available')
    def test_install_path_exec(self):
        print('++++++++++ test_install_path_exec ++++++++++')
        if os.name == 'nt':
            print('skipped on Windows')
            return
        execFile = os.path.join(PROJECT_DIR, 'resources/exec-app.bin')
        nonExecFile = os.path.join(PROJECT_DIR, 'resources/exec.xml')
        os.chmod(execFile, 0o777) # rwx
        os.chmod(nonExecFile, 0o666) # rw
        opt.main(['--debug', '-y', 'install', APP_NAME, execFile, nonExecFile])
        self.assertFalse(self._isDirEmpty(opt.BIN_DIR))
        expectedFile = os.path.join(opt.BIN_DIR, 'exec-app.bin')
        self.assertTrue(os.path.exists(expectedFile), msg=f'Only executable file allowed: {expectedFile}')
        # reset permissions
        os.chmod(execFile, 0o666) # rw

    def test_update(self):
        print('++++++++++ test_update ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'), ['test_file1.txt'])
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file2.txt'], update=True)
    def test_update_overwrite(self):
        print('++++++++++ test_update_overwrite ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
        print('+++++ mod file')
        expectedFile = os.path.join(self._getAppDir(APP_NAME), 'test_file1.txt')
        with open(expectedFile, 'w') as f:
            f.write('Config: 2')
        print('+++++ update')
        opt.main(['--debug', '-y', 'update', APP_NAME, 'resources/test_file.tar'])
        self.assertTrue(os.path.getsize(expectedFile) == 0)
    def test_update_keep(self):
        print('++++++++++ test_update_keep ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
        print('+++++ mod file')
        expectedFile = os.path.join(self._getAppDir(APP_NAME), 'test_file1.txt')
        with open(expectedFile, 'w') as f:
            f.write('Config: 2')
        print('+++++ update')
        opt.main(['--debug', '-y', 'update', '--keep', expectedFile, APP_NAME, 'resources/test_file.tar'])
        self.assertTrue(os.path.getsize(expectedFile) > 0)
    def test_update_delete_keep(self):
        print('++++++++++ test_update_delete_keep ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
        print('+++++ mod file')
        expectedFile1 = os.path.join(self._getAppDir(APP_NAME), 'test_file1.txt')
        expectedFile2 = os.path.join(self._getAppDir(APP_NAME), 'test_file2.txt')
        expectedFile3 = os.path.join(self._getAppDir(APP_NAME), 'test_file3.txt')
        with open(expectedFile1, 'w') as f:
            f.write('Config: 2')
        print('+++++ update')
        opt.main(['--debug', '-y', 'update', '--keep', expectedFile1, '--keep', expectedFile2, '--delete', APP_NAME, 'resources/test_file3.txt'])
        self.assertTrue(os.path.getsize(expectedFile1) > 0)
        self.assertTrue(os.path.exists(expectedFile1))
        self.assertTrue(os.path.exists(expectedFile2))
        self.assertTrue(os.path.exists(expectedFile3))
        opt.main(['--debug', '-y', 'update', '--keep', expectedFile1, '--delete', APP_NAME, 'resources/test_file3.txt'])
        self.assertTrue(os.path.getsize(expectedFile1) > 0)
        self.assertTrue(os.path.exists(expectedFile1))
        self.assertFalse(os.path.exists(expectedFile2))
        self.assertTrue(os.path.exists(expectedFile3))
        opt.main(['--debug', '-y', 'update', '--delete', APP_NAME, 'resources/test_file3.txt'])
        self.assertFalse(os.path.exists(expectedFile1))
        self.assertFalse(os.path.exists(expectedFile2))
        self.assertTrue(os.path.exists(expectedFile3))
    def test_update_nodelete_overwritefile(self):
        print('++++++++++ test_update_nodelete_overwritefile ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
        print('+++++ mod file')
        expectedFile = os.path.join(self._getAppDir(APP_NAME), 'test_file1.txt')
        with open(expectedFile, 'w') as f:
            f.write('Config: 2')
        print('+++++ update and overwrite all files')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), update=True, updateDelete=False)
        self.assertTrue(os.path.getsize(expectedFile) == 0)
        print('+++++ mod file')
        with open(expectedFile, 'w') as f:
            f.write('Config: 2')
        print('+++++ update and overwrite only one file')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), update=True, updateDelete=False)
        self.assertTrue(os.path.exists(expectedFile), msg=f'File still exists: {expectedFile}')
        self.assertTrue(os.path.getsize(expectedFile) > 0, msg=f'File still changed: {expectedFile}')
    def test_update_nodelete_addfile(self):
        print('++++++++++ test_update_nodelete_addfile ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'), ['test_file1.txt', 'test_file2.txt'])
        print('+++++ update')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file3.txt'), update=True, updateDelete=False)
        for i in range(1,4):
            expectedFile = os.path.join(self._getAppDir(APP_NAME), f'test_file{i}.txt')
            self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
   
    def test_list(self):
        print('++++++++++ test_list ++++++++++')
        APP_NAME_2 = 'app-v2'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._installOrUpdate(APP_NAME_2, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._installOrUpdate('audiosolutions-2.3.0', os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        print('+++++ list')
        opt.main(['--debug', '-y', 'list'])
        print('+++++ list detail')
        opt.main(['--debug', '-y', 'list', APP_NAME])
    def test_list_update(self):
        print('++++++++++ test_list_update ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file2.txt'], update=True)
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file2.txt'], update=True)
        print('+++++ list')
        opt.main(['--debug', '-y', 'list'])
        print('+++++ list detail')
        opt.main(['--debug', '-y', 'list', APP_NAME])

    def test_path(self):
        print('++++++++++ test_path ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        os.chmod(os.path.join(self._getAppDir(APP_NAME), 'test_file1.txt'), 0o777) # rwx
        self._path(APP_NAME, 'test_file1.txt')

    def test_path_wrong_file(self):
        print('++++++++++ test_path_wrong_file ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._remove(APP_NAME, pathOnly=True, desktopOnly=False)
        opt.main(['--debug', '-y', 'path', APP_NAME, 'resources/test_file1.txt'])
        self.assertTrue(self._isDirEmpty(opt.BIN_DIR))

    def test_autocomplete(self):
        print('++++++++++ test_autocomplete ++++++++++')
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        opt.main(['--debug', 'autocomplete', APP_NAME, 'resources/test_file1.txt'])
        expectedFile = os.path.join(opt.AUTOCOMPLETE_DIR, 'test_file1.txt')
        self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)

    def test_alias(self):
        print('++++++++++ test_alias ++++++++++')
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
    def test_alias_update(self):
        """Update of alias app is not allowed."""
        print('++++++++++ test_alias_update ++++++++++')
        APP_ALIAS = 'app-alias'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        print('+++++ alias')
        opt.main(['--debug', '-y', 'alias', APP_ALIAS, APP_NAME])
        print('+++++ update')
        opt.main(['--debug', '-y', 'update', APP_ALIAS, os.path.join(PROJECT_DIR, 'resources/test_file2.txt')])
        self.assertTrue(os.path.islink(self._getInstallDir(APP_ALIAS)))
        expectedFile = os.path.join(self._getInstallDir(APP_ALIAS), 'test_file1.txt')
        self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
    def test_alias_install(self):
        """Changing installed app to alias app is not allowed."""
        print('++++++++++ test_alias_install ++++++++++')
        APP_NAME_2 = 'app-v2'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file1.txt'))
        self._installOrUpdate(APP_NAME_2, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'))
        print('+++++ alias')
        opt.main(['--debug', '-y', 'alias', APP_NAME_2, APP_NAME])
        self.assertFalse(os.path.islink(self._getInstallDir(APP_NAME)))
        self.assertFalse(os.path.islink(self._getInstallDir(APP_NAME_2)))
        expectedFile = os.path.join(self._getInstallDir(APP_NAME_2), 'test_file2.txt')
        self.assertTrue(os.path.exists(expectedFile), msg=expectedFile)
    
    def test_remove(self):
        print('++++++++++ test_remove ++++++++++')
        executable = 'test_file1.txt'
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file.tar'))
        self._path(APP_NAME, executable)
        opt.main(['--debug', 'autocomplete', APP_NAME, 'resources/test_file1.txt'])
        self._remove(APP_NAME)
        self.assertFalse(os.path.exists(os.path.join(opt.BIN_DIR, executable)))
        self.assertTrue(self._isDirEmpty(opt.BIN_DIR))
        self.assertTrue(self._isDirEmpty(opt.INSTALL_DIR))
        self.assertTrue(self._isDirEmpty(opt.DESKTOP_DIR))
        self.assertTrue(self._isDirEmpty(opt.AUTOCOMPLETE_DIR))
        self.assertTrue(self._isDirEmpty(opt.ICON_DIR))
    def test_remove_brokenlink(self):
        print('++++++++++ test_remove_brokenlink ++++++++++')
        execSrcFile = os.path.join(PROJECT_DIR, 'resources/test_file1.txt')
        os.chmod(execSrcFile, 0o777) # rwx
        self._installOrUpdate(APP_NAME, execSrcFile)
        # symlink to test_file1.txt
        executable = os.path.join(opt.BIN_DIR, 'test_file1.txt')
        self.assertTrue(os.path.exists(executable))
        # symlink is broken because file does not exist anymore
        self._installOrUpdate(APP_NAME, os.path.join(PROJECT_DIR, 'resources/test_file2.txt'), ['test_file2.txt'], update=True)
        self.assertFalse(os.path.exists(executable), msg=f'exists for broken link: {executable}')
        self.assertTrue(os.path.islink(executable), msg=f'islink: {executable}')
        self._remove(APP_NAME)
        self.assertFalse(os.path.exists(executable), msg=f'exists for broken link: {executable}')
        self.assertFalse(os.path.islink(executable), msg=f'islink not deleted: {executable}')
        # reset permission
        os.chmod(execSrcFile, 0o666) # rw
    
    def test_remove_unmanaged(self):
        print('++++++++++ test_remove_unmanaged ++++++++++')
        appDir = os.path.join(opt.OPT_DIR, APP_NAME)
        os.makedirs(appDir, exist_ok=True)
        opt.main(['--debug', '-y', 'remove', APP_NAME])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
        self.assertTrue(os.path.exists(appDir))
    def test_remove_unmanaged_forced(self):
        print('++++++++++ test_remove_unmanaged_forced ++++++++++')
        appDir = os.path.join(opt.OPT_DIR, APP_NAME)
        os.makedirs(appDir, exist_ok=True)
        opt.main(['--debug', '-y', 'remove', '-f', APP_NAME])
        self.assertFalse(os.path.exists(opt.INSTALL_DIR))
        self.assertFalse(os.path.exists(appDir), appDir)
    
    def test_clean(self):
        shutil.rmtree(ROOT_DIR)
    
    # Helper methods
    def _installOrUpdate(self, name, installFile, expectedFiles=[], skipFolder=None, update=False, updateDelete=True):
        print(f'+++++ {"update" if update else "install"}')
        cmd = ['-y', '--debug']
        if update:
            cmd.append('update') 
            if updateDelete:
                cmd.append('--delete') 
        else:
            cmd.append('install')
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
    
