#include <ESP32Servo.h>

Servo panServo;

#define SERVO_PIN 9

#define STOP_SPEED 90
#define RIGHT_SPEED 100
#define LEFT_SPEED 80

void moveRight(int timeMs) {
  Serial.print("Right ");
  Serial.print(timeMs);
  Serial.println(" ms");

  panServo.write(RIGHT_SPEED);
  delay(timeMs);

  panServo.write(STOP_SPEED);
  delay(50);
}

void moveLeft(int timeMs) {
  Serial.print("Left ");
  Serial.print(timeMs);
  Serial.println(" ms");

  panServo.write(LEFT_SPEED);
  delay(timeMs);

  panServo.write(STOP_SPEED);
  delay(50);
}


void setup() {

  Serial.begin(115200);
  delay(1000);

  panServo.setPeriodHertz(50);
  panServo.attach(SERVO_PIN, 1000, 2000);

  // No movement at startup
  panServo.write(STOP_SPEED);

  Serial.println("==============================");
  Serial.println("360 Servo Sequence Control");
  Serial.println("==============================");
  Serial.println("Example:");
  Serial.println("L800 R1000 L800 R1000");
}


void loop() {

  if (Serial.available()) {

    String command = Serial.readStringUntil('\n');
    command.trim();

    int start = 0;

    while (start < command.length()) {

      // Find next space
      int space = command.indexOf(' ', start);

      String part;

      if (space == -1) {
        part = command.substring(start);
        start = command.length();
      } 
      else {
        part = command.substring(start, space);
        start = space + 1;
      }

      part.trim();

      if (part.length() < 2)
        continue;


      char direction = part.charAt(0);
      int duration = part.substring(1).toInt();


      if (direction == 'R' || direction == 'r') {
        moveRight(duration);
      }

      else if (direction == 'L' || direction == 'l') {
        moveLeft(duration);
      }
    }

    Serial.println("Sequence finished");
  }
}