# Opt.py

Opt.py is an installation manager for the /opt directory. The /opt directory is reserved for all the software and add-on packages that are not part of the default installation. 

If a program does not provide an installation file for the package manager used (e.g. APT), the program can be installed in /opt. However, this installation can be tedious: 
- Files must be unpacked
- $PATH variable must be extended
- Desktop entry must be created
- When uninstalling the program, all these changes should be undone.

To simplify this, Opt.py provides a simple command line interface modeled after APT. 

Supported file formats are: .zip, .tar.bz2, .tar, .tar.gz, .tgz, .tar.xz

## Install
1. Install Python3 and pip as follows in Ubuntu/Debian Linux:
```
sudo apt install python3.6
```

2. Download Opt.py and set execute permissions:
```
curl -LJO https://github.com/byte-cook/opt/raw/main/opt.py
curl -LJO https://github.com/byte-cook/opt/raw/main/fileutil.py
chmod +x opt.py
```

3. Install Opt.py in the /opt directory:
```
./opt.py install opt opt.py fileutil.py
```
The $PATH variable is automatically extended!

## Uninstall

Use this command:
```
./opt.py remove opt
```

## Example usage

General structure of the commands:
```
opt.py <command> <app-name> ...
```

List installed applications:
```
opt.py list
```

Install application:
```
opt.py install application-12-3 application-12.3.tar.gz
```

Install another version of the same application:
```
opt.py install application-19-81 application-19.81.tar.gz
```

Create alias ("application" refers to "application-12-3"):
```
opt.py alias application application-12-3
```

Extend $PATH variable:
```
opt.py path application /opt/application/application.sh
```

Add desktop entry:
```
opt.py desktop application application.desktop application.png
```

Change alias (application refers to application-19-81):
```
opt.py alias application application-19-81
```

Delete old version and all related files:
```
opt.py remove application-12-3
```

Delete all versions of this application:
```
opt.py remove application-19-81
opt.py remove application
```

## Testing

Run all tests:
```
test_opt.py
```

Run single test:
```
test_opt.py TestOpt.test_remove_unmanaged_forced
```

Clean up test directory:
```
test_opt.py TestOpt.test_clean
```

