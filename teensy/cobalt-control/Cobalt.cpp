#include "Cobalt.h"
#include "Arduino.h"

Cobalt::Cobalt(){
}


void Cobalt::begin() {
  analogWriteResolution(DAC_RESOLUTION); 
  analogReadResolution(13); 
  pinMode(LASER_PIN,OUTPUT);
  pinMode(AIN_PIN,INPUT);
  pinMode(POT_PIN,INPUT);
  BASE_VAL = map(NULL_VOLTAGE,0,1,0,DAC_RANGE/V_REF);
  if (MODE =='S'){analogWrite(LASER_PIN,BASE_VAL);}
  if (MODE =='B'){analogWrite(LASER_PIN,0);}
}


void Cobalt::_turn_on_binary(float amp){
  // Turn on the light instantaneously at a given amplitude. Scaled between 0 and 1 V
  int digAmp = map(amp,0,1,0,DAC_RANGE/V_REF);
  analogWrite(LASER_PIN,digAmp);
}

void Cobalt::_turn_off_binary(){
  // Turn off the light instataneously.
  analogWrite(LASER_PIN,0);
}

void Cobalt::_turn_on_sigm(float amp){
  // Turn on the light with a sigmoidal ramp Scales the ramp between a base amplitude (which is a voltage just below where the laser is on) to 1v.
  // The amplitude parameter scales maximum ramp.
  
  float sigmoidalValue;
  float t;
  uint startTime = micros();
  while ((micros() - startTime) < SIGM_RISETIME*1000) {
    t = float(micros() - startTime) / (SIGM_RISETIME *1000);
    sigmoidalValue = 1 / (1 + exp(-10 * (t - 0.5))); // Sigmoidal function
    sigmoidalValue = map(sigmoidalValue,0,1,BASE_VAL,DAC_RANGE/V_REF*amp);
    analogWrite(LASER_PIN, int(sigmoidalValue));
  }
}

void Cobalt::_turn_off_sigm(float amp){
  float sigmoidalValue;
  float t;
  uint startTime = micros();
  while ((micros() - startTime) < SIGM_RISETIME*1000) {
    t = float(micros() - startTime) / (SIGM_RISETIME *1000);
    sigmoidalValue = 1-(1 / (1 + exp(-10 * (t - 0.5)))); // Sigmoidal function
    sigmoidalValue = map(sigmoidalValue,0,1,BASE_VAL,DAC_RANGE/V_REF*amp);
    analogWrite(LASER_PIN, int(sigmoidalValue));
  }
  analogWrite(LASER_PIN, BASE_VAL);
}

void Cobalt::_turn_on(float amp){
  // Overload turn on function. Can either be in binary or sigmoidal mode
  switch (MODE){
    case 'B':
      _turn_on_binary(amp);
      break;
    case 'S':
      _turn_on_sigm(amp);
      break;
    default:
      _turn_on_sigm(amp);
  }
}

void Cobalt::_turn_off(float amp){
  // Overload turn off function. Can either be in binary or sigmoidal mode
  switch (MODE){
    case 'B':
      _turn_off_binary();
      break;
    case 'S':
      _turn_off_sigm(amp);
      break;
    default:
      _turn_off_sigm(amp);
  }
}

void Cobalt::pulse(float amp,uint dur_ms){
  // Run a single pulse with amplitude "amp"
  _turn_on(amp);
  int t_pulse_on = micros();
  while ((micros()-t_pulse_on)<(dur_ms*1000)){};
  _turn_off(amp);
}

void Cobalt::train(float amp,float freq_hz,uint dur_pulse,uint dur_train){
  // Run a sequence of pulses at a given amplitude and frequency
  // Also known as a pulse train
  // freq_hz - frequeny of stimulation
  // dur_pulse - duration of each pulse in the train 
  // dur_train- duration of the train
  // It is up to the user to make sure that the pulse duration is not too long for the frequency, and that the pulse duration is not 
  // longer than the train. 

  if (dur_pulse>dur_train){
    dur_pulse=dur_train-5;
  }
  uint full_duty_time = (1000.0/freq_hz)*1000; //in microseconds

  uint t_start_train = micros();

  while ((micros()-t_start_train)<dur_train*1000){
    uint t_start_pulse = micros();
    pulse(amp,dur_pulse);
    while((micros()-t_start_pulse)<full_duty_time){}
  }
}

void Cobalt::train_duty(float amp,float freq_hz, float duty, uint dur_train){
  // Run a sequence of pulses at a given frequency and duty cycle.
  // Also known as a pulse train
  // freq_hz - frequeny of stimulation
  // duty - percent of the cycle that the light should be on
  // dur_train - length of the train in ms

  if (duty>1){duty=1;}
  uint dur_pulse = (1000.0/freq_hz * duty);
  uint full_duty_time = (1000.0/freq_hz)*1000; //in microseconds
  uint t_start_train = micros();
  while ((micros()-t_start_train)<(dur_train*1000)){
    uint t_start_pulse = micros();
    pulse(amp,dur_pulse);
    while((micros()-t_start_pulse)<full_duty_time){}
  }
}

void Cobalt::run_10ms_tagging(int n){
  // Run a standard tagging of 10 ms pulses at full amplitude
  //n - number of pulses. Default is 75
  for (int ii=0; ii<n; ii++){
    pulse(1,10);
    delay(5000);
  }
}

void Cobalt::run_multiple_pulses(int n, float amp, uint dur_pulse, uint IPI){
  // Run a sequence of pulses seperated by a fixed interval
  // Equivalent to a train, but easier to program for a lot of single pulses
  for (int ii=0; ii<n; ii++){
    pulse(amp,dur_pulse);
    delay(IPI);
  }
}

void Cobalt::run_multiple_trains(int n, float amp, float freq_hz, uint dur_pulse, uint dur_train,uint intertrain_interval){
  for (int ii=0; ii<n; ii++){
    train(amp,freq_hz, dur_pulse, dur_train);
    delay(intertrain_interval);
  }
}


void Cobalt::phasic_stim_insp(uint n, float amp, uint dur_active,uint intertrial_interval){
    for (uint ii=0;ii<n;ii++){

  bool laser_on=false;
  _turn_off(NULL_VOLTAGE);

  
  uint t_start = millis();
  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);
    if ((ain_val>thresh_val) & !laser_on){
      _turn_on(amp);
      laser_on=true;
    }
    if ((ain_val<thresh_down) & laser_on){
      _turn_off(amp);
      laser_on=false;
    }
  }

  if (laser_on){_turn_off(amp);}
  delay(intertrial_interval);

}
}

void Cobalt::phasic_stim_insp_pulse(uint n, float amp, uint dur_active,uint intertrial_interval,uint pulse_dur){
    for (uint ii=0;ii<n;ii++){

  _turn_off(NULL_VOLTAGE);
  
  uint t_start = millis();
  bool have_stimmed = false;

  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);
    if ((ain_val>thresh_val) & !have_stimmed){
      pulse(amp, pulse_dur);
      have_stimmed=true;
    }
    if ((ain_val<thresh_down) & have_stimmed){
      have_stimmed=false;
    }
  }
  delay(intertrial_interval);

}
}

void Cobalt::phasic_stim_insp_train(uint n, float amp, float freq_hz, uint dur_ms, uint dur_active,uint intertrial_interval){
  for (uint ii=0;ii<n;ii++){

  _turn_off(NULL_VOLTAGE);
  bool is_insp=false;
    
  uint full_duty_time = (1000.0/freq_hz)*1000; //in microseconds

  uint last_stim_on = micros();
  uint t_start = millis();
  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);

    if ((ain_val>thresh_val)){

      is_insp = true;
    }
    if ((ain_val<thresh_down)){

      is_insp = false;
    }
    if (is_insp){
      if ((micros() - last_stim_on)>full_duty_time){
        last_stim_on = micros();
        pulse(amp,dur_ms);
        
      }
    }

  }
  delay(intertrial_interval);
  }
}


void Cobalt::phasic_stim_exp(uint n, float amp, uint dur_active,uint intertrial_interval){
    for (uint ii=0;ii<n;ii++){

  _turn_off(NULL_VOLTAGE);
  bool laser_on=false;
    
  uint t_start = millis();
  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);
    if ((ain_val>thresh_val) & laser_on){
      _turn_off(amp);
      laser_on=false;
    }
    if ((ain_val<thresh_down) & !laser_on){
      _turn_on(amp);
      laser_on=true;
    }
  }
  if (laser_on){_turn_off(amp);}
  delay(intertrial_interval);
}
}

void Cobalt::phasic_stim_exp_pulse(uint n, float amp, uint dur_active,uint intertrial_interval,uint pulse_dur){
    for (uint ii=0;ii<n;ii++){

  _turn_off(NULL_VOLTAGE);
    

  bool have_stimmed=false;

  uint t_start = millis();
  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);
    if ((ain_val>thresh_val) & have_stimmed){
      have_stimmed=false;
      
    }
    if ((ain_val<thresh_down) & !have_stimmed){
      pulse(amp, pulse_dur);
      have_stimmed=true;
    }
  }
  delay(intertrial_interval);
}
}

void Cobalt::phasic_stim_exp_train(uint n, float amp, float freq_hz, uint dur_ms, uint dur_active,uint intertrial_interval){
  for (uint ii=0;ii<n;ii++){

  _turn_off(NULL_VOLTAGE);
  bool is_insp=false;
    

  uint full_duty_time = (1000.0/freq_hz)*1000; //in microseconds

  uint last_stim_on = micros();
  uint t_start = millis();
  while ((millis()-t_start)<=dur_active){
    ain_val = analogRead(AIN_PIN);
    thresh_val =  get_thresh();
    thresh_down = int(float(thresh_val)*0.9);

    if ((ain_val>thresh_val)){

      is_insp = true;
    }
    if ((ain_val<thresh_down)){

      is_insp = false;
    }
    if (!is_insp){
      if ((micros() - last_stim_on)>full_duty_time){
        last_stim_on = micros();
        pulse(amp,dur_ms);
        
      }
    }

  }
  delay(intertrial_interval);
  }
}

int Cobalt::poll_laser_power(float amp){
  _turn_on(amp);
  delay(100);
  uint power_int = 0;
  for (int i=0; i<20; i++){     
    power_int += analogRead(POWER_METER_PIN);
    delay(5);
  }
  uint average = power_int /20;
  _turn_off(amp);
  return average;
}

int Cobalt::get_thresh(){
  int readin = analogRead(POT_PIN);
  thresh_val = map(readin,0,8191,3000,5500);
  return thresh_val;
}