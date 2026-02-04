# Face Expressions Reference

Inkling has two sets of face expressions: ASCII (compatible everywhere) and Unicode (prettier in browsers).

## ASCII Faces (Always Work)

These work in SSH mode, web UI, and any terminal:

| Face | Expression | Use Case |
|------|------------|----------|
| (^_^) | happy | Default, content state |
| (*^_^*) | excited | Very happy, enthusiastic |
| (^_^)b | grateful | Thankful, appreciative |
| (o_O)? | curious | Questioning, investigating |
| (>_<) | intense | Concentrating, focused |
| ( -_-) | cool | Relaxed, chill |
| (-_-) | bored | Uninterested, waiting |
| (;_;) | sad | Upset, disappointed |
| (>_<#) | angry | Frustrated, annoyed |
| (-.-)zzZ | sleepy | Tired, drowsy |
| (O_O) | awake | Alert, surprised |
| (@_@) | thinking | Processing, pondering |
| (?_?) | confused | Uncertain, puzzled |
| (O_o) | surprised | Unexpected event |
| (*^3^) | love | Affectionate |
| (^_~) | wink | Playful |
| (._.)> | working | Busy with task |
| (o_o) | searching | Looking for something |
| (>.<) | fetching | Retrieving data |
| (._.) | writing | Creating content |
| (^_^)v | success | Task completed! |

## Unicode Faces (Better in Browser)

These look better in the web UI with proper Unicode support:

| Face | Expression | Use Case |
|------|------------|----------|
| (◉‿◉) | awake/motivated | Alert and ready |
| (•‿‿•) | happy | Content, pleased |
| (◕‿◕) | excited/grateful | Very happy |
| (ᴗ﹏ᴗ) | sleep | Sleeping |
| (•﹏•) | sleep2 | Light sleep |
| (-‿‿-) | sleepy | Getting drowsy |
| (-__-) | bored | Uninterested |
| (•_•) | intense | Focused |
| (⌐■_■) | cool | Deal with it |
| (•__•) | demotivated | Low energy |
| (·•·) | lonely | Isolated |
| (╥﹏╥) | sad | Very upset |
| (ಠ_ಠ) | angry | Disapproving |
| (ಠ‿ಠ)? | curious | Intrigued |
| (◕.◕) | thinking | Pondering |
| (•_•)? | confused | Puzzled |
| (◉_◉)! | surprised | Shocked |
| (◕‿◕✿) | friend | Friendly |
| (✖╭╮✖) | broken | Error state |
| (◈‿◈) | debug | Debugging |
| (♥‿♥) | love | Affectionate |
| (⌐◉‿◉) | upload | Sending data |
| (◉_•) | working | Processing |
| (◕‿◕)v | success | Victory! |

## Looking Directions

Special faces for directional context:

| Face | Expression | Direction |
|------|------------|-----------|
| ( ◉_◉) | look_r | Looking right |
| (◉_◉ ) | look_l | Looking left |
| ( ◉‿◉) | look_r_happy | Happy, looking right |
| (◉‿◉ ) | look_l_happy | Happy, looking left |

## Web UI Display

The web UI automatically uses Unicode faces when available, falling back to ASCII if needed.

**Font Stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif`

This ensures:
- ✅ Native emoji support on iOS/macOS
- ✅ Windows emoji support
- ✅ Linux fallback to system fonts
- ✅ Always readable (ASCII fallback)

## SSH Mode Display

SSH mode prefers Unicode faces when the terminal supports them, but will show ASCII faces if Unicode renders incorrectly.

**Check your terminal's Unicode support:**
```bash
# Test in SSH mode
python main.py --mode ssh
/faces
```

## Changing Faces

### Via Commands
```bash
# SSH mode
/face happy
/face thinking

# Web UI
Click "Faces" button to see all
Type /face <name> in chat
```

### Programmatically
```python
# In code
personality.face = "excited"
await display.update(face="excited", text="I'm excited!")
```

## Custom Faces

To add new faces, edit `core/ui.py`:

```python
# Add to FACES dict (ASCII)
FACES = {
    ...
    "myface": "(o_o)",
}

# Or add to UNICODE_FACES dict (Unicode)
UNICODE_FACES = {
    ...
    "myface": "(◉‿◉)",
}
```

## Mood-Face Mapping

Faces automatically change based on mood in autonomous mode:

| Mood | Default Face |
|------|--------------|
| happy | (◕‿◕) |
| excited | (*^_^*) |
| grateful | (^_^)b |
| curious | (ಠ‿ಠ)? |
| intense | (•_•) |
| cool | (⌐■_■) |
| bored | (-__-) |
| sad | (╥﹏╥) |
| sleepy | (ᴗ﹏ᴗ) |
| lonely | (·•·) |

## Troubleshooting

### Faces showing as boxes or question marks?

**In Web UI:**
- Make sure your browser is up to date
- Try Chrome/Firefox/Safari (best Unicode support)
- Clear browser cache and refresh

**In SSH mode:**
- Your terminal may not support Unicode
- SSH with `-T` flag: `ssh -T user@inkling.local`
- Use a modern terminal (iTerm2, Windows Terminal, GNOME Terminal)
- Check terminal encoding: should be UTF-8

### Faces look squished or misaligned?

**Web UI:**
- Check browser zoom (should be 100%)
- The CSS uses letter-spacing for better rendering
- Try a different browser

**E-ink display:**
- Font size is optimized for 250x122 display
- Faces are centered automatically
- Some Unicode chars may not render on e-ink (uses ASCII fallback)

## Best Practices

1. **Use ASCII faces** for compatibility (SSH, logs)
2. **Use Unicode faces** for visual appeal (web UI)
3. **Let the system choose** - it picks the best for each context
4. **Test new faces** in both SSH and web modes before deploying

---

*For developers: See `core/ui.py` for face definitions and rendering logic.*
