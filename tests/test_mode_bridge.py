from core.mode_bridge import InklingModeBridge


class DummyWebMode:
    def _handle_command_sync(self, command: str):
        return {"response": f"handled {command}"}

    def _handle_chat_sync(self, message: str):
        return {"response": f"chat {message}"}


def test_handle_help_command_web_mode():
    bridge = InklingModeBridge(mode=DummyWebMode(), loop=None)
    output = bridge.handle_line("/help")
    assert output.startswith("OK 0")
    assert "handled /help" in output


def test_bash_command():
    bridge = InklingModeBridge(mode=DummyWebMode(), loop=None, allow_bash=True)
    output = bridge.handle_line("/bash echo hi")
    assert output.startswith("OK 0")
    assert "hi" in output


def test_chat_routes_to_web_handler():
    bridge = InklingModeBridge(mode=DummyWebMode(), loop=None)
    output = bridge.handle_line("hello")
    assert output.startswith("OK 0")
    assert "chat hello" in output
