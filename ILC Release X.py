import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import customtkinter as ctk
import serial
import serial.tools.list_ports
import csv
import os
from base64 import b64encode, b64decode
from Crypto.Cipher import ChaCha20
import time
import threading
import serial
import webbrowser

# last edit 04/10/2024 12:16 am

global version 
version = 'X'

global TimeoutErrorTime
TimeoutErrorTime = 3

########################################################################################################################################################
#                                                                  main class                                                                          #
########################################################################################################################################################
class ILCApplication(ctk.CTk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name = f"ILC Software Release {version}"
        self.title(name)
        self.geometry("800x600")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.paddyx = 25
        self.paddyy = 25
        self.ser = None
        self.connection_status = False
        self.currently_open_lab_name = "No Lab Selected"
        self.active_frame = None  # This will hold the currently active frame
        self.allow_serial_read = True  # Add this line
        self.read_thread = None
        self.tmp_state_for_status_widget = ''
        self.isClockOn = False
	self.key = bytes([
    	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
	])
        self.main_frame = None
        self.initialize_main_window_widget()

    def read_from_serial(self):
            """Background thread task to read serial data and update GUI.

            This method is responsible for continuously reading data from the serial connection
            and updating the GUI with the received data. It runs as a background thread.

            Raises:
                serial.SerialException: If there is an error with the serial connection.

            """
            try:
                while self.connection_status:
                    if self.ser.inWaiting() > 0 and self.allow_serial_read:
                        response = self.ser.readline().decode('utf-8').strip()
                        # Use the main thread to update the GUI
                        self.tmp_state_for_status_widget = response
                        self.update_gui(response)
            except serial.SerialException as e:
                # Handle the SerialException here (e.g., display an error message)
                self.switch_to_main_mode()
                self.active_frame.make_canvas_say(f"ILC Disconnected")
                self.connection_status = False
                self.allow_serial_read = False
    
    def update_gui(self, response):
            """
            Updates the GUI based on the Arduino's response.
            
            This method is intended to be called from the main thread.
            
            Parameters:
            response (str): The response received from the Arduino.
            """
            if self.active_frame and hasattr(self.active_frame, 'update_circles_based_on_input'):
                if len(response) == 15:  # Assuming each response ends with a newline character

                    self.active_frame.update_circles_based_on_input(response)
            
    def stop_read_thread(self):
        """
        Stops the read thread if it is currently running.

        This method sets the `allow_serial_read` flag to False, which stops the read thread from reading data from the serial port.
        It also sets the `read_thread` variable to None, indicating that the read thread is no longer active.

        Note:
        - If the read thread is not running, this method has no effect.
        - After calling this method, the read thread cannot be restarted. To start reading again, you need to create a new read thread.

        """
        if self.read_thread is not None and self.read_thread.is_alive():
            self.allow_serial_read = False
            self.read_thread = None

    def start_read_thread(self):
        """
        Starts a new thread to read data from the serial port.

        This method ensures that any existing thread is stopped first before starting a new one.
        It sets the `allow_serial_read` flag to True, indicating that reading from the serial port is allowed.
        The `read_from_serial` method is then executed in a separate thread.

        Note: This method should be called after initializing the serial port.

        Returns:
            None
        """
        self.stop_read_thread()  # Ensure any existing thread is stopped first
        self.allow_serial_read = True
        self.read_thread = threading.Thread(target=self.read_from_serial, daemon=True)
        self.read_thread.start()

    def initialize_main_window_widget(self):
        """
        Initializes the main window widget.

        This method destroys the existing main frame (if any) and creates a new instance of the MainFrame class.
        It also updates the active frame reference.

        Parameters:
        - self: The current instance of the class.

        Returns:
        None
        """
        if self.main_frame is not None:
            self.main_frame.destroy()
        self.main_frame = MainFrame(self, self.connect_to_ilc, self.disconnect_from_ilc, self.switch_to_tt_mode, self.toggle_clock)
        self.main_frame.pack(padx=self.paddyx, pady=self.paddyx)
        self.active_frame = self.main_frame  # Update the active frame reference

    def switch_to_tt_mode(self):

        if self.connection_status:
            self.main_frame.pack_forget()
            self.tt_mode_frame = TTModeFrame(self, self.switch_to_main_mode, self.key, self.ser, self.toggle_clock)
            self.tt_mode_frame.pack(padx=self.paddyx, pady=self.paddyy, fill='both', expand=True)
            self.active_frame = self.tt_mode_frame  # Update the active frame reference
        else:
            self.main_frame.make_canvas_say("Not Connected to ILC")

    def switch_to_main_mode(self):
        """
        Switches to the main mode by displaying the main frame and hiding the active frame (if any).

        This method is responsible for switching the application to the main mode by displaying the main frame and hiding
        the active frame (if any). It first checks if there is an active frame, and if so, it hides it using the
        `pack_forget()` method. Then, it displays the main frame using the `pack()` method with the specified padding
        values. Finally, it updates the `active_frame` attribute to the main frame.

        Note: Depending on your setup, you may need to use `grid_forget()` instead of `pack_forget()` to hide the active frame.

        Args:
            self: The instance of the class.

        Returns:
            None
        """
        if self.active_frame is not None:
            self.active_frame.pack_forget()  # Or grid_forget(), depending on your setup
        self.main_frame.pack(padx=self.paddyx, pady=self.paddyy)
        self.active_frame = self.main_frame
        if self.connection_status:
            self.active_frame.update_circles_based_on_input(self.tmp_state_for_status_widget)

    def connect_to_ilc(self):
        error = ''
        if self.connection_status:
            self.main_frame.make_canvas_display("Already Connected")
            self.allow_serial_read = True  # Resume the background thread reading
            return
        arduino_ports = [
            p.device for p in serial.tools.list_ports.comports()
            if 'CH340' in p.description or 'Arduino' in p.description
        ]

        if len(arduino_ports) == 1:
            self.ser = serial.Serial(arduino_ports[0], 9600, timeout=TimeoutErrorTime)
            self.connection_status = True
            self.isClockOn = True
            self.main_frame.make_canvas_say("Connecting... 2 seconds")
            self.main_frame.update()
            wait_time = 2  # Wait for 2 seconds before sending the first command
            time.sleep(wait_time)

            
            self.ser.write(b'1')
            response = self.get_response_from_serial()
            if response == '':  # Check if the response is empty
                self.main_frame.make_canvas_say("No response from ILC")
                return

            self.main_frame.update_circles_based_on_input(response)
            self.tmp_state_for_status_widget = response
            self.start_read_thread()  # Start the background thread to read serial dat
        elif not arduino_ports:
            # If no Arduino is found, show a popup to select the COM port
            self.show_com_port_selection_popup()
            error = ("No Arduino found")
        elif len(arduino_ports) > 1:
            self.show_com_port_selection_popup()
            error = ("Multiple Arduinos found")
        elif error != '':
            self.main_frame.make_canvas_say(f" {error} ")
            self.connection_status = False
            self.allow_serial_read = False  # Stop the background thread from reading     

    def disconnect_from_ilc(self):
        """
        Disconnects from the ILC device.

        This method stops the background thread from reading, closes the serial connection,
        and updates the connection status.

        Returns:
            None
        """
        if self.connection_status and self.ser:
            self.stop_read_thread()  # Stop the background thread from reading
            self.allow_serial_read = False
            self.ser.close()
            self.connection_status = False
        else:
            self.main_frame.make_canvas_say("Not Connected")

    def toggle_clock(self):
        """
        Toggles the clock on or off.

        If the connection status is True, the method toggles the clock on or off by sending a '#' character
        to the serial port. If the clock is currently on, it turns it off, and if it's off, it turns it on.
        The method also updates the `isClockOn` attribute accordingly.

        If the connection status is False, the method displays a message on the active frame canvas indicating
        that the device is not connected to the ILC.
        """
        if self.connection_status:
            self.allow_serial_read = False
            if self.isClockOn:
                self.ser.write('#'.encode('utf-8'))
                self.isClockOn = False
            else:
                self.ser.write('#'.encode('utf-8'))
                self.isClockOn = True
            self.allow_serial_read = True
        else:
            self.active_frame.make_canvas_say("Not Connected to ILC")

    def manual_connect(self, port, popup_to_close):
        """Attempt manual connection to the specified port and close the popup on success."""
        self.ser = serial.Serial(port, 9600)
            # Connection was successful, close the popup
        popup_to_close.destroy()
        self.connection_status = True
        self.isClockOn = True
        self.main_frame.make_canvas_display("Connecting... 2 seconds")
        self.main_frame.update()
        wait_time = 2  # Wait for 2 seconds before sending the first command
        time.sleep(wait_time)

        self.ser.write(b'1')
        response = self.get_response_from_serial()
        if response == '':  # Check if the response is empty
            self.main_frame.make_canvas_display("No response from ILC")
            return
        
        self.main_frame.update_circles_based_on_input(response)
        self.tmp_state_for_status_widget = response
        self.start_read_thread()  # Start the background thread to read serial dat

    def show_com_port_selection_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Select COM Port")
        popup.geometry("400x300")
        popup.attributes('-topmost', True)
        # popup.set_appearance_mode("Dark")  # Make sure customTkinter supports this method
        # popup.set_default_color_theme("blue")  # Check if this method is available in ctk; might vary by version

        label = ctk.CTkLabel(popup, text="Select a COM Port:")
        label.pack(pady=(10, 0))

        ports = serial.tools.list_ports.comports()
        if not ports:
            ctk.CTkLabel(popup, text="No COM ports available.").pack(pady=10)
            need_help_button = ctk.CTkButton(popup, text="Device Not Shown? Click Here for Driver", command=self.go_to_driver_page)
            need_help_button.pack(pady=10)
            return

        for port in ports:
            port_info = f"{port.device} - {port.description}"
            port_button = ctk.CTkButton(popup, text=port_info, 
                                        command=lambda p=port.device: self.manual_connect(p, popup))
            port_button.pack(pady=5, padx=50)

        need_help_button = ctk.CTkButton(popup, text="Device Not Shown? Click Here for Driver", command=self.go_to_driver_page)
        need_help_button.pack(pady=10)

    def go_to_driver_page(self):
        """Open the web browser to the driver download page."""
        webbrowser.open("https://cpen.vesulo.com/reference/ch340")

    def get_response_from_serial(self):
        response = ""
        start_time = time.time()
        timeout = 3  # Set a timeout period (in seconds)

        # Wait for a response or until timeout
        while (time.time() - start_time) < timeout:
            if self.ser.inWaiting() > 0:
                response = self.ser.readline().decode('utf-8').strip()
                print(f"Received: {response}")
                if len(response) == 15:  # Assuming each response ends with a newline character
                    break  # Exit loop once a complete response is received
        return response

        
########################################################################################################################################################
            

########################################################################################################################################################
#                                                                  MainFrame class                                                                     #
########################################################################################################################################################
class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, connect_func, disconnect_func, switch_to_tt, clock_o, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.connect_func = connect_func
        self.disconnect_func = disconnect_func
        self.switch_to_tt = switch_to_tt
        self.paddyx = 10
        self.paddyy = 10
        self.status_widget, self.canvas = self.create_status_widget()
        self.clock_toggle = clock_o
        self.setup_ui()

    def create_status_widget(self):
        status_widget = ctk.CTkFrame(self)

        canvas = ctk.CTkCanvas(status_widget, width=650, height=100, highlightthickness=0, bg = "darkgrey")
        canvas.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        status_widget.pack(padx=10, pady=10)  # Adjust as needed

        return status_widget, canvas
    
    def update_circles_based_on_input(self, input_string):
        if len(input_string) != 15:
            return
        self.parent.tmp_state_for_status_widget = input_string
        self.canvas.delete("all")  # Clear the canvas before drawing new circles
        circle_size = 30
        gap = 6
        start_x = 10
        start_y = 40

        self.canvas.create_text(140,18,text='Input Status', font=("Arial", 12), fill="black")

        self.canvas.create_text(415,18,text='Output Status', font=("Arial", 12), fill="black")
        
        colors = input_string.replace('|', '')  # Remove the separator '|'
        for i, color in enumerate(colors):
            if i == 7:
                start_x += 20  # Add extra gap after the 7th circle
            fill_color = 'red' if color == '1' else 'grey'
            
            
            if i <= 6:
                self.canvas.create_rectangle(start_x+5-3, start_y-2, start_x + circle_size/2 + 2, start_y + circle_size +2, fill='grey', outline="black")

                if color == "1":
                    self.canvas.create_rectangle(start_x+5, start_y, start_x + circle_size/2, start_y-15 + circle_size, fill='black', outline="")
                if color == "0":
                    self.canvas.create_rectangle(start_x+5, start_y+15, start_x + circle_size/2, start_y + circle_size, fill='black', outline="")

                self.canvas.create_text(start_x+12.5, start_y + 45, text = f'S{i+1}', font=("Arial", 12), fill="black")
            if i > 6:
                self.canvas.create_oval(start_x, start_y, start_x + circle_size, start_y + circle_size, fill=fill_color, outline="black")
                self.canvas.create_text(start_x+12.5, start_y + 45, text = f'L{i-7}', font=("Arial", 12), fill="black")
            start_x += circle_size + gap


        # offsets for the 7 segment display
        # column 1 left most edge x = 625  seg 4 and 5
        # column 2 left most edge x = 640  seg 6 and 3 and 0
        # column 3 left most edge x = 665  seg 2 and 1
        column_1_x_offset = 25
        column_2_x_offset = 35
        column_3_x_offset = 65
        starting_x = 550
        horizontal_seg_length = 30
        vertical_seg_width = 10
        for i, color in enumerate(colors):
        
            fill_color = 'red' if color == '1' else 'grey' 

            if i == 0:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 10 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 20 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 10, starting_x + column_2_x_offset + horizontal_seg_length, 20, fill=fill_color, outline="black")
            if i == 1:
                #self.canvas.create_rectangle(starting_x + column_3_x_offset -2, 10 -2, starting_x + column_3_x_offset + vertical_seg_width +2 , 50 +2 , fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_3_x_offset, 10, starting_x + column_3_x_offset + vertical_seg_width, 50, fill=fill_color, outline="black") 
            if i == 2:
                #self.canvas.create_rectangle(starting_x + column_3_x_offset -2, 50 -2, starting_x + column_3_x_offset + vertical_seg_width +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_3_x_offset, 50, starting_x + column_3_x_offset + vertical_seg_width, 90, fill=fill_color, outline="black")
            if i == 3:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 80 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 80, starting_x + column_2_x_offset + horizontal_seg_length, 90, fill=fill_color, outline="black")
            if i == 4:
                #self.canvas.create_rectangle(starting_x + column_1_x_offset -2, 50 -2, starting_x + column_1_x_offset + vertical_seg_width +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_1_x_offset, 50, starting_x + column_1_x_offset + vertical_seg_width, 90, fill=fill_color, outline="black") 
            if i == 5:
                #self.canvas.create_rectangle(starting_x + column_1_x_offset -2, 10 -2, starting_x + column_1_x_offset + vertical_seg_width +2, 50 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_1_x_offset, 10, starting_x + column_1_x_offset + vertical_seg_width, 50, fill=fill_color, outline="black")
            if i == 6:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 45 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 55 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 45, starting_x + column_2_x_offset + horizontal_seg_length, 55, fill=fill_color, outline="black") 



        
    def make_canvas_display(self, text):
        self.canvas.delete("all")
        self.canvas.create_text(350, 50, text=text, font=("Arial", 24), fill="black")
        self.canvas.update()
        time.sleep(2)
        self.update_circles_based_on_input(self.parent.tmp_state_for_status_widget)

    def make_canvas_say(self, text):
        self.canvas.delete("all")
        self.canvas.create_text(350, 50, text=text, font=("Arial", 24), fill="black")
        self.canvas.update()
        
        
        

    def setup_ui(self):
        connect_button = ctk.CTkButton(self, text="Connect to ILC", command=self.connect_func)
        disconnect_button = ctk.CTkButton(self, text="Disconnect from ILC", command=self.disconnect_func)
        switch_button = ctk.CTkButton(self, text="Switch to Testing Mode", command=self.switch_to_tt)
        
        goToFaqButton = ctk.CTkButton(self, text="User Guide", command=self.goToFaq)

        connect_button.pack(padx=self.paddyx, pady=self.paddyy, side="left")
        disconnect_button.pack(padx=self.paddyx, pady=self.paddyy, side="left")
        switch_button.pack(padx=self.paddyx, pady=self.paddyy, side="left")
        
        goToFaqButton.pack(padx=self.paddyx, pady=self.paddyy, side="left")
        
        if self.parent.connection_status:
            self.update_circles_based_on_input(self.parent.tmp_state_for_status_widget)
        else:
            self.make_canvas_display(f"Welcome to ILC Software")
    
    def goToFaq(self):
        webbrowser.open("https://cpen.vesulo.com/guides/v1#_top")
########################################################################################################################################################





########################################################################################################################################################
#                                                                  TTModeFrame class                                                                   #    
########################################################################################################################################################
class TTModeFrame(ctk.CTkScrollableFrame):
    MAX_COLUMNS = 7

    def __init__(self, parent, switch_to_main_callback, key, serial_connection, callToToggleCLock, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.switch_to_main_callback = switch_to_main_callback
        
        self.key = key
        self.paddyy = 10
        self.paddyx = 10
        self.ser = serial_connection
        self.rows = 0  # Initialize with 0, will be set based on lab data
        self.input_table = []
        self.output_table = []
        self.status_widget, self.canvas, self.progress_canvas = self.create_status_widget()
        self.output_row_index = 0  # Initialize the output row index
        self.currently_open_lab_name = "No Lab Selected"
        self.input_column_visibility_states = [True] * self.MAX_COLUMNS  # Assuming True means visible
        self.output_column_visibility_states = [True] * self.MAX_COLUMNS  # Assuming True means visible
        self.state_machine_row_counter = 0
        self.entry_rows_for_state_machine = [] 
        self.tmp_state_perm_widget = ctk.CTkFrame(self)
        self.toggleClock = callToToggleCLock
        self.setup_ui()
        self.seg_dict = {
            'a': '1110111','b': '0011111','c': '1001110','d': '0111101','e': '1001111','f': '1000111','g': '1111011',
            'h': '0010111','i': '0110000','j': '0111000','l': '0001110','n': '0010101','o': '1111110','p': '1100111',
            'q': '1110011','r': '0000101','s': '1011011','t': '0001111','u': '0011100','y': '0111011','z': '1101101',
            '1': '0110000','2': '1101101','3': '1111001','4': '0110011','5': '1011011','6': '1011111','7': '1110000',
            '8': '1111111','9': '1110011','0': '1111110','-': '0000001','Blank': '0000000'
        }

    def create_status_widget(self):
        status_widget = ctk.CTkFrame(self)

        self.canvas = ctk.CTkCanvas(status_widget, width=650, height=100, highlightthickness=0, bg="darkgrey")
        self.canvas.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        self.progress_canvas = ctk.CTkCanvas(status_widget, width=650, height=20, highlightthickness=0, bg="lightgrey")
        self.progress_canvas.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        status_widget.grid(row = 0, column = 0, padx=10, pady=10, columnspan = 4 )  # Adjust as needed

        return status_widget, self.canvas, self.progress_canvas
    
    def update_circles_based_on_input(self, input_string):
        self.parent.tmp_state_for_status_widget = input_string
        if len(input_string) != 15:
            return
        self.canvas.delete("all")  # Clear the canvas before drawing new circles
        circle_size = 30
        gap = 6
        start_x = 10
        start_y = 40

        self.canvas.create_text(140,18,text='Input Status', font=("Arial", 12), fill="black")

        self.canvas.create_text(415,18,text='Output Status', font=("Arial", 12), fill="black")
        
        colors = input_string.replace('|', '')  # Remove the separator '|'
        for i, color in enumerate(colors):
            if i == 7:
                start_x += 20  # Add extra gap after the 7th circle
            fill_color = 'red' if color == '1' else 'grey'
            
            
            if i <= 6:
                self.canvas.create_rectangle(start_x+5-2, start_y-2, start_x + circle_size/2 + 2, start_y + circle_size +2, fill='grey', outline="black")

                if color == "1":
                    self.canvas.create_rectangle(start_x+5, start_y, start_x + circle_size/2, start_y-15 + circle_size, fill='black', outline="")
                if color == "0":
                    self.canvas.create_rectangle(start_x+5, start_y+15, start_x + circle_size/2, start_y + circle_size, fill='black', outline="")

                self.canvas.create_text(start_x+12.5, start_y + 45, text = f'S{i+1}', font=("Arial", 12), fill="black")
            if i > 6:
                self.canvas.create_oval(start_x, start_y, start_x + circle_size, start_y + circle_size, fill=fill_color, outline="black")
                self.canvas.create_text(start_x+12.5, start_y + 45, text = f'L{i-6}', font=("Arial", 12), fill="black")
            start_x += circle_size + gap


        # offsets for the 7 segment display
        # column 1 left most edge x = 625  seg 4 and 5
        # column 2 left most edge x = 640  seg 6 and 3 and 0
        # column 3 left most edge x = 665  seg 2 and 1
        column_1_x_offset = 25
        column_2_x_offset = 35
        column_3_x_offset = 65
        starting_x = 550
        horizontal_seg_length = 30
        vertical_seg_width = 10
        for i, color in enumerate(colors):
        
            fill_color = 'red' if color == '1' else 'grey' 

            if i == 0:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 10 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 20 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 10, starting_x + column_2_x_offset + horizontal_seg_length, 20, fill=fill_color, outline="black")
            if i == 1:
                #self.canvas.create_rectangle(starting_x + column_3_x_offset -2, 10 -2, starting_x + column_3_x_offset + vertical_seg_width +2 , 50 +2 , fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_3_x_offset, 10, starting_x + column_3_x_offset + vertical_seg_width, 50, fill=fill_color, outline="black") 
            if i == 2:
                #self.canvas.create_rectangle(starting_x + column_3_x_offset -2, 50 -2, starting_x + column_3_x_offset + vertical_seg_width +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_3_x_offset, 50, starting_x + column_3_x_offset + vertical_seg_width, 90, fill=fill_color, outline="black")
            if i == 3:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 80 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 80, starting_x + column_2_x_offset + horizontal_seg_length, 90, fill=fill_color, outline="black")
            if i == 4:
                #self.canvas.create_rectangle(starting_x + column_1_x_offset -2, 50 -2, starting_x + column_1_x_offset + vertical_seg_width +2, 90 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_1_x_offset, 50, starting_x + column_1_x_offset + vertical_seg_width, 90, fill=fill_color, outline="black") 
            if i == 5:
                #self.canvas.create_rectangle(starting_x + column_1_x_offset -2, 10 -2, starting_x + column_1_x_offset + vertical_seg_width +2, 50 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_1_x_offset, 10, starting_x + column_1_x_offset + vertical_seg_width, 50, fill=fill_color, outline="black")
            if i == 6:
                #self.canvas.create_rectangle(starting_x + column_2_x_offset -2, 45 -2, starting_x + column_2_x_offset + horizontal_seg_length +2, 55 +2, fill='black', outline="")
                self.canvas.create_rectangle(starting_x + column_2_x_offset, 45, starting_x + column_2_x_offset + horizontal_seg_length, 55, fill=fill_color, outline="black") 

    def make_canvas_display(self, text):
        self.canvas.delete("all")
        self.canvas.create_text(350, 50, text=text, font=("Arial", 24), fill="black")
        self.canvas.update()
        time.sleep(2)
        self.update_circles_based_on_input(self.parent.tmp_state_for_status_widget)

    def make_canvas_say(self, text):
        self.canvas.delete("all")
        self.canvas.create_text(350, 50, text=text, font=("Arial", 24), fill="black")
        self.canvas.update()

    def update_progress_bar(self, current_row, total_rows):
        self.progress_canvas.delete("all")  # Clear the canvas before drawing new progress
        
        if total_rows == 0: return  # Avoid division by zero

        progress_width = self.progress_canvas.winfo_width()  # Get the current width of the canvas
        section_width = progress_width / total_rows  # Calculate the width of each section

        # Calculate the width of the filled part
        filled_width = section_width * current_row
        
        # Draw the filled part of the progress bar
        self.progress_canvas.create_rectangle(0, 0, filled_width, 20, fill="blue", outline="blue")

        self.progress_canvas.update()  # Update the canvas to reflect the new drawing

    def setup_ui(self):
        # UI components like buttons and labels
        back_button = ctk.CTkButton(self, text="Back to Main", command=self.switch_to_main)
        back_button.grid(row=1, column=0, padx=self.paddyx, pady=self.paddyy)
        
        toggle_clock_button = ctk.CTkButton(self, text="Toggle Clock / Disable Live View", command=self.toggleClock)
        toggle_clock_button.grid(row=1, column=1, padx=self.paddyx, pady=self.paddyy)
                                 
        self.show_7seg_dict_button = ctk.CTkButton(self, text="Show 7 Segment Dict", command=self.show_7seg_dict)
        self.show_7seg_dict_button.grid(row=1, column=2, padx=self.paddyx, pady=self.paddyy)



        load_test_lab_button = ctk.CTkButton(self, text="Test Lab File", command=self.load_test_encrypted_lab)
        load_test_lab_button.grid(row=2, column=0, padx=self.paddyx, pady=self.paddyy)

        self.selected_lab_label = ctk.CTkLabel(self, text=f"Selected Lab: {self.currently_open_lab_name}")
        self.selected_lab_label.grid(row=2, column=1, padx=self.paddyx, pady=self.paddyy)

        create_enc_lab_imhouse = ctk.CTkButton(self, text="Custom Test", command=self.custom_tt_test)
        create_enc_lab_imhouse.grid(row=3, column=0, padx=self.paddyx, pady=self.paddyy)


        self.test_button = ctk.CTkButton(self, text="Run Custom Test", command=self.test_input_table_data)
        self.test_button.grid(row=3, column=2, padx=self.paddyx, pady=self.paddyy)
        self.test_button.grid_remove()  # Hide the test button initially

        self.default_tt_button = ctk.CTkButton(self, text="Default TT", command=self.fill_input_table_with_binary)
        self.default_tt_button.grid(row=3, column=1, padx=self.paddyx, pady=self.paddyy)
        self.default_tt_button.grid_remove()  # Hide the default TT button initially

        self.cancel_custom_test_button = ctk.CTkButton(self, text="Cancel Custom Test", command=self.hide_custom_test)
        self.cancel_custom_test_button.grid(row=3, column=3, padx=self.paddyx, pady=self.paddyy)
        self.cancel_custom_test_button.grid_remove()  # Hide the cancel custom test button initially

        # STATE MACHINE UI BELOW ##############################################################################################################
        
        self.state_machine_button = ctk.CTkButton(self, text="State Machine", command=self.show_state_machine)
        self.state_machine_button.grid(row=4, column=0, padx=self.paddyx, pady=self.paddyy)
        
        self.state_machine_run_button = ctk.CTkButton(self, text="Run State Machine", command=self.run_state_machine)
        self.state_machine_run_button.grid(row=4, column=1, padx=self.paddyx, pady=self.paddyy)
        self.state_machine_run_button.grid_remove()  # Hide the run state machine button initially

        self.state_machine_cancel_button = ctk.CTkButton(self, text="Cancel State Machine", command=self.hide_state_machine)
        self.state_machine_cancel_button.grid(row=4, column=2, padx=self.paddyx, pady=self.paddyy)
        self.state_machine_cancel_button.grid_remove()  # Hide the cancel state machine button initially

        self.state_machine_words_label = ctk.CTkLabel(self, text="State Machine Words")
        self.state_machine_words_label.grid(row=5, column=0, padx=self.paddyx, pady=self.paddyy)
        self.state_machine_words_label.grid_remove()

        self.state_machine_switch_label = ctk.CTkLabel(self, text="Switch 7 State")
        self.state_machine_switch_label.grid(row=5, column=1, padx=self.paddyx, pady=self.paddyy)
        self.state_machine_switch_label.grid_remove()

        self.wl_state_machine_entry = ctk.CTkEntry(self, width=100)
        self.wl_state_machine_entry.grid(row=6, column=0, padx=self.paddyx, pady=self.paddyy)
        self.wl_state_machine_entry.grid_remove()  # Hide the entry initially


        
        self.w1_step_machine = ctk.CTkButton(self, text="Step 0", command=self.step_x0)
        self.w1_step_machine.grid(row=6, column=2, padx=self.paddyx, pady=self.paddyy)
        self.w1_step_machine.grid_remove()  # Hide the button initially
        
        self.w2_step_machine = ctk.CTkButton(self, text="Step 1", command=self.step_x1)
        self.w2_step_machine.grid(row=7, column=2, padx=self.paddyx, pady=self.paddyy)
        self.w2_step_machine.grid_remove()  # Hide the button initially

        self.wl_switch_label = ctk.CTkLabel(self, text="0")
        self.wl_switch_label.grid(row=6, column=1, padx=self.paddyx, pady=self.paddyy)
        self.wl_switch_label.grid_remove()

        self.w2_state_machine_entry = ctk.CTkEntry(self, width=100) 
        self.w2_state_machine_entry.grid(row=7, column=0, padx=self.paddyx, pady=self.paddyy)
        self.w2_state_machine_entry.grid_remove()  # Hide the entry initially

        self.w2_switch_label = ctk.CTkLabel(self, text="1")
        self.w2_switch_label.grid(row=7, column=1, padx=self.paddyx, pady=self.paddyy)
        self.w2_switch_label.grid_remove()

        self.add_state_machine_permutaion_boxs_button = ctk.CTkButton(self, text="Add Extra State To Check", command=self.add_state_machine_permutaion_boxs)
        self.add_state_machine_permutaion_boxs_button.grid(row=10, column=0, padx=self.paddyx, pady=self.paddyy)
        self.add_state_machine_permutaion_boxs_button.grid_remove()  # Hide the button initially

        self.perm_widget_label = ctk.CTkLabel(self, text="State Machine Permutation's")
        self.perm_widget_label.grid(row=8, column=0, padx=self.paddyx, pady=self.paddyy)
        self.perm_widget_label.grid_remove()  # Hide the label initially
        
        self.update_circles_based_on_input(self.parent.tmp_state_for_status_widget)

        
    def step_x0(self):
        if not self.parent.isClockOn:
            
            self.parent.allow_serial_read = False
            
            self.w2_step_machine.grid_remove()
            self.update()
            
            self.ser.write('x0'.encode('utf-8'))
            response = self.parent.get_response_from_serial()
            if response == '':
                self.make_canvas_display("No response from ILC")
                self.w2_step_machine.grid(row=6, column=2, padx=self.paddyx, pady=self.paddyy)
                self.parent.allow_serial_read = True
                self.update()
                return
            
            input_data, output_data = response.split('|') if '|' in response else ('', '')
            self.update_circles_based_on_input(response)
            
            self.w2_step_machine.grid(row=6, column=2, padx=self.paddyx, pady=self.paddyy)
            self.update()
            
            self.parent.allow_serial_read = True
        else:
            self.make_canvas_display("Make Sure Clock is off")
    def step_x1(self):

        if not self.parent.isClockOn:
            
            self.parent.allow_serial_read = False
            
            self.w2_step_machine.grid_remove()
            self.update()
            
            self.ser.write('x1'.encode('utf-8'))
            response = self.parent.get_response_from_serial()
            if response == '':
                self.make_canvas_display("No response from ILC")
                self.w2_step_machine.grid(row=7, column=2, padx=self.paddyx, pady=self.paddyy)
                self.parent.allow_serial_read = True
                self.update()
                return
            
            input_data, output_data = response.split('|') if '|' in response else ('', '')
            self.update_circles_based_on_input(response.strip())
            
            self.w2_step_machine.grid(row=7, column=2, padx=self.paddyx, pady=self.paddyy)
            self.update()
            
            self.parent.allow_serial_read = True
        else:
            self.make_canvas_display("Make Sure Clock is off")


    def add_state_machine_permutaion_boxs(self):
        """
        Adds state machine permutation boxes to the GUI.

        This method adds a set of input boxes to the GUI for specifying the starting state, starting letter, and state after input
        for a state machine permutation. The input boxes are dynamically created and placed in the GUI grid.

        Returns:
            None
        """
        self.tmp_state_perm_widget.grid(row=9, column=0, columnspan=1, padx=self.paddyx, pady=self.paddyy)

        perm_box_1 = ctk.CTkEntry(self.tmp_state_perm_widget, width=30)
        perm_box_1.grid(row=self.state_machine_row_counter+1, column=0, padx=self.paddyx, pady=self.paddyy,)
        starting_state = ctk.CTkLabel(self.tmp_state_perm_widget, text="Starting State")
        starting_state.grid(row=0, column=0, padx=self.paddyx, pady=self.paddyy)

        perm_box_2 = ctk.CTkEntry(self.tmp_state_perm_widget, width=30)
        perm_box_2.grid(row=self.state_machine_row_counter+1, column=1, padx=self.paddyx, pady=self.paddyy)
        starting_letter = ctk.CTkLabel(self.tmp_state_perm_widget, text="Starting Letter")
        starting_letter.grid(row=0, column=1, padx=self.paddyx, pady=self.paddyy)

        perm_box_3 = ctk.CTkEntry(self.tmp_state_perm_widget, width=30)
        perm_box_3.grid(row=self.state_machine_row_counter+1, column=2, padx=self.paddyx, pady=self.paddyy)
        state_afer_input = ctk.CTkLabel(self.tmp_state_perm_widget, text="State After Input")
        state_afer_input.grid(row=0, column=2, padx=self.paddyx, pady=self.paddyy)

        self.entry_rows_for_state_machine.append([perm_box_1, perm_box_2, perm_box_3])

        self.state_machine_row_counter += 1

    def remove_all_entry_rows_for_state_machine(self):
        # Iterate through all rows in the entry_rows_for_state_machine list
        for row in self.entry_rows_for_state_machine:
            # Loop through each entry widget in the row and remove it from the grid
            for entry in row:
                entry.destroy()  # or entry.destroy() if you want to permanently delete it
        
        # Clear the list of entry rows after removing the widgets
        self.entry_rows_for_state_machine.clear()
        
        # Reset the state_machine_row_counter since all entries are removed
        self.state_machine_row_counter = 0
        
        # Reposition the button for adding new rows of entries
        # Assuming the button should be positioned after all existing rows
        # Adjust this line if the button should be in a different position

    def switch_to_main(self):
        self.destroy()
        self.switch_to_main_callback()

    def run_state_machine(self):
        self.parent.allow_serial_read = False


        doesStateMachinePass = True

        if self.parent.isClockOn:
            self.ser.write('#'.encode('utf-8'))
            time.sleep(2)
            self.parent.isClockOn = False

        word1 = self.wl_state_machine_entry.get().lower()
        word1_switch_state = self.wl_switch_label.cget("text")
        word2 = self.w2_state_machine_entry.get().lower()
        word2_switch_state = self.w2_switch_label.cget("text")
        
        if True != (self.is_string_valid(word1) and self.is_string_valid(word2)):
            self.make_canvas_display("Please enter valid strings/edge cases.")
            return
        edge_case_list = []

        for row in self.entry_rows_for_state_machine:
            values = [entry.get() for entry in row]  # Retrieve the current value from each Entry
            edge_case_list.append(values)  # Append the list of values to the edge_case_list

        word1_list = (list)(word1)
        word2_list = (list)(word2)

        output_data = ""
        for i in range(len(word1_list)+1):  # Replace 100 with the desired maximum number of iterations
            self.make_canvas_display(f"searching for first state")
            if output_data == self.seg_dict_find_opposite(word1_list[0]):
                self.make_canvas_display(f"found first state")
                break
            
            self.ser.write('x0'.encode('utf-8'))
            response = self.parent.get_response_from_serial()
            if response == '':
                self.make_canvas_display("No response from ILC")
                break
            
            inputtrash, output_data = response.split('|') if '|' in response else ('', '')
            
            
            if i == len(word1_list):
                self.make_canvas_display("ILC did not reach first state")
                self.ser.write('#'.encode('utf-8'))
                self.parent.isClockOn = True
                time.sleep(1)
                self.parent.allow_serial_read = True
                return

        self.make_canvas_display(f"Testing word 1")
        for i in range(len(word1_list)):
            self.update_progress_bar(i, len(word1_list))
            if i != 0:
                self.ser.write('x0'.encode('utf-8'))
                response = self.parent.get_response_from_serial()
                if response == '':
                    self.make_canvas_display("No response from ILC")
                    break
                
                input_data, output_data = response.split('|') if '|' in response else ('', '')
            if output_data != self.seg_dict_find_opposite(word1_list[i]):
                self.make_canvas_display(f"Letter {i} in word 1 is wrong")
                doesStateMachinePass = False
                break
            if i == len(word1_list)-1:
                self.make_canvas_display(f"Valid for word 1")
                self.update_progress_bar(0, 1) # Reset the progress bar after completing the test

                
        self.make_canvas_display(f"Testing word 2")        
        for i in range(len(word2_list)):
            self.update_progress_bar(i, len(word2_list))
            if i != 0:
                self.ser.write('x1'.encode('utf-8'))
                response = self.parent.get_response_from_serial()
                if response == '':
                    self.make_canvas_display("No response from ILC")
                    break
                
                input_data, output_data = response.split('|') if '|' in response else ('', '')
            if output_data != self.seg_dict_find_opposite(word2_list[i]):
                self.make_canvas_display(f"Letter {i} in word 2 is wrong")
                doesStateMachinePass = False
                break
            if i == len(word2_list)-1:
                self.make_canvas_display(f"Valid for word 2")
                self.update_progress_bar(0, 1) # Reset the progress bar after completing the test

                
        self.make_canvas_display(f"Testing extra states")  
        edgeCounter = 0     
        for edge_case in edge_case_list:
            self.update_progress_bar(edgeCounter, len(edge_case_list))
            edgeCounter += 1
            
            # check if edde_case[0] is 0 or 1
            # if 0 then send x0 untill the output is equal to self.seg_dict_find_opposite(edge_case[1])
            # if 1 then send x1 untill the output is equal to self.seg_dict_find_opposite(edge_case[1])
            # if the output is equat to edge_case[1] then send the opposite either x0 or x1
            # and check if output is equal to edge_case[2]
            if edge_case[0] == '0':
                for i in range(len(word1_list)):
                    if output_data == self.seg_dict_find_opposite(edge_case[1]):
                        self.ser.write('x1'.encode('utf-8'))
                        response = self.parent.get_response_from_serial()
                        if response == '':
                            self.make_canvas_display("No response from ILC")
                            break
                        
                        _, output_data = response.split('|') if '|' in response else ('', '')
                        if output_data == self.seg_dict_find_opposite(edge_case[2]):
                            self.make_canvas_display(f"Valid: {edge_case}")

                        else:
                            self.make_canvas_display(f"Extra State Not Valid")
                            doesStateMachinePass = False

                    else:
                        self.ser.write('x0'.encode('utf-8'))
                        response = self.parent.get_response_from_serial()
                        if response == '':
                            self.make_canvas_display("No response from ILC")
                            break
                        
                        _, output_data = response.split('|') if '|' in response else ('', '')
                    if i == len(word1_list):
                        doesStateMachinePass = False
                        self.make_canvas_display(f"Not Valid for: {edge_case}")
                        self.update_progress_bar(0, 1) # Reset the progress bar after completing the test
                        break
            if edge_case[0] == '1':
                for i in range(len(word2_list)):
                    if output_data == self.seg_dict_find_opposite(edge_case[1]):
                        self.ser.write('x0'.encode('utf-8'))
                        response = self.parent.get_response_from_serial()
                        if response == '':
                            self.make_canvas_display("No response from ILC")
                            break
                        
                        _, output_data = response.split('|') if '|' in response else ('', '')
                        if output_data == self.seg_dict_find_opposite(edge_case[2]):
                            self.make_canvas_display(f"Valid: {edge_case}")

                        else:
                            self.make_canvas_display(f"Extra State Not Valid")
                            doesStateMachinePass = False

                    else:
                        self.ser.write('x1'.encode('utf-8'))
                        response = self.parent.get_response_from_serial()
                        if response == '':
                            self.make_canvas_display("No response from ILC")
                            break
                        
                        _, output_data = response.split('|') if '|' in response else ('', '')
                    if i == len(word2_list):
                        doesStateMachinePass = False
                        self.make_canvas_display(f"Not Valid for: {edge_case}")
                        self.update_progress_bar(0, 1) # Reset the progress bar after completing the test
                        break
            

        
        if doesStateMachinePass:
            self.make_canvas_display("State Machine is valid")
            self.update_progress_bar(0, 1) # Reset the progress bar after completing the test
            self.ser.write('#'.encode('utf-8'))
            self.parent.isClockOn = True
        else:
            self.make_canvas_display("State Machine DID not pass")
            self.update_progress_bar(0, 1) # Reset the progress bar after completing the test
            self.ser.write('#'.encode('utf-8'))
            self.parent.isClockOn = True

        self.parent.allow_serial_read = True
            
            

    def is_string_valid(self, input_string):
        """
        Check if the input string uses only keys available in the provided dictionary.

        :param input_string: The string to check.
        :param mapping_dict: The dictionary with available keys.
        :return: True if the string uses only keys from the dictionary, False otherwise.
        """
        return all(char in self.seg_dict for char in input_string)
      
        
    def seg_dict_find_opposite(self, input_value):
        """
        Given a dictionary mapping and an input value (either a key or a value of the dictionary),
        return the opposite (if a key is given, return value; if a value is given, return key).
        If the input_value is not found, return None.
        """
        # If the input is a key in the dictionary, return its value
        if input_value in self.seg_dict:
            return self.seg_dict[input_value]
        
        # If the input is a value in the dictionary, return its key
        for key, value in self.seg_dict.items():
            if input_value == value:
                return key
        
        # If the input value is not found as a key or value, return None
        return None
    def show_7seg_dict(self):
        popup = ctk.CTkToplevel(self)
        popup.title("7 segment dictionary")
        popup.geometry("200x650")
        popup.attributes('-topmost', True)

        row_ = 0
        column_ = 0
        for key, value in self.seg_dict.items():
            ctk.CTkLabel(popup, text=f"{key} : {value}").grid(padx=10, pady=1, row = row_, column = column_)
            row_ += 1

            if key == 'z':
                row_ = 0
                column_ += 1


        return

    def custom_tt_test(self):
            # Special command or password to switch to InstructorAccessFrame
            special_command = "ILC_is_number_1"

            # Ask for input, which could be the special command or the desired number of rows
            user_input = simpledialog.askstring("Set Rows:", "Enter the number of rows for the table:")

            # Check if the user input matches the special command
            if user_input == special_command:
                self.switch_to_instructor_access()
            else:
                if not user_input.isdigit() or int(user_input) < 0:
                    # Do something if the user input is not a number or a negative number
                    self.make_canvas_display("Please enter a valid number.")
                    return
                try:
                    num_rows = int(user_input)
                    if 1 <= num_rows <= (7*7):  # Assuming you have a maximum limit
                        self.rows = num_rows
                        self.setup_tables()  # Re-setup tables based on new row count
                except ValueError:
                    # If the conversion fails, it means the input was not a valid integer
                    self.make_canvas_display("Please enter a valid number.")
            self.show_custom_test()

    def switch_to_instructor_access(self):
        # Assuming self.parent is an instance of ILCApplication
        # Transition to InstructorAccessFrame
        instructor_frame = InstructorAccessFrame(self.parent, self.key, self.parent.switch_to_main_mode)
        instructor_frame.pack(padx=self.paddyx, pady=self.paddyy, expand=True, fill='both')
        self.pack_forget()  # Hide the current TTModeFrame

    def setup_tables(self):
        # Clear existing tables if they exist and their frames
        if hasattr(self, 'input_table_frame'):
            self.input_table_frame.destroy()
        if hasattr(self, 'output_table_frame'):
            self.output_table_frame.destroy()


        
        # Create frames for the input and output tables
        self.input_table_frame = ctk.CTkFrame(self)
        self.input_table_frame.grid(row=4, column=0, columnspan=2, padx=self.paddyx, pady=self.paddyy)

        input_table_label = ctk.CTkLabel(self.input_table_frame, text="Input Table")
        input_table_label.grid(row=0, column=0, padx=self.paddyx, pady=self.paddyy, columnspan=self.MAX_COLUMNS)

        for col_index in range(self.MAX_COLUMNS):
            s_label = ctk.CTkLabel(self.input_table_frame, text=f"S{col_index+1}")
            s_label.grid(row=1, column=col_index, padx=1, pady=1, sticky="nsew")
        
        self.output_table_frame = ctk.CTkFrame(self)
        self.output_table_frame.grid(row=4, column=2, columnspan=2, padx=self.paddyx, pady=self.paddyy)

        output_table_label = ctk.CTkLabel(self.output_table_frame, text="Output Table")
        output_table_label.grid(row=0, column=0, padx=self.paddyx, pady=self.paddyy, columnspan=self.MAX_COLUMNS)

        for col_index in range(self.MAX_COLUMNS):
            l_label = ctk.CTkLabel(self.output_table_frame, text=f"L{col_index+1}")
            l_label.grid(row=1, column=col_index, padx=1, pady=1)

        self.input_table = []
        self.output_table = []


        for i in range(self.MAX_COLUMNS):  # Use MAX_COLUMNS for input table
            switch = ctk.CTkCheckBox(self.input_table_frame, text=f"", command=lambda i=i: self.update_column_visibility(i, is_input=True), width=20, height=15) 
            switch.grid(row=2, column=i)  # Align directly with columns starting from 0
            switch.select()  # Deselect the checkbox by default
        
        for i in range(self.MAX_COLUMNS):  # Use MAX_COLUMNS for input table
            switch = ctk.CTkCheckBox(self.output_table_frame, text=f"", command=lambda i=i: self.update_column_visibility(i, is_input=False), width=20, height=15)
            switch.grid(row=2, column=i)  # Align directly with columns starting from 0
            switch.select()  # Deselect the checkbox by default

        # Initialize the input and output tables within their respective frames
        self.initialize_input_table(1, self.input_table_frame)
        self.initialize_output_table(1, self.output_table_frame)

    def update_column_visibility(self, column_index, is_input):
        # Toggle the state based on checkbox action
        if is_input:
            self.input_column_visibility_states[column_index] = not self.input_column_visibility_states[column_index]
            # Update visibility for the specific column in the input table
            for row_entries in self.input_table:
                entry = row_entries[column_index]
                if self.input_column_visibility_states[column_index]:
                    entry.grid()
                else:
                    entry.delete(0, 'end')  # Clear the entry if it's hidden
                    entry.insert(0, "0")
                    entry.grid_remove()
        else:
            self.output_column_visibility_states[column_index] = not self.output_column_visibility_states[column_index]
            # Update visibility for the specific column in the output table
            for row_entries in self.output_table:
                    entry = row_entries[column_index]
                    if self.output_column_visibility_states[column_index]:
                        entry.grid()
                    else:
                        entry.grid_remove()


    def initialize_input_table(self, start_row, parent_widget):
        self.input_table = []
        for row_index in range(self.rows):
            row_entries = []
            for col_index in range(self.MAX_COLUMNS):
                entry = ctk.CTkEntry(parent_widget, width=30, height=25)
                entry.grid(row=row_index+3, column=col_index, padx=2, pady=1)           # +2 to account for the label row
                row_entries.append(entry) # Call the method to update the visibility
            self.input_table.append(row_entries)

    def initialize_output_table(self, start_row, parent_widget):
        self.output_table = []
        for row_index in range(self.rows):
            row_entries = []
            for col_index in range(self.MAX_COLUMNS):
                entry = ctk.CTkEntry(parent_widget, width=30, height=25, state='disabled') 
                entry.grid(row=row_index+3, column=col_index, padx=2, pady=1)           # +2 to account for the label row
                row_entries.append(entry) # Call the method to update the visibility
            self.output_table.append(row_entries)

    def hide_custom_test(self):
        if hasattr(self, 'input_table_frame'):
            self.input_table_frame.grid_remove()
        if hasattr(self, 'output_table_frame'):
            self.output_table_frame.grid_remove()
        self.test_button.grid_remove()
        self.default_tt_button.grid_remove()
        self.cancel_custom_test_button.grid_remove()

        self.state_machine_button.grid() # State Machine button is shown

        self.input_column_visibility_states = [True] * self.MAX_COLUMNS  # Reset the visibility states
        self.output_column_visibility_states = [True] * self.MAX_COLUMNS  # Reset the visibility states

 
    def show_custom_test(self):
        self.state_machine_button.grid_remove()
        self.setup_tables()
        self.input_table_frame.grid()
        self.output_table_frame.grid()
        self.test_button.grid()
        self.default_tt_button.grid()
        self.cancel_custom_test_button.grid()


        self.hide_state_machine()                 # Hide the state machine UI
           # Hide the state machine button

    def show_state_machine(self):
        self.state_machine_run_button.grid()
        self.state_machine_cancel_button.grid()
        self.wl_state_machine_entry.grid()
        self.wl_switch_label.grid()
        self.w2_state_machine_entry.grid()
        self.w2_switch_label.grid()
        self.state_machine_words_label.grid()
        self.state_machine_switch_label.grid()
        self.add_state_machine_permutaion_boxs_button.grid()
        self.tmp_state_perm_widget.grid()  # Show the temporary state machine permutation widget
        self.w1_step_machine.grid()
        self.w2_step_machine.grid()
        
        
        self.hide_custom_test()               # Hide the custom test UI


    def hide_state_machine(self):
        self.state_machine_run_button.grid_remove()
        self.state_machine_cancel_button.grid_remove()
        self.wl_state_machine_entry.grid_remove()
        self.wl_switch_label.grid_remove()
        self.w2_state_machine_entry.grid_remove()
        self.w2_switch_label.grid_remove()
        self.state_machine_words_label.grid_remove()
        self.state_machine_switch_label.grid_remove()
        self.add_state_machine_permutaion_boxs_button.grid_remove()
        self.perm_widget_label.grid_remove()
        self.w1_step_machine.grid_remove()
        self.w2_step_machine.grid_remove()

        self.tmp_state_perm_widget.grid_remove()  # Hide the temporary state machine permutation widget
        self.remove_all_entry_rows_for_state_machine()  # Remove all entry rows from the state machine UI

    


    def test_input_table_data(self):
        self.parent.allow_serial_read = False  # Stop the background thread from reading
        for row_entries in self.input_table:
            for entry in row_entries:
                if len(entry.get()) > 1:
                    self.make_canvas_display("Please enter only one bit per cell.")
                    return
                if not entry.get().isdigit():
                    self.make_canvas_display("Please enter only binary values.")
                    return
        self.output_row_index = 0  # Reset the output row index before starting the test
        total_rows = len(self.input_table)

        for row_entries in self.input_table:
            input_data = ''.join([entry.get() for entry in row_entries])
            self.ser.write(input_data.encode('utf-8'))
            print(f"Sent: {input_data}")

            # Initialize variables for response waiting
            response = ""
            start_time = time.time()
            timeout = 3  # Set a timeout period (in seconds)

            # Wait for a response or until timeout
            response = self.parent.get_response_from_serial()
            if response == '':
                print("No response from ILC")
                break

            # Check if a response was received
            if response.strip() and self.output_row_index < self.rows:
                self.update_output_table_with_response(response.strip())
                self.update_circles_based_on_input(response.strip())
                self.update_progress_bar(self.output_row_index + 1, total_rows)
                self.output_row_index += 1  # Move to the next row
            else:
                print(f"INVALID / No Response row {self.output_row_index}")
                break  # Exit if no response is received or we've filled all rows


        self.update_progress_bar(0, 1)  # Reset the progress bar
        self.parent.allow_serial_read = True  # Resume the background thread reading

    def update_output_table_with_response(self, response):
        # Split the response into input and output parts
        _, output_data = response.split('|') if '|' in response else ('', '')

        # Check if the output_data has the expected length for one row
        if len(output_data) == self.MAX_COLUMNS:
            row_entries = self.output_table[self.output_row_index]  # Get the current row to update
            for entry, bit in zip(row_entries, output_data):
                entry.configure(state='normal')  # Enable the entry to modify it
                entry.delete(0, "end")
                entry.insert(0, bit)
                entry.configure(state='disabled')  # Disable the entry again
                self.update()
        else:
            print(f"Output data format error: {output_data}")
            print(f"Full response: {response}")

    def fill_input_table_with_binary(self):
        print("Filling input table with binary values")  # Debug print
        for i, row_entries in enumerate(self.input_table):
            binary_string = format(i, '0{}b'.format(self.MAX_COLUMNS))
            print(f"Row {i} binary: {binary_string}")  # Debug print
            for entry, bit in zip(row_entries, binary_string):
                entry.delete(0, "end")
                entry.insert(0, bit)
        self.update()  # Refresh the GUI

    def decrypt_lab_data(self, encrypted_lab_content):
        lines = encrypted_lab_content.splitlines()
        if len(lines) < 2:
            print("Encrypted lab file format error.")
            return []

        nonce = b64decode(lines[0])
        ciphertext = b64decode(lines[1])
        
        cipher = ChaCha20.new(key=self.key, nonce=nonce)
        decrypted_data = cipher.decrypt(ciphertext).decode('utf-8')

        lab_data = [row.split(',') for row in decrypted_data.split('\r\n') if row]
        return lab_data

    def load_test_encrypted_lab(self):
        filename = filedialog.askopenfilename(title="Open Encrypted Lab", filetypes=(("Encrypted labs", "*.ILC"), ("All files", "*.*")))
        if not filename:
            return

        with open(filename, 'r') as file:
            encrypted_lab_content = file.read()

        self.currently_open_lab_name = os.path.basename(filename)
        self.selected_lab_label.configure(text=f"Selected Lab: {self.currently_open_lab_name}")

        decrypted_lab_data = self.decrypt_lab_data(encrypted_lab_content)
        print(f"Decrypted lab data: {decrypted_lab_data}")                       # DEBUGGING PRINT

        self.rows = len(decrypted_lab_data)
        self.setup_tables()

        for i, row_data in enumerate(decrypted_lab_data):
            input_data = ','.join(row_data).split('|')[0].split(',')
            for entry, bit in zip(self.input_table[i], input_data):
                entry.delete(0, "end")
                entry.insert(0, bit)
                entry.configure(state='readonly')

        # Hide the tables after loading
        self.hide_custom_test()

        # Trigger the encrypted lab test
        self.run_encrypted_lab_test(decrypted_lab_data)  # Uncomment or modify according to your needs

    def run_encrypted_lab_test(self, decrypted_lab_data):
        self.parent.allow_serial_read = False  # Stop the background thread from reading
        self.test_input_table_data()  # Assuming this method populates the output table correctly

        all_matched = True
        for i, row_data in enumerate(decrypted_lab_data):
            # Concatenate the row into a CSV string and then split by '|'
            row_str = ','.join(row_data)
            parts = row_str.split('|')
            if len(parts) == 2:
                # Strip leading/trailing spaces that might cause empty elements
                desired_output_str = parts[1].strip()
                desired_output = [bit.strip() for bit in desired_output_str.split(',') if bit]

                # Retrieve the actual output from the output table
                actual_output_entries = self.output_table[i]
                actual_output = [entry.get() for entry in actual_output_entries]

                # Debug print to check the actual and expected values
                # print(f"Row {i} expected: {desired_output}, got: {actual_output}")

                if actual_output != desired_output:
                    print(f"Mismatch found in row {i}: expected {desired_output}, got {actual_output}")
                    all_matched = False
                    self.make_canvas_display(f"Mismatch found in row {i}")
                    break  # Stop at first mismatch

        if all_matched:
            self.make_canvas_display("Success your circuit is Valid.")
            time.sleep(2)
        self.update_progress_bar(0, 1)  # Reset the progress bar
        self.parent.allow_serial_read = True  # Resume the background thread reading
########################################################################################################################################################




########################################################################################################################################################
#                                                                  InstructorAccessFrame class                                                         #
########################################################################################################################################################            
class InstructorAccessFrame(ctk.CTkScrollableFrame):
    def __init__(self, parent, key, switch_to_main_callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.key = key
        self.paddy_x = 10
        self.paddy_y = 5
        self.switch_to_main_callback = switch_to_main_callback
        self.rows = 0  # Start with no rows, will be set by the user
        self.input_table = []  # Store input table entries
        self.output_table = []  # Store output table entries
        self.MAX_COLUMNS = 7  # Maximum number of columns
        self.setup_ui()

    def setup_ui(self):
        self.back_button = ctk.CTkButton(self, text="Back", command=self.switch_to_main)
        self.back_button.grid(row= 0, column = 0, pady=10)

        self.encrypt_from_csv_button = ctk.CTkButton(self, text="Encrypt New Lab from .csv", command=self.encrypt_new_lab_from_csv)
        self.encrypt_from_csv_button.grid(row= 1, column = 0,pady = self.paddy_y, padx = self.paddy_x)



        # New UI components for data input
        self.create_enc_lab_inhouse = ctk.CTkButton(self, text="Make .ILC in app", command=self.create_enc_lab_inhouse)
        self.create_enc_lab_inhouse.grid(row= 2, column = 0,pady = self.paddy_y, padx = self.paddy_x)

        self.encrypt_and_save_lab_inhouse = ctk.CTkButton(self, text="Encrypt & Save Lab", command=self.encrypt_and_save_lab)
        self.encrypt_and_save_lab_inhouse.grid(row= 2, column = 1,pady = self.paddy_y, padx = self.paddy_x)
        self.encrypt_and_save_lab_inhouse.grid_remove()  # Hide the encrypt button initially

        self.default_input_button = ctk.CTkButton(self, text="Default Input", command=self.fill_input_table_with_binary)
        self.default_input_button.grid(row=0, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.default_input_button.grid_remove()  # Hide the default input button initially

        self.default_output_button = ctk.CTkButton(self, text="Default Output", command=self.fill_output_table_with_binary)
        self.default_output_button.grid(row=1, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.default_output_button.grid_remove()  # Hide the default output button initially

        # Add these lines in your setup_ui method
        self.fill_input_row_1_button = ctk.CTkButton(self, text="Input Row All 1", command=lambda: self.prompt_and_fill('input_row', '1'))
        self.fill_input_row_1_button.grid(row=2, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_row_1_button.grid_remove()  # Hide the button initially

        self.fill_output_row_1_button = ctk.CTkButton(self, text="Output Row All 1", command=lambda: self.prompt_and_fill('output_row', '1'))
        self.fill_output_row_1_button.grid(row=3, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_row_1_button.grid_remove()  # Hide the button initially

        self.fill_input_col_1_button = ctk.CTkButton(self, text="Input Col All 1", command=lambda: self.prompt_and_fill('input_col', '1'))
        self.fill_input_col_1_button.grid(row=4, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_col_1_button.grid_remove()  # Hide the button initially

        self.fill_output_col_1_button = ctk.CTkButton(self, text="Output Col All 1", command=lambda: self.prompt_and_fill('output_col', '1'))
        self.fill_output_col_1_button.grid(row=5, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_col_1_button.grid_remove()  # Hide the button initially

        # Repeat for buttons to fill with 0's
        self.fill_input_row_0_button = ctk.CTkButton(self, text="Input Row All 0", command=lambda: self.prompt_and_fill('input_row', '0'))
        self.fill_input_row_0_button.grid(row=6, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_row_0_button.grid_remove()

        self.fill_output_row_0_button = ctk.CTkButton(self, text="Output Row All 0", command=lambda: self.prompt_and_fill('output_row', '0'))
        self.fill_output_row_0_button.grid(row=7, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_row_0_button.grid_remove()

        self.fill_input_col_0_button = ctk.CTkButton(self, text="Input Col All 0", command=lambda: self.prompt_and_fill('input_col', '0'))
        self.fill_input_col_0_button.grid(row=8, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_col_0_button.grid_remove()

        self.fill_output_col_0_button = ctk.CTkButton(self, text="Output Col All 0", command=lambda: self.prompt_and_fill('output_col', '0'))
        self.fill_output_col_0_button.grid(row=9, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_col_0_button.grid_remove()

        self.fill_input_all_1_button = ctk.CTkButton(self, text="Input All 1", command=lambda: self.fill_input_all('1'))
        self.fill_input_all_1_button.grid(row=10, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_all_1_button.grid_remove()  # Hide the button initially

        self.fill_input_all_0_button = ctk.CTkButton(self, text="Input All 0", command=lambda: self.fill_input_all('0'))
        self.fill_input_all_0_button.grid(row=11, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_input_all_0_button.grid_remove()  # Hide the button initially

        self.fill_output_all_1_button = ctk.CTkButton(self, text="Output All 1", command=lambda: self.fill_output_all('1'))
        self.fill_output_all_1_button.grid(row=12, column=4, pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_all_1_button.grid_remove()  # Hide the button initially

        self.fill_output_all_0_button = ctk.CTkButton(self, text="Output All 0", command=lambda: self.fill_output_all('0'))
        self.fill_output_all_0_button.grid(row=13, column=4,  pady = self.paddy_y, padx = self.paddy_x)
        self.fill_output_all_0_button.grid_remove()  # Hide the button initially

        # Placeholder frames for input and output tables
        self.input_table_frame = ctk.CTkFrame(self)
        self.input_table_frame.grid(row= 3, column = 0,pady=10, padx=10, columnspan = 2, rowspan = 20)

        self.output_table_frame = ctk.CTkFrame(self)
        self.output_table_frame.grid(row= 3, column = 2, pady=10 , padx=10, columnspan = 2, rowspan = 20)

    def switch_to_main(self):
        self.pack_forget()
        self.switch_to_main_callback()

    def encrypt_new_lab_from_csv(self):
        # Prompt the user for the new lab name
        new_lab_name = simpledialog.askstring("New Lab Name", "Enter the name of the new lab:")
        if new_lab_name:
            # Ask the user for the CSV file to encrypt
            new_lab_path = filedialog.askopenfile(title="Open Lab File", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
            if new_lab_path:  # Ensure the user selected a file
                self.encrypt(new_lab_path, new_lab_name)

    def encrypt(self, plainfile_path, new_lab_name):
        reader = csv.reader(plainfile_path, dialect='excel', quoting=csv.QUOTE_MINIMAL) #!

        pt = ''
        for row in reader:
            pt += ",".join(row) + "\r\n"
        if(pt[-1] == "\n" and pt[-2] == "\r"):
            pt = pt[:-2]
            
        cipher = ChaCha20.new(key=self.key)
        nonce = b64encode(cipher.nonce).decode('utf-8')
        ectxt = b64encode(cipher.encrypt(pt.encode('utf-8')))
        
        with open(f'{new_lab_name}_encrypted.ILC', 'w', newline='') as encfile:
            encfile.write(nonce+"\r\n")
            encfile.write(ectxt.decode('utf-8-sig'))

            messagebox.showinfo("Success", f"Lab '{new_lab_name}' encrypted and saved as '{new_lab_name}'_encrypted.ILC ")

    def create_enc_lab_inhouse(self):
        # Ask the user for the number of rows
        self.encrypt_and_save_lab_inhouse.grid()  # Show the encrypt button
        self.default_input_button.grid()  # Show the default input button
        self.default_output_button.grid()  # Show the default output button

        self.fill_input_row_1_button.grid()  # Show the fill input row 1 button
        self.fill_output_row_1_button.grid()  # Show the fill output row 1 button
        self.fill_input_col_1_button.grid()  # Show the fill input col 1 button
        self.fill_output_col_1_button.grid()  # Show the fill output col 1 button

        self.fill_input_row_0_button.grid()  # Show the fill input row 0 button
        self.fill_output_row_0_button.grid()  # Show the fill output row 0 button
        self.fill_input_col_0_button.grid()  # Show the fill input col 0 button
        self.fill_output_col_0_button.grid()  # Show the fill output col 0 button

        self.fill_input_all_1_button.grid()  # Show the fill input all 1 button
        self.fill_input_all_0_button.grid()  # Show the fill input all 0 button
        self.fill_output_all_1_button.grid()  # Show the fill output all 1 button
        self.fill_output_all_0_button.grid()  # Show the fill output all 0 button

        num_rows = simpledialog.askinteger("Number of Rows", "Enter the number of rows:", parent=self)
        if num_rows and num_rows > 0:
            self.rows = num_rows
            self.initialize_tables()
    
    def fill_input_table_with_binary(self):
        for i, row in enumerate(self.input_table):
            binary_string = format(i, f'0{self.MAX_COLUMNS}b')
            for entry, bit in zip(row, binary_string):
                entry.delete(0, ctk.END)
                entry.insert(0, bit)

    def fill_output_table_with_binary(self):
        for i, row in enumerate(self.output_table):
            binary_string = format(i, f'0{self.MAX_COLUMNS}b')
            for entry, bit in zip(row, binary_string):
                entry.delete(0, ctk.END)
                entry.insert(0, bit)

    def fill_row(self, table, row_index, value):
        if row_index < len(table):
            for entry in table[row_index]:
                entry.delete(0, "end")
                entry.insert(0, value)

    def fill_column(self, table, col_index, value):
        for row in table:
            if col_index < len(row):
                row[col_index].delete(0, "end")
                row[col_index].insert(0, value)

    def prompt_and_fill(self, fill_type, value):
        if fill_type in ['input_row', 'output_row']:
            row_index = simpledialog.askinteger("Row Index", "Enter the row index:")
            if row_index is not None:
                table = self.input_table if fill_type == 'input_row' else self.output_table
                self.fill_row(table, row_index, value)
        elif fill_type in ['input_col', 'output_col']:
            col_index = simpledialog.askinteger("Column Index", "Enter the column index:")
            if col_index is not None:
                table = self.input_table if fill_type == 'input_col' else self.output_table
                self.fill_column(table, col_index, value)

    def fill_table(self, table, value):
        for row in table:
            for entry in row:
                entry.delete(0, "end")
                entry.insert(0, value)

    def fill_input_all(self, value):
        self.fill_table(self.input_table, value)

    def fill_output_all(self, value):
        self.fill_table(self.output_table, value)

    def initialize_tables(self):
        # Clear existing table entries
        for row in self.input_table:
            for entry in row:
                entry.destroy()
        for row in self.output_table:
            for entry in row:
                entry.destroy()
        self.input_table.clear()
        self.output_table.clear()

        # Create new table entries based on self.rows
        for row_index in range(self.rows):
            input_row_entries = []
            output_row_entries = []
            for col_index in range(self.MAX_COLUMNS):
                input_entry = ctk.CTkEntry(self.input_table_frame, width=30, height=25)
                input_entry.grid(row=row_index, column=col_index)
                input_row_entries.append(input_entry)

                output_entry = ctk.CTkEntry(self.output_table_frame, width=30, height=25)
                output_entry.grid(row=row_index, column=col_index)
                output_row_entries.append(output_entry)

            self.input_table.append(input_row_entries)
            self.output_table.append(output_row_entries)

    def encrypt_and_save_lab(self):
        # Ensure input and output tables have the same number of rows
        if len(self.input_table) != len(self.output_table):
            messagebox.showerror("Error", "Input and output tables size mismatch.")
            return

        # Combine input and output data into the expected format
        combined_data = []
        for input_row, output_row in zip(self.input_table, self.output_table):
            input_data_str = ','.join([entry.get() for entry in input_row])
            output_data_str = ','.join([entry.get() for entry in output_row])
            combined_row = f"{input_data_str}|{output_data_str}"
            combined_data.append(combined_row)
        csv_data = "\r\n".join(combined_data)

        # Encrypt the combined CSV data
        cipher = ChaCha20.new(key=self.key)
        nonce = cipher.nonce
        encrypted_data = cipher.encrypt(csv_data.encode('utf-8'))

        # Save the encrypted data and nonce to a file
        lab_name = simpledialog.askstring("Lab Name", "Enter the name for the new lab:", parent=self)
        if lab_name:
            with open(f"{lab_name}_encrypted.ILC", 'wb') as file:  # Note 'wb' mode for binary write
                file.write(b64encode(nonce) + b"\r\n")
                file.write(b64encode(encrypted_data))
            messagebox.showinfo("Success", f"Lab '{lab_name}' has been encrypted and saved.")
########################################################################################################################################################

if __name__ == "__main__":
    app = ILCApplication()
    app.mainloop()