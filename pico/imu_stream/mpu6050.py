class MPU6050:
    PWR_MGMT_1 = 0x6B
    WHO_AM_I = 0x75
    ACCEL_CONFIG = 0x1C
    GYRO_CONFIG = 0x1B
    ACCEL_XOUT_H = 0x3B
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43

    ACCEL_SCALE = {
        2: (0x00, 16384.0),
        4: (0x08, 8192.0),
        8: (0x10, 4096.0),
        16: (0x18, 2048.0),
    }

    GYRO_SCALE = {
        250: (0x00, 131.0),
        500: (0x08, 65.5),
        1000: (0x10, 32.8),
        2000: (0x18, 16.4),
    }

    def __init__(self, i2c, address=0x68, accel_range=2, gyro_range=250):
        self.i2c = i2c
        self.address = address
        self._accel_divider = None
        self._gyro_divider = None

        self._write_register(self.PWR_MGMT_1, 0x00)
        self.set_accel_range(accel_range)
        self.set_gyro_range(gyro_range)

    def who_am_i(self):
        return self._read_register(self.WHO_AM_I)

    def set_accel_range(self, accel_range):
        if accel_range not in self.ACCEL_SCALE:
            raise ValueError("Gecersiz ivme araligi: {}".format(accel_range))

        register_value, divider = self.ACCEL_SCALE[accel_range]
        self._write_register(self.ACCEL_CONFIG, register_value)
        self._accel_divider = divider

    def set_gyro_range(self, gyro_range):
        if gyro_range not in self.GYRO_SCALE:
            raise ValueError("Gecersiz gyro araligi: {}".format(gyro_range))

        register_value, divider = self.GYRO_SCALE[gyro_range]
        self._write_register(self.GYRO_CONFIG, register_value)
        self._gyro_divider = divider

    def read(self):
        accel_raw = self._read_vector(self.ACCEL_XOUT_H)
        temp_raw = self._read_signed_16(self.TEMP_OUT_H)
        gyro_raw = self._read_vector(self.GYRO_XOUT_H)

        return {
            "accel_raw": accel_raw,
            "gyro_raw": gyro_raw,
            "temp_raw": temp_raw,
            "accel_g": tuple(value / self._accel_divider for value in accel_raw),
            "gyro_dps": tuple(value / self._gyro_divider for value in gyro_raw),
            "temp_c": (temp_raw / 340.0) + 36.53,
        }

    def _read_vector(self, register):
        data = self.i2c.readfrom_mem(self.address, register, 6)
        return (
            self._combine_bytes(data[0], data[1]),
            self._combine_bytes(data[2], data[3]),
            self._combine_bytes(data[4], data[5]),
        )

    def _read_signed_16(self, register):
        data = self.i2c.readfrom_mem(self.address, register, 2)
        return self._combine_bytes(data[0], data[1])

    def _read_register(self, register):
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def _write_register(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value]))

    @staticmethod
    def _combine_bytes(high_byte, low_byte):
        value = (high_byte << 8) | low_byte
        if value & 0x8000:
            value -= 65536
        return value
