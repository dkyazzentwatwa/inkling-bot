"""
BLE GATT transport for Inkling command input.

Uses BlueZ via bluezero to expose a Nordic UART-style service.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from core.mode_bridge import InklingModeBridge

try:
    from bluezero import peripheral, adapter
except Exception:  # pragma: no cover - optional dependency
    peripheral = None
    adapter = None


UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class BleTransport:
    """BLE transport that routes RX writes into InklingModeBridge."""

    def __init__(
        self,
        bridge: InklingModeBridge,
        device_name: str,
        adapter_addr: Optional[str] = None,
        max_chunk_bytes: int = 180,
    ) -> None:
        self._bridge = bridge
        self._device_name = device_name
        self._adapter_addr = adapter_addr
        self._max_chunk_bytes = max_chunk_bytes

        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._ready = threading.Event()  # Signals BLE is fully initialized
        self._init_error: Optional[Exception] = None  # Stores initialization errors
        self._rx_buffer = bytearray()

        self._ble = None
        self._tx_char = None  # Will be set by notify callback when client subscribes
        self._service_id = 1
        self._rx_char_id = 1
        self._tx_char_id = 2

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if peripheral is None:
            raise RuntimeError(
                "bluezero is not installed. Install with: pip install bluezero (requires bluez system package)"
            )
        if not self._adapter_addr:
            self._adapter_addr = self._get_default_adapter_addr()
        if not self._adapter_addr:
            raise RuntimeError("No Bluetooth adapter found")
        self._running.set()
        self._thread = threading.Thread(target=self._run, name="ble-transport", daemon=True)
        self._thread.start()

        # Wait for BLE to be fully initialized (with timeout)
        if not self._ready.wait(timeout=5.0):
            error_msg = "BLE initialization timed out"
            if self._init_error:
                error_msg += f": {self._init_error}"
            raise RuntimeError(error_msg)

        # Check if initialization failed with an error
        if self._init_error:
            raise RuntimeError(f"BLE initialization failed: {self._init_error}")

        print("[BLE] Initialization complete")

    def stop(self) -> None:
        self._running.clear()
        if self._ble is None:
            return
        for method_name in ("stop", "quit", "unpublish"):
            method = getattr(self._ble, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

    def _run(self) -> None:
        adapter_addr = self._adapter_addr
        if not adapter_addr:
            self._init_error = RuntimeError("No adapter address")
            self._ready.set()
            return

        try:
            print("[BLE] Creating peripheral...")
            self._ble = peripheral.Peripheral(adapter_addr, local_name=self._device_name)

            print("[BLE] Adding service...")
            self._ble.add_service(srv_id=self._service_id, uuid=UART_SERVICE_UUID, primary=True)

            print("[BLE] Adding RX characteristic...")
            self._ble.add_characteristic(
                srv_id=self._service_id,
                chr_id=self._rx_char_id,
                uuid=UART_RX_UUID,
                value=[],
                notifying=False,
                flags=["write", "write-without-response"],
                write_callback=self._on_rx_write,
            )

            print("[BLE] Adding TX characteristic...")
            # add_characteristic() returns None, but notify_callback captures the object
            self._ble.add_characteristic(
                srv_id=self._service_id,
                chr_id=self._tx_char_id,
                uuid=UART_TX_UUID,
                value=[],
                notifying=True,
                flags=["notify"],
                notify_callback=self._on_tx_notify_enabled,  # This captures the characteristic
            )
            print("[BLE] TX characteristic added (waiting for client to enable notifications)")

            # Signal ready BEFORE publish() since all characteristics are created
            # publish() will block and enter the mainloop
            print("[BLE] Service ready, publishing...")
            self._ready.set()

            # This call blocks and runs the GLib mainloop
            self._ble.publish()

        except Exception as e:
            print(f"[BLE] ERROR during initialization: {e}")
            import traceback
            traceback.print_exc()
            self._init_error = e
            # Signal ready even on error so start() doesn't hang forever
            self._ready.set()

    def _on_tx_notify_enabled(self, notifying, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Called when client enables/disables notifications on TX characteristic."""
        if notifying:
            # Capture the characteristic object (passed as first positional arg)
            self._tx_char = args[0] if args else None
            print(f"[BLE] Client enabled notifications, TX char captured: {self._tx_char!r}")
        else:
            print("[BLE] Client disabled notifications")
            self._tx_char = None

    def _on_rx_write(self, value, options=None, *args, **kwargs) -> None:  # type: ignore[override]
        # Guard against writes before initialization completes
        if not self._ready.is_set():
            print("[BLE] WARNING: Received write before initialization complete, ignoring")
            return

        try:
            data = bytes(value)
            print(f"[BLE] RX received {len(data)} bytes: {data!r}")
        except Exception as e:
            print(f"[BLE] ERROR: Failed to convert RX data: {e}")
            return

        self._rx_buffer.extend(data)
        while b"\n" in self._rx_buffer:
            line, _, rest = self._rx_buffer.partition(b"\n")
            self._rx_buffer = bytearray(rest)
            try:
                text = line.decode("utf-8", errors="replace")
                print(f"[BLE] Processing command: {text!r}")
            except Exception as e:
                print(f"[BLE] ERROR: Failed to decode: {e}")
                text = ""

            try:
                response = self._bridge.handle_line(text)
                print(f"[BLE] Bridge returned {len(response)} bytes: {response[:100]!r}")
                self._send_response(response)
            except Exception as e:
                print(f"[BLE] ERROR: Bridge failed: {e}")
                import traceback
                traceback.print_exc()
                error_response = f"ERR 1\nInternal error: {e}\n<END>\n"
                self._send_response(error_response)

    def _send_response(self, response: str) -> None:
        if not response:
            return
        data = response.encode("utf-8", errors="replace")
        for i in range(0, len(data), self._max_chunk_bytes):
            chunk = data[i : i + self._max_chunk_bytes]
            self._notify(chunk)
            time.sleep(0.01)

    def _notify(self, chunk: bytes) -> None:
        if self._tx_char is None:
            print("[BLE] WARNING: Cannot notify - client hasn't subscribed to notifications yet")
            return

        value = list(chunk)
        print(f"[BLE] Notifying {len(value)} bytes via {self._tx_char!r}: {chunk[:50]!r}")

        try:
            # This is the standard bluezero pattern for sending notifications
            self._tx_char.set_value(value)
            print("[BLE] ✓ Notification sent successfully")
        except Exception as e:
            print(f"[BLE] ✗ Notification failed: {e}")
            import traceback
            traceback.print_exc()

    def _get_default_adapter_addr(self) -> Optional[str]:
        if adapter is None:
            return None
        try:
            # bluezero adapter helper
            adapters = adapter.list_adapters()  # type: ignore[attr-defined]
            if adapters:
                return adapters[0]
        except Exception:
            pass
        try:
            adapters = adapter.Adapter.available()  # type: ignore[attr-defined]
            if adapters:
                return adapters[0].address
        except Exception:
            pass
        return None
