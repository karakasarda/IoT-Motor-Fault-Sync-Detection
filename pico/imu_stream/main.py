from math import sqrt
from machine import I2C, Pin
from time import sleep_ms, ticks_diff, ticks_ms

from mpu6050 import MPU6050


I2C_ID = 0
SDA_PIN = 20
SCL_PIN = 21
I2C_FREQ = 400_000
SAMPLE_DELAY_MS = 20
DEVICE_RETRY_MS = 1000
SUPPORTED_WHO_AM_I = {0x68, 0x72}
STREAM_LABEL = "live"
PULSE_PIN_NO = 22
PULSE_RATE_WINDOW_MS = 250
STREAM_HEADERS = (
    "time_ms,ax,ay,az,gx,gy,gz,acc_mag,gyro_mag,"
    "pulse_count,edge_count,rise_count,fall_count,state,pulse_rate_hz,last_edge_dt_ms,label"
)


def build_i2c():
    return I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=I2C_FREQ)


def wait_for_sensor(i2c):
    while True:
        try:
            devices = i2c.scan()
        except OSError as exc:
            print("# I2C tarama hatasi:", exc, "- tekrar deneniyor.")
            sleep_ms(DEVICE_RETRY_MS)
            continue

        if devices:
            print("# I2C cihazlari:", [hex(device) for device in devices])
            sensor_address = 0x68 if 0x68 in devices else devices[0]
            sensor = MPU6050(i2c, address=sensor_address)
            try:
                who_am_i = sensor.who_am_i()
            except OSError as exc:
                print("# WHO_AM_I okunamadi:", exc, "- tekrar denenecek.")
                sleep_ms(DEVICE_RETRY_MS)
                continue

            print("# MPU6050 adresi:", hex(sensor_address))
            print("# WHO_AM_I:", hex(who_am_i))

            if who_am_i not in SUPPORTED_WHO_AM_I:
                print(
                    "# Beklenmeyen WHO_AM_I degeri:",
                    hex(who_am_i),
                    "- tekrar denenecek.",
                )
                sleep_ms(DEVICE_RETRY_MS)
                continue

            if who_am_i != 0x68:
                print("# Uyari: Sensor 0x72 kimligi dondu. Modul MPU6050 uyumlu calisiyor.")

            return sensor

        print("# I2C cihaz bulunamadi. Kablolari kontrol et. Tekrar deneniyor...")
        sleep_ms(DEVICE_RETRY_MS)


class PulseCounter:
    def __init__(self, pin_no):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self.start_ms = ticks_ms()
        self.edge_count = 0
        self.rise_count = 0
        self.fall_count = 0
        self.last_edge_ms = None
        self.last_edge_dt_ms = -1
        self.rate_window_fall_start = 0
        self.rate_window_start_ms = 0
        self.pulse_rate_hz = 0.0
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.on_edge)

    def on_edge(self, pin):
        now = ticks_diff(ticks_ms(), self.start_ms)
        self.edge_count += 1
        if pin.value():
            self.rise_count += 1
        else:
            self.fall_count += 1
        if self.last_edge_ms is None:
            self.last_edge_dt_ms = -1
        else:
            self.last_edge_dt_ms = now - self.last_edge_ms
        self.last_edge_ms = now

    def snapshot(self, now_ms):
        elapsed = now_ms - self.rate_window_start_ms
        if elapsed >= PULSE_RATE_WINDOW_MS:
            window_falls = self.fall_count - self.rate_window_fall_start
            self.pulse_rate_hz = (window_falls * 1000) / elapsed if elapsed else 0.0
            self.rate_window_fall_start = self.fall_count
            self.rate_window_start_ms = now_ms

        return {
            "pulse_count": self.fall_count,
            "edge_count": self.edge_count,
            "rise_count": self.rise_count,
            "fall_count": self.fall_count,
            "state": self.pin.value(),
            "pulse_rate_hz": self.pulse_rate_hz,
            "last_edge_dt_ms": self.last_edge_dt_ms,
        }


def main():
    i2c = build_i2c()
    sensor = wait_for_sensor(i2c)
    pulse_counter = PulseCounter(PULSE_PIN_NO)

    print("# Feature stream basladi.")
    print("# sample_delay_ms=", SAMPLE_DELAY_MS)
    print("# pulse_pin=", PULSE_PIN_NO)
    print("# pulse_rate_window_ms=", PULSE_RATE_WINDOW_MS)
    print(STREAM_HEADERS)
    start_ms = ticks_ms()

    while True:
        try:
            reading = sensor.read()
        except OSError as exc:
            print("# Veri okuma hatasi:", exc, "- sensor yeniden baglaniyor.")
            sleep_ms(DEVICE_RETRY_MS)
            i2c = build_i2c()
            sensor = wait_for_sensor(i2c)
            continue

        accel = reading["accel_g"]
        gyro = reading["gyro_dps"]
        time_ms = ticks_diff(ticks_ms(), start_ms)
        pulse = pulse_counter.snapshot(time_ms)
        acc_mag = sqrt(
            accel[0] * accel[0] + accel[1] * accel[1] + accel[2] * accel[2]
        )
        gyro_mag = sqrt(
            gyro[0] * gyro[0] + gyro[1] * gyro[1] + gyro[2] * gyro[2]
        )

        print(
            "{},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{},{},{},{},{},{:.3f},{},{}".format(
                time_ms,
                accel[0],
                accel[1],
                accel[2],
                gyro[0],
                gyro[1],
                gyro[2],
                acc_mag,
                gyro_mag,
                pulse["pulse_count"],
                pulse["edge_count"],
                pulse["rise_count"],
                pulse["fall_count"],
                pulse["state"],
                pulse["pulse_rate_hz"],
                pulse["last_edge_dt_ms"],
                STREAM_LABEL,
            )
        )
        sleep_ms(SAMPLE_DELAY_MS)


main()
