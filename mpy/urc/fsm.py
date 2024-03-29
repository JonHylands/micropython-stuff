
import time

#================================================
#
#        Class State
#

class State:

    def __init__(self, stateName, enterFunction, updateFunction, exitFunction):
        self.userEnter = enterFunction
        self.userUpdate = updateFunction
        self.userExit = exitFunction
        self.name = stateName

    def enter(self):
        self.startTimeMillis = time.ticks_ms()
        if self.userEnter is not None:
            self.userEnter()

    def update(self):
        if self.userUpdate is not None:
            self.userUpdate()

    def exit(self):
        if self.userExit is not None:
            self.userExit()

    def elapsedTimeMillis(self):
        return time.ticks_ms() - self.startTimeMillis

    def getName(self):
        return self.name

#================================================
#
#        Class FiniteStateMachine
#

class FiniteStateMachine:

    def __init__(self, startState):
        self.currentState = startState
        self.nextState = startState
        self.needToTriggerEnter = True
        self.cycleCount = 0

    def transitionTo(self, newState):
        self.nextState = newState

    def getCycleCount(self):
        return self.cycleCount

    def getCurrentStateMillis(self):
        return self.currentState.elapsedTimeMillis()

    def update(self):
        if self.needToTriggerEnter:
            self.currentState.enter()
            self.needToTriggerEnter = False
        if self.currentState.getName() != self.nextState.getName():
            self.currentState.exit()
            self.currentState = self.nextState
            self.currentState.enter()
            self.cycleCount = 0
        self.cycleCount += 1
        self.currentState.update()
