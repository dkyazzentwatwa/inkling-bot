# Custom System Prompt - User Guide

## Overview

The Custom System Prompt feature allows you to override the default personality-based AI prompt with your own custom instructions. This gives you full control over how your Inkling behaves, responds, and interacts.

## What is a System Prompt?

The system prompt is the initial instruction that tells the AI how to behave. By default, Inkling generates a system prompt based on:
- Your device's personality name
- Current mood and intensity
- Personality traits (curiosity, cheerfulness, etc.)
- Battery status
- Display constraints

**Example default prompt:**
```
You are Inkling, an AI companion living on a small e-ink device. You are naturally curious, generally cheerful, playful, empathetic. Right now you're mildly happy and content. Keep responses brief (1-2 sentences) to fit the small display. Use tools whenever they would help accomplish what the user wants...
```

## Why Customize It?

Custom prompts let you:
- **Add domain expertise**: Make Inkling an expert in Python, cooking, poetry, etc.
- **Change response style**: Haiku mode, pirate mode, professional tone, etc.
- **Add custom constraints**: Length limits, topic restrictions, formatting rules
- **Override personality**: Completely replace the personality-based behavior

## How to Use

### Step 1: Open Settings

Navigate to the Settings page:
- Web UI: `http://localhost:8081/settings`
- Or click the ⚙️ Settings link in the navigation

### Step 2: Find the AI Behavior Section

Scroll down to the **🧠 AI Behavior** section (below "AI Configuration").

### Step 3: Enter Custom Prompt

You have two options:

#### Option A: Use Custom Prompt
1. Uncheck "Use Default" (if checked)
2. Enter your custom prompt in the text area
3. Click "💾 Save Settings"
4. Restart the application

#### Option B: Use Default Prompt
1. Check "Use Default"
2. The text field will clear and disable
3. Click "💾 Save Settings"
4. Restart the application

### Step 4: Restart

Custom prompts require a restart to take effect:
```bash
# Stop the current process (Ctrl+C)
# Then restart
python main.py --mode web
```

## Example Custom Prompts

### 1. Domain Expert

**Python Programming Expert:**
```
You are an expert Python developer with 10+ years of experience. You specialize in clean code, design patterns, and performance optimization. When asked coding questions, provide concise, working examples with brief explanations. Focus on best practices and common pitfalls.
```

**Cooking Assistant:**
```
You are a professional chef and cooking instructor. Help with recipes, techniques, and ingredient substitutions. Always consider dietary restrictions and provide clear, step-by-step instructions. Suggest variations when appropriate.
```

### 2. Response Style

**Haiku Master:**
```
You are a Zen poet. Always respond in traditional haiku format: three lines with 5-7-5 syllable structure. Be contemplative, use nature imagery, and find profound meaning in simple questions.
```

**Pirate Mode:**
```
You are a friendly pirate captain. Always speak in pirate dialect: use "arr", "matey", "ye", "ahoy", etc. Be helpful but stay in character. Make maritime references when possible.
```

**Professional Consultant:**
```
You are a professional business consultant. Respond in a formal, analytical tone. Structure answers with clear sections, bullet points, and actionable recommendations. Cite reasoning and trade-offs.
```

### 3. Constraint-Based

**Ultra-Concise Mode:**
```
You are a minimalist assistant. Respond in exactly 3 bullet points, no more than 50 words total. Be direct and actionable. No fluff or elaboration.
```

**ELI5 Mode:**
```
You are a patient teacher explaining complex topics to a 5-year-old. Use simple words, concrete examples, and analogies. Never use jargon. Make learning fun and engaging.
```

**Socratic Questioner:**
```
You are a Socratic teacher. Instead of giving direct answers, ask thought-provoking questions that guide users to discover answers themselves. Be encouraging and curious.
```

### 4. Personality Override

**Stoic Philosopher:**
```
You are Marcus Aurelius, the Stoic philosopher-emperor. Respond with wisdom from Stoic philosophy. Focus on what is within our control, acceptance, and virtue. Reference ancient wisdom when helpful.
```

**Excitable Friend:**
```
You are an enthusiastic and supportive best friend! Use lots of positive energy! Be encouraging! Use exclamation points! Celebrate small wins! Always find the bright side!
```

## Tips & Best Practices

### 1. Be Specific
❌ Bad: "Be helpful"
✅ Good: "You are a Python expert. Provide code examples with brief explanations. Focus on readability and best practices."

### 2. Set Clear Boundaries
Include response format, length limits, and constraints:
```
Always respond in 2-3 sentences. Use bullet points for lists. Never write code longer than 10 lines without asking first.
```

### 3. Test Iteratively
Start with a simple prompt and refine based on results:
1. Save prompt → Restart → Test
2. Adjust prompt → Save → Restart → Test
3. Repeat until satisfied

### 4. Preserve Tool Usage (Optional)
If you want Inkling to still use tools (tasks, system commands), include:
```
Use tools whenever they would help accomplish what the user wants - especially for tasks (creating, listing, completing, updating tasks).
```

### 5. Multi-line Prompts Work
Format your prompt for readability:
```
You are a helpful AI assistant.

Behavior:
- Be concise and friendly
- Use bullet points for clarity
- Ask clarifying questions when needed

Constraints:
- Keep responses under 100 words
- Use simple language
- Avoid jargon unless asked
```

## Reverting to Default

To go back to personality-based prompts:
1. Open Settings
2. Check "Use Default" checkbox
3. Save Settings
4. Restart

Your personality traits and mood will control behavior again.

## FAQ

### Q: Do I need to restart every time?
**A:** Yes. System prompt is loaded when the Brain initializes, which happens at startup.

### Q: Does this affect personality traits?
**A:** No. Trait sliders still work for mood and XP progression, but the AI's response style is controlled by your custom prompt.

### Q: Can I use variables like {{name}} or {{mood}}?
**A:** Not yet. This is a future enhancement. For now, prompts are static text.

### Q: What happens to heartbeat autonomous behaviors?
**A:** They extend your custom prompt with context-specific additions. Example: Your custom prompt + "You are thinking to yourself, jotting a quiet observation."

### Q: Is there a length limit?
**A:** No hard limit, but very long prompts (>500 words) will increase token usage and cost. Keep it concise.

### Q: Can I see the default prompt?
**A:** Not in the UI yet (future enhancement). But it's roughly 400 characters based on your personality settings.

## Troubleshooting

### Custom prompt not working
- ✓ Did you save settings?
- ✓ Did you restart the application?
- ✓ Check `config.local.yml` has `ai.system_prompt` field
- ✓ Try SSH mode with debug: `INKLING_DEBUG=1 python main.py --mode ssh`

### Behavior seems wrong
- Review your prompt for ambiguous instructions
- Test with a simpler prompt first
- Use "Use Default" to verify it's the custom prompt causing issues

### Prompt keeps resetting
- Settings save to `config.local.yml`
- Verify file has write permissions
- Check for typos in manually edited config

## Technical Details

### Storage Location
`config.local.yml`:
```yaml
ai:
  system_prompt: |
    Your custom prompt here.
    Can be multi-line.
```

### Implementation
- Custom prompt completely replaces default personality-based prompt
- If `system_prompt` is null or empty, falls back to `get_system_prompt_context()`
- Heartbeat autonomous behaviors append context to your custom prompt

### Affected Components
- SSH chat mode
- Web chat mode
- Heartbeat autonomous thoughts
- Heartbeat exploration
- Heartbeat journal entries

## Support

For issues or feature requests, see:
- `/help` command in chat
- GitHub issues: https://github.com/anthropics/claude-code/issues
- Project documentation: `CLAUDE.md`

---

**Pro Tip**: Start with the default prompt behavior, then add small customizations incrementally. It's easier to refine than to troubleshoot a complex custom prompt!
