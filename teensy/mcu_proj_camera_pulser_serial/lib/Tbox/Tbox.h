
#ifndef TBOX_H
#define TBOX_H

#include "Arduino.h"

class Tbox
{
  public:
    Tbox();
    void begin();
    void attach_O2(int pin);
    void attach_RA(int pin);
    void attach_HC(int pin);
    void attach_HO(int pin);
    void attach_N2(int pin);
    void attach_CPAP(int pin);
    void attach_REC(int pin);
    void attach_TONE(int pin);
    void attachDefaults();

    void open_O2();
    void open_RA();
    void open_HC();
    void open_HO();
    void open_N2();

    void wait(float wait_min);
    void start_recording();
    void stop_recording();
    void hering_breuer(uint n_reps, uint dur_ms, uint interstim_ms);
    void hering_breuer_start();
    void hering_breuer_stop();
    void playAlert();
    void playTone(uint freq, uint duration);
    void syncUSV();

    int DAC_RESOLUTION=12;
    float DAC_RANGE=pow(2.0,float(DAC_RESOLUTION))-1;
    float V_REF=3.3;

  private:
    int _O2_PIN; 
    int _RA_PIN; 
    int _HC_PIN; 
    int _HO_PIN; 
    int _CPAP_PIN; 
    int _N2_PIN;
    int _TONE_PIN;
    int _REC_PIN;
    bool _USE_SERIAL;
    
    int _O2_PIN_DEFAULT=0; 
    int _RA_PIN_DEFAULT=1; 
    int _HC_PIN_DEFAULT=2; 
    int _HO_PIN_DEFAULT=3; 
    int _N2_PIN_DEFAULT = 4;
    int _CPAP_PIN_DEFAULT=5; 
    int _TONE_PIN_DEFAULT=12; 
    int _REC_PIN_DEFAULT = 13;

};
#endif
