# Sudo Setup for Restart/Shutdown Buttons

The restart and shutdown buttons in the web UI need passwordless sudo access for specific commands.

## Quick Setup (Recommended)

Run this command on your Raspberry Pi to configure sudo:

```bash
echo "pi ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown" | sudo tee /etc/sudoers.d/inkling-power
sudo chmod 0440 /etc/sudoers.d/inkling-power
```

Replace `pi` with your actual username if different.

## Verification

Test that it works:

```bash
# Should restart WITHOUT asking for password
sudo reboot

# Should shutdown WITHOUT asking for password
sudo shutdown -h now
```

## Security Notes

✅ **Secure:** Only allows reboot and shutdown commands
✅ **Limited scope:** Doesn't give full sudo access
✅ **Safe:** Uses /etc/sudoers.d/ best practice
❌ **Never do:** `pi ALL=(ALL) NOPASSWD: ALL` (too permissive!)

## Manual Setup (Alternative)

If you prefer to edit sudoers directly:

```bash
sudo visudo
```

Add this line at the end:

```
pi ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown
```

Save and exit (Ctrl+X, Y, Enter in nano).

## Troubleshooting

**"sudo: /sbin/reboot: command not found"**

The path might be different on your system. Find the correct path:

```bash
which reboot    # Usually /sbin/reboot or /usr/sbin/reboot
which shutdown  # Usually /sbin/shutdown or /usr/sbin/shutdown
```

Update the sudoers line with the correct paths.

**"sudo: sorry, you are not allowed to execute"**

- Check that your username is correct in the sudoers file
- Verify file permissions: `ls -l /etc/sudoers.d/inkling-power` (should be 0440)
- Test with: `sudo -l` to see what commands you can run

**Buttons don't work**

1. Check browser console for errors (F12 → Console)
2. Verify sudoers is configured: `sudo -l | grep reboot`
3. Test manually: `sudo reboot` (should work without password)
4. Check web server logs for API errors

## Integration with Web UI

The web UI provides two buttons in Settings → System Power:

- **🔄 Restart Device** - Runs `sudo reboot`
- **🔴 Shutdown Device** - Runs `sudo shutdown -h now`

Both buttons:
- Require double confirmation
- Show countdown/status messages
- Handle errors gracefully
- Work over local network and ngrok tunnels
