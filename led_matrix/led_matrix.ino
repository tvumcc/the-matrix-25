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

struct Frame {
  short time_ms; 
  uint8_t bits[5];
};

struct Animation {
  uint8_t num_loops = 1;
  uint8_t num_frames;
  Frame frames[13];
};

Animation spiral;
Animation spin;
Animation ripple;

void setup_animations() {
  setup_spiral_animation(&spiral);
  setup_spin_animation(&spin);
  setup_ripple_animation(&ripple);
}

void setup_spiral_animation(Animation* animation) {
  int speed = 100;
  animation->num_frames = 13;
  animation->num_loops = 1;

  animation->frames[0] = {speed, {0b11000,0b00000,0b00000,0b00000,0b00000}};
  animation->frames[1] = {speed, {0b11110,0b00000,0b00000,0b00000,0b00000}};
  animation->frames[2] = {speed, {0b11111,0b00001,0b00000,0b00000,0b00000}};
  animation->frames[3] = {speed, {0b11111,0b00001,0b00001,0b00001,0b00000}};
  animation->frames[4] = {speed, {0b11111,0b00001,0b00001,0b00001,0b00011}};
  animation->frames[5] = {speed, {0b11111,0b00001,0b00001,0b00001,0b01111}};
  animation->frames[6] = {speed, {0b11111,0b00001,0b00001,0b10001,0b11111}};
  animation->frames[7] = {speed, {0b11111,0b10001,0b10001,0b10001,0b11111}};
  animation->frames[8] = {speed, {0b11111,0b11101,0b10001,0b10001,0b11111}};
  animation->frames[9] = {speed, {0b11111,0b11111,0b10011,0b10001,0b11111}};
  animation->frames[10] = {speed, {0b11111,0b11111,0b10011,0b10111,0b11111}};
  animation->frames[11] = {speed, {0b11111,0b11111,0b11011,0b11111,0b11111}};
  animation->frames[12] = {1500, {0b11111,0b11111,0b11111,0b11111,0b11111}};
}

void setup_spin_animation(Animation* animation) {
  int speed = 150;
  animation->num_frames = 4;
  animation->num_loops = 10;

  animation->frames[0] = {speed, {0b00100, 0b00100, 0b11111, 0b00100, 0b00100}};
  animation->frames[1] = {speed, {0b00010, 0b11010, 0b00100, 0b01011, 0b01000}};
  animation->frames[2] = {speed, {0b10001, 0b01010, 0b00100, 0b01010, 0b10001}};
  animation->frames[3] = {speed, {0b01000, 0b01011, 0b00100, 0b11010, 0b00010}};
}

void setup_ripple_animation(Animation* animation) {
  int speed = 150;
  animation->num_frames = 6;
  animation->num_loops = 10;

  animation->frames[0] = {speed, {0b00000,0b00000,0b00000,0b00000,0b00000}};
  animation->frames[1] = {speed, {0b00000,0b00000,0b00100,0b00000,0b00000}};
  animation->frames[2] = {speed, {0b00000,0b00100,0b01010,0b00100,0b00000}};
  animation->frames[3] = {speed, {0b00100,0b01010,0b10001,0b01010,0b00100}};
  animation->frames[4] = {speed, {0b01010,0b10001,0b00000,0b10001,0b01010}};
  animation->frames[5] = {speed, {0b10001,0b00000,0b00000,0b00000,0b10001}};
}

void setup() {
  for (int i = 0; i < 5; i++) {
    pinMode(col_pins[i], OUTPUT);
    digitalWrite(col_pins[i], HIGH);
  }

  for (int i = 0; i < 5; i++) {
    pinMode(row_pins[i], OUTPUT);
    digitalWrite(row_pins[i], LOW);
  }

  setup_animations();
}

Animation* animations[3] = {
  &spiral,
  &spin,
  &ripple,
};

int multiplexer_delay = 2;
int current_frame = 0;
int current_loop = 0;
int current_animation = 0;
int num_animations = 3;
long long frame_start = millis();

void loop() {
  for (int i = 0; i < 5; i++) {
    for (int j = 0; j < 5; j++)
      digitalWrite(row_pins[j], LOW);
    for (int j = 0; j < 5; j++)
      digitalWrite(row_pins[j], ((animations[current_animation]->frames[current_frame].bits[j] & (1 << (4 - i))) != 0) ? HIGH : LOW);
    digitalWrite(col_pins[i], LOW);

    delay(multiplexer_delay);
    digitalWrite(col_pins[i], HIGH);
  }

  if (millis() - frame_start >= spiral.frames[current_frame].time_ms) {
    current_frame = (current_frame + 1) % animations[current_animation]->num_frames; 
    if (current_frame == 0) {
      current_loop++;
      if (current_loop > animations[current_animation]->num_loops) {
        current_animation = (current_animation + 1) % num_animations;
        current_loop = 0;
      }
    }
    frame_start = millis();
  }
}
