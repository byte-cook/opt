#!/usr/bin/env python3

import argparse
import logging
import os
import stat
import traceback
import tempfile
from enum import Enum
import shutil
import fileutil
from textwrap import dedent

"""
History:
2013-11-14	initial version
2013-11-29	rework menu creation
2016-05-30	improve alias handling
2023-07-22  check for unmanaged apps + complete refactoring
"""

OPT_DIR = '/opt'
BIN_DIR = '/usr/local/bin/'
DESKTOP_DIR = '/usr/share/applications/'
ICON_DIR = '/usr/share/pixmaps/'
INSTALL_DIR = os.path.join(OPT_DIR, '.installer')

# commands
CMD_LIST = 'list'
CMD_INSTALL = 'install'
CMD_UPDATE = 'update'
CMD_REMOVE = 'remove'
CMD_DESKTOP = 'desktop'
CMD_MENU_DEPRECATED = "menu"
CMD_ALIAS = 'alias'
CMD_PATH = 'path'

class OptError(Exception):
    def __init__(self, msg, items=[]):
        self.msg = msg
        self.items = sorted(items)

class FileOp:
    """File operation with source/destination files."""
    def __init__(self, file, targetDir, targetFileName=None):
        self.src = os.path.abspath(file)
        if targetFileName:
            self.dst = os.path.abspath(os.path.join(targetDir, targetFileName))
        else:
            self.dst = os.path.abspath(os.path.join(targetDir, os.path.basename(file)))
    
    def __str__(self):
        exists = "!" if self.existsDst() else ""
        return f'{exists}{self.src}'
        
    def __lt__(self, other):
        return self.src < other.src

    def getAliasString(self):
        exists = "!" if self.existsDst() else ""
        return f'{exists} {self.dst} -> {self.src}'
    
    def existsDst(self):
        return os.path.exists(self.dst)

class ApplicationState(Enum):
    NEW = 1
    INSTALLED = 2
    ALIAS = 3
    UNMANAGED = 4
class Application:
    def __init__(self, name):
        self.name = name
        self.appDir = os.path.abspath(os.path.join(OPT_DIR, name)) # /opt/<name>
        self.appInstallDir = os.path.abspath(os.path.join(INSTALL_DIR, name)) # /opt/.installer/<name>
        appDirExists = os.path.exists(self.appDir)
        appInstallDirExists = os.path.exists(self.appInstallDir)
        if appDirExists != appInstallDirExists:
            self.state = ApplicationState.UNMANAGED
        elif appDirExists:
            if os.path.exists(self.getLogFile(CMD_ALIAS)):
                self.state = ApplicationState.ALIAS 
                self.aliasTarget = os.path.realpath(self.appInstallDir)
            else: 
                self.state = ApplicationState.INSTALLED
                self.aliasTarget = None
        else:
            self.state = ApplicationState.NEW

    def isAppFile(self, file):
        return os.path.abspath(file).startswith(self.appDir)

    def getLogFile(self, command):
        return os.path.join(INSTALL_DIR, f'{self.name}.{command}')
    
    def readLogFile(self, command):
        logFile = self.getLogFile(command)
        if not os.path.exists(logFile):
            return []
        with open(logFile, "r") as log:
            return log.read().splitlines()
    
    def printShortSummary(self):
        print(f'{self.name:<20} {self.state.name:<12} {self.appInstallDir}')
        
    def printSummary(self):
        dirs = []
        dirs.append(f'{self.appDir}')
        if self.state != ApplicationState.UNMANAGED:
            dirs.append(f'Installed at: {self.appInstallDir}')
        if self.state == ApplicationState.ALIAS:
            dirs.append(f'Linking to:   {self.aliasTarget}')
        _printList(f'== {self.name+" ":=<30} {self.state.name+" ":=<20}', dirs)
        print()
    
    def printDetails(self):
        files = []
        files.extend(self.readLogFile(CMD_INSTALL))
        files.extend(self.readLogFile(CMD_UPDATE))
        files.extend(self.readLogFile(CMD_ALIAS))
        files.extend(self.readLogFile(CMD_DESKTOP))
        files.extend(self.readLogFile(CMD_MENU_DEPRECATED))
        files.extend(self.readLogFile(CMD_PATH))
        # remove duplicates
        files = set(files)
        existing, nonExisting = _validateFiles(files)
        existing.sort()
        if files:
            _printList('Related files and folders:', existing)

class EmptyTask:
    def printSummary(self):
        pass
        
    def execute(self):
        pass

class InstallTask:
    def __init__(self, app, files, update, exclude):
        if app.state == ApplicationState.ALIAS:
            raise OptError(f'Application "{app.name}" is available but is an alias. Choose another application name or delete the alias application.')
        elif app.state == ApplicationState.UNMANAGED:
            raise OptError(f'Application "{app.name}" is not managed by opt.py. Choose another application name or delete the application directory.')
        elif update and app.state == ApplicationState.NEW:
            raise OptError(f'Application "{app.name}" does not exist')
        elif not update and app.state == ApplicationState.INSTALLED:
            raise OptError(f'Application "{app.name}" is already installed')
        self.app = app
        self.files = files
        self.files.sort()
        self.update = update
        self.exclude = []
        for e in exclude:
            e = os.path.abspath(e)
            if not os.path.exists(e):
                raise OptError(f'Exclusion "{e}" does not exist')
            elif not app.isAppFile(e):
                raise OptError(f'Exclusion "{e}" does not belong to application "{app.name}"')
            else:
                self.exclude.append(e)
        self.exclude.sort()
    
    def getTargetFile(self, file, fileInArchive=None):
        if file in self.files:
            basename = fileInArchive if fileInArchive else os.path.basename(file)
            return os.path.join(self.app.appDir, basename)
        return None
        
    def printSummary(self):
        if self.update:
            excludeMsg = ', excluding:' if self.exclude else ''
            _printList(f'Delete content of "{self.app.appInstallDir}"{excludeMsg}', self.exclude)
        _printList(f'Copy files to "{self.app.appInstallDir}":', self.files)
        print(f'Create symlink in "{self.app.appDir}"')
        
    def getFilesByRelevance(self):
        # Prefer files with same prefix as application
        files = self.files.copy()
        files.sort(key=lambda f: (1 if os.path.basename(f).startswith(self.app.name) else 100) + len(f))
        return files
        
    def execute(self):
        # ensure install dir is created
        os.makedirs(INSTALL_DIR, exist_ok=True)
    
        logFile = self.app.getLogFile(CMD_UPDATE if self.update else CMD_INSTALL)
        with open(logFile, 'a') as log, tempfile.TemporaryDirectory() as tmpDir:
            logging.debug(f'Use temporary directory: {tmpDir}')
            # _save_exlusions
            for e in self.exclude:
                tmpRelPath = os.path.relpath(e, start=self.app.appDir) # /opt/name/folder/file.ext -> folder/file.ext
                tmpFile = os.path.join(tmpDir, tmpRelPath) # folder/file -> <tmpDir>/folder/file
                fileutil.copyFileOrFolder(e, os.path.dirname(tmpFile) if os.path.isfile(e) else tmpFile)
            
            if os.path.exists(self.app.appInstallDir):
                shutil.rmtree(self.app.appInstallDir)
            os.makedirs(self.app.appInstallDir, exist_ok=True)
            # copy files
            for file in self.files:
                if fileutil.isArchiveFile(file):
                    fileutil.extractArchive(file, self.app.appInstallDir)
                else:
                    fileutil.copyFileOrFolder(file, self.app.appInstallDir)
            # set owner
            #fileutil.chown_recursively(self.app.appInstallDir)
            # _restore_exclusions
            fileutil.copyFileOrFolder(tmpDir, self.app.appInstallDir)
            # create symlink
            if os.path.exists(self.app.appDir):
                os.unlink(self.app.appDir) 
            symlinkSrc = fileutil.skipContainerDirs(self.app.appInstallDir)
            os.symlink(symlinkSrc, self.app.appDir, target_is_directory=True)
            
            # _save_log
            log.write(f'{self.app.appInstallDir}\n')
            log.write(f'{self.app.appDir}\n')

        # set permisions (does not work in with section)
        os.chmod(self.app.appInstallDir, 0o755)

def installOrUpdate(args, update):
    existing, nonExisting = _validateFiles(args.file)
    if nonExisting:
        raise OptError('File(s) do not exist:', nonExisting)
    # app
    app = Application(args.name)
    # install
    install = InstallTask(app, existing, update, args.exclude if update and args.exclude is not None else [])
    # path
    if update or args.noPath:
        path = EmptyTask()
    else:
        # auto-detect best matching executable for $PATH
        installFiles = install.getFilesByRelevance()
        if installFiles:
            installFile = installFiles[0]
            if fileutil.isArchiveFile(installFile):
                with tempfile.TemporaryDirectory() as tmpDir:
                    fileutil.extractArchive(installFile, tmpDir)
                    # skip single container dirs
                    archiveDir = fileutil.skipContainerDirs(tmpDir)
                    fileCandidates = fileutil.getAllSubFiles(archiveDir)
                    if fileCandidates:
                        logging.debug(f'Archive file candidates: {fileCandidates}')
                        fileCandidates.sort(key=lambda f: (1 if os.path.basename(f).startswith(app.name) else 100) + len(os.path.dirname(f))*10 + len(os.path.basename(f)))
                        fileInArchive = fileCandidates[0]
                        target = install.getTargetFile(installFile, fileInArchive)
                        path = PathTask(app, target, checkTarget=False)
            else:
                target = install.getTargetFile(installFile)
                path = PathTask(app, target, checkTarget=False)
    
    app.printSummary()
    install.printSummary()
    path.printSummary()
    print()
    doContinue = True if args.noPrompt else getYesOrNo('Do you want to continue?', True)
    if doContinue:
        install.execute()
        path.execute()

class PathTask:
    def __init__(self, app, target, linkName=None, checkTarget=True):
        """Create symlink: symlinkFile -> target."""
        if app.state == ApplicationState.UNMANAGED:
            raise OptError(f'Application "{app.name}" is not managed by opt.py')
        elif checkTarget:
            if not os.path.isfile(target):
                raise OptError(f'Target "{target}" must be a file')
            elif not app.isAppFile(target):
                raise OptError(f'Target "{target}" does not belong to application "{app.name}"')
            elif not os.access(target, os.X_OK):
                raise OptError(f'File "{target}" is not executable')
        self.app = app
        self.linkName = linkName if linkName else os.path.basename(target)
        self.op = FileOp(target, BIN_DIR, self.linkName)
        self.overwrite = self.op.existsDst()
    
    def printSummary(self):
        _printList(f'Add to $PATH by creating alias in "{BIN_DIR}":', [self.op], lambda op: op.getAliasString())
        
    def execute(self):
        logFile = self.app.getLogFile(CMD_PATH)
        with open(logFile, 'a') as log:
            # src : the target of the symlink
            # dst : the new destination, which didn't exist previously (= new symlink)
            logging.debug('Path src: ' + self.op.src)
            logging.debug('Path dst/symlink: ' + self.op.dst)
            # check target (disabled for auto-detect in install)
            if not os.path.exists(self.op.src): 
                print(f'Warning: Alias could not be created because "{self.op.src}" does not exist')
                return
            # remove old alias if exists
            if os.path.exists(self.op.dst): 
                os.unlink(self.op.dst) 
            os.symlink(self.op.src, self.op.dst, target_is_directory=False)
            log.write(f'{self.op.dst}\n')

def path(args):
    existing, nonExisting = _validateFiles([args.file])
    if nonExisting:
        raise OptError('File(s) do not exist:', nonExisting)
    app = Application(args.name)
    linkName = args.linkName if args.linkName else None
    path = PathTask(app, existing[0], linkName)

    app.printSummary()
    path.printSummary()
    print()
    doContinue = True if args.noPrompt or not path.overwrite else getYesOrNo('Overwrite exiting files (marked with prefix "!")?', False)
    if doContinue:
        path.execute()

class RemoveTask:
    def __init__(self, app, desktopOnly, pathOnly, force):
        if not force and app.state == ApplicationState.UNMANAGED:
            raise OptError(f'Application "{app.name}" is not managed by opt.py')
        elif app.state == ApplicationState.NEW:
            raise OptError(f'Application "{app.name}" does not exist')
        self.app = app
        removeAll = not desktopOnly and not pathOnly
        files = []
        logFiles = []
        if removeAll:
            files.append(app.appDir)
            files.append(app.appInstallDir)
            files.extend(app.readLogFile(CMD_INSTALL))
            files.extend(app.readLogFile(CMD_UPDATE))
            files.extend(app.readLogFile(CMD_ALIAS))
            logFiles.append(app.getLogFile(CMD_INSTALL))
            logFiles.append(app.getLogFile(CMD_UPDATE))
            logFiles.append(app.getLogFile(CMD_ALIAS))
        if removeAll or desktopOnly:
            files.extend(app.readLogFile(CMD_DESKTOP))
            files.extend(app.readLogFile(CMD_MENU_DEPRECATED))
            logFiles.append(app.getLogFile(CMD_DESKTOP))
            logFiles.append(app.getLogFile(CMD_MENU_DEPRECATED))
        if removeAll or pathOnly:
            files.extend(app.readLogFile(CMD_PATH))
            logFiles.append(app.getLogFile(CMD_PATH))
        existing, nonExisting = _validateFiles(set(files))
        self.files = sorted(existing)
        existing, nonExisting = _validateFiles(set(logFiles))
        self.logFiles = sorted(existing)
        self.empty = not self.files and not self.logFiles
        
    def printSummary(self):
        if self.files:
            _printList(f'Remove the following files and directories:', self.files)
        if self.logFiles:
            _printList(f'Remove the following log files:', self.logFiles)
        if self.empty:
            print('No files to delete')
        
    def execute(self):
        for file in self.files:
            if os.path.islink(file):
                os.unlink(file)
            elif os.path.isdir(file):
                shutil.rmtree(file)
            else:
                os.remove(file)
        for file in self.logFiles:
            os.remove(file)

def remove(args):
    """Removes an application."""
    app = Application(args.name)
    remove = RemoveTask(app, args.desktopOnly, args.pathOnly, args.force)

    app.printSummary()
    remove.printSummary()
    print()
    doContinue = True if args.noPrompt or remove.empty else getYesOrNo('Do you want to continue?', False)
    if doContinue:
        remove.execute()

def listApps(args):
    """List applications."""
    if args.name is None:
        # determine all dirs OPT_DIR
        files = sorted(os.listdir(OPT_DIR))
        if len(files) == 0:
            # no applications installed
            return
        for file in files:
            appDir = os.path.join(OPT_DIR, file)
            if appDir == INSTALL_DIR:
                continue
            if os.path.isdir(appDir):
                app = Application(file)
                app.printShortSummary()
            
    else:
        app = Application(args.name)
        app.printSummary()
        app.printDetails()

class DesktopTask:
    def __init__(self, app, files):
        self.app = app
        self.overwrite = False
        self.desktopOps = []
        self.pngOps = []
        for file in files:
            if file.endswith(".desktop"):
                op = FileOp(file, DESKTOP_DIR)
                self.overwrite |= op.existsDst()
                self.desktopOps.append(op)
            elif file.endswith(".png"):
                op = FileOp(file, ICON_DIR)
                self.overwrite |= op.existsDst()
                self.pngOps.append(op)
            else:
                raise OptError(f'Unsupported file format: {file}')
        self.desktopOps.sort()
        self.pngOps.sort()

    def printSummary(self):
        _printList(f'Copy .desktop files to "{DESKTOP_DIR}":', self.desktopOps)
        _printList(f'Copy .png files to "{ICON_DIR}":', self.pngOps)

    def execute(self):
        logFile = self.app.getLogFile(CMD_DESKTOP)
        with open(logFile, 'a') as log:
            for op in self.desktopOps:
                shutil.copyfile(op.src, op.dst)
                fileutil.chmod_add(op.dst, stat.S_IEXEC | stat.S_IREAD)
                log.write(f'{op.dst}\n')
            for op in self.pngOps:
                shutil.copyfile(op.src, op.dst)
                fileutil.chmod_add(op.dst, stat.S_IREAD)
                log.write(f'{op.dst}\n')

def desktop(args):
    """Install menu entries (*.desktop)."""
    # see: https://help.ubuntu.com/community/UnityLaunchersAndDesktopFiles
    # see: https://developer.gnome.org/integration-guide/stable/desktop-files.html.en
    # see: https://specifications.freedesktop.org/desktop-entry-spec/latest/index.html
    existing, nonExisting = _validateFiles(args.file)
    if nonExisting:
        raise OptError('File(s) do not exist:', nonExisting)
    app = Application(args.name)
    desktop = DesktopTask(app, existing)

    app.printSummary()
    desktop.printSummary()
    print()
    doContinue = True if args.noPrompt or not desktop.overwrite else getYesOrNo('Overwrite exiting files (marked with prefix "!")?', False)
    if doContinue:
        desktop.execute()

class AliasTask:
    def __init__(self, aliasApp, targetApp):
        if targetApp.name == aliasApp.name:
            raise OptError(f'Application and target must not be identical: {targetApp.name}')
        if aliasApp.state == ApplicationState.UNMANAGED:
            raise OptError(f'Application "{aliasApp.name}" is not managed by opt.py')
        if targetApp.state == ApplicationState.UNMANAGED:
            raise OptError(f'Application "{targetApp.name}" is not managed by opt.py')
        if targetApp.state == ApplicationState.NEW:
            raise OptError(f'Application "{targetApp.name}" does not exist')
        self.aliasApp = aliasApp
        self.targetApp = targetApp
        self.overwrite = self.aliasApp.state in [ApplicationState.INSTALLED, ApplicationState.ALIAS]

    def printSummary(self):
        _printList(f'Create alias "{self.aliasApp.name}" for application "{self.targetApp.name}"', []) #, [self.aliasApp], lambda op: op.getAliasString())
        
    def execute(self):
        logFile = self.aliasApp.getLogFile(CMD_ALIAS)
        with open(logFile, 'a') as log:
            # if os.path.exists(self.op.dst): 
                # os.unlink(self.op.dst) 
            # os.symlink(self.op.src, self.op.dst, target_is_directory=False)

            # clean application folder with old data
            if os.path.exists(self.aliasApp.appInstallDir):
                if os.path.islink(self.aliasApp.appInstallDir): # os.path.isdir(self.aliasApp.appInstallDir):
                    os.unlink(self.aliasApp.appInstallDir) 
                else:
                    shutil.rmtree(self.aliasApp.appInstallDir)
            # create alias symlink to target
            os.symlink(self.targetApp.appDir, self.aliasApp.appInstallDir, target_is_directory=True)
            log.write(f'{self.aliasApp.appInstallDir}\n')
            # utils.execute_command(cmd=["ln", "-sf",  "--no-dereference", targetDataFolder, param.dataFolder], verbose=param.verbose, simulate=param.simulate)
            # _save_log(param, param.dataFolder)
            if not os.path.exists(self.aliasApp.appDir):
                os.symlink(self.aliasApp.appInstallDir, self.aliasApp.appDir, target_is_directory=True)
                log.write(f'{self.aliasApp.appDir}\n')
            # if not os.path.exists(param.symlink):
                # utils.execute_command(cmd=["ln", "-sf",  "--no-dereference", param.dataFolder, param.symlink], verbose=param.verbose, simulate=param.simulate)
                # _save_log(param, param.symlink)

def alias(args):
    """Create an alias for an application."""
    targetApp = Application(args.target)
    aliasApp = Application(args.name)
    alias = AliasTask(aliasApp, targetApp)
    
    aliasApp.printSummary()
    alias.printSummary()
    print()
    doContinue = True if args.noPrompt or not alias.overwrite else getYesOrNo('Overwrite exiting application?', False)
    if doContinue:
        alias.execute()

def _validateFiles(files):
    """Check if files exist and convert to absolute paths."""
    existing = []
    nonExisting = []
    for file in set(files):
        if os.path.exists(file):
            existing.append(os.path.abspath(file))
        else:
            nonExisting.append(os.path.abspath(file))
    return existing, nonExisting
    
def _printList(msg, list, fn=lambda i: i):
    """Print a message and a list of items."""
    print(msg)
    for i in list:
        print(f'   {fn(i)}')

def getYesOrNo(question, default=True):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    prompt = {True: " [Y/n] ", False: " [y/N] ", None: " [y/n] "}
    while True:
        print(question + prompt[default], end='')
        choice = input().lower()
        if default is not None and choice == "":
            return default
        elif choice in valid:
            return valid[choice]
        else:
            print('Please respond with "yes" or "no" (or "y" or "n").')
            
def main(argv=None):
    try:
        PROG_DESC = """\
            Opt.py is an installation manager for the /opt directory. The /opt directory is reserved for all the software and add-on packages that are not part of the default installation. 
            
            If a program does not provide an installation file for the package manager used (e.g. APT), the program can be installed in /opt. However, this installation can be tedious: 
            - Files must be unpacked
            - $PATH variable must be extended
            - Desktop entry must be created
            - When uninstalling the program, all these changes should be undone.

            To simplify this, Opt.py provides a simple command line interface modeled after APT. 
            
            Example:
            
            General structure of the commands:
            > opt.py <command> <app-name> ...

            List installed applications:
            > opt.py list
            
            Install application:
            > opt.py install application-12-3 application-12.3.tar.gz

            Install another version of the same application:
            > opt.py install application-19-81 application-19.81.tar.gz
            
            Create alias (application refers to application-12-3):
            > opt.py alias application application-12-3

            Extend $PATH variable:
            > opt.py path application /opt/application/application.sh
            
            Add desktop entry:
            > opt.py desktop application application.desktop application.png

            Change alias (application refers to application-19-81):
            > opt.py alias application application-19-81
            
            Delete old version and all related files:
            > opt.py remove application-12-3
            
            Delete all versions of this application:
            > opt.py remove application-19-81
            > opt.py remove application
            
            Directory strucuture:
            
            /opt/application-12-3        -> /opt/.installer/application-12-3  (contains application files)
            /opt/application             -> /opt/.installer/application       (alias)
            /opt/.installer/application  -> /opt/.installer/application-12-3

            Log files contain created files:
            
            /opt/.installer/<name>.<command>
            /opt/.installer/application-12-3.install
            /opt/.installer/application-12-3.path
            /opt/.installer/application-12-3.desktop
            /opt/.installer/application.alias
            
            """
        
        parser = argparse.ArgumentParser(description=dedent(PROG_DESC), formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--debug', help="activate DEBUG logging", action="store_true")
        parser.add_argument('-y', '--yes', action="store_true", dest="noPrompt", help="answer all questions with yes")

        subparsers = parser.add_subparsers(dest='command')
        # list
        listParser = subparsers.add_parser(CMD_LIST, help='')
        # install
        installParser = subparsers.add_parser(CMD_INSTALL, help='install a new application', description='Installs a new application')
        installParser.add_argument('--no-path', default=False, dest='noPath', action='store_true', help='')
        #installParser.add_argument("--owner", help="owner of all installed files", default="root")
        installParser.add_argument('name', help='application name')
        installParser.add_argument('file', nargs='+', help='file to install')
        # update
        updateParser = subparsers.add_parser(CMD_UPDATE, help='update application', description='Replace the application data by the given file(s). Use "--exclude" to keep settings files.')
        updateParser.add_argument('--no-path', dest='noPath', default=False, action='store_true', help='')
        updateParser.add_argument('--exclude', dest='exclude', action='append', help='exclude file')
        #updateParser.add_argument("--owner", help="owner of all installed files", default="root")
        updateParser.add_argument('name', help='application name')
        updateParser.add_argument('file', nargs='+', help='file to install')
        # remove
        removeParser = subparsers.add_parser(CMD_REMOVE, help="remove application/alias", description="Removes an application or alias")
        removeParser.add_argument('-f', '--force', action="store_true", dest="force", help="force to remove all files and folders")
        removeParser.add_argument('--path-only', action="store_true", dest="pathOnly", help="remove path symlinks only")
        removeParser.add_argument('--desktop-only', action="store_true", dest="desktopOnly", help="remove menu entries in desktop only")
        removeParser.add_argument('name', help='application name or alias')
        # desktop 
        menuParser = subparsers.add_parser(CMD_DESKTOP, help="create menu entry according to freedesktop.org specifications", description="Create a menu entry by using a .desktop file")
        menuParser.add_argument("name", help="application name")
        menuParser.add_argument("file", nargs="+", help="*.desktop/*.png file")
        # path
        pathParser = subparsers.add_parser(CMD_PATH, help="add application to $PATH", description=f'Add application to $PATH by creating a symlink in "{BIN_DIR}"')
        pathParser.add_argument("--link-name", dest='linkName', help='link name in $PATH')
        pathParser.add_argument("name", help="application name")
        pathParser.add_argument("file", help=f'executable target file, e.g. {OPT_DIR}/<name>/yourapp')
        # list
        listParser = subparsers.add_parser(CMD_LIST, help="list installed applications", description="List all installed applications or all files belonging to one application")
        listParser.add_argument("name", nargs="?", help="application name")
        # alias
        aliasParser = subparsers.add_parser(CMD_ALIAS, help="create an alias for an installed application", description="Create an alias for an installed application")
        aliasParser.add_argument("name", help="application alias")
        aliasParser.add_argument("target", help="target application name (must already be installed)")

        args = parser.parse_args(argv)
        # init logging
        level = logging.DEBUG if args.debug else logging.WARNING
        logging.basicConfig(format='%(levelname)s: %(message)s', level=level, force=True)
        
        if os.geteuid() != 0:
            raise OptError('Root privileges required')
        if args.command is None:
            # if no command is specified, print application list
            args.command = CMD_LIST
            args.name = None

        if args.command == CMD_INSTALL:
            installOrUpdate(args, False)
        elif args.command == CMD_UPDATE:
            installOrUpdate(args, True)
        elif args.command == CMD_REMOVE:
            remove(args)
        elif args.command == CMD_PATH:
            path(args)
        elif args.command == CMD_DESKTOP:
            desktop(args)
        elif args.command == CMD_LIST:
            listApps(args)
        elif args.command == CMD_ALIAS:
            alias(args)

    except OptError as e:
        _printList(e.msg, e.items)
#        print(f'Error: {e}')
    except Exception as e:
        print(e)
        logging.debug(type(e))
        if args.debug:
            traceback.print_exc()

if __name__ == '__main__':
    main()

