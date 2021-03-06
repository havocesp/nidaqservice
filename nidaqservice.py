import PyDAQmx as daq
import zmq
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.zmq import ZmqServerTransport
from tinyrpc.server import RPCServer
from tinyrpc.dispatch import RPCDispatcher
from os import system

import argparse

parser = argparse.ArgumentParser(prog="pydaqservice",
                        description="JSON RPC service for writing to NI-DAQ analog output ports.")
#parser.add_argument('channel', type=str, help='The physical output channel to write to')
parser.add_argument('--port', dest='port', type=int, default=5002,
                   help='The port on which to bind to service.')
parser.add_argument('--persist', dest='persist', type=bool, default=False,
                    help='set whether or not to persist the connection to the daq after a call')

                   
args = parser.parse_args()


ctx = zmq.Context()
dispatcher = RPCDispatcher()


endpoint = 'tcp://127.0.0.1:%i' % args.port
transport = ZmqServerTransport.create(ctx, endpoint)
print "serving requests at %s" % endpoint
system("Title " + "NI DAQ Device Service")

rpc_server = RPCServer(
    transport,
    JSONRPCProtocol(),
    dispatcher
)


channelTasks = dict()

def initializeDigitalOutput(channel):
    digital_output = daq.Task()
    digital_output.CreateDOChan(channel,"",daq.DAQmx_Val_ChanPerLine)
    return digital_output

def initializeDigitalInput(channel):
    digital_input = daq.Task()
    digital_input.CreateDIChan(channel,"",daq.DAQmx_Val_ChanPerLine)
    return digital_input

def initializeAnalogOutput(channel,value,min_value=0.0,max_value=5.0):
    analog_output = daq.Task()
    analog_output.CreateAOVoltageChan(channel,"", min_value,max_value,daq.DAQmx_Val_Volts,None)
    return analog_output

def initializeAnalogInput(channel):
    analog_input = daq.Task()
    analog_input.CreateAIVoltageChan(channel,"",daq.DAQmx_Val_RSE,-10.0,10.0,daq.DAQmx_Val_Volts,None)
    return analog_input


@dispatcher.public
def writeDigitalOutput(channel,value):
    if not channelTasks.has_key(channel):
        channelTasks[channel] = initializeDigitalOutput(channel)
    
    digital_output = channelTasks[channel]

    try:    
        digital_output.WriteDigitalScalarU32(True,0,value,None)
    except Exception as ex:
        del channelTasks[channel]
        raise ex


@dispatcher.public
def writeAnalogOutput(channel,value,min_value=0.0,max_value=5.0):
    if not channelTasks.has_key(channel):
        channelTasks[channel] = initializeAnalogOutput(channel,min_value,max_value)
    
    analog_output = channelTasks[channel]    
    try:
        analog_output.WriteAnalogScalarF64(True,0,value,None)
    except Exception as ex:
        del channelTasks[channel]
        raise ex


@dispatcher.public
def readAnalogInput(channel):
    if not channelTasks.has_key(channel):
        channelTasks[channel] = initializeAnalogInput(channel)
        
    analog_input = channelTasks[channel]    

    value = daq.float64()
    try:
        analog_input.ReadAnalogScalarF64(10,daq.byref(value),None)
        return value.value
    except Exception as ex:
        del channelTasks[channel]
        raise ex
        


@dispatcher.public
def readDigitalInput(channel):
    if not channelTasks.has_key(channel):
        channelTasks[channel] = initializeDigitalInput(channel)
        
    digital_input = channelTasks[channel]    
    
    value = daq.c_uint32
    try:
        digital_input.ReadDigitalScalarU32(0,daq.byref(value),None)
        return value.value
    except Exception as ex:
        del channelTasks[channel]
        raise ex
    
    

rpc_server.serve_forever()