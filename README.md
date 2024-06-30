<img src="https://raw.githubusercontent.com/labscript-suite/labscript-suite/master/art/blacs_32nx32n.svg" height="64" alt="the labscript suite – blacs" align="right">

# the _labscript suite_ » blacs

### Graphical interface to scientific instruments and experiment supervision

[![Actions Status](https://github.com/labscript-suite/blacs/workflows/Build%20and%20Release/badge.svg?branch=maintenance%2F3.0.x)](https://github.com/labscript-suite/blacs/actions)
[![License](https://img.shields.io/pypi/l/blacs.svg)](https://github.com/labscript-suite/blacs/raw/master/LICENSE.txt)
[![Python Version](https://img.shields.io/pypi/pyversions/blacs.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/blacs.svg)](https://pypi.org/project/blacs)
[![Conda Version](https://img.shields.io/conda/v/labscript-suite/lyse)](https://anaconda.org/labscript-suite/blacs)
[![Google Group](https://img.shields.io/badge/Google%20Group-labscriptsuite-blue.svg)](https://groups.google.com/forum/#!forum/labscriptsuite)
<!--[![DOI](http://img.shields.io/badge/DOI-10.1063%2F1.4817213-0F79D0.svg)](https://doi.org/10.1063/1.4817213)-->


**blacs** supervises the execution of experiments controlled by the [*labscript suite*](https://github.com/labscript-suite/labscript-suite). It manages experiment queuing and hardware-timed execution, and provides manual control over devices between experiment shots.


## My Fork

This fork seeks to optimize the runtime of **blacs**, in particular the overhead between the execution of experimental shots. 

I have identified the following aspects of BLACS where possible improvements could be made:

1. The State Machine
2. Reliance on QT Main Thread
3. Worker Processes

The following sections motivate the need for changes to these aspects and describes the current implementations.

## 1. State Machine

The first bottleneck is due to the transition to the Manual Mode state at the end of each shot (Figure 1). Manual mode allows the user to provide manual control over devices between experiment shots. The problem arises when there are multiple shots in the queue, in which case after the transition to Manual mode we immediately call `transition_to_buffered` meaning we can longer manually control the devices. It is clear that there is no need for manual mode device operation in between queued up shots.

However, it is not as simple as removing the `transition_to_manual` when we have shots in the queue due to the fact that `transition_to_manual` is a "compound" state transition - it has multiple functionalities. It is responsible for post-processing the data collected from an experiment (saving acquired data, images, etc.), keeping track of the internal state flags of the device, and programming the devices to operate in manual mode.

Through testing, it was found that the actual Manual mode programming of devices (starting manual mode tasks using driver calls) was consuming the most amount of time in some cases. 

<p align="center">
  <img src="./readme_images/default_blacs_state_machine.png" alt="Project Screenshot" width="600"/>
  <br>
  <b>Figure 1:</b> Original BLACS State Machine flow (https://docs.labscriptsuite.org/projects/blacs/en/latest/shot-management/)
</p>

### Proposed solution
Introduce a new `post_experiment` state that will, as the name suggests, be responsible for all the functionality required at the end of a shot. This way, "transition_to_manual" will only be responsible for setting up manual mode on the devices. 

Since manual mode device operation is not needed between queued up shots, we do not call `transition_to_manual` in this case (Figure 2).

<p align="center">
  <img src="./readme_images/new_blacs_state_machine.png" alt="Project Screenshot" width="600"/>
  <br>
  <b>Figure 2:</b> New BLACS State Machine flow to skip manual mode when shots are queued up.
</p>

#### Notes

* Most devices don't have expensive manual mode task setup calls. Only the NI-6363 acquisition worker seemed to have a >30ms manual setup time.
* `transition_to_manual` is called as soon as the experiment queue is paused. In general, `transition_to_manual` should only be called when it is possible for the user to actually control the devices.
* To add support for your device to use the new state machine flow, add a to all your device workers. The best way to start is to rename you `transition_to_manual` function as `post_experiment` and then add an empty `transition_to_manual`. You can then decide what functionality needs to occur in `post_experiment` and what can be moved to `transition_to_manual`. 

#### Backwards Compatibility

Fallback to `transition_to_manual` state function execution if `post_experiment` is not implemented in device workers.

## 2. QT Main Thread

Almost all functionality is queued up and execution on the QT MainThread. I believe the developers did this for 2 reasons:

* A thread where all the GUI modifications would occur
* To serialize oeprations on a single thread to maintain thread safety of non-GUI objects (e.g. StateQueue)

By scheduling on a single thread, the context switching overhead becomes non-neglible. Furthermore, most of the functions being scheduled `inmain` did not touch the GUI/non-thread-safe objects, which meant we were unnecessarily delaying their execution by waiting to perform them on MainThread. This scheduling delay resulted amounted to about ~20-30ms slowdown each shot.

```
2024-06-04 17:02:47,100 DEBUG BLACS.ni_6363.mainloop: Processing event _transition_to_buffered
2024-06-04 17:02:47,109 DEBUG BLACS.pb.mainloop: Processing event _transition_to_buffered
2024-06-04 17:02:47,110 DEBUG BLACS.ni_6363.mainloop: Instructing worker main_worker to do job _transition_to_buffered
2024-06-04 17:02:47,114 DEBUG BLACS.ni_6363_main_worker.worker: Got job request _transition_to_buffered
2024-06-04 17:02:47,115 DEBUG BLACS.ni_6363_main_worker.worker: Starting job _transition_to_buffered
2024-06-04 17:02:47,126 DEBUG BLACS.pb.mainloop: Instructing worker main_worker to do job _transition_to_buffered
```
After the line 1, the `ni_6363.mainloop` schedules the generator function on the MainThread. We see an unnecessary 10ms delay until we hear back from the generator function and we can start the `ni_6363_main_worker`. It is clear we are not maximizing the concurrency of our program.  

### Proposed Solution

I have removed the `inmain` decorators which allows function execution from various threads such as all the `DeviceTab.mainloop`s and `ExperimentQueue.manager`. To address the developers concerns I have made the following changes:
* Added fine-grain locks for the QT Application GUI. Instead of scheduling an entire function that has one line that modifies the GUI on the MainThread, we now grab the QTlock before making any GUI update.
* Made a thread safe implementation of the Single-Consumer Multi-Producer StateQueue object using local locks.

Here is an example of the log prints after the change. We are now able to launch the `transition_to_buffered` worker processes as soon as we recieve the event!
```
2024-06-30 11:34:09,607 DEBUG BLACS.pb.mainloop: Processing event _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.ni_6363.mainloop: Processing event _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.pb.mainloop: Instructing worker main_worker to do job _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.pb_main_worker.worker: Got job request _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.pb_main_worker.worker: Starting job _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.ni_6363.mainloop: Instructing worker main_worker to do job _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.ni_6363_main_worker.worker: Got job request _transition_to_buffered
2024-06-30 11:34:09,607 DEBUG BLACS.ni_6363_main_worker.worker: Starting job _transition_to_buffered
```

## 3. Worker Processes

For devices that have multiple workers, they are processed serially. We grab a single worker task at a time from the yield in the State GUI generator function, execute the worker, pass back the results and receive the next work task is there is one. There is no reason for these workers to be serialized.

### Proposed Solution

The `DeviceTab.mainloop` that processes the State GUI generator function now expects to receive a list of all the worker tasks (Figure 2). These are then scheduled at the same time and returns the results of each of the workers in a list.

The worker processing time is no longer a sum of all the workers, and is bound by the longest worker.

#### Backwards Compatibility

Fallback to accepting a single worker at a time if the State GUI generator function is out of date.

## 4. Other Performance Hacks

1. Do not open h5 file unnecessarily
    * The start of a shot involves retrieving the device list associated with the current h5 file. This is not necessary, especially when all the shots are using the exact same devices. 

2. Do not update the GUI unnecessarily
    * BLACs GUI is quite "verbose" as they try to update as much information as possible for the user to see. GUI updates can only be done serially and is quite slow, especially when trying to update so much information in such a short amount of time. Removing these updates saves a lot of time


### Results
Overall, these changes bring down the overhead between shots in our experimental set up from **380ms to 220ms**. With the hard-coded performance hacks, the overhead is closer to **170ms**.

It should be noted that the impact of some of the optimizations are specific to the experimental set up and the hardware/functionalities being used. For example, if you have no devices with multiple workers, then my parallelization change will not impact you. That being said, you may not see the same level of improvements I achieved when applying to your experiment.

### Things I am looking into (performance or otherwise)

- Proper plugin implementation allowing user to define a "sequence device-list" (to address 4.1)
- A DeviceTab for remote operation of pre-existing experiment control GUI softwares (e.g. LabVIEW laser locking, Laser Raster software). Should be a lot more convenient compared to re-creating the GUI in a BLACS tab.

If you have any thoughts/concerns or ideas for additional features please feel free to open an Issue or contact me directly at haques24@mit.edu.

## Installation
blacs is distributed as a Python package on [PyPI](https://pypi.org/user/labscript-suite) and [Anaconda Cloud](https://anaconda.org/labscript-suite), and should be installed with other components of the _labscript suite_. Please see the [installation guide](https://docs.labscriptsuite.org/en/latest/installation) for details.
