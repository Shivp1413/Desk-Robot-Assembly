#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ================= PINS =================
// Your ESP32-S3 pins
#define OLED_SDA 6
#define OLED_SCL 5
#define SERVO_PIN 9

// ================= OLED =================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDRESS 0x3C

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  OLED_RESET
);

bool oledOK = false;

// ================= SERVO PWM =================
// Continuous rotation servo pulse values.
// These match your old ESP32Servo values approximately:
// write(90)  = stop  = 1500 us
// write(100) = right = about 1556 us
// write(80)  = left  = about 1444 us

#define SERVO_FREQ 50
#define SERVO_RES_BITS 14

#define STOP_US 1500
#define RIGHT_US 1556
#define LEFT_US 1444

// For old Arduino-ESP32 core fallback
#define SERVO_CHANNEL 0

// ================= FACE =================

#define FRAME_INTERVAL 120

enum FaceMode {
  FACE_HAPPY,
  FACE_SAD
};

FaceMode currentFace = FACE_HAPPY;

unsigned long lastFrameTime = 0;
uint32_t faceFrame = 0;

// ================= SEQUENCE =================

enum ActionType {
  ACTION_NONE,
  ACTION_FACE_WAIT,
  ACTION_SERVO_MOVE
};

ActionType currentAction = ACTION_NONE;

String inputLine = "";
String sequence = "";

int sequencePos = 0;
bool sequenceRunning = false;

unsigned long actionStartTime = 0;
unsigned long actionDuration = 0;

unsigned long lastInputTime = 0;
bool inputWaiting = false;

// =====================================================
// SERVO USING LEDC DIRECTLY
// =====================================================

uint32_t servoUsToDuty(uint32_t pulseUs) {
  uint32_t maxDuty = (1UL << SERVO_RES_BITS) - 1;
  return (uint32_t)(((uint64_t)pulseUs * maxDuty) / 20000UL);
}

bool initServoPWM() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  return ledcAttach(SERVO_PIN, SERVO_FREQ, SERVO_RES_BITS);
#else
  ledcSetup(SERVO_CHANNEL, SERVO_FREQ, SERVO_RES_BITS);
  ledcAttachPin(SERVO_PIN, SERVO_CHANNEL);
  return true;
#endif
}

void servoWriteUs(uint32_t pulseUs) {
  uint32_t duty = servoUsToDuty(pulseUs);

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(SERVO_PIN, duty);
#else
  ledcWrite(SERVO_CHANNEL, duty);
#endif
}

void stopServo() {
  servoWriteUs(STOP_US);
}

void startRight() {
  servoWriteUs(RIGHT_US);
}

void startLeft() {
  servoWriteUs(LEFT_US);
}

// =====================================================
// SMALL DRAWING FUNCTIONS
// =====================================================

void star(int x, int y) {
  if (!oledOK) return;

  display.drawPixel(x, y, SSD1306_WHITE);
  display.drawPixel(x - 1, y, SSD1306_WHITE);
  display.drawPixel(x + 1, y, SSD1306_WHITE);
  display.drawPixel(x, y - 1, SSD1306_WHITE);
  display.drawPixel(x, y + 1, SSD1306_WHITE);
}

void balloon(int x, int y) {
  if (!oledOK) return;

  display.drawCircle(x, y, 7, SSD1306_WHITE);
  display.drawPixel(x, y + 8, SSD1306_WHITE);
  display.drawLine(x, y + 9, x, y + 20, SSD1306_WHITE);
}

// =====================================================
// HAPPY FACE
// =====================================================

// =====================================================
// HAPPY FACE WITH RISING BALLOONS
// =====================================================

void happyFace(uint32_t frame) {
  if (!oledOK) return;

  display.clearDisplay();

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setTextWrap(false);

  display.setCursor(1, 0);
  display.print(" Input your text");

  star(10, 15);
  star(25, 8);
  star(105, 12);
  star(115, 25);

  // ---------- Rising balloons ----------
  // Each balloon starts below the screen and floats up.
  // Total travel: from y=90 up to y=-25 (fully off top), range = 115 px

  // Balloon 1: right side, normal speed
  int b1 = 90 - (int)((frame * 2) % 115);
  balloon(105, b1);

  // Balloon 2: left side, slower
  int b2 = 90 - (int)(((frame + 20) * 1) % 115);
  balloon(14, b2);

  // Balloon 3: middle-right, faster
  int b3 = 90 - (int)(((frame + 45) * 3) % 115);
  balloon(90, b3);

  // Balloon 4: middle-left, medium speed
  int b4 = 90 - (int)(((frame + 70) * 2) % 115);
  balloon(30, b4);

  // ---------- Face ----------
  display.drawCircle(55, 38, 22, SSD1306_WHITE);

  if (frame % 10 == 0) {
    display.drawLine(46, 32, 52, 32, SSD1306_WHITE);
    display.drawLine(58, 32, 64, 32, SSD1306_WHITE);
  } else {
    display.fillCircle(49, 32, 2, SSD1306_WHITE);
    display.fillCircle(61, 32, 2, SSD1306_WHITE);
  }

  display.drawCircle(40, 41, 2, SSD1306_WHITE);
  display.drawCircle(70, 41, 2, SSD1306_WHITE);

  int y = 48 + (frame % 2);

  display.drawPixel(45, y, SSD1306_WHITE);
  display.drawPixel(46, y + 2, SSD1306_WHITE);
  display.drawLine(47, y + 3, 63, y + 3, SSD1306_WHITE);
  display.drawPixel(64, y + 2, SSD1306_WHITE);
  display.drawPixel(65, y, SSD1306_WHITE);

  display.display();
}

// =====================================================
// SAD FACE WITH ORIGINAL FALLING TEARS
// =====================================================

void sadFace(uint32_t frame) {
  if (!oledOK) return;

  display.clearDisplay();

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setTextWrap(false);

  // 2-line text
  display.setCursor(16, 0);
  display.print("im SAD, please");

  display.setCursor(0, 10);
  display.print(" Input your text here");

  // Face moved down
  display.drawCircle(64, 41, 23, SSD1306_WHITE);

  // Eyes
  display.fillCircle(56, 37, 3, SSD1306_WHITE);
  display.fillCircle(72, 37, 3, SSD1306_WHITE);

  // Eyebrows
  display.drawLine(50, 31, 57, 28, SSD1306_WHITE);
  display.drawLine(71, 28, 78, 31, SSD1306_WHITE);

  // Sad mouth
  display.drawPixel(53, 54, SSD1306_WHITE);
  display.drawPixel(54, 53, SSD1306_WHITE);
  display.drawLine(55, 52, 73, 52, SSD1306_WHITE);
  display.drawPixel(72, 53, SSD1306_WHITE);
  display.drawPixel(73, 54, SSD1306_WHITE);

  // Tears kept
  int tear1 = 44 + (frame % 14);
  int tear2 = 48 + ((frame + 6) % 14);

  display.fillCircle(56, tear1, 2, SSD1306_WHITE);
  display.fillCircle(72, tear2, 2, SSD1306_WHITE);

  display.display();
}

// =====================================================
// FACE CONTROL
// =====================================================

void drawFaceNow() {
  if (!oledOK) return;

  if (currentFace == FACE_HAPPY) {
    happyFace(faceFrame);
  } else {
    sadFace(faceFrame);
  }
}

void setHappyFace() {
  currentFace = FACE_HAPPY;
  faceFrame = 0;
  drawFaceNow();
  lastFrameTime = millis();
}

void setSadFace() {
  currentFace = FACE_SAD;
  faceFrame = 0;
  drawFaceNow();
  lastFrameTime = millis();
}

void updateFaceAnimation() {
  if (!oledOK) return;

  unsigned long now = millis();

  if (now - lastFrameTime >= FRAME_INTERVAL) {
    lastFrameTime = now;
    drawFaceNow();
    faceFrame++;
  }
}

// =====================================================
// COMMAND PARSING
// =====================================================

char toUpperChar(char c) {
  if (c >= 'a' && c <= 'z') {
    return c - 32;
  }

  return c;
}

bool isSeparator(char c) {
  return c == ' ' || c == '\t' || c == ',';
}

String getNextToken() {
  while (sequencePos < sequence.length() && isSeparator(sequence.charAt(sequencePos))) {
    sequencePos++;
  }

  if (sequencePos >= sequence.length()) {
    return "";
  }

  int start = sequencePos;

  while (sequencePos < sequence.length() && !isSeparator(sequence.charAt(sequencePos))) {
    sequencePos++;
  }

  return sequence.substring(start, sequencePos);
}

bool parseToken(String token, char &cmd, uint32_t &value) {
  token.trim();

  if (token.length() < 2) {
    return false;
  }

  cmd = toUpperChar(token.charAt(0));

  uint32_t number = 0;

  for (int i = 1; i < token.length(); i++) {
    char c = token.charAt(i);

    if (c < '0' || c > '9') {
      return false;
    }

    number = number * 10 + (c - '0');
  }

  if (number == 0) {
    return false;
  }

  value = number;
  return true;
}

// =====================================================
// SEQUENCE CONTROL
// =====================================================

void finishSequence() {
  stopServo();

  sequenceRunning = false;
  currentAction = ACTION_NONE;
  sequence = "";
  sequencePos = 0;

  Serial.println("Sequence finished");
  Serial.println("Last face keeps animating");
}

void cancelSequence() {
  stopServo();

  sequenceRunning = false;
  currentAction = ACTION_NONE;
  sequence = "";
  sequencePos = 0;

  Serial.println("Sequence cancelled");
}

void beginNextAction() {
  while (sequenceRunning) {
    String token = getNextToken();

    if (token.length() == 0) {
      finishSequence();
      return;
    }

    char cmd;
    uint32_t value;

    if (!parseToken(token, cmd, value)) {
      Serial.print("Bad token ignored: ");
      Serial.println(token);
      continue;
    }

    if (cmd == 'H') {
      stopServo();
      setHappyFace();

      currentAction = ACTION_FACE_WAIT;
      actionStartTime = millis();
      actionDuration = value * 1000UL;

      Serial.print("Happy for ");
      Serial.print(value);
      Serial.println(" seconds");

      return;
    }

    if (cmd == 'S') {
      stopServo();
      setSadFace();

      currentAction = ACTION_FACE_WAIT;
      actionStartTime = millis();
      actionDuration = value * 1000UL;

      Serial.print("Sad for ");
      Serial.print(value);
      Serial.println(" seconds");

      return;
    }

    if (cmd == 'R') {
      startRight();

      currentAction = ACTION_SERVO_MOVE;
      actionStartTime = millis();
      actionDuration = value;

      Serial.print("Right ");
      Serial.print(value);
      Serial.println(" ms");

      return;
    }

    if (cmd == 'L') {
      startLeft();

      currentAction = ACTION_SERVO_MOVE;
      actionStartTime = millis();
      actionDuration = value;

      Serial.print("Left ");
      Serial.print(value);
      Serial.println(" ms");

      return;
    }

    Serial.print("Unknown token ignored: ");
    Serial.println(token);
  }
}

void startSequence(String newSequence) {
  newSequence.trim();

  if (newSequence.length() == 0) {
    return;
  }

  stopServo();

  sequence = newSequence;
  sequencePos = 0;
  sequenceRunning = true;
  currentAction = ACTION_NONE;

  Serial.println();
  Serial.print("Starting sequence: ");
  Serial.println(sequence);

  beginNextAction();
}

void updateSequence() {
  if (!sequenceRunning) {
    return;
  }

  if (currentAction == ACTION_NONE) {
    beginNextAction();
    return;
  }

  unsigned long now = millis();

  if (now - actionStartTime >= actionDuration) {
    if (currentAction == ACTION_SERVO_MOVE) {
      stopServo();
    }

    currentAction = ACTION_NONE;
    beginNextAction();
  }
}

// =====================================================
// SERIAL INPUT
// =====================================================

void runInputLine() {
  inputLine.trim();

  if (inputLine.length() == 0) {
    inputWaiting = false;
    return;
  }

  if (inputLine.equalsIgnoreCase("X") || inputLine.equalsIgnoreCase("STOP")) {
    cancelSequence();
  } else {
    startSequence(inputLine);
  }

  inputLine = "";
  inputWaiting = false;
}

void readSerialInput() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      runInputLine();
      continue;
    }

    if (c >= 32 && c <= 126) {
      inputLine += c;
      lastInputTime = millis();
      inputWaiting = true;
    }
  }

  // Allows Serial Monitor "No line ending" too
  if (inputWaiting && millis() - lastInputTime > 400) {
    runInputLine();
  }
}

// =====================================================
// SETUP
// =====================================================

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("BOOTING...");

  Serial.println("Starting servo PWM...");

  bool servoOK = initServoPWM();

  if (servoOK) {
    stopServo();
    Serial.println("Servo PWM OK");
  } else {
    Serial.println("Servo PWM FAILED");
  }

  Serial.println("Starting OLED...");

  Wire.begin(OLED_SDA, OLED_SCL);

  oledOK = display.begin(
    SSD1306_SWITCHCAPVCC,
    OLED_ADDRESS,
    true,
    false
  );

  if (oledOK) {
    Serial.println("OLED OK");

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setTextWrap(false);
    display.display();

    setHappyFace();
  } else {
    Serial.println("OLED FAILED");
    Serial.println("Servo will still work.");
    Serial.println("Try OLED address 0x3D if needed.");
  }

  Serial.println();
  Serial.println("==============================");
  Serial.println("OLED + Servo Sequence Control");
  Serial.println("==============================");
  Serial.println("Commands:");
  Serial.println("H5    = happy face for 5 seconds");
  Serial.println("S3    = sad face for 3 seconds");
  Serial.println("R800  = servo right for 800 ms");
  Serial.println("L500  = servo left for 500 ms");
  Serial.println("X     = stop/cancel");
  Serial.println();
  Serial.println("Example:");
  Serial.println("H5 R800 S3 L500 H2 R1000");
  Serial.println("==============================");
}

// =====================================================
// LOOP
// =====================================================

void loop() {
  readSerialInput();
  updateSequence();
  updateFaceAnimation();
}
