# Transit Network Simulator

This repository contains a transit network simulation framework written in Python3 based on simpy package. Included features are
 - cmd line simulator
 - Qt5 UI for cmd line simulation tool
 - event log analysis and some graph generation
 - cmd line tool for network congestion visualization based on networkx and matplotlib (does not work well, will be done in future)

With each release a zip will be provided which contains a folder containing windows executable built using pyinstaller5.1

## Requirements
Tested with Python3.9
Exes are run and tested in Windows 10

## Usage
User needs to provide both code and data to simulate their model. How to input these can be found at Tools section of this README.md.

### Data Requirement
Data is provided by providing the folder containing some data files. All files are txt files.
- network.txt
- demand.txt
- route.txt
- fleet.txt
- edgecap.txt

Among these, only edgecap.txt is optional. If not provided, simulator will use network.txt information to fulfill capacity information of all the edges in network. (How it is used depends on user provided model)

### Code Requirement
User provided code will determine behavior of three agents in the simulation. They are,
- Vehicle
- Dispatcher
- Node

Basic simulation model is this, Vehicle is dispatched to a route by Dispatcher. Vehicle do a forward pass and  backward pass. Then signals Dispatcher if it likes to continue. Dispatcher will decide if will continue in same route or different route. Node acts like a supplier of demand (currently as a sink is not implemented). Vehicle takes demand from one Node and offload the demand to another. By demand we thought of passenger but interpretation is not limited to passengers.

To change their behavior, user has to provide their implementation of following classes
- VehicleStrategy (default implementation is in strategy.py)
- DispatchStrategy (default implementation is in strategy.py)
- Node (default implementation is in node.py)

Default implementation contains the necessary methods and their interface description. Default implementation Node just have demand according to given demand.txt. Default DispatchStrategy just do a round robin fleet assignment at begining and no rerouting. Default VehicleStrategy do nothing, just sit and exit. 

An example where Vehicle do one roundtrip and stop at every node to greediliy pick up passenger and offload if it contains some passenger for current stop can be found in simple_model folder of the repo.


## Tools

### cmd line simulation
run main.py to run cmd line simulation
```
> python .\main.py
```
Output should be
```
usage: main.py [-h] -input INPUT_DIR [-sim] [-simtime SIMULATE_TIME_LENGTH] [-al] [-ts TIME_STEP] -st STRATEGY_CLASS_SCRIPT_PATH -nc NODE_CLASS_SCRIPT_PATH [-velplot AVGVELOCITY_PLOT] [-eplot EVACTIME_PLOT] [-tplot TRIPCOMPLETE_PLOT]

main.py: error: the following arguments are required: -input/--input_dir, -ds/--dispatch_strategy, -vs/--vehicle_strategy
```

Corresponding exe is "transport_simulator_cmd.exe"

The meanings of the useful arguments are given below (got by using -h argument when executing main.py)
```
-h, --help            show this help message and exit
-input INPUT_DIR, --input_dir INPUT_DIR
					folder path containing the input files
-sim, --simulate      if will simulate from input data
-simtime SIMULATE_TIME_LENGTH, --simulate_time_length SIMULATE_TIME_LENGTH
					how many unit time to simulate
-al, --analyze        if will analyze even-log.txt and generate graphs
-ts TIME_STEP, --time_step TIME_STEP
					time step used in generate data point for graphs
-st STRATEGY_CLASS_SCRIPT_PATH, --strategy_class_script_path STRATEGY_CLASS_SCRIPT_PATH
					script path containing VehicleStrategy and DispatchStrategy class
-nc NODE_CLASS_SCRIPT_PATH, --node_class_script_path NODE_CLASS_SCRIPT_PATH
					script path containing Node class
```

Although there are some other arguments, those are for future implementations.


### simulator UI
![simulator ui image](./doc/simulator_ui.PNG)

Corresponding exe is "transport_simulator.exe"

### visualizer cmd line tool

This does not work well.
run network_visualizer.py to visualize network based on given input
```
> python .\network_visualizer.py
```
Output should be 
```
usage: network_visualizer.py [-h] -dir INPUT_DIR -elog EVENT_LOG [-ts TIME_STEP] [-dur DURATION]
network_visualizer.py: error: the following arguments are required: -dir/--input_dir, -elog/--event_log
```

Corresponding exe is "visualizer.exe"