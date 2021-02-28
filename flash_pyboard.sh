echo "flashing pyboard"
rshell cp ./boot.py /flash/boot.py
rshell cp ./main.py /flash/main.py
rshell cp ./embedded/resistance_motor.py /flash/embedded/resistance_motor.py
rshell cp ./embedded/rpm_sensor.py /flash/embedded/rpm_sensor.py
echo "finis!"