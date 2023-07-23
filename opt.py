#!/usr/bin/env python3

from xml.etree import ElementTree
import argparse
import os
import utils
import tempfile
import shutil
import csv

"""
Installer for non-standard applications
- All applications are installed in one root directory (e.g. /opt)
- Each application gets its own directory
- Support install, remove, menu creation, path extension
- Creates softlinks to real data
- Allows to use alias name
- Remove deletes all created files (stored in log files)

Example:
> # Install 'app-1.0'
> opt.py install app-1.0 app-1.0.tar.gz
> 
> # Create alias 'app' for 'app-1.0'
> opt.py alias app app-1.0
>
> # Create desktop entry for 'app'
> opt.py menu app app.desktop app-icon.png
>
> # Update 'app-1.0'
> opt.py update app-1.0 app-1.3.tar.gz
>
> # Uninstall 'app'
> opt.py remove app


Directory strucuture:
/opt/app-1.0         -> /opt/.installer/app-1.0
/opt/.installer/app-1.0/<content>
/opt/app             -> /opt/.installer/app
/opt/.installer/app  -> /opt/.installer/app-1.0

Log files contain created files:
/opt/.installer/app-1.0.install
/opt/.installer/app.alias
/opt/.installer/<name>.<command>

History:
2013-11-14	initial version
2013-11-29	rework menu creation
2016-05-30	improve alias handling
"""

ROOT_DIR = "/opt/"
INSTALL_DIR = ROOT_DIR + ".installer/"
TMP_DIR = os.path.join(tempfile.gettempdir(), "installer")
EXCLUDE_DIR = TMP_DIR + "/exclude/"

# commands
CMD_INSTALL = "install"
CMD_UPDATE = "update"
CMD_REMOVE = "remove"
CMD_MENU = "menu"
CMD_ALIAS = "alias"
CMD_PATH = "path"
CMD_LIST = "list"

class InstallParam:
    """Installation parameters."""
    def __init__(self):
        self.command = None
        self.name = None
        self.symlink = None
        self.dataFolder = None
        self.installed = False
        self.targetName = None
        self.targetSymlink = None
        self.files = list()
        self.owner = None
        self.exclusions = list()
        self.skipDirs = False
        self.menuOnly = False
        self.pathOnly = False
        self.cmdName = None
        self.noPrompt = False
        self.verbose = False
        self.simulate = False
    def print_param(self,  msg):
        info = " (dry-run)" if self.simulate else ""
        print(msg + info + ":")
        print(" {0:<15}: {1}".format("Name", self.name))
        print(" {0:<15}: {1}".format("Symlink", self.symlink))
        if self.installed:
            if os.path.islink(self.dataFolder):
                realFolder = os.path.realpath(self.dataFolder)
                print(" {0:<15}: {1} -> {2}".format("Data Folder", self.dataFolder, realFolder))
            else:
                print(" {0:<15}: {1}".format("Data Folder", self.dataFolder))
        print(" {0:<15}: {1}".format("Installed", self.installed))

        if self.targetName is not None:
            print(" {0:<15}: {1}".format("Target Name", self.targetName))
            print(" {0:<15}: {1}".format("Target Symlink", self.targetSymlink))
        for file in self.files:
            print(" {0:<15}: {1}".format("File", file))
        if self.owner is not None:
            print(" {0:<15}: {1}".format("Owner", self.owner))
        for exclusion in self.exclusions:
            print(" {0:<15}: {1}".format("Exclude", exclusion))
        if self.skipDirs:
            print(" {0:<15}: {1}".format("Skip Dirs", self.skipDirs))
        if self.menuOnly:
            print(" {0:<15}: {1}".format("Menu Only", self.menuOnly))
        if self.pathOnly:
            print(" {0:<15}: {1}".format("Path Only", self.pathOnly))
        if self.cmdName is not None:
            print(" {0:<15}: {1}".format("Command Name", self.cmdName))

def _save_log(param,  file):
    """Save file in log file"""
    if param.simulate or param.name is None:
        return
    logFile = INSTALL_DIR + param.name + "." + param.command
    with open(logFile, "a") as f:
        f.write(file + "\n")
        
def _read_log(param,  command):
    """Read log file and returns all files without duplicates"""
    logFile = INSTALL_DIR + param.name + "." + command
    if not os.path.exists(logFile):
        return list()
    files = list()
    with open(logFile, "r") as f:
        for line in f:
            # remove \n
            file = line[:-1]
            if os.path.exists(file) or os.path.islink(file):
                files.append(file)
    # convert to set and remove duplicates
    return set(files)

def _delete_log(param,  command):
    """Deletes a log file."""
    if param.simulate:
        return
    logFile = INSTALL_DIR + param.name + "." + command
    if os.path.exists(logFile):
        utils.execute_command(cmd=["rm", "-f", logFile], verbose=False, simulate=param.simulate)
    
def _save_exlusions(param):
    """Saving exclusions to /tmp directory."""
    # nothing installed -> skip
    if not os.path.exists(param.symlink):
        return
    if len(param.exclusions) == 0:
        return
    if param.verbose:
        print("Save exclusions to: " + EXCLUDE_DIR)
    # clear tmp EXCLUDE_DIR
    utils.execute_command(cmd=["rm", "-rf", EXCLUDE_DIR], verbose=param.verbose, simulate=param.simulate)
    for exclusion in param.exclusions:
        relativeExclusion = exclusion.replace(param.symlink,  "")
        # remove starting slash
        if relativeExclusion[0] == "/":
            relativeExclusion = relativeExclusion[1:]
        src = os.path.join(param.symlink, relativeExclusion)
        if not src.startswith(param.symlink):
            continue
        if os.path.exists(src):
            dst = os.path.join(EXCLUDE_DIR, relativeExclusion)
            if not os.path.exists(os.path.dirname(dst)):
                utils.execute_command(cmd=["mkdir", "-p", os.path.dirname(dst)], verbose=param.verbose, simulate=param.simulate)
            utils.execute_command(cmd=["cp", src, dst], verbose=param.verbose, simulate=param.simulate)
        else:
            utils.prompt_yes_no(msg="Ignore missing exclusion file '" + src + "'? (Y/N) ", simulate=param.simulate, noPrompt=param.noPrompt)

def _restore_exclusions(param):
    """Restoring exclusions from /tmp directory."""
    if len(param.exclusions) == 0:
        return
    if param.verbose:
        print("Restore exclusions from: " + EXCLUDE_DIR)
    for exclusion in param.exclusions:
        relativeExclusion = exclusion.replace(param.symlink,  "")
        # remove starting slash
        if relativeExclusion[0] == "/":
            relativeExclusion = relativeExclusion[1:]
        src = os.path.join(EXCLUDE_DIR, relativeExclusion)
        if os.path.exists(src):
            dst = os.path.join(param.symlink, relativeExclusion)
            utils.execute_command(cmd=["cp", src, dst], verbose=param.verbose, simulate=param.simulate)

def _create_softlink(param): 
    """Creates the application softlink."""
    if param.verbose:
        print("# Create softlink: " + param.symlink)
    if os.path.islink(param.symlink):
        # remove old symbolic link
        utils.execute_command(cmd=["unlink", param.symlink], verbose=param.verbose, simulate=param.simulate)
    
    subFolder = ""
    # skip container dirs
    if param.skipDirs and os.path.exists(param.dataFolder):
        files = os.listdir(param.dataFolder)
        while len(files) == 1:
            subFolder += files[0] + "/"
            files = os.listdir(os.path.join(param.dataFolder, subFolder))
    # create symbolic link
    utils.execute_command(cmd=["ln", "-s", os.path.join(param.dataFolder, subFolder), param.symlink], verbose=param.verbose, simulate=param.simulate)
    _save_log(param,  param.symlink)
    
def _copy_file(param, file):
    """Copy file to installation folder"""
    if param.verbose:
        print("# Copy installation file: " + file)
    # unpack file to dataFolder
    packed = False
    if file.endswith(".zip"):
        utils.execute_command(cmd=["unzip",  "-o", file, "-d",  param.dataFolder], verbose=param.verbose, simulate=param.simulate)
        packed = True
    elif file.endswith(".tar.gz") or file.endswith(".tgz"):
        utils.execute_command(cmd=["tar", "--overwrite", "-xzf",  file, "--directory",  param.dataFolder], verbose=param.verbose, simulate=param.simulate)
        packed = True
    elif file.endswith(".xz"):
        # sudo apt install xz-utils
        utils.execute_command(cmd=["tar", "--overwrite", "-xf",  file, "--directory",  param.dataFolder], verbose=param.verbose, simulate=param.simulate)
        packed = True
    elif file.endswith(".tar.bz2"):
        utils.execute_command(cmd=["tar", "--overwrite", "-xjf",  file, "--directory",  param.dataFolder], verbose=param.verbose, simulate=param.simulate)
        packed = True
    elif file.endswith(".tar"):
        utils.execute_command(cmd=["tar", "--overwrite", "-xf",  file, "--directory",  param.dataFolder], verbose=param.verbose, simulate=param.simulate)
        packed = True
        
    # if no archive file
    if not packed:
        # copy file to folder
        utils.execute_command(cmd=["cp", file, param.dataFolder], verbose=param.verbose, simulate=param.simulate)
    _save_log(param,  param.dataFolder)
    
def _install(param,  cleanFolder):
    """Installs an application."""
    _save_exlusions(param)
    # clean application folder with old data
    if cleanFolder and param.installed:
        utils.execute_command(cmd=["rm", "-rf", param.dataFolder], verbose=param.verbose, simulate=param.simulate)
    # create dataFolder
    if not os.path.exists(param.dataFolder):
        utils.execute_command(cmd=["mkdir",  "-p", param.dataFolder], verbose=param.verbose, simulate=param.simulate)
    for file in param.files:
        # copy installation file
        _copy_file(param, file)
    if param.owner is not None:
        # set owner
        utils.execute_command(cmd=["chown", "-Rf", param.owner + ":" + param.owner, param.dataFolder], verbose=param.verbose, simulate=param.simulate)
    # create softlink before restoring exclusions
    _create_softlink(param)
    _restore_exclusions(param)

def install(param):
    """Installs an application."""
    param.print_param("Installing application (removes pre-installed application)")
    utils.prompt_yes_no(simulate=param.simulate, noPrompt=param.noPrompt, exitIfNo=True)
    print()
    _install(param=param,  cleanFolder=True)

def update(param):
    """Updates an application."""
    param.print_param("Updating application")
    if not param.installed:
        raise Exception("Application is not installed: " + param.name)
    utils.prompt_yes_no(simulate=param.simulate, noPrompt=param.noPrompt, exitIfNo=True)
    print()
    _install(param=param,  cleanFolder=False)
 
def remove(param):
    """Removes an application."""
    param.print_param("Removing application")
    if not param.installed:
        raise Exception("Application is not installed: " + param.name)
    utils.prompt_yes_no(simulate=param.simulate, noPrompt=param.noPrompt, exitIfNo=True)
    print()
    removeAll = not param.menuOnly and not param.pathOnly
    # remove other files (from logFile)
    files = list()
    if removeAll:
        files.extend(_read_log(param,  CMD_INSTALL))
        files.extend(_read_log(param,  CMD_UPDATE))
        files.extend(_read_log(param,  CMD_ALIAS))
    if removeAll or param.menuOnly:
        files.extend(_read_log(param,  CMD_MENU))
    if removeAll or param.pathOnly:
        files.extend(_read_log(param,  CMD_PATH))
    # remove duplicates
    files = set(files)
    for file in files:
        if os.path.exists(file) or os.path.islink(file):
            if os.path.isdir(file):
                utils.execute_command(cmd=["rm", "-rf", file], verbose=param.verbose, simulate=param.simulate)
            else:
                utils.execute_command(cmd=["rm", "-f", file], verbose=param.verbose, simulate=param.simulate)
    if removeAll:
        _delete_log(param,  CMD_INSTALL)
        _delete_log(param,  CMD_UPDATE)
        _delete_log(param,  CMD_ALIAS)
    if removeAll or param.menuOnly:
        _delete_log(param,  CMD_MENU)
    if removeAll or param.pathOnly:
        _delete_log(param,  CMD_PATH)

def alias(param):
    """Create an alias for an application."""
    param.print_param("Create application alias (removes pre-installed application)")
    if param.name == param.targetName:
        raise Exception("Application and target name must not be identical: " + param.name)
    if not os.path.exists(param.targetSymlink):
        raise Exception("Application is not installed: " + param.targetName)
    targetDataFolder = os.path.realpath(param.targetSymlink)
    if not os.path.exists(targetDataFolder):
        raise Exception("Target Data Folder does not exist: " + targetDataFolder)
    utils.prompt_yes_no(simulate=param.simulate, noPrompt=param.noPrompt, exitIfNo=True)
    print()

    # clean application folder with old data
    if param.installed:
        utils.execute_command(cmd=["rm", "-rf", param.dataFolder], verbose=param.verbose, simulate=param.simulate)

    # create alias symlink to target
    utils.execute_command(cmd=["ln", "-sf",  "--no-dereference", targetDataFolder, param.dataFolder], verbose=param.verbose, simulate=param.simulate)
    _save_log(param, param.dataFolder)

    if not os.path.exists(param.symlink):
        utils.execute_command(cmd=["ln", "-sf",  "--no-dereference", param.dataFolder, param.symlink], verbose=param.verbose, simulate=param.simulate)
        _save_log(param, param.symlink)
        
def menu(param):
    """Install menu entries (*.desktop)."""
    # see: https://help.ubuntu.com/community/UnityLaunchersAndDesktopFiles
    # see: https://developer.gnome.org/integration-guide/stable/desktop-files.html.en
    param.print_param("Install menu entries")
    print()
    DESKTOP_DIR = "/usr/share/applications/"
    ICON_DIR = "/usr/share/pixmaps/"
    for file in param.files:
        if file.endswith(".desktop"):
            dst = os.path.join(DESKTOP_DIR,  os.path.basename(file))
            if not os.path.exists(dst) or utils.prompt_yes_no(msg="Overwrite '" + dst + "'? (Y/N) ", simulate=param.simulate, noPrompt=param.noPrompt):
                #utils.execute_command(cmd=["desktop-file-install", file], verbose=param.verbose, simulate=param.simulate)
                utils.execute_command(cmd=["cp", "--force", file, dst], verbose=param.verbose, simulate=param.simulate)
                utils.execute_command(cmd=["chmod", "+xr", dst], verbose=param.verbose, simulate=param.simulate)
                _save_log(param,  dst)
        elif file.endswith(".png"):
            dst = os.path.join(ICON_DIR,  os.path.basename(file))
            if not os.path.exists(dst) or utils.prompt_yes_no(msg="Overwrite '" + dst + "'? (Y/N) ", simulate=param.simulate, noPrompt=param.noPrompt):
                utils.execute_command(cmd=["cp", "--force", file, dst], verbose=param.verbose, simulate=param.simulate)
                utils.execute_command(cmd=["chmod", "+r", dst], verbose=param.verbose, simulate=param.simulate)
                _save_log(param,  dst)
        else:
            print("Unsupported file format: " + file)

def path(param):
    """Add executable to PATH."""
    # see: http://www.linuxquestions.org/questions/linux-desktop-74/adding-a-script-to-path-828517/
    param.print_param("Create symlink for PATH")
    print()
    PATH_DIR = "/usr/local/bin/"
    if param.cmdName is not None and len(param.files) > 1:
        raise Exception("Too many files given")
    for file in param.files:
        if os.access(file,  os.X_OK):
            baseName = os.path.basename(file)
            if param.cmdName is not None:
                baseName = param.cmdName
            dst = os.path.join(PATH_DIR, baseName)
            if not os.path.exists(dst) or utils.prompt_yes_no(msg="Overwrite '" + dst + "'? (Y/N) ", simulate=param.simulate, noPrompt=param.noPrompt):
                utils.execute_command(cmd=["ln", "--force",  "-s", file, dst], verbose=param.verbose, simulate=param.simulate)
                _save_log(param,  dst)
        else:
            raise Exception("File is not executable: " + file)

def list_app(param):
    """List applications."""
    if param.name is None:
        if os.path.exists(INSTALL_DIR):
            files = sorted(os.listdir(INSTALL_DIR))
            if len(files) == 0:
                # no applications installed
                return
            print("Installed applications:")
            for file in files:
                dataFolder= os.path.join(INSTALL_DIR,  file)
                if os.path.isdir(dataFolder) or os.path.islink(dataFolder):
                    folder = os.path.join(ROOT_DIR,  file)
                    target = os.path.realpath(folder)
                    print(" {0:<15}: {1} -> {2}".format(file, folder, target))
#                    print(" {0:<15}: {1}".format(file, folder, target))
#                    print(" " + " " * 15 + "  -> {2}".format(file, folder, target))
    else:
        param.print_param("List application")
        print()
        files = list()
        files.extend(_read_log(param,  CMD_INSTALL))
        files.extend(_read_log(param,  CMD_UPDATE))
        files.extend(_read_log(param,  CMD_ALIAS))
        files.extend(_read_log(param,  CMD_MENU))
        files.extend(_read_log(param,  CMD_PATH))
        files.sort()
        # remove duplicates
        files = set(files)
        print("Related files/folders:")
        for file in files:
            print(" {0}".format(file))

def _create_param(args):
    """Creates param"""
    param = InstallParam()
    param.command = args.command if args.command is not None else CMD_LIST
    if hasattr(args, "name") and args.name is not None:
        param.name = args.name
        param.symlink = ROOT_DIR + args.name
        param.dataFolder = INSTALL_DIR + args.name
        param.installed = os.path.exists(param.symlink) or os.path.islink(param.symlink)
    if hasattr(args, "target"):
        param.targetName = args.target
        param.targetSymlink = ROOT_DIR + args.target
    if hasattr(args, "exclude") and args.exclude is not None:
        param.exclusions.extend(args.exclude)
    param.files = args.file if hasattr(args, "file") else list()
    param.owner = args.owner if hasattr(args, "owner") else None
    param.skipDirs = args.skipDirs if hasattr(args, "skipDirs") else False
    param.menuOnly = args.menuOnly if hasattr(args, "menuOnly") else False
    param.pathOnly = args.pathOnly if hasattr(args, "pathOnly") else False
    param.cmdName = args.cmdName if hasattr(args, "cmdName") else None
    param.noPrompt = args.noPrompt if hasattr(args, "noPrompt") else False
    param.verbose = args.verbose if hasattr(args, "verbose") else False
    param.simulate = args.simulate if hasattr(args, "simulate") else False
    # validate param
    if param.symlink is not None and param.symlink + "/" == INSTALL_DIR:
        raise Exception("Illegal data folder: " + INSTALL_DIR)
    for file in param.files:
        if not os.path.exists(file) or not os.path.isfile(file):
            raise Exception("File does not exist or is invalid: " + file)
    return param

if __name__ == "__main__":
    try:
        # parse arguments
        parser = argparse.ArgumentParser(description="OPTional Package Tool: Installer for non-standard applications to " + ROOT_DIR, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("--version", action="version", version=utils.get_version("OPTional Package Tool", "2.0"))
        subparsers = parser.add_subparsers(title="Commands", dest="command", help="available commands", description="Supported commands to handle applications")
        # install
        installParser = subparsers.add_parser(CMD_INSTALL, help="install application (removes pre-installed application)", description="Installs an application by removing and copying")
        installParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        installParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        installParser.add_argument("-y", "--yes", action="store_true", dest="noPrompt", help="answer all questions with yes")
        installParser.add_argument("--exclude", action="append", help="exclude file")
        installParser.add_argument("--owner", help="owner of all installed files", default="root")
        installParser.add_argument("--skip-dirs", action="store_true", dest="skipDirs", help="skip container directories of archive file")
        installParser.add_argument("name", help="application name")
        installParser.add_argument("file", nargs="+", help="installation file")
        # update
        updateParser = subparsers.add_parser(CMD_UPDATE, help="update application (retain pre-installed application)", description="Updates an application by overwriting")
        updateParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        updateParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        updateParser.add_argument("-y", "--yes", action="store_true", dest="noPrompt", help="answer all questions with yes")
        updateParser.add_argument("--exclude", action="append", help="exclude file")
        updateParser.add_argument("--owner", help="owner of all installed files", default="root")
        updateParser.add_argument("--skip-dirs", action="store_true", dest="skipDirs", help="skip container directories of archive file")
        updateParser.add_argument("name", help="application name")
        updateParser.add_argument("file", nargs="+", help="installation file")
        # alias
        aliasParser = subparsers.add_parser(CMD_ALIAS, help="create an alias for an application", description="Create an alias for an installed application")
        aliasParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        aliasParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        aliasParser.add_argument("-y", "--yes", action="store_true", dest="noPrompt", help="answer all questions with yes")
        aliasParser.add_argument("name", help="application alias")
        aliasParser.add_argument("target", help="target application name (must already be installed)")
        # menu
        menuParser = subparsers.add_parser(CMD_MENU, help="create menu entry", description="Create a menu entry by .desktop file")
        menuParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        menuParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        menuParser.add_argument("-y", "--yes", action="store_true",  dest="noPrompt", help="answer all questions with yes")
        menuParser.add_argument("name", help="application name")
        menuParser.add_argument("file", nargs="+", help="*.desktop/*.png file")
        # path
        pathParser = subparsers.add_parser(CMD_PATH, help="add application to PATH", description="Add application to PATH by creating a symlink")
        pathParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        pathParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        pathParser.add_argument("-y", "--yes", action="store_true", dest="noPrompt", help="answer all questions with yes")
        pathParser.add_argument("--command", dest="cmdName", help="command name in PATH")
        pathParser.add_argument("name", help="application name")
        pathParser.add_argument("file", nargs="+", help="executable file")
        # remove
        removeParser = subparsers.add_parser(CMD_REMOVE, help="remove application/alias", description="Removes an application or alias")
        removeParser.add_argument("-n", "--dry-run", action="store_true", dest="simulate", help="simulate installation process")
        removeParser.add_argument("-v", "--verbose", action="store_true", help="print verbose output")
        removeParser.add_argument("-y", "--yes", action="store_true", dest="noPrompt", help="answer all questions with yes")
        removeParser.add_argument("--path-only", action="store_true", dest="pathOnly", help="remove path symlinks only")
        removeParser.add_argument("--menu-only", action="store_true", dest="menuOnly", help="remove menu entries only")
        removeParser.add_argument("name", help="application name or alias")
        # list
        listParser = subparsers.add_parser(CMD_LIST, help="list installed applications", description="List all installed applications or all files belonging to one application")
        listParser.add_argument("name", nargs="?", help="application name")
        
        args = parser.parse_args()

        if os.geteuid() != 0:
            exit("Root privileges required")
        if args.command is None:
            parser.print_help()
            exit(0)

        # create param
        param = _create_param(args)
        
        if param.command in (CMD_INSTALL):
            install(param)
        elif param.command in (CMD_UPDATE):
            update(param)
        elif param.command in (CMD_REMOVE):
            remove(param)
        elif param.command in (CMD_MENU):
            menu(param)
        elif param.command in (CMD_ALIAS):
            alias(param)
        elif param.command in (CMD_PATH):
            path(param)
        elif param.command in (CMD_LIST):
            list_app(param)

    except Exception as e:
        print(e)
        raise e
        exit(1)

