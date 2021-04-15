echo "flashing pyboard"
#rshell cp ./embedded/boot.py /flash/boot.py
rshell --buffer-size=1 cp ./embedded/main.py /flash/main.py
#rshell cp ./embedded/resistance_motor.py /flash/embedded/resistance_motor.py
#rshell cp ./embedded/rpm_sensor.py /flash/embedded/rpm_sensor.py
#rshell cp ./embedded/inputs.py /flash/embedded/inputs.py
#rshell cp ./embedded/debug.py /flash/embedded/debug.py
#rshell cp ./embedded/lcd.py /flash/embedded/lcd.py
echo "finis!"