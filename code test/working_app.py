from flask import Flask, render_template
from flask_socketio import SocketIO
import serial
import threading
import time

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to store the latest time
current_time = "Waiting for data..."

# Function to read UART data and send it to the web clients via SocketIO
def read_uart():
    global current_time
    # Configure the serial connection
    ser = serial.Serial(
        port='/dev/serial0',  # Serial port (UART) on Raspberry Pi
        baudrate=115200,      # Baud rate (must match ESP32)
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )

    print("Waiting for data from ESP32...")

    try:
        while True:
            if ser.in_waiting > 0:  # Check if data is available
                data = ser.readline().decode('utf-8').strip()  # Read and decode the data
                current_time = data  # Store the received data
                print(f"Received elapsed time: {current_time} seconds")
                # Emit the time to all connected clients
                socketio.emit('update_time', {'time': current_time})
    except KeyboardInterrupt:
        print("Program terminated.")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    finally:
        ser.close()  # Close the serial connection when done

# Route to serve the HTML page
@app.route('/')
def index():
    return render_template('index.html')

# SocketIO event listener for connection
@socketio.on('connect')
def handle_connect():
    print("Client connected")
    # Emit the latest time immediately after connection
    socketio.emit('update_time', {'time': current_time})

# Start UART reading in a separate thread
uart_thread = threading.Thread(target=read_uart)
uart_thread.daemon = True
uart_thread.start()

# Run the Flask app with SocketIO
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

