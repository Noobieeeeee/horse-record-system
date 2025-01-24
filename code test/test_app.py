from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import serial
import serial.tools.list_ports
import threading
import time

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to store the latest time
current_time = "Waiting for data..."

# Function to find the serial port connected to the ESP32
def find_esp32_port():
    # List all available serial ports
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Found port: {port.device} - {port.description}")
        # Check if the port description matches the ESP32 (common descriptions include "USB Serial" or "CP210x")
        if "USB" in port.description or "CP210" in port.description:
            print(f"ESP32 likely connected to: {port.device}")
            return port.device
    return None

# Function to read UART data and send it to the web clients via SocketIO
def read_uart():
    global current_time

    # Find the ESP32 port
    esp32_port = find_esp32_port()
    if not esp32_port:
        print("ESP32 not found. Please check the connection.")
        return

    # Configure the serial connection
    ser = None
    try:
        ser = serial.Serial(
            port=esp32_port,      # Dynamically detected port
            baudrate=115200,      # Baud rate (must match ESP32)
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )

        print(f"Connected to ESP32 on {esp32_port}. Waiting for data...")

        while True:
            if ser.in_waiting > 0:  # Check if data is available
                data = ser.readline().decode('utf-8').strip()  # Read and decode the data
                # Filter out bootloader messages (assume valid time data is numeric)
                if data.isdigit():
                    current_time = data  # Store the received data
                    print(f"Received elapsed time: {current_time} seconds")
                    # Emit the time to all connected clients
                    socketio.emit('update_time', {'time': current_time})
                else:
                    print(f"Ignoring bootloader message: {data}")
    except KeyboardInterrupt:
        print("Program terminated.")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()  # Close the serial connection when done
            print("Serial port closed.")
        time.sleep(1)  # Add a delay before reopening the port

# Route to serve the HTML page
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')  # Serve index.html from the current directory

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