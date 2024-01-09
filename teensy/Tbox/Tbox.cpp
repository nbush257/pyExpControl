#include "Tbox.H"
#include "Arduino.h"
//Much of this is deprecated by the new python serial controller. Organizes valve, audio, and recording control.
Tbox::Tbox()
{
}

void Tbox::begin()
{
    attachDefaults();
}

void Tbox::attach_O2(int pin)
{
    _O2_PIN = pin;
    pinMode(_O2_PIN, OUTPUT);
    digitalWrite(_O2_PIN, LOW);
}
void Tbox::attach_RA(int pin)
{
    _RA_PIN = pin;
    pinMode(_RA_PIN, OUTPUT);
    digitalWrite(_RA_PIN, LOW);
}
void Tbox::attach_HC(int pin)
{
    _HC_PIN = pin;
    pinMode(_HC_PIN, OUTPUT);
    digitalWrite(_HC_PIN, LOW);
}
void Tbox::attach_HO(int pin)
{
    _HO_PIN = pin;
    pinMode(_HO_PIN, OUTPUT);
    digitalWrite(_HO_PIN, LOW);
}
void Tbox::attach_N2(int pin)
{
    _N2_PIN = pin;
    pinMode(_N2_PIN, OUTPUT);
    digitalWrite(_N2_PIN, LOW);
}
void Tbox::attach_CPAP(int pin)
{
    _CPAP_PIN = pin;
    pinMode(_CPAP_PIN, OUTPUT);
    digitalWrite(_CPAP_PIN, HIGH);
}
void Tbox::attach_REC(int pin)
{
    _REC_PIN = pin;
    pinMode(_REC_PIN, OUTPUT);
    digitalWrite(_REC_PIN, LOW);
}

void Tbox::attach_TONE(int pin)
{
    _TONE_PIN = pin;
    pinMode(_TONE_PIN, OUTPUT);
    digitalWrite(_TONE_PIN, LOW);
}

void Tbox::attachDefaults()
{
    // Attch the default pins and open oxygen as the rig is designed on 2023-08-16
    // O2 -   0
    // RA -   1
    // HC -   2
    // HO -   3
    // N2 -   4
    // CPAP - 5
    // TONE - 12
    // REC -  13
    attach_O2(_O2_PIN_DEFAULT);
    attach_RA(_RA_PIN_DEFAULT);
    attach_HC(_HC_PIN_DEFAULT);
    attach_HO(_HO_PIN_DEFAULT);
    attach_N2(_N2_PIN_DEFAULT);
    attach_CPAP(_CPAP_PIN_DEFAULT);
    attach_REC(_REC_PIN_DEFAULT);
    attach_TONE(_TONE_PIN_DEFAULT);
    digitalWrite(_O2_PIN, HIGH);
}

void Tbox::open_O2()
{
    digitalWrite(_O2_PIN, HIGH);
    digitalWrite(_RA_PIN, LOW);
    digitalWrite(_HC_PIN, LOW);
    digitalWrite(_HO_PIN, LOW);
    digitalWrite(_N2_PIN, LOW);
}

void Tbox::open_RA()
{
    digitalWrite(_O2_PIN, LOW);
    digitalWrite(_RA_PIN, HIGH);
    digitalWrite(_HC_PIN, LOW);
    digitalWrite(_HO_PIN, LOW);
    digitalWrite(_N2_PIN, LOW);
}

void Tbox::open_HC()
{
    digitalWrite(_O2_PIN, LOW);
    digitalWrite(_RA_PIN, LOW);
    digitalWrite(_HC_PIN, HIGH);
    digitalWrite(_HO_PIN, LOW);
    digitalWrite(_N2_PIN, LOW);
}

void Tbox::open_HO()
{
    digitalWrite(_O2_PIN, LOW);
    digitalWrite(_RA_PIN, LOW);
    digitalWrite(_HC_PIN, LOW);
    digitalWrite(_HO_PIN, HIGH);
    digitalWrite(_N2_PIN, LOW);
}

void Tbox::open_N2()
{
    digitalWrite(_O2_PIN, LOW);
    digitalWrite(_RA_PIN, LOW);
    digitalWrite(_HC_PIN, LOW);
    digitalWrite(_HO_PIN, LOW);
    digitalWrite(_N2_PIN, HIGH);
}


void Tbox::wait(float wait_min)
{
    // Delay by a predetermined amount of time (in minutes)
    // 


    uint wait_ms = uint(wait_min * 60 * 1000);
    uint t_start_pause = millis();
    elapsedMillis updateTimer = 100000; // Make this large so we print right away
    bool alerted = false;
    while ((millis() - t_start_pause) < wait_ms)
    {

        // Manual shortcut of the settle time

        // Update monitor every 30s
        if (updateTimer >= 30000)
        {
            updateTimer = 0;
        }
        if ((int(millis()) - int(t_start_pause) - int(wait_ms)) > -30000)
        {
            if (!alerted)
            {
                playAlert();
                alerted = true;
                updateTimer = 0;
            }
        }
    }
}

void Tbox::start_recording()
{
    digitalWrite(_REC_PIN, HIGH);
}

void Tbox::stop_recording()
{
    // Stop the recording by setting the record pin to low and turn on O2

    digitalWrite(_REC_PIN, LOW);
    open_O2();
    delay(5000);

}

void Tbox::hering_breuer(uint n_reps, uint dur_ms, uint interstim_ms)
{
    // Run the Hering Breuer stimulations by closing the CPAP solenoid briefly
    // n_reps - number of HB repitions to do
    // dur_ms - duration to have the solenoid closed in milliseconds
    // interstim_ms - duration between stimulations in milliseconds

    for (uint ii = 0; ii < n_reps; ii++)
    {
        digitalWrite(_CPAP_PIN, LOW);
        delay(dur_ms);
        digitalWrite(_CPAP_PIN, HIGH);
        delay(interstim_ms);
    }
}

void Tbox::hering_breuer_start(){
    digitalWrite(_CPAP_PIN, LOW);
}

void Tbox::hering_breuer_stop(){
    digitalWrite(_CPAP_PIN, HIGH);

}

void Tbox::playAlert()
{
    // Play a tone to alert the user
    tone(_TONE_PIN, 1000, 500);
}

void Tbox::playTone(uint freq, uint duration)
{
    // Play a tone to alert the user
    tone(_TONE_PIN, freq, duration);
}


void Tbox::syncUSV()
{
    // Play a sequence of tones that can be used to synchronize the audio recording with the ephys
    tone(_TONE_PIN, 1000, 100);
    delay(350);
    tone(_TONE_PIN, 2000, 100);
    delay(350);
    tone(_TONE_PIN, 5000, 500);
    delay(750);
}