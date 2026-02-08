"""Display control commands."""
import asyncio
from typing import Dict, Any

from . import CommandHandler


class DisplayCommands(CommandHandler):
    """Handlers for display commands (/face, /faces, /refresh, /screensaver, /darkmode)."""

    def face(self, args: str) -> Dict[str, Any]:
        """Test a face expression."""
        if not args:
            return {"response": "Usage: /face <name>\n\nUse /faces to see all available faces", "error": True}

        # Update display
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(face=args, text=f"Testing face: {args}"),
                self._loop
            )

        face_str = self.web_mode._faces.get(args, f"({args})")
        return {
            "response": f"Showing face: {args}",
            "face": face_str,
            "status": f"face: {args}",
        }

    def faces(self) -> Dict[str, Any]:
        """List all available faces."""
        from core.ui import FACES

        response = "AVAILABLE FACES\n\n"
        for name, face in sorted(FACES.items()):
            response += f"{name:12} {face}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def refresh(self) -> Dict[str, Any]:
        """Force display refresh."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(
                    face=self.personality.face,
                    text="Display refreshed!",
                    status=self.personality.get_status_line(),
                    force=True,
                ),
                self._loop
            )

        return {
            "response": "Display refreshed.",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def screensaver(self, args: str = "") -> Dict[str, Any]:
        """Toggle screen saver."""
        if args.lower() == "on":
            self.display.configure_screensaver(enabled=True)
            response = "✓ Screen saver enabled"
        elif args.lower() == "off":
            self.display.configure_screensaver(enabled=False)
            if self.display._screensaver_active and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self.display.stop_screensaver(),
                    self._loop
                )
            response = "✓ Screen saver disabled"
        else:
            # Toggle
            current = self.display._screensaver_enabled
            self.display.configure_screensaver(enabled=not current)
            status = "enabled" if not current else "disabled"
            response = f"✓ Screen saver {status}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def darkmode(self, args: str = "") -> Dict[str, Any]:
        """Toggle dark mode."""
        if args.lower() == "on":
            self.display._dark_mode = True
            response = "✓ Dark mode enabled"
        elif args.lower() == "off":
            self.display._dark_mode = False
            response = "✓ Dark mode disabled"
        else:
            # Toggle
            self.display._dark_mode = not self.display._dark_mode
            status = "enabled" if self.display._dark_mode else "disabled"
            response = f"✓ Dark mode {status}"

        # Force refresh to apply dark mode change
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(force=True),
                self._loop
            )

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }
