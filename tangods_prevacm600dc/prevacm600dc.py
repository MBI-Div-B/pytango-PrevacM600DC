import sys
import time
from typing import Any

from pymodbus.client import ModbusTcpClient
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property

DT = ModbusTcpClient.DATATYPE


class PrevacM600DC(Device):
    """
    This docstring should describe your Tango Class and optionally
    what it depends on (drivers etc).
    """

    # ------ Device Properties ------ #

    hostname: str = device_property(
        doc="Host name or IP address of device",
    )
    port: int = device_property(
        doc="ModbusTCP port to use",
        default_value=502,
    )

    # ------ Attributes ------ #

    plasma_on: bool = attribute(access=AttrWriteType.READ)
    plasma_failure: bool = attribute(access=AttrWriteType.READ)

    power: float = attribute(
        access=AttrWriteType.READ,
        doc="Magnetron power",
        unit="W",
    )
    power_setpoint: float = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Magnetron power setpoint",
        unit="W",
    )
    power_ramp: int = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Power ramp value (1 .. 1000 W/s)",
        min_value=1,
        max_value=1000,
        unit="W/s",
    )

    voltage: float = attribute(
        access=AttrWriteType.READ,
        doc="Magnetron voltage",
        unit="V",
    )
    voltage_setpoint: float = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Magnetron voltage setpoint",
        unit="V",
    )
    voltage_ramp: int = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Voltage ramp value (1 .. 1000 V/s)",
        min_value=1,
        max_value=1000,
        unit="V/s",
    )

    current: float = attribute(
        access=AttrWriteType.READ,
        doc="Magnetron current",
        unit="A",
    )
    current_setpoint: float = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Magnetron current setpoint",
        unit="A",
    )
    current_ramp: int = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Current ramp value (1 .. 1000 mA/s)",
        min_value=1,
        max_value=1000,
        unit="mA/s",
    )

    output_active: int = attribute(
        access=AttrWriteType.READ,
        doc="Number of active HV output [1, 2, 3]",
    )

    output_power_limits: [int] = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Power limits of outputs 1-3. 1...600 W",
        unit="W",
    )
    output_voltage_limits: [int] = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Voltage limits of outputs 1-3. 50...1200 V",
        unit="V",
    )
    output_current_limits: [int] = attribute(
        access=AttrWriteType.READ_WRITE,
        doc="Current limits of outputs 1-3. 1...1200 mA",
        unit="mA",
    )

    def init_device(self):
        Device.init_device(self)

        self.client = ModbusTcpClient(self.hostname, port=self.port)
        if self.client.connect():
            self.info_stream("Connection established")
        else:
            self.error_stream(
                f"Could not establish connection to {self.host}:{self.port}"
            )
            sys.exit(1)

        self._last_status_query = 0
        self._status_refresh_interval = 0.5

    def delete_device(self):
        self.set_state(DevState.OFF)
        self.info_stream("Closing connection")
        self.client.close()

    def read_register(self, address: int, count: int, dtype: DT) -> Any:
        """Read register data and convert to python type.

        Read <count> bytes of raw data starting from register <address>
        and convert to given data type.

        address: int
        count: int
        dtype: pymodbus DATATYPE enum
        """
        ret = self.client.read_holding_registers(address, count=count)
        return self.client.convert_from_registers(ret.registers, dtype)

    def write_register(self, address: int, value: Any, dtype: DT) -> None:
        """Write register data.

        Writes the given data to (multi-count) register after converting to target type.
        """
        self.client.write_registers(
            address,
            self.client.convert_to_registers(value, dtype),
        )

    def always_executed_hook(self):
        """Check device state and update state and status."""
        now = time.monotonic()
        if now - self._last_status_query > self._status_refresh_interval:
            status = "Unknown"
            state = DevState.UNKNOWN
            
            devstate = self.read_register(0, 1, DT.INT16)
            if devstate:
                status.append("OPERATE")
                state = DevState.MOVING
            else:
                status = "STANDBY"
                state = DevState.ON

            self.set_state(state)
            self.set_status(status)
            self._last_status_query = now

    # ------ Attribute R/W ------ #
    def read_plasma_on(self) -> bool:
        bits = self.read_register(2, 2, DT.BITS)
        return bits[0]

    def read_plasma_failure(self) -> bool:
        bits = self.read_register(2, 2, DT.BITS)
        return bits[1]

    def read_output_active(self) -> bool:
        self.read_register(90, 1, DT.UINT16)

    def read_power(self) -> float:
        return self.read_register(4, 2, DT.FLOAT32)

    def read_power_setpoint(self) -> float:
        return self.read_register(19, 2, DT.FLOAT32)

    def write_power_setpoint(self, value: float) -> None:
        self.write_register(19, value, DT.FLOAT32)

    def read_power_ramp(self) -> int:
        return self.read_register(45, 1, DT.INT16)

    def write_power_ramp(self, value: int) -> None:
        self.write_register(45, value, DT.INT16)

    def read_voltage(self) -> float:
        return self.read_register(6, 2, DT.FLOAT32)

    def read_voltage_setpoint(self) -> float:
        return self.read_register(21, 2, DT.FLOAT32)

    def write_voltage_setpoint(self, value: float) -> None:
        self.write_register(21, value, DT.FLOAT32)

    def read_voltage_ramp(self) -> int:
        return self.read_register(46, 1, DT.INT16)

    def write_voltage_ramp(self, value: int) -> None:
        self.write_register(46, value, DT.INT16)

    def read_current(self) -> float:
        return self.read_register(8, 2, DT.FLOAT32)

    def read_current_setpoint(self) -> float:
        return self.read_register(23, 2, DT.FLOAT32)

    def write_current_setpoint(self, value: float) -> None:
        return self.write_register(23, value, DT.FLOAT32)

    def read_current_ramp(self) -> int:
        return self.read_register(47, 1, DT.INT16)

    def write_current_ramp(self, value: int) -> None:
        self.write_register(47, value, DT.INT16)

    def read_output_power_limits(self) -> [int]:
        return self.read_register(36, 3, DT.INT16)

    def write_output_power_limits(self, values: [int]) -> None:
        self._write_output_limits(36, values, 1, 600)

    def read_output_voltage_limits(self) -> [int]:
        return self.read_register(39, 3, DT.INT16)

    def write_output_voltage_limits(self, values: [int]) -> None:
        self._write_output_limits(39, values, 50, 1200)

    def read_output_current_limits(self) -> [int]:
        return self.read_register(42, 3, DT.INT16)

    def write_output_current_limits(self, values: [int]) -> None:
        self._write_output_limits(42, values, 1, 1000)

    def _write_output_limits(self, register, values, vmin, vmax):
        """Helper to set current/ voltage/ power limits on all 3 outputs."""
        if len(values) != 3:
            raise ValueError("Exactly 3 values are required")
        for value in values:
            if not (vmin <= value <= vmax):
                raise ValueError(f"All power limits must be in range {vmin}..{vmax}")
        self.write_register(register, values, DT.INT16)

    @command
    def set_active_output(self, output: int) -> None:
        self.write_register(89, output, DT.UINT16)

    @command
    def output_on(self) -> None:
        self.write_register(17, 1, DT.UINT16)

    @command
    def output_off(self) -> None:
        self.write_register(18, 1, DT.UINT16)

