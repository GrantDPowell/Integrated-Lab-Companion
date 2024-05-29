

const int numPins = 14;             // Number of digital pins inputs x 2
int currentPinStateArray[numPins];  // array for state values of pins

int lastPinStateArray[numPins / 2];
char serialDataBuffer[8];  // used as a buffer array

const unsigned long commandTimeout = 3000;  // Timeout period in milliseconds
unsigned long lastCommandTime = 0;

const int switchPinArray[numPins / 2] = { 2, 3, 4, 5, 6, 7, 8 };         // New Pin Numbers
const int outputPinArray[numPins / 2] = { A0, A1, A2, A3, A4, A5, A6 };  // New Pin Numbers
const int SwitchPowerPin = 10;                                           // new pin number
const int ClkPin = 9;

unsigned long startTime = 0.0;  // used for the timing logs and such
unsigned long endTime = 0.0;

float newClockSpeed = 0.0;
bool isClockOn = false;

void setup() {

  Serial.begin(9600);  // Initialize Serial communication

  ResetSerialDataBuffer();  // Set Buffer To Null Initially
  SetAllPinsToInput();      // default to all pins as input

  pinMode(ClkPin, OUTPUT);
  setClk(2);

  resetStateArray();
  InitializeLastPinStateArray();

}

void loop() {
  delay(100);
  ReadSerialData();
  ProcessSerialData();
  if (isClockOn)
    CheckForInputChanges();  // Check for input changes and send state log if changed
}

void RequestStateLog() {

  // Read and store each state of pin into statArray(is Printed later)
  for (int i = 0; i < numPins / 2; i++) {
    currentPinStateArray[i] = digitalRead(switchPinArray[i]);
    if (i != 6) {
      currentPinStateArray[i + 7] = digitalRead(outputPinArray[i]);
    } else {
      const int k = analogRead(outputPinArray[i]);
      int m = 0;
      if (k > 300) {
        m = 1;
      }
      currentPinStateArray[i + 7] = m;
    }
  }

  // Print the pin states to the Serial Monitor
  // Serial.println("    Inputs    |   Outputs   ");
  for (int i = 0; i < numPins / 2; i++) {
    Serial.print(currentPinStateArray[i]);
    // Serial.print(" ");
  }
  Serial.print("|");
  for (int i = 0; i < numPins / 2; i++) {
    Serial.print(currentPinStateArray[i + 7]);
    // Serial.print(" ");
  }
  // endTime = micros();
  Serial.println();
  // Serial.print("Finished With Operation took: ");
  // Serial.print( abs(endTime - startTime));
  // Serial.println("μs");
  // Serial.println();

  // Reset Buffer To Null, logging is called at the end of any operation

  ResetSerialDataBuffer();
  resetStateArray();
}

void SetSwitchPinsToInput() {  // Sets switch pins to INPUT

  for (int i = 0; i < numPins / 2; i++) {
    digitalWrite(switchPinArray[i], LOW);
    pinMode(switchPinArray[i], INPUT);
  }
  // delay(500);
  digitalWrite(SwitchPowerPin, HIGH);  // turns back on manual mode
}

void SetSwitchPinsToOutput() {  // Set switch pins to OUTPUT

  digitalWrite(SwitchPowerPin, LOW);  // turns off manual mode
  // delay(500);
  for (int i = 0; i < numPins / 2; i++) {
    pinMode(switchPinArray[i], OUTPUT);
  }
}

void resetStateArray() {
  for (int i = 0; i < numPins / 2; i++) {
    currentPinStateArray[i] = 0;
    currentPinStateArray[i + 7] = 0;
  }
}

void SetAllPinsToInput() {
  for (int i = 0; i < numPins / 2; i++) {  // Set All Inputs & Outputs pins to INPUT or READ mode
    pinMode(switchPinArray[i], INPUT);
    pinMode(outputPinArray[i], INPUT);
  }

  pinMode(SwitchPowerPin, OUTPUT);  // Turn on Power to switches
  digitalWrite(SwitchPowerPin, HIGH);
}

void InitializeLastPinStateArray() {
  for (int i = 0; i < numPins / 2; i++) {
    lastPinStateArray[i] = digitalRead(switchPinArray[i]);
  }
}

void CheckForInputChanges() {
  bool stateChanged = false;
  for (int i = 0; i < numPins / 2; i++) {
    int currentState = digitalRead(switchPinArray[i]);
    if (currentState != lastPinStateArray[i]) {
      stateChanged = true;
      lastPinStateArray[i] = currentState;
    }
  }
  if (stateChanged) {
    RequestStateLog();
  }
}


void ResetSerialDataBuffer() {

  memset(serialDataBuffer, '\0', sizeof(serialDataBuffer));  // Set Buffer To Null
}



bool isValidData(const char *data) {
  // Example validation: check data length and content
  for (int i = 0; i < 7; i++) {
    if (data[i] != '0' && data[i] != '1') {
      return false;  // Invalid data
    }
  }
  return true;  // Valid data
}


void ReadSerialData() {
  // Clear the buffer first
  memset(serialDataBuffer, '\0', sizeof(serialDataBuffer));

  // Then read new data into the buffer
  if (Serial.available() > 0) {
    Serial.readBytes(serialDataBuffer, sizeof(serialDataBuffer) - 1);
  }
}

void ProcessSerialData() {

    if ((serialDataBuffer[0] == '1' || serialDataBuffer[0] == '0') && (serialDataBuffer[1] != '1' && serialDataBuffer[1] != '0')) {
        // startTime = micros();
        RequestStateLog();
    }

    // If data is present at 7th value IE last value then control mode initializes with the said value IE inputted data
    if (serialDataBuffer[6] == '1' || serialDataBuffer[6] == '0') {
        // startTime = micros();
        ControlMode(serialDataBuffer);
        ResetSerialDataBuffer();
    }

    if (serialDataBuffer[0] == '#') {
        if (isClockOn == true) {
            offClk();
            ResetSerialDataBuffer();
        } else if (isClockOn == false) {
            setClk(2);
            ResetSerialDataBuffer();
        }
    }

    if (serialDataBuffer[0] == '?') {
        Serial.println("1V8");
    }

    if (serialDataBuffer[0] == 'x' && serialDataBuffer[1] == '0') {
        cycleAndState0();
        ResetSerialDataBuffer();
    }

    if (serialDataBuffer[0] == 'x' && serialDataBuffer[1] == '1') {
        cycleAndState1();
        ResetSerialDataBuffer();
    }

    if (serialDataBuffer[0] == 'f') {
        String stringOne = String(serialDataBuffer);
        int len = stringOne.length();
        if (len == 3 || len == 4) {
            float newFreq = stringOne.substring(1, len - 1).toFloat();
            if (newFreq >= 0 && newFreq <= 30) {
                setClk(newFreq);
            }
        }
    }
}


void setClk(float freq) {
  TCCR1A = 0x41;                // Change to use COM1A1:0 bits for OCR1A (pin 9)
  TCCR1B = 0x14;                // Same as before, as we are still using Timer 1
  OCR1A = 0x7A12 / (freq * 2);  // Set frequency for pin 9
  OCR1B = OCR1A * 0.5;          // This line now affects pin 10 instead of pin 9
  isClockOn = true;
}

void offClk() {

  TCCR1A = 0x00;   // Reset TCCR1A to default
  TCCR1B = 0x00;   // Reset TCCR1B to default
  OCR1A = 0x0000;  // Reset OCR1A to default
  OCR1B = 0x0000;  // Reset OCR1B to default
  delay(10);
  digitalWrite(ClkPin, LOW);
  isClockOn = false;
}

void toggleClk() {
  if (isClockOn == false) {
    delay(5);
    digitalWrite(ClkPin, HIGH);
    delay(5);
    digitalWrite(ClkPin, LOW);
  }
}

void cycleAndState0() {
  SetSwitchPinsToOutput();
  digitalWrite(switchPinArray[6], LOW);
  toggleClk();
  delay(500);
  RequestStateLog();
  digitalWrite(switchPinArray[6], HIGH);
  SetSwitchPinsToInput();
}

void cycleAndState1() {
  SetSwitchPinsToOutput();
  digitalWrite(switchPinArray[6], HIGH);       // sw 7
  toggleClk();
  delay(500);
  RequestStateLog();
  digitalWrite(switchPinArray[6], LOW);
  SetSwitchPinsToInput();
  
}

void ControlMode(const char data[]) {
  unsigned long entryTime = millis();  // Record the time when ControlMode was entered

  do {
    SetSwitchPinsToOutput();

    for (int i = 0; i < 7; ++i) {  // Sets Switches to 1 or 0
      if (data[i] == '1') {
        digitalWrite(switchPinArray[i], HIGH);
      } else if (data[i] == '0') {
        digitalWrite(switchPinArray[i], LOW);
      }
    }

    RequestStateLog();  // Log the current state

    // Minimal delay or perform other necessary operations here
    // Consider reducing or removing this delay to improve responsiveness
    delay(600);

    if (Serial.available() > 0) {
      // If new data is available, read it and reset the entryTime
      ReadSerialData();  // Make sure this function properly populates `serialDataBuffer`
      if (isValidData(serialDataBuffer)) {
        entryTime = millis();  // Reset entry time since we have a new command
      }
    } else {
      // If no new data, check if the timeout has elapsed
      if (millis() - entryTime >= commandTimeout) {
        
        break;  // Exit the loop if the timeout has elapsed
      }
    }
  } while (true);

  SetSwitchPinsToInput();  // Make sure to set back to input mode when exiting control mode
  RequestStateLog();
}


