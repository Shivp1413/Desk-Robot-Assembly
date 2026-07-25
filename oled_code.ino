#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define OLED_SDA 6
#define OLED_SCL 5
#define OLED_RESET -1

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  OLED_RESET
);


void star(int x, int y) {
  display.drawPixel(x,y,SSD1306_WHITE);
  display.drawPixel(x-1,y,SSD1306_WHITE);
  display.drawPixel(x+1,y,SSD1306_WHITE);
  display.drawPixel(x,y-1,SSD1306_WHITE);
  display.drawPixel(x,y+1,SSD1306_WHITE);
}


void balloon(int x, int y) {

  display.drawCircle(x,y,7,SSD1306_WHITE);
  display.drawPixel(x,y+8,SSD1306_WHITE);
  display.drawLine(x,y+9,x,y+20,SSD1306_WHITE);

}


// HAPPY FACE

void happyFace(int frame) {

  display.clearDisplay();


  // Text
  display.setTextSize(1);
  display.setCursor(35,0);
  display.println("I'M HAPPY");


  // Stars
  star(10,15);
  star(25,8);
  star(105,12);
  star(115,25);


  // Floating balloon
  balloon(105,20+(frame%5));


  // Face
  display.drawCircle(55,38,22,SSD1306_WHITE);


  // Eyes blink
  if(frame%10==0) {

    display.drawLine(46,32,52,32,SSD1306_WHITE);
    display.drawLine(58,32,64,32,SSD1306_WHITE);

  } else {

    display.fillCircle(49,32,2,SSD1306_WHITE);
    display.fillCircle(61,32,2,SSD1306_WHITE);

  }


  // Cheeks
  display.drawCircle(40,41,2,SSD1306_WHITE);
  display.drawCircle(70,41,2,SSD1306_WHITE);


  // Curved smile
  int y=48+(frame%2);

  display.drawPixel(45,y,SSD1306_WHITE);
  display.drawPixel(46,y+2,SSD1306_WHITE);
  display.drawLine(47,y+3,63,y+3,SSD1306_WHITE);
  display.drawPixel(64,y+2,SSD1306_WHITE);
  display.drawPixel(65,y,SSD1306_WHITE);


  display.display();

}



// SAD FACE WITH TEARS

void sadFace(int frame) {

  display.clearDisplay();


  // Text
  display.setTextSize(1);
  display.setCursor(38,0);
  display.println("I'M SAD");


  // Face
  display.drawCircle(64,35,23,SSD1306_WHITE);


  // Sad eyes
  display.fillCircle(56,31,3,SSD1306_WHITE);
  display.fillCircle(72,31,3,SSD1306_WHITE);


  // Eyebrows
  display.drawLine(50,25,57,22,SSD1306_WHITE);
  display.drawLine(71,22,78,25,SSD1306_WHITE);


  // Sad curved mouth
  display.drawPixel(53,48,SSD1306_WHITE);
  display.drawPixel(54,47,SSD1306_WHITE);
  display.drawLine(55,46,73,46,SSD1306_WHITE);
  display.drawPixel(72,47,SSD1306_WHITE);
  display.drawPixel(73,48,SSD1306_WHITE);


  // Falling tears
  int tear1 = 38 + (frame%18);
  int tear2 = 42 + ((frame+8)%18);


  display.fillCircle(56,tear1,2,SSD1306_WHITE);
  display.fillCircle(72,tear2,2,SSD1306_WHITE);


  display.display();

}



void setup() {

  Wire.begin(OLED_SDA,OLED_SCL);

  display.begin(
    SSD1306_SWITCHCAPVCC,
    0x3C
  );

}



void loop() {


  // Happy for 4 seconds
  for(int i=0;i<33;i++) {

    happyFace(i);
    delay(120);

  }


  // Sad for 4 seconds
  for(int i=0;i<33;i++) {

    sadFace(i);
    delay(120);

  }

}