import time
from pyfirmata2 import Arduino

# --- CONFIGURATION ---
PORT = 'COM4' 

# Define your Arduino pins here
SERVO_X_PIN = 9
SERVO_Y_PIN = 8
BUTTON_X_PIN = 2
BUTTON_Y_PIN = 3

# Connect to the Arduino
print(f"Connecting to Arduino on {PORT}...")
board = Arduino(PORT)

# Start internal sampling (replaces util.Iterator). 
# This tells the Arduino to check inputs every 20 milliseconds.
board.samplingOn(20) 
print("Connected!")

# --- PIN SETUP ---
servo_x = board.get_pin(f'd:{SERVO_X_PIN}:s')
servo_y = board.get_pin(f'd:{SERVO_Y_PIN}:s')

# 'u' = input with internal pull-up resistor
button_x = board.get_pin(f'd:{BUTTON_X_PIN}:u')
button_y = board.get_pin(f'd:{BUTTON_Y_PIN}:u')

# --- STATE & DEBOUNCE VARIABLES ---
state_x = 0  
state_y = 0  

# We use time to prevent a single button press from registering multiple times
last_x_time = 0
last_y_time = 0
DEBOUNCE_DELAY = 0.3 # 300 milliseconds between allowed presses

# --- CALLBACK FUNCTIONS ---
def x_button_pressed(value):
    global state_x, last_x_time
    
    # Because of the pull-up resistor, a press pulls the value to 0 (False)
    if value == 0 or value == False:
        current_time = time.time()
        
        # Check if enough time has passed since the last press (Debounce)
        if current_time - last_x_time > DEBOUNCE_DELAY:
            state_x = (state_x + 1) % 4 
            
            if state_x == 1:
                print("X-Axis: Moving Right")
                servo_x.write(0)
            elif state_x == 2:
                print("X-Axis: Returning to Center")
                servo_x.write(90)
            elif state_x == 3:
                print("X-Axis: Moving Left")
                servo_x.write(180)
            elif state_x == 0:
                print("X-Axis: Returning to Center")
                servo_x.write(90)
                
            last_x_time = current_time

def y_button_pressed(value):
    global state_y, last_y_time
    
    if value == 0 or value == False:
        current_time = time.time()
        
        if current_time - last_y_time > DEBOUNCE_DELAY:
            state_y = (state_y + 1) % 4 
            
            if state_y == 1:
                print("Y-Axis: Moving Up")
                servo_y.write(0)
            elif state_y == 2:
                print("Y-Axis: Returning to Center")
                servo_y.write(90)
            elif state_y == 3:
                print("Y-Axis: Moving Down")
                servo_y.write(180)
            elif state_y == 0:
                print("Y-Axis: Returning to Center")
                servo_y.write(90)
                
            last_y_time = current_time

# --- REGISTER CALLBACKS ---
# This links the physical pins to the functions we just wrote
button_x.register_callback(x_button_pressed)
button_x.enable_reporting()

button_y.register_callback(y_button_pressed)
button_y.enable_reporting()

# --- INITIALIZATION ---
print("Moving to home position...")
servo_x.write(90)
servo_y.write(90)
time.sleep(1)

print("Ready! Press the buttons to move the servos.")

# --- MAIN LOOP ---
try:
    # Since callbacks handle the logic in the background, 
    # our main loop just needs to stay alive and do nothing.
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nProgram stopped by user. Centering servos...")
    servo_x.write(90)
    servo_y.write(90)
    time.sleep(0.5)
    board.exit()