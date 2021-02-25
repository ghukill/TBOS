echo "flashing pyboard"
rshell cp ./boot.py /flash/boot.py
rshell cp ./main.py /flash/main.py
rshell cp ./controller/embedded.py /flash/controller/embedded.py
echo "finis."