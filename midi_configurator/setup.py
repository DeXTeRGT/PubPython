import cx_Freeze

exe = [cx_Freeze.Executable("DWSC.py",targetName="DWCONF" ,base = "Win32GUI", icon='icon.ico')] # <-- HERE

cx_Freeze.setup(
    name = "MIDI SWC",
    version = "1.0",
    options = {"build_exe": {"packages": ["pyqt5", "configparser", "serial"],  
        "include_files": ["resources", "config.ini", "ui"], 'include_msvcr': True}},
    executables = exe
)