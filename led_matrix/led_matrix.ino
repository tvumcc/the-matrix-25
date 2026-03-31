#define LED_COL_GND_0 0
#define LED_COL_GND_1 1
#define LED_COL_GND_2 2
#define LED_COL_GND_3 3
#define LED_COL_GND_4 4

#define LED_ROW_0 5
#define LED_ROW_1 6
#define LED_ROW_2 7
#define LED_ROW_3 8
#define LED_ROW_4 9

#define BUTTON 10

int col_pins[5] = {
  LED_COL_GND_0,
  LED_COL_GND_1,
  LED_COL_GND_2,
  LED_COL_GND_3,
  LED_COL_GND_4
};

int row_pins[5] = {
  LED_ROW_0,
  LED_ROW_1,
  LED_ROW_2,
  LED_ROW_3,
  LED_ROW_4
};

void setup() {
  for (int i = 0; i < 5; i++) {
    pinMode(col_pins[i], OUTPUT);
    digitalWrite(col_pins[i], HIGH);
  }

  for (int i = 0; i < 5; i++) {
    pinMode(row_pins[i], OUTPUT);
    digitalWrite(row_pins[i], LOW);
  }

  pinMode(BUTTON, INPUT);
}

unsigned char frame[5] = {
  0b01010,
  0b11111,
  0b11111,
  0b01110,
  0b00100
};

int multiplexer_delay = 32;
int button_state;
int last_button_state = LOW;
unsigned long last_debounce_time = 0;
unsigned long debounce_delay = 50;

void loop() {
  int button_reading = digitalRead(BUTTON);

  if (button_reading != last_button_state) {
    last_debounce_time = millis();
  }

  if ((millis() - last_debounce_time) > debounce_delay) {
    if (button_reading != button_state) {
      button_state = button_reading;
      if (button_state == HIGH) {
        multiplexer_delay /= 2;
        if (multiplexer_delay <= 0) {
          multiplexer_delay = 32;
        }
      }
    }
  }

  for (int i = 0; i < 5; i++) {
    for (int j = 0; j < 5; j++)
      digitalWrite(row_pins[j], LOW);
    for (int j = 0; j < 5; j++)
      digitalWrite(row_pins[j], ((frame[j] & (1 << (4 - i))) != 0) ? HIGH : LOW);
    digitalWrite(col_pins[i], LOW);

    delay(multiplexer_delay);
    digitalWrite(col_pins[i], HIGH);
  }

  last_button_state = button_reading;
}
