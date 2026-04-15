/*
       |    |    |    |    |
       0    1    2    3    4
       |    |    |    |    |
       |    |    |    |    |
--0----O----O----O----O----O
       |    |    |    |    |
--1----O----O----O----O----O
       |    |    |    |    |
--2----O----O----O----O----O
       |    |    |    |    |
--3----O----O----O----O----O
       |    |    |    |    |
--4----O----O----O----O----O
*/
#include <EEPROM.h>

#define LED_COL_GND_0 3
#define LED_COL_GND_1 4
#define LED_COL_GND_2 5
#define LED_COL_GND_3 6
#define LED_COL_GND_4 7

#define LED_ROW_0 1
#define LED_ROW_1 2
#define LED_ROW_2 10
#define LED_ROW_3 9
#define LED_ROW_4 8

#define BUTTON 0

#define NUM_TOTAL_FRAMES 128

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

uint8_t basis[] = {0, 20, 100, 150, 0, 0, 0};
uint8_t start_indices[] = {0, 12, 25, 45, 53, 79, 99, NUM_TOTAL_FRAMES}; // 7 Animations, starting idx of 128 is added to the end for convenience when looping

uint8_t multiplexer_delay = 2;
uint8_t current_frame = 0;
uint8_t current_animation = 0;
uint8_t num_animations = 7;
long long frame_start = millis();

int button_state;
int last_button_state = LOW;
unsigned long last_debounce_time = 0;
unsigned long debounce_delay = 50;

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

uint32_t get_eeprom_frame(unsigned int frame_idx) {
  return ((uint32_t)EEPROM.read(frame_idx * 4 + 0) << 24) | 
         ((uint32_t)EEPROM.read(frame_idx * 4 + 1) << 16) | 
         ((uint32_t)EEPROM.read(frame_idx * 4 + 2) << 8)  | 
         ((uint32_t)EEPROM.read(frame_idx * 4 + 3));
}

void loop() {
  int button_reading = digitalRead(BUTTON);

  if (button_reading != last_button_state) {
    last_debounce_time = millis();
  }

  if ((millis() - last_debounce_time) > debounce_delay) {
    if (button_reading != button_state) {
      button_state = button_reading;
      if (button_state == HIGH) {
        current_animation = (current_animation + 1) % num_animations;
        current_frame = 0;
        frame_start = millis();
      }
    }
  }

  uint32_t frame_idx = start_indices[current_animation] + current_frame;
  uint32_t frame_data = get_eeprom_frame(frame_idx);
  uint32_t frame_delay = 0;
  for (int i = 0; i < 7; i++) {
    if (((frame_data >> 25) & (1 << (6 - i))) != 0) {
      frame_delay += basis[i];
    }
  }

  for (int i = 0; i < 5; i++) {
    for (int j = 0; j < 5; j++)
      digitalWrite(row_pins[j], LOW);
    for (int j = 0; j < 5; j++) {
      uint32_t frame_row = (frame_data >> (5 * (4 - j))) & 0x1F;
      digitalWrite(row_pins[j], ((frame_row & (1 << (4 - i))) != 0) ? HIGH : LOW);
    }
      
    digitalWrite(col_pins[i], LOW);

    delay(multiplexer_delay);
    digitalWrite(col_pins[i], HIGH);
  }

  if (millis() - frame_start >= frame_delay) {
    current_frame = (current_frame + 1) % (start_indices[current_animation + 1] - start_indices[current_animation]); 
    frame_start = millis();
  }

  last_button_state = button_reading;
}
