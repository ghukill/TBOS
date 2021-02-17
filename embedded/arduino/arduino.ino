/*
  TBOS resistance driver v1
*/

// include the library code:
#include <LiquidCrystal.h>

#define ENABLE 5
#define DIRA 3
#define DIRB 4

// initialize the library with the numbers of the interface pins
LiquidCrystal lcd(7, 8, 9, 10, 11, 12);

// setup motor constants
int lowerBound = -1;
int upperBound = -1;
int servoSweepPause = 0;
int servoReadPause = 0;
int stepInc = -1;
const int proximityThreshold = 3;

// flags and global variables
bool settled = false;
int sensorValue = 0;
int previousTargetValue = 0;
int initialLevel = 5;
int targetValue = -1;

void setup()
{

  // setup comm
  Serial.begin(9600);

  // setup constants based on debug mode
  int debugSensor = analogRead(A1);
  if (debugSensor > 0){
    Serial.println("DEBUG MODE: false");
    lowerBound = 240;
    upperBound = 640;
    servoSweepPause = -1;
    servoReadPause = -1;
  }
  else {
    Serial.println("DEBUG MODE: true");
    lowerBound = 10;
    upperBound = 610;
    servoSweepPause = 6;
    servoReadPause = 50; 
  }
  stepInc = int(int(upperBound - lowerBound) / 20);
  targetValue = upperBound - (stepInc * initialLevel);
  Serial.print("initial target: ");
  Serial.println(targetValue);
    
  Serial.print("step: ");
  Serial.println(stepInc);

  // clear LCD
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Get your TBOS on");
  lcd.setCursor(0, 1);
  String t1 = "Start level: ";
  String t2 = t1 + initialLevel;
  lcd.print(t2);
  delay(3000);
  lcd.clear();

  // setup motor control
  pinMode(ENABLE, OUTPUT);
  pinMode(DIRA, OUTPUT); // currently counter-clockwise
  pinMode(DIRB, OUTPUT); // currently clockwise
}

void updateLCD(int sensorValue, int targetValue)
{

  // Function to update the LCD with current and target values

  lcd.setCursor(9, 0);
  lcd.print("       ");
  lcd.setCursor(9, 1);
  lcd.print("       ");
  String topRowBase = "Current: ";
  String topRow = topRowBase + sensorValue;
  lcd.setCursor(0, 0);
  lcd.print(topRow);
  String bottomRowBase = "Target:  ";
  String bottomRow = bottomRowBase + targetValue;
  lcd.setCursor(0, 1);
  lcd.print(bottomRow);
}

void adjustPosition(int sensorValue, int targetValue)
{
  // send message that adjusting
  Serial.print("Position adjust amount: ");
  Serial.println(sensorValue - targetValue);
  lcd.setCursor(12, 0);
  lcd.print(" ");
  if (sensorValue > targetValue)
  {
    // move counter-clockwise (DIRA)
    digitalWrite(ENABLE, HIGH);
    digitalWrite(DIRA, HIGH);
    digitalWrite(DIRB, LOW);
  }
  else
  {
    // move clockwise (DIRB)
    digitalWrite(ENABLE, HIGH);
    digitalWrite(DIRA, LOW);
    digitalWrite(DIRB, HIGH);
  }

  // DEBUG SERVO: move slowly and then stop
  if (servoSweepPause > 0) {
    delay(servoSweepPause);
    digitalWrite(ENABLE, LOW);
  }

}

void readChangeRequest() {
  if (Serial.available() > 0)
  {
    char targetValueChar = Serial.read();

    // increments
    if (targetValueChar == '+')
    {
      targetValue += stepInc;
    }
    else if (targetValueChar == '-')
    {
      targetValue -= stepInc;
    }
    else if (targetValueChar == 'e')
    {
      targetValue = upperBound;
    }
    else if (targetValueChar == 'h')
    {
      targetValue = lowerBound;
    }

    // bounds
    if (targetValue < lowerBound)
    {
      targetValue = lowerBound;
    }
    else if (targetValue > upperBound)
    {
      targetValue = upperBound;
    }

    settled = false;
    Serial.print("NEW TARGET: ");
    Serial.println(targetValue);
  }
}

void loop()
{
  
  // if settled, allow changes to value
  if (settled == true)
  {
    delay(250);
    readChangeRequest();
  }

  // get current sensor value
  if (servoReadPause > 0) { // helpful for letting voltage during pull come back
    delay(servoReadPause);
  }
  sensorValue = analogRead(A0);

  // update LCD
  updateLCD(sensorValue, targetValue);

  // if settled, do nothing
  if (settled)
  {
    lcd.setCursor(13, 0);
    lcd.print("set");
  }
  // if within threshold, set as settled and stop
  else if (abs(sensorValue - targetValue) <= proximityThreshold)
  {
    digitalWrite(ENABLE, LOW);
    settled = true;
    previousTargetValue = targetValue;
    lcd.setCursor(13, 0);
    lcd.print("set");
    Serial.println("settled");
  }
  else
  {
    // set settled
    settled = false;

    // adjust position
    adjustPosition(sensorValue, targetValue);
  }
}
