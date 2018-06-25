#!/usr/bin/env python
import socket
import time
import sys
import argparse

import struct
import math

import pyaudio
import Queue

import wave


class vu():
  def __init__(self, name, max_int, samp_rate):
    #print "vu __init__"
    self.name = "{:12s}".format(name)
    self.peak = 0
    self.peak_time = time.time()
    self.old_time = time.time()
    self.decay_per_second = 0.01
    self.decay_constant = -math.log(self.decay_per_second)
    self.val = 0
    self.peak_hold_time = 3
    self.peak_updated = False
    self.max_int = float(max_int)
    self.update_counter = 0
    self.update_limit = 1 #For 100Hz update
    min_db = 100
    self.min_db = 10**(-min_db / 20) * max_int

  def update(self, block, idx):
    val = 0
    for i in range(block_size):
      val = block[i] if block[i] > val else val
    if val > max_int:
     return
    if val > self.val:
      self.val = val
    #Check for new peak value
    if self.val > self.peak:
      self.old_peak = self.peak
      self.peak = self.val
      self.peak_time = time.time()
    self.update_counter += 1
    if (self.update_counter == self.update_limit):  #Only do decay and display at 100Hz
      self.update_counter = 0
      self.display_log(self.val, self.peak, idx)
      curr_time = time.time()
      elapsed_time = curr_time - self.old_time
      #do decay
      #self.val = self.val * (self.decay_per_second * (1 - elapsed_time) ) #linear decay
      self.val = self.val * math.exp(-elapsed_time * self.decay_constant) #exponential decay
      self.old_time = curr_time
    #clear peak after time has elapsed
      if (curr_time - self.peak_time) > self.peak_hold_time:
        self.peak = self.val

  def set_vu_peak_hold_time(self, peak_hold_time):
    self.peak_hold_time = peak_hold_time

  #use terminal output for VU display
  def display_log(self, val, peak, idx):
    line = "\r"
    line += "\033[" + str(idx + 1) + "B" #down
    line += self.name
    log_peak = -100
    if (val > self.min_db):
      log_val = 20 * math.log(val / self.max_int, 10)
      val_str = "{:7.2f}dB".format(log_val)
    else:
      val_str = "    -inf "
      log_val = -100
    if (peak > self.min_db):
      log_peak = 20 * math.log(peak / self.max_int, 10)
      peak_str = "{:7.2f}dB  ".format(log_peak)
    else:
      peak_str = "    -inf   "
    line += val_str + peak_str
    last_time_peak = False
    for i in range (-78, 0, 3):
      if last_time_peak and log_peak < i:
        line += "@"
      elif log_val > i:
        line += "*"
      else:
        line += "-"
      if log_peak > i:
        last_time_peak = True
      else:
        last_time_peak = False

    line += "\r"
    line += "\033[" + str(idx + 1) + "A" #up
    sys.stdout.write(line)
    sys.stdout.flush()


class  xscope_handler():
  XSCOPE_SOCKET_MSG_EVENT_REGISTER       = 1
  XSCOPE_SOCKET_MSG_EVENT_RECORD         = 2
  XSCOPE_SOCKET_MSG_EVENT_STATS          = 3
  XSCOPE_SOCKET_MSG_EVENT_TARGET_DATA    = 4
  XSCOPE_SOCKET_MSG_EVENT_CONNECT        = 5
  XSCOPE_SOCKET_MSG_EVENT_ALL_REGISTERED = 6
  XSCOPE_SOCKET_MSG_EVENT_CLOCK          = 7
  XSCOPE_SOCKET_MSG_EVENT_PRINT          = 8

  XSCOPE_GET_REGISTRATION = bytearray(b'\x0B')

  def __init__(self, queue, args):
    self.connected = False
    self.running = True
    self.host = "localhost"
    self.args = args
    self.port = args.port
    self.queue = queue
    self.do_monitor = False
    self.n_vus = 0
    if type(args.monitor_channel) is int:
      self.do_monitor = True
    self.connect()

  def connect(self):
    print "Please start target app: xrun --xscope-port localhost:{} <binary.xe>".format(self.port)
    while not self.connected:
      try:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
      except:
        sys.stdout.write(".")
        sys.stdout.flush()
        try:
          time.sleep(1)
        except KeyboardInterrupt:
          sys.exit(0)
        continue
      self.connected = True
      print "\rConnected on {}: {}".format(self.host, self.port)
      print "Expecting xscope_int data: {}b @ {}Hz".format(args.samp_depth, args.samp_rate)
      """
      self.listen_thread = threading.Thread(target=self.listen, args=(self.sock,))
      self.listen_thread.demon = True
      self.listen_thread.start()
      """
      self.sock.sendall(xscope_handler.XSCOPE_GET_REGISTRATION)
      #print "Registering xscope probes:"
      try:
        self.listen(self.sock)
      except KeyboardInterrupt:
        self.running = False
        #on exit, move curson down into clean screen area
        print "\n" * self.n_vus
        continue

  def listen(self, sock):
    probes = dict()
    vus = []
    wr = []
    buffers_byte = []
    buffers_int = []
    while self.running:
      header = sock.recv(1) #Blocking so we use shutdown() further down to quit from ctrl-c
      if not header:
        self.running = False
        print "\n" * self.n_vus
        continue
      header = struct.unpack("B", header)[0]

      if header == xscope_handler.XSCOPE_SOCKET_MSG_EVENT_REGISTER:
        connected = True
        probe_idx = None
        probe_name = None
        for idx in range(0,12):
          if idx == 6 or idx == 8 or idx == 11:
            chunk_size = val
          else:
            chunk_size = 4
          data = sock.recv(chunk_size)

          if idx == 6 or idx == 8 or idx == 11:
            val = data
          else:
            val = struct.unpack("i", data[0:4])[0]
          if idx == 6:
            probe_name = val
          if idx == 0:
            probe_idx = val
          #print "Param {}: {}".format(idx, val)
        if probe_name != None and probe_idx != None:
          probes[probe_idx] = probe_name
          #print 'Registered index: {}, probe: "{}"'.format(probe_idx, probe_name)
          vus.append(vu(probe_name, max_int, self.args.samp_rate) )
          print
          self.n_vus += 1
          buffers_byte.append("")
          buffers_int.append([])
          if args.wav_file:
            file_name_split = args.wav_file.split(".")
            file_name = file_name_split[0] + "_" + str(probe_idx) + ".wav"
            wr.append(wave_writer(file_name, self.args.samp_rate) )

          
          """
      elif header == xscope_handler.XSCOPE_SOCKET_MSG_EVENT_RECORD:
        probe_idx = 0
        for idx in range(0,6):
          if idx == 3:
            chunk_size = 4
            unpack_str = "i" #signed
          elif idx == 4 or idx == 5:
            chunk_size = 8
            unpack_str = "Q" #unsigned
          else:
            chunk_size = 1
            unpack_str = "b"
          data = sock.recv(chunk_size)
          val = struct.unpack(unpack_str, data[0:chunk_size])[0]
          #print "Param {}: len: {}  {}".format(idx, chunk_size, val)
          if idx == 0:
            probe_idx = val
          if idx == 4:
            #print "probe: {}, val: {}".format(probes[probe_idx], val)
            vus[probe_idx].update(val)
          """

      #Much faster version of above assuming fixed message size for ints
      elif header == xscope_handler.XSCOPE_SOCKET_MSG_EVENT_RECORD:
        data = sock.recv(23)

        probe_idx = struct.unpack("B", data[0])[0]
        val = struct.unpack("i", data[7:11])[0]
        #print "probe: {}, val: {}".format(probes[probe_idx], val)
        samp_s16 = val >> (self.args.samp_depth - 16)
        buffers_byte[probe_idx] += struct.pack("h", samp_s16)
        buffers_int[probe_idx].append(val)
        if len(buffers_byte[probe_idx]) == block_size * 2:
          #print len(buffers_byte[probe_idx])
          if not self.args.no_vu:
            vus[probe_idx].update(buffers_int[probe_idx], probe_idx)
          if self.do_monitor and self.args.monitor_channel == probe_idx:
            self.queue.put(buffers_byte[probe_idx])
          if self.args.wav_file:
            wr[probe_idx].write(buffers_byte[probe_idx])
          buffers_byte[probe_idx] = ""
          buffers_int[probe_idx] = []
          #print len(buffers_byte[probe_idx])

      elif header == xscope_handler.XSCOPE_SOCKET_MSG_EVENT_PRINT:
        for idx in range(0,3):
          if idx == 1:
            chunk_size = 4
            unpack_str = "i" #signed
          elif idx == 0:
            chunk_size = 8
            unpack_str = "Q" #unsigned
          else:
            chunk_size = val
            data = sock.recv(chunk_size).rstrip()
            print data
            continue
          data = sock.recv(chunk_size)
          val = struct.unpack(unpack_str, data[0:chunk_size])[0]
          #print "Param {}: len: {}  {}".format(idx, chunk_size, val)

      else:
        print "Unhandled xscope header type: {}".format(header)


  def exit(self):
    self.sock.shutdown(socket.SHUT_WR)
    self.running = False

class audio_handler():
  def __init__(self, queue):
    self.queue = queue

  def audio_callback(self, in_data, frame_count, time_info, status):
    audio = self.queue.get()
    #print len(audio)
    #print "play"
    return (audio, pyaudio.paContinue)

class wave_writer():
  def __init__(self, name, samp_rate):
    self.wf = wave.open(name, 'w')  
    self.wf.setparams((1, (16 / 8), samp_rate, block_size, 'NONE', 'not compressed'))

  def write(self, block):
    self.wf.writeframes(block)

  def __del__(self):
   self.wf.close()


#how many samples to handle at a time. Relates to VU, pyaudio and also wave write
block_size = 4096

parser = argparse.ArgumentParser(description='XMOS Audio Probe Tool', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-r','--samp_rate', help='Sample rate in Hz', type=int, default=16000)
parser.add_argument('-s','--samp-depth', help='Number of bits in audio samples from device xscope_int() output', type=int, default=32)
parser.add_argument('-p','--port', help='Port of localhost used to commincate with xrun', type=int, default=6363)
parser.add_argument('-w','--wav-file', help='Write wav file', type=str, required=False)
parser.add_argument('-m','--monitor_channel', help='Live monitor audio output channel of a probe. WARNING: May contain glitches', required=False, type=int)
parser.add_argument('-n','--no-vu', help='Disable VU', action='store_true')
args = parser.parse_args()
max_int = 2**(args.samp_depth - 1) - 1

#args = vars(parser.parse_args()) #turn args into dict

queue = None
if type(args.monitor_channel) == int:
  queue = Queue.Queue()
  p = pyaudio.PyAudio()
  ah = audio_handler(queue)
  stream = p.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=args.samp_rate,
                  output=True,
                  frames_per_buffer=block_size,
                  stream_callback=ah.audio_callback)
  stream.start_stream()
xs = xscope_handler(queue, args)

if args.monitor_channel:
  stream.stop_stream()
  stream.close()
  p.terminate()

sys.exit(0)
