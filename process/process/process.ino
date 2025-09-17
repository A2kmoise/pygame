const int joyYPin = A1;
const int buttonPin = 2;


void setup() {
Serial.begin(9600);
pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  int joyY = analogRead(joyYPin);
  int buttonState = digitalRead(buttonPin);

int speedModifier = map(joyY, 0, 1023, 5, 1);


Serial.print(joyY);
Serial.print(",");
Serial.print(buttonState);
Serial.print(",");
Serial.print(speedModifier);
Serial.println();

delay(50);

}
