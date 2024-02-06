#ifndef COBALT_H
#define COBALT_H

#include "Arduino.h"

class Cobalt
{
  public:
    Cobalt();
    void begin();
    void _turn_on(float amp);
    void _turn_off(float amp);
    int poll_laser_power(float amp);
    void pulse(float amp, uint dur_ms);
    void train(float amp, float freq_hz, uint dur_pulse, uint dur_train);
    void train_duty(float amp,float freq_hz, float duty, uint dur_train);
    void run_10ms_tagging(int n);
    void run_multiple_pulses(int n, float amp, uint dur_pulse, uint IPI);
    void run_multiple_trains(int n, float amp, float freq_hz, uint dur_pulse, uint dur_train,uint intertrain_interval);
    void phasic_stim_insp(uint n, float amp, uint dur_active,uint intertrial_interval);
    void phasic_stim_insp_pulse(uint n, float amp, uint dur_active,uint intertrial_interval, uint pulse_dur);
    void phasic_stim_insp_train(uint n, float amp, float freq_hz, uint dur_ms, uint dur_active,uint intertrial_interval);
    void phasic_stim_exp(uint n, float amp,uint dur_active,uint intertrial_interval);
    void phasic_stim_exp_train(uint n, float amp, float freq_hz, uint dur_ms, uint dur_active,uint intertrial_interval);
    void phasic_stim_exp_pulse(uint n, float amp, uint dur_active,uint intertrial_interval,uint pulse_dur);
    int LASER_PIN=A14; // A14 for teensy 3.2
    int AIN_PIN=23;
    int POT_PIN=15;
    int POWER_METER_PIN = A2; // Pin to read from the thorlabs powermeter
    char MODE='S';
    int DAC_RESOLUTION=12;
    float DAC_RANGE=pow(2.0,float(DAC_RESOLUTION))-1;
    float V_REF=3.3;
    float NULL_VOLTAGE=0.3;
    float BASE_VAL = map(NULL_VOLTAGE,0,1,0,DAC_RANGE/V_REF);
    float SIGM_RISETIME=2;
  private:
    void _turn_on_binary(float amp);
    void _turn_off_binary();
    void _turn_on_sigm(float amp);
    void _turn_off_sigm(float amp);
};
#endif
