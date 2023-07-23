#!/usr/bin/env python3

import logging
import os
import subprocess
import sys

def get_version(prog, version):
    """Returns the version information."""
    return \
    "{prog} {version} \n".format(prog=prog, version=version) +\
    "Copyright (C) 2015 Christoph Korn\n" +\
    "License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.\n" +\
    "This is free software: you are free to change and redistribute it.\n" +\
    "There is NO WARRANTY, to the extent permitted by law.\n" +\
    "See <https://kobich.de> for more information.\n"

def config_logging(filename="python.log", level=logging.DEBUG):
    """Configures logging."""
    logging.basicConfig(filename=filename, level=level)

def findFile(fileName):
    """Searches for a file using following order:
    1. in $home directory: ~/.tools/<fileName>
    2. in script folder: <scriptDir>/<fileName>
    """
    file = os.path.expanduser("~user") + "/.tools/" + fileName
    if not os.path.exists(file): 
        file = os.path.dirname(os.path.abspath(__file__)) + "/" + fileName
    return file

def forceRoot(sudo="gksudo"):
    """Forces to be root; re-run script again if necessary."""
    euid = os.geteuid()
    if euid != 0:
        logging.debug("Script not started as root. Running sudo...")
        logging.debug(sys.executable)
        logging.debug(sys.argv)
        args = [sys.executable] + sys.argv
        # re-runs the script with sudo
        status = execute_command([sudo, _cmd_to_str(args)], verbose=True, ignoreError=True)
        exit(status)

def execute_command(cmd, shell=False, verbose=False, simulate=False, ignoreError=False, stdout=None, stderr=None):
    """Executes the given command."""
    if verbose or simulate:
        print(_cmd_to_str(cmd))
    if simulate:
        return None

    # flush stdout to keep output synchronized
    sys.stdout.flush()
        
    logging.debug("Command: " + _cmd_to_str(cmd))
    p = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr, universal_newlines=True)
    p.wait()
    if not ignoreError and p.poll() != 0:
        raise Exception("Command failed: " + " ".join(cmd))
    return p

def open_terminal(cmd=None, verbose=False, simulate=False):
    """Opens the terminal and run the given command if available."""
    if cmd is None:
        command = ["gnome-terminal"]
    else:
        command = ["gnome-terminal", "-e", "bash -c '" + _cmd_to_str(cmd) + "; echo; read -n 1 -p \"press any key to continue\"'"]
    execute_command(command, shell=False, verbose=verbose, simulate=simulate)

def _cmd_to_str(cmd):
    """Converts a command to string."""
    if isinstance(cmd, str):
        return cmd
    cmdStr = ""
    for c in cmd:
        # add quotes if parameter contains a space
        if " " in c:
            cmdStr += "\"" + c + "\" "
        else:
            cmdStr += c + " "
    cmdStr = cmdStr.strip()
    return cmdStr

def parse_xml_tag(child, tag, required=False):
    """Helper function to analyse a xml tag."""
    if child.find(tag) is not None:
        if child.find(tag).text is not None:
            return child.find(tag).text
    #print("Attribute " + tag + " not set")
    if required:
        raise Exception("Required tag missing: " + tag)
    return None 

def parse_xml_tag_list(child, tag):
    """Helper function to analyse a xml tag which can be occure several times."""
    items = list()
    tags = child.findall(tag)
    for tag in tags:
        items.append(tag.text)
    return items

def parse_xml_attrib(child, attr, required=False, default=None):
    """Helper function to analyse a xml attribute."""
    if attr in child.attrib:
        return child.attrib[attr]
    if required:
        raise Exception("Required attribute missing: " + attr)
    return default 

def prompt_yes_no(msg="Do you want to continue? (Y/N) ", simulate=False, noPrompt=False, exitIfNo=False):
    """Prompt for yes or no."""
    if simulate:
        return True
    if noPrompt:
        return True
    while True:
        print(msg, end="") 
        v = input()
        if v in ("n", "N"):
            if exitIfNo:
                exit(0)
            return False
        elif v in ("y", "Y"):
            return True

def get_files(tops, recursive=False, normCase=True, returnTopDirs=False):
    """Returns all files and folders."""
    dirList = list()
    fileList = list()
    for top in tops:
        top = os.path.abspath(top)
        if normCase:
            top = os.path.normcase(top)
        if os.path.isdir(top):
            if returnTopDirs:
                dirList.append(top)
            if recursive:
                for (root, dirs, files) in os.walk(top):
                    for d in dirs:
                        d = os.path.join(root, d)
                        if normCase:
                            d = os.path.normcase(d)
                        dirList.append(d)
                    for f in files:
                        f = os.path.join(root, f)
                        if normCase:
                            f = os.path.normcase(f)
                        fileList.append(f)
            else:
                for f in os.listdir(top):
                    f = os.path.join(top, f)
                    if normCase:
                        f = os.path.normcase(f)
                    if os.path.isdir(f):
                        dirList.append(f)
                    else:
                        fileList.append(f)
        else:
            fileList.append(top)
    # remove duplicates
    dirList = set(dirList)
    fileList = set(fileList)
    return dirList, fileList

