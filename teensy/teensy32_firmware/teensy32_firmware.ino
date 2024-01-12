// Requires Cobalt and Tbox modules by NEB. 
// The cobalt module provides control over an analog out that is sent to a cobalt MLD laser. REQUIRES TEENSY WITH A REAL DAC (3.2, 3.6? NOT 4.x)
// The tbox module mostly provides default pin mappings for our experiments. Most of its job was UI over serial, but now that has been put into python. TODO: deprecate the old tbox stuff.
#include <ArCOM.h>
#include <Cobalt.h>
#include <Tbox.h>
ArCOM pyControl(SerialUSB);
ArCOM cameraPulser(Serial2);
Cobalt cobalt;
Tbox tbox;

const int numValves = 5;  // Number of gas valves to be included in the valve control. These should only have one open at a time
int valves[numValves] = {0, 1, 2, 3, 4};  // Pins that the valves are on

void setup() {
  SerialUSB.begin(115200);
  Serial2.begin(115200);
  // Flush any serial data in the buffer
  while (pyControl.available()) {pyControl.readByte();}
  // Initialize valve pins as OUTPUT
  for (int i = 0; i < numValves; i++) {
    pinMode(valves[i], OUTPUT);
  }
  cobalt.begin();
  tbox.begin();
  tbox.attachDefaults();
}


void loop() {
  if (pyControl.available() >=2) {
    // pyControl.flush();
    // Instructions should always be at least two bytes. The first byte tells us which command class to run
    // Different command classes can have different trailing bytes that define parameters. If no further parameters are needed, the trailing byte will be discarded.

    // Get the command class
    char commandType = pyControl.readChar();

    // Run the appropriate subcommand
    switch (commandType) {
      case 'v':
        processCommandV(); // valves
        break;
      case 'p':
        processCommandP(); // pulses
        break;
      case 't':
        processCommandT(); // trains
        break;
      case 'm': // manual - use to set an arbitrary pin high or low.
        processCommandM();
        break;
      case 'a':
        processCommandA(); // Auxiliary functions (Take a second char)
        break;
      case 'r':
        processCommandR(); // Record control
        break;
      case 'h':
        processCommandH(); // Hering Breuer
        break;
      case 'o':
        processCommandO();
        break;
      case 'c': // Cobalt
        processCommandC();
        break;

      // Add more cases if needed
    }
    // Write back to the pycontroller to let it know we finished that command
    pyControl.writeUint8(255);

  }

}

void processCommandC(){
  char subcommand = pyControl.readChar();
  switch(subcommand){
    case 'm': //'modify' - modify the cobalt object
      char mode = pyControl.readChar();
      
      int power_meter_pin = pyControl.readUint8();    
      cobalt.MODE = mode;
  
      cobalt.POWER_METER_PIN = power_meter_pin;
      cobalt.begin();


    break;

  }
}

void processCommandO(){ // opto utilities
  char subcommand = pyControl.readChar();
  int amp = pyControl.readUint8();
  float amp_f = amp2float(amp);
  uint power;

  switch (subcommand){
    case 'p':
      power = cobalt.poll_laser_power(amp_f);
      pyControl.writeUint16(power);
      break;
    //poll
    case 'o':
      cobalt._turn_on(amp_f);
      break;
    // laser on
    case 'x':
      cobalt._turn_off(amp_f);
      break;
    //laser off
  }
}


void processCommandH() {
  char subcommand = pyControl.readChar();
  switch (subcommand) {
    case 'e':
      tbox.hering_breuer_stop();
      break;
    case 'b':
      tbox.hering_breuer_start();
      break;

}
}

// ------------------------------------- //
// Sub commands that are passed on to the Tbox or Cobalt objects
// ------------------------------------- //
//Record control
void processCommandR() {
  char subcommand = pyControl.readChar();
  switch (subcommand) {
    case 'b':
      cameraPulser.writeChar('b');
      cameraPulser.writeInt8(120);
      break;
    case 'e':
      cameraPulser.writeChar('e');
      cameraPulser.writeInt8(120);
      break;
}
}

//Valves (exclusive)
void processCommandV() {
  int valveNumber = pyControl.readUint8();
  if (valveNumber >= 0 && valveNumber < numValves) {
    setValves(valveNumber);
  }
}

//Pulses
void processCommandP() {
  int duration = pyControl.readUint16();
  int amp = pyControl.readUint8();
  float amp_f = amp2float(amp);

  cobalt.pulse(amp_f,duration);
}

//Trains
void processCommandT() {
  int duration = pyControl.readUint16();
  int freq = pyControl.readUint8();
  int amp = pyControl.readUint8();
  int pulse_dur = pyControl.readUint8();
  float amp_f = amp2float(amp);
  cobalt.train(amp_f,float(freq), pulse_dur, duration);
}

void processCommandA() {
  char subcommand = pyControl.readChar();
  switch (subcommand) {
    case 'p':
      runPhasic(); // phasic stimulations
      break;
    case 't':
      runTagging();
      break;
    case 'a':
      playTone();
      break;
    case 's':
      tbox.syncUSV();
      break;
}
}

void playTone() {
  int freq = pyControl.readUint16();
  int duration = pyControl.readUint16();
  tbox.playTone(freq,duration);
  delay(duration);
}

void runTagging() {
  int n = pyControl.readUint8(); // Number of stims
  cobalt.run_10ms_tagging(n);
}


void runPhasic() {
  // Run phasic triggered stimulations from a serial input

  char phase = pyControl.readChar();
  char mode = pyControl.readChar();
  int n = pyControl.readUint8(); // Number of stim epochs
  int duration = pyControl.readUint16();  // Epoch duration
  int intertrain_interval = pyControl.readUint16();  // Time between stimulation periods
  int amp = pyControl.readUint8(); // Amplitude
  float amp_f = amp2float(amp);
  
  int pulse_dur=0;
  int freq=0;

 // TODO: allow for single pulses or trains at I-on, E-ON
 // i,e for insp/exp
 // h - hold, p - pulse, t - train
  switch (phase) {
    case 'e': // Expiratory 
      switch (mode){
        case 'h':
          cobalt.phasic_stim_exp(n,amp_f,duration,intertrain_interval);
          break;
        case 'p':
          pulse_dur = pyControl.readUint8();
          cobalt.phasic_stim_exp_pulse(n,amp_f,duration,intertrain_interval,pulse_dur);
          break;
        case 't':
          pulse_dur = pyControl.readUint8();
          freq = pyControl.readUint8();
          cobalt.phasic_stim_exp_train(n,amp_f,float(freq),pulse_dur,duration,intertrain_interval);
          break;
      }
      break;
    case 'i':
      switch (mode){
        case 'h':
          cobalt.phasic_stim_insp(n,amp_f,duration,intertrain_interval);
          break;
        case 'p':
          pulse_dur = pyControl.readUint8();
          cobalt.phasic_stim_insp_pulse(n,amp_f,duration,intertrain_interval,pulse_dur);
          break;
        case 't':
          pulse_dur = pyControl.readUint8();
          freq = pyControl.readUint8();
          cobalt.phasic_stim_insp_train(n,amp_f,float(freq),pulse_dur,duration,intertrain_interval);
          break;
    }
      break;
}
}

void processCommandM() {
  //TODO: TEST
  int pin = pyControl.readUint8();
  int val = pyControl.readUint8();
  bool val_bool = bool(val); 
  digitalWrite(pin, val_bool);
}



// ------------------------------------- //
// Helper functions
// ------------------------------------- //

// Convinience function to set all but the
void setValves(int activeValve) {
  for (int i = 0; i < numValves; i++) {
    digitalWrite(valves[i], (i == activeValve) ? HIGH : LOW);
  }
}

float amp2float(int amp){
  float amp_f;
  amp_f = float(amp)/100.0;
  return amp_f;
}

