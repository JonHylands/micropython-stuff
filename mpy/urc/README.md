### Universal Robot Configurer

This folder holds the code for my universal robot configurer. It is in a very primitive state right now.

![](images/PXL_20240305_013810338.jpg)

This is a wearable device based on a [Waveshare ESP32-S3 Round Touch LCD](https://www.waveshare.com/esp32-s3-touch-lcd-1.28.htm). It is also based on Russ Hughes' excellent [MicroPython GC9A01 display driver](https://github.com/russhughes/gc9a01_mpy).

The code allows you to build a complex touch-based windowing system for this device. You can easily create windows with widgets like buttons and labels and lists. You can scroll between sets of windows. I'll be adding a bunch of documentation on how to use it, but for now look at main.py, admin.py, and rover.py for an example. Everything in this GUI is based off the touch screen pin interrupt, with real-time updates happening via hardware timers. The main loop sits in a loop and calls time.sleep_ms(1000).

![](images/PXL_20240304_235733175.jpg)

![](images/PXL_20240228_012842145.jpg)

![](images/PXL_20240228_012910481.jpg)

# Overall Architecture
### Touch Based Windowing System

There are two main objects that interact with the outside world - the TouchManager for input, and the Display for output. The WindowManager handles the mechanics of managing the windowing system, and Windows, WindowChains, Views, and VisualComponents are client-created objects for displaying information.

### Display

The Display object is a singleton, which interfaces with the [GC9A01 driver](https://github.com/russhughes/gc9a01_mpy). It creates an SPI connection, and provides some simple methods to interact with the physical display. Most of the more complex functions for drawing are implemented in the driver, and can be accessed by asking the Display for its screen.

### TouchManager

The TouchManager is also a singleton, which handles all user touch interactions. It is entirely interrupt driven, based off touch events causing the touch interrupt pin from the driver chip to go high. This pin change interrupt is caught by the touch manager's ISR, and almost all interactions with the system derive from there. The touch manager gets raw touch down and touch up events, and uses a finite state machine to built higher level touch events (touch press, touch release, double touch, long touch, drag start, drag continue, drag stop) that are sent to VisualComponent objects that have registered interest in them.

### WindowManager

The WindowManager is a singleton, which manages windows (as the name implies). Window manager provides a framework for switching between windows, and uses two simple mechanisms for window construction. The first mechanism is a stack, where you can push new windows onto the stack, and then pop them off again. The second mechanism is a window chain, which is a collection of windows that can be pushed on the stack as one unit, and the windows in the chain can be scrolled horizontally to reach the next or previous window in the chain. You can push either a single window or a window chain, but a single window is just a special case of a chain with only one window in it.

The window manager adds slider buttons to the sides of each window in the chain, both as a visual representation that there is a multi-window chain present, and as active visual components that the touch manager sends events to. When you push a window/chain, the window manager also adds a bottom slider button to each window in the chain, and sliding up from that slider is what triggers a pop.

### Window

A Window is a client-created object, that represents a single expression of information and interaction on the display. Windows always take up the entire screen, and there is only one active window at a time. A window defines a screen-level coordinate system, where (0, 0) is the top left of the screen, and (239, 239) is the bottom right. Because this system runs on a round screen, those specific pixels are not visible.

Clients can register to get notified when a window is activated and/or when a window is closing. This allows the client to enable and disable any timers or other physical resources that will be or have been allocated while the window is active. If the screensaver is active, the client can also register to be notified of when the screensaver activates and deactivates, for the same reasons.

### WindowChain

A WindowChain is just a collection of windows that are laid out as if they are connected by a horizontal chain, and the user can swipe left or right to switch between windows in the chain. You can use window chains to choose amongst a number of selections (one selection per window in the chain). You can choose to have all windows in the chain push to another single window or chain, or each window in the chain can have its own sub-windows/chains.

### View

A View is a client-created object that represents a rectangular area on the screen, and implements its own local coordinate system. Windows can have one or many views.

### VisualComponent

A VisualComponent represents a specific item on the screen, like a button or a label. It can be display-only (like a label), or have both a visual representation and handle touch interactions (like a button). Sometimes, you want something like a button that has no visual representation but still handles touch interactions, and that is possible as well (at least for buttons).

Visual components are laid out inside a view, and use the view's coordinate system as its own.

### Overall Concepts

In general, a client creates a window, registers for touch events, and pushes it using the window manager functions. The window manager handles scrolling between windows in a chain, and also popping the current window/chain. Client code can react to touch interactions (like button pushes) by pushing a new window/chain, and/or updating information on the window. There are many ways to accomplish this, the example system provided is just one of many.

WindowManager reserves Timer0 for its own use (the screensaver countdown), but clients can use whatever other timers they want. On the Waveshare ESP32-S3 Round Touch Display, the following pins/resources are used by the touch based windowing system:

*   I2C Port: 0
*   SPI Port: 2
*   Touch interrupt pin: 5
*   Touch SCL pin: 6
*   Touch SDA pin: 7
*   Display SCK pin: 10
*   Display MOSI pin: 11
*   Display CS pin: 9
*   Display DC pin: 8
*   Display reset pin: 14
*   Display backlight pin: 2

All other pins are available for user/client functions. Battery voltage level can be read on pin 1. See AdminWindow >> get\_battery\_level() for an example of how to convert the ADC value to actual voltage. GPIO pins 15, 16, 17, 18, 21, and 33 are all available on the pin harness connector.
