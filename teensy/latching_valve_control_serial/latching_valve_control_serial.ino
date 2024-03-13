// Control the Lee latching valves by receiving serial commands
// Messages are two bytes. THe first byte is the command, the second byte tells which valve to apply to
// Begin with a character command: 'o' (open), 'c' (close), 'b' (binary). 
// The second byte is a uint_8 (1-8) or a bit array (e.g., 01101111). The bit array tells to open (1) or close (0) the corresponding valve.
// e.g. 00010110 is 22
// VALVES 3 and 4 are dead!
// TODO: test 
//
#include <ArCOM.h>

ArCOM teensyControl(Serial1);


const int out_1A = 14;
const int out_1B = 15;
const int led_1 = 17;

const int out_2A = 10;
const int out_2B = 11;
const int led_2 = 18;

const int out_5A = 8;
const int out_5B = 9;
const int led_5 = 19;

const int out_6A = 6;
const int out_6B = 7;
const int led_6 = 20;

const int out_7A = 4;
const int out_7B = 5;
const int led_7 = 21;

const int out_8A = 2;
const int out_8B = 3;
const int led_8 = 22;

int valveState[8] = {0,0,0,0,0,0,0,0};


void setup() {
  SerialUSB.begin(9600);
  Serial1.begin(115200);
  while (teensyControl.available()>0){teensyControl.readByte();}

  pinMode(out_1A,OUTPUT);
  pinMode(out_1B,OUTPUT);
  pinMode(led_1,OUTPUT);
  closeValve(1);
  
  pinMode(out_2A,OUTPUT);
  pinMode(out_2B,OUTPUT);
  pinMode(led_2,OUTPUT);
  closeValve(2);

  // pinMode(out_3A,OUTPUT);
  // pinMode(out_3B,OUTPUT);
  // pinMode(led_3,OUTPUT);
  // closeValve(3);
  
  // pinMode(out_4A,OUTPUT);
  // pinMode(out_4B,OUTPUT);
  // pinMode(led_4,OUTPUT);
  // closeValve(4);

  pinMode(out_5A,OUTPUT);
  pinMode(out_5B,OUTPUT);
  pinMode(led_5,OUTPUT);
  closeValve(5);
  
  pinMode(out_6A,OUTPUT);
  pinMode(out_6B,OUTPUT);
  pinMode(led_6,OUTPUT);
  closeValve(6);

  pinMode(out_7A,OUTPUT);
  pinMode(out_7B,OUTPUT);
  pinMode(led_7,OUTPUT);
  closeValve(7);

  pinMode(out_8A,OUTPUT);
  pinMode(out_8B,OUTPUT);
  pinMode(led_8,OUTPUT);
  closeValve(8);

  pinMode(13,OUTPUT);
  digitalWrite(13,HIGH);
  SerialUSB.println("Connected!");
}

void loop() {
   if (teensyControl.available() >=2) {
    char commandType = teensyControl.readChar();
    int valveID = teensyControl.readUint8(); 

    delay(2);
    switch (commandType) {
      case 'o':    
        openValve(valveID);
        teensyControl.writeUint8(255);
        break;
      case 'c':
        closeValve(valveID);
        teensyControl.writeUint8(255);
        break;
      case 'b': // set the state of several valves
        processBinaryControl(valveID);
        teensyControl.writeUint8(255);
        break;
      case 'q':
        //todo: implement valve query by checking state and writing to uint8 byte
        break;
      default:
        digitalWrite(13,LOW);
        delay(100);
        digitalWrite(13,HIGH);
        processBinaryControl(B00000000);
        teensyControl.writeUint8(255);
   }

   }

}

void processBinaryControl(uint bitArray){
  for (int i = 0; i < 8; i++) {
    closeValve(i+1);
    if (bitRead(bitArray, i)) { // Check if the bit is set
      openValve(i + 1); // Print the index (indices start from 1)
    }
  }
}

void closeValve(int valveNum){
  switch (valveNum){
    case 1:
      _close(out_1A,out_1B,led_1);

      break;
    case 2:
      _close(out_2A,out_2B,led_2);
      break;
    // case 3:
    //   _close(out_3A,out_3B,led_3);
    //   break;
    // case 4:
    //   _close(out_4A,out_4B,led_4);
    //   break;
    case 5:
      _close(out_5A,out_5B,led_5);
      break;
    case 6:
      _close(out_6A,out_6B,led_6);
      break;   
    case 7:
      _close(out_7A,out_7B,led_7);
      break;
    case 8:
      _close(out_8A,out_8B,led_8);
      break;
  }
  valveState[valveNum-1] = 0;
}

void openValve(int valveNum){
  switch (valveNum){
    case 1:
      _open(out_1A,out_1B,led_1);
      break;
    case 2:
      _open(out_2A,out_2B,led_2);
      break;
    // case 3:
    //   _open(out_3A,out_3B,led_3);
    //   break;
    // case 4:
    //   _open(out_4A,out_4B,led_4);
    //   break;
    case 5:
      _open(out_5A,out_5B,led_5);
      break;
    case 6:
      _open(out_6A,out_6B,led_6);
      break;
    case 7:
      _open(out_7A,out_7B,led_7);
      break;
    case 8:
      _open(out_8A,out_8B,led_8);
      break;

  }
  valveState[valveNum-1] = 1;
}


void _close(int out_A, int out_B, int led) {
  digitalWrite(out_A, LOW);  // Ensure valve is closed
  digitalWrite(out_B, HIGH);   // Ensure valve is closed
  digitalWrite(led, LOW);     // Turn off LED  
  delay(5);
  digitalWrite(out_A,LOW); 
  digitalWrite(out_B,LOW);
}


void _open(int out_A, int out_B, int led) {
  digitalWrite(out_A, HIGH);   // Ensure valve is open
  digitalWrite(out_B, LOW);  // Ensure valve is open
  digitalWrite(led ,HIGH);    // Turn on LED
  delay(5);
  digitalWrite(out_A,LOW);
  digitalWrite(out_B,LOW);
}

