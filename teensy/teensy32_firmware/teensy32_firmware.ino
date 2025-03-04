// Requires Cobalt and Tbox modules by NEB. 
// The cobalt module provides control over an analog out that is sent to a cobalt MLD laser. REQUIRES TEENSY WITH A REAL DAC (3.2, 3.6? NOT 4.x)
// The tbox module mostly provides default pin mappings for our experiments. Most of its job was UI over serial, but now that has been put into python. TODO: deprecate the old tbox stuff.
//Have to hardwire/hardcode the serial ports for lack of better knowledge at this point.

#include <ArCOM.h>
#include <Cobalt.h>
#include <Tbox.h>
ArCOM pyControl(SerialUSB);
ArCOM cameraPulser(Serial2);
ArCOM olfactometer(Serial3); 
Cobalt cobalt;
Tbox tbox;

const int numValves = 5;  // Number of gas valves to be included in the valve control. These should only have one open at a time
int valves[numValves] = {0, 1, 2, 3, 4};  // Pins that the valves are on
const int statusPin = 22;

const int numGpPins = 2;
int gpPins[numGpPins] = {17,11};

void setup() {
  SerialUSB.begin(115200);
  Serial2.begin(115200);
  Serial3.begin(115200);
  // Flush any serial data in the buffer
  while (pyControl.available()>0) {pyControl.readByte();}
  while (cameraPulser.available()>0) {cameraPulser.readByte();}
  while (olfactometer.available()>0) {olfactometer.readByte();}
  // Initialize valve pins as OUTPUT
  for (int i = 0; i < numValves; i++) {
    pinMode(valves[i], OUTPUT);
  }
  pinMode(statusPin,OUTPUT);
  digitalWrite(statusPin,HIGH);
  delay(100);
  digitalWrite(statusPin,LOW);

// Set GP output pins low
  for (int i = 0; i < numGpPins; i++) {
    pinMode(gpPins[i], OUTPUT);
    digitalWrite(gpPins[i],LOW);
  }
  

  cobalt.begin();
  tbox.begin();
  tbox.attachDefaults();
}


void loop() {
  if (pyControl.available() >=2) {
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
        processCommandO(); // opto power measure
        break;
      case 'c': // Cobalt
        processCommandC();
        break;
      case 's': // Olfactometer ([S]mell)
        processCommandS();
        break;

      // Add more cases if needed
    }
    // Write back to the pycontroller to let it know we finished that command
    pyControl.writeUint8(255);

  }

}

//olfactometer (smell) Simply forward the command
void processCommandS(){
  char subcommand = pyControl.readChar();
  int valve = pyControl.readUint8();
  switch (subcommand) {
  case 'o':
    olfactometer.writeChar('o');
    break;
  case 'c':
    olfactometer.writeChar('c');
    break;
  case 'b':
    olfactometer.writeChar('b');
    break;
}
  olfactometer.writeUint8(valve);
  digitalWrite(statusPin, HIGH);
  while (olfactometer.available()==0){} // Wait for response
  while (olfactometer.available()>0){olfactometer.readByte();} // Clear response from olfactometer
  digitalWrite(statusPin, LOW);
}


void processCommandC(){
  char subcommand = pyControl.readChar();
  switch(subcommand){
    case 'm': //'modify' - modify the cobalt object
      char mode = pyControl.readChar();
      
      int power_meter_pin = pyControl.readUint8();    
      int null_voltage_uint8 = pyControl.readUint8();    
      float null_voltage = static_cast<float>(null_voltage_uint8) / 255;
      cobalt.MODE = mode;
      cobalt.POWER_METER_PIN = power_meter_pin;
      cobalt.NULL_VOLTAGE = null_voltage;
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
      tbox.start_recording();
      break;
    case 'e':
      tbox.stop_recording();
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
    case 'v':
      processCameraCommands();
      break;
    case 'h':
      runPhasic_HB();
      break;
}
}
//Manual
void processCommandM() {
  char subcommand = pyControl.readChar();
  int duration = pyControl.readUint16();
  int p = pyControl.readUint8();
  int usePin = gpPins[p];
  switch (subcommand) {
    case 'p':
      digitalWrite(usePin,HIGH);
      delayMicroseconds(duration*1000);
      digitalWrite(usePin,LOW);
      break;
    case 'l':
      digitalWrite(usePin,LOW);
      break;
    case 'h':
      digitalWrite(usePin,HIGH);
      break;
}
}


void processCameraCommands(){
  char subcommand = pyControl.readChar();
  int fps = pyControl.readUint8();
  switch (subcommand) {
    case 'b':
      cameraPulser.writeChar('b');
      cameraPulser.writeUint8(fps);
      break;
    case 'e':
      cameraPulser.writeChar('e');
      cameraPulser.writeUint8(fps);
      break;
}
  while (cameraPulser.available()==0){} // Wait for response
  while (cameraPulser.available()>0){cameraPulser.readByte();} // Clear response 
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
void runPhasic_HB() {
  // Run phasic triggered Hering breuer from a serial input

  char phase = pyControl.readChar();
  char mode = pyControl.readChar();
  int n = pyControl.readUint8();                     // Number of stim epochs
  int duration = pyControl.readUint16();             // Epoch duration
  int intertrain_interval = pyControl.readUint16();  // Time between stimulation periods


  int pulse_dur = 0;
  int freq = 0;

  // TODO: allow for single pulses or trains at I-on, E-ON
  // i,e for insp/exp
  // h - hold, p - pulse, t - train
  switch (phase) {
    case 'e':  // Expiratory
      // switch (mode){
      //   case 'h':
      //     cobalt.phasic_stim_exp(n,amp_f,duration,intertrain_interval);
      //     break;
      //   case 'p':
      //     pulse_dur = pyControl.readUint8();
      //     cobalt.phasic_stim_exp_pulse(n,amp_f,duration,intertrain_interval,pulse_dur);
      //     break;
      //   case 't':
      //     pulse_dur = pyControl.readUint8();
      //     freq = pyControl.readUint8();
      //     cobalt.phasic_stim_exp_train(n,amp_f,float(freq),pulse_dur,duration,intertrain_interval);
      //     break;
      // }
      break;
    case 'i':
      switch (mode) {
        case 'h':
          _phasic_HB_insp(n, duration, intertrain_interval);
          break;
          // case 'p':
          //   pulse_dur = pyControl.readUint8();
          //   cobalt.phasic_stim_insp_pulse(n,amp_f,duration,intertrain_interval,pulse_dur);
          //   break;
          // case 't':
          //   pulse_dur = pyControl.readUint8();
          //   freq = pyControl.readUint8();
          //   cobalt.phasic_stim_insp_train(n,amp_f,float(freq),pulse_dur,duration,intertrain_interval);
          //   break;
      }
      break;
  }
}

void _phasic_HB_insp(uint n, uint dur_active,uint intertrial_interval) {

  //Inspiratory triggered hering breuer stims
  for (uint ii = 0; ii < n; ii++) {

    bool stim_on = false;
    tbox.hering_breuer_stop();
    int ain_val = analogRead(cobalt.AIN_PIN);
    int thresh_val = analogRead(cobalt.POT_PIN);
    int thresh_down = int(float(thresh_val) * 0.9);

    uint t_start = millis();
    while ((millis() - t_start) <= dur_active) {
      ain_val = analogRead(cobalt.AIN_PIN);
      thresh_val = analogRead(cobalt.POT_PIN);
      thresh_down = int(float(thresh_val) * 0.9);
      if ((ain_val > thresh_val) & !stim_on) {
        tbox.hering_breuer_start();
        stim_on = true;
      }
      if ((ain_val < thresh_down) & stim_on) {
        tbox.hering_breuer_stop();
        stim_on = false;
      }
    }

    if (stim_on) {tbox.hering_breuer_stop(); }
    delay(intertrial_interval);
  }
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

