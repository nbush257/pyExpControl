/* LED Blink, Teensyduino Tutorial #1
   http://www.pjrc.com/teensy/tutorial.html
 
   This example code is in the public domain.
*/
// Teensy 2.0 has the LED on pin 11
// Teensy++ 2.0 has the LED on pin 6
// Teensy 3.x / Teensy LC have the LED on pin 13
#include <ArCOM.h>
#include <Bounce2.h>
ArCOM pyControl(Serial1);

const int ledPin = 12;
const int statusPin = 13;
const int interruptPin = 4;
Bounce2::Button button = Bounce2::Button();
bool record = false;
int t1=micros();
int t2 = micros();
float fps = 120.0;
int inter_frame_interval = (int)((1.0/fps)*1000.0*1000.0);

bool ledState=LOW;
void setup() {
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin,LOW);  

  pinMode(statusPin,OUTPUT);
  digitalWrite(statusPin,ledState);  

  button.attach(interruptPin,INPUT_PULLDOWN);
  button.interval(5);
  button.setPressedState(HIGH); 

  
  Serial1.begin(115200);
  record=false;
  t1 = micros();
  t2 = micros();
  while (pyControl.available()){pyControl.readByte();}
  
  
}

void loop() {
  button.update();
  if (button.pressed()){
    toggleRecording();
    }

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
    digitalWrite(statusPin,HIGH);
}

void endRecording(){
    pyControl.readUint8();
    record=false;  
    digitalWrite(ledPin,LOW);
    digitalWrite(statusPin,LOW);
}

void toggleRecording(){
  digitalWrite(statusPin,HIGH);
  delay(100);
  digitalWrite(statusPin,LOW);

  if (record){
    record=false;  
    digitalWrite(ledPin,LOW);
    digitalWrite(statusPin,LOW);
  }
  else{
    inter_frame_interval = (int)((1.0/float(fps))*1000.0*1000.0);
    record = true;
    digitalWrite(statusPin,HIGH);
  }
}
