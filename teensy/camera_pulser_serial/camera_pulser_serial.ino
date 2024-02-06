/* LED Blink, Teensyduino Tutorial #1
   http://www.pjrc.com/teensy/tutorial.html
 
   This example code is in the public domain.
*/
// Teensy 2.0 has the LED on pin 11
// Teensy++ 2.0 has the LED on pin 6
// Teensy 3.x / Teensy LC have the LED on pin 13
#include <ArCOM.h>
ArCOM pyControl(Serial1);

const int ledPin = 12;
const int touchPin = 4;
int val;
bool record = false;
int t1=micros();
int t2 = micros();
float fps = 120.0;
int inter_frame_interval = (int)((1.0/fps)*1000.0*1000.0);

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial1.begin(115200);
  
}

void loop() {
   if (pyControl.available() >=2) {
    char commandType = pyControl.readChar();
    switch (commandType) {
      case 'b':
        beginRecording();
        break;
      case 'e':
        endRecording();
        break;
   }
   }

  if (record){
    if((t2-t1)<inter_frame_interval){}
    else{
      t1=micros();
      digitalWrite(ledPin,HIGH);
      delay(2);// How long to keep the pin high.
      digitalWrite(ledPin,LOW);
    }
  }

  t2=micros();

}


void beginRecording(){
    int fps = pyControl.readUint8();
    inter_frame_interval = (int)((1.0/float(fps))*1000.0*1000.0);
    record = true;
}

void endRecording(){
    pyControl.readUint8();
    record=false;  
}
