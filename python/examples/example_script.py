"""
This script demonstrates how to use the nebPod controller to run some optogenetic stimulations and gas challenges
Assumes SpikeGLX is running and gates and triggers are set to remote control
"""
import sys
sys.path.append('D:/pyExpControl/python')
from nebPod import Controller

PORT = 'COM11'
controller = Controller(PORT)


# Start the expriment
# Preroll does a lot of initializing and is worth reading about in the documentation
# It starts the recording
controller.preroll() 
controller.present_gas('O2',60) # Present O2 for 60 seconds

#Assuming we have loaded an opto calibration file in preroll, map amplitude from power to volt
amp_mw = 10
amp = controller.mW_to_volts(amp_mw)


# Run 5, 100ms opto pulses at 3 second intervals
controller.run_pulse(
    pulse_duration_sec=0.1,
    amp=amp,
    n=5,
    interval=3,
)

controller.wait(10) # Wait for 10 seconds


# Loop through amplitudes at 5 and 10 mW and run 10 second inspiratory triggered hold stim
amps_mw = [5,10]
amps = controller.mW_to_volts(amps_mw)
for amp in amps:
    controller.phasic_stim(
        duration_sec=10,
        mode='h',
        phase='i',
        amp=amp
    )

controller.wait(10) # Wait for 10 seconds

# Run a 3 second expiratory triggered pulse stim at 10 mW
amp = controller.mW_to_volts(10)
controller.phasic_stim(
    duration_sec=3,
    phase='e',
    mode='p',
    amp=amp,
    pulse_duration_sec=0.1,
)

# Run a set of 10s optogenetic stimulation trains at 10 mW, 5, 10, and 20 Hzm for 5 repititions at 30 second intervals
amp = controller.mW_to_volts(10)
for freq in [5,10,20]:
    controller.run_train(
        duration_sec=10,
        freq=freq,
        n=5,
        interval=30,
        pulse_duration_sec=0.025,
        amp=amp
    )

controller.wait(10) # Wait for 10 seconds

controller.present_gas('room air',60)

controller.present_gas('O2',60)

# Present Hering Breuer stimulation for 5 seconds, 5 times, at 20 second intervals
controller.timed_hb(
    duration=5,
    n=5,
    interval=20
)

controller.stop_recording()

