import cx_Freeze

exe = [cx_Freeze.Executable("SerialToMQTT.py",targetName="SERMQTT")] # <-- HERE

cx_Freeze.setup(
    name = "SerialToMQTT",
    version = "1.0",
    options = {"build_exe": {"packages": ["configparser", "serial"],  
        "include_files": ["config", "log"], 'include_msvcr': True}},
    executables = exe
)