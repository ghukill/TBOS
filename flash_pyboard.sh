echo "flashing pyboard"
rshell cp ./embedded/boot.py /flash/boot.py
rshell cp ./embedded/main.py /flash/main.py
rshell cp ./embedded/resistance_motor.py /flash/embedded/resistance_motor.py
rshell cp ./embedded/rpm_sensor.py /flash/embedded/rpm_sensor.py
rshell cp ./embedded/inputs.py /flash/embedded/inputs.py
echo "finis!"