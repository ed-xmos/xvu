XVU Audio Utility
=================

XVU (Xmos VU) is a host side utility written in Python that captures low-overhead xscope_int() instrumentation probes from your xcore app and turns the output into:

* A real time decibel meter with a peak hold function
* A wav file recorder
* An audio output from your host (Will be slightly glitchy due to rate mismatch)

The tool is tested with Xmos tools version 14.3.4.

Usage 
-----

You need to *simultaneously* run the firmware and the xvu script. They communicate via a port on the localhost::

  xvu.py  -r 48000 -p 6231

and::

  xrun --xscope-port localhost:6231 my_test_app.xe

The run command runs the binary and forwards the debug output over xscope to a port. The xvu.py script listens to the port and decodes the messages. 

VU Meter example
----------------

Here is what the VU meter looks like to run:
 
xvu.py  -r 48000 -p 6231
Please start target app: xrun --xscope-port localhost:6231 <binary.xe>
Connected on localhost: 6231
Expecting xscope_int data: 32b @ 48000Hz
 
Raw mic     -17.56dB -10.27dB  *********************--@--
Processed   -19.63dB -10.27dB  ********************---@--
 
Wav file capture usage example
------------------------------

xvu.py -r 16000 -p 6231 -w ./micData.wav

xrun --xscope-port localhost:6231 app_voice_processing.xe 


Performance
-----------

It copes OK with 2 channels at 48k on my 2014 i5 macbook, so should be able to do Multiple channels at 16k.

Enabling xscope
---------------

Please see the following for a simple example::

  http://www.xcore.com/viewtopic.php?f=48&t=6939


Options
-------

Here is the help output from the utility:

usage: xvu.py [-h] [-r SAMP_RATE] [-s SAMP_DEPTH] [-p PORT] [-w WAV_FILE]
              [-m MONITOR] [-n]
 
XMOS Audio Probe Tool
 
optional arguments:
  -h, --help            show this help message and exit
  -r SAMP_RATE, --samp_rate SAMP_RATE
                        Sample rate in Hz (default: 16000)
  -s SAMP_DEPTH, --samp-depth SAMP_DEPTH
                        Number of bits in audio samples from device
                        xscope_int() output (default: 32)
  -p PORT, --port PORT  Port of localhost used to communicate with xrun
                        (default: 6363)
  -w WAV_FILE, --wav-file WAV_FILE
                        Write wav file (default: None)
  -m MONITOR, --monitor MONITOR
                        Live monitor audio output of a probe. WARNING: May
                        contain glitches (default: None)
  -n, --no-vu           Disable VU (default: False)
