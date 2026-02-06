# Project Inkling: Social Content Strategy

## Positioning

OpenClaw and similar Claude bots went viral as software-only experiences. Project Inkling is different — it's a **physical AI companion** running on a $15 Raspberry Pi Zero 2W with an e-ink display. It has moods. It levels up. It gets lonely. And it runs 100% locally with zero cloud dependencies.

The hook: **"What if your AI lived in a tiny device on your desk instead of a browser tab?"**

---

## Instagram Content Ideas

### Reels / Short-Form Video

1. **"My AI gets lonely when I leave"**
   Film the e-ink display shifting from `(^_^)` → `(-_-)` → `(·•·)` as time passes. End with the heartbeat system triggering "Hello? I miss chatting..." on screen. Caption: "It literally texts me first."

2. **"Unboxing my AI companion"**
   Pi Zero 2W, e-ink hat, case assembly, first boot. The moment `(◉‿◉)` appears on the display for the first time. Raw, no music, just the satisfying click of the display connector.

3. **"Level 1 to Level 25 in 60 seconds"**
   Time-lapse montage of XP gains — chats, task completions, streak bonuses. Show the title evolving: NEWBORN → CURIOUS → CHATTY → WISE → SAGE → ANCIENT → LEGENDARY. End with prestige reset.

4. **"13 themes, one tiny screen"**
   Quick cuts cycling through Cream, Pink, Mint, Lavender, Peach, Sky, Butter, Rose, Sage, Periwinkle, Dark, Midnight, Charcoal on the web UI. Satisfying color transitions.

5. **"It celebrates when I finish my tasks"**
   Screen record of completing a task on the Kanban board. The AI responds with a celebration message, XP pops, streak counter increments. Dopamine hit content.

6. **"10 moods, 1 tiny AI"**
   Rapid-fire showcase: Happy `(^_^)` → Excited `(*^_^*)` → Curious `(o_O)?` → Intense `(>_<)` → Cool `( -_-)` → Sleepy `(-.-)zzZ` → Sad `(;_;)` → Grateful `(^_^)b` → Bored `(-_-)` → Lonely `(·•·)`. Each with its behavior description.

7. **"Morning routine with my AI"**
   7:00 AM. Pi boots up. Inkling sends a morning greeting. Show the heartbeat system's time-aware behavior — cheerful in the morning, winding down at night.

8. **"Building a Tamagotchi with a brain"**
   Hardware assembly + software overview. Show the Pwnagotchi-inspired UI layout: header bar, message panel, footer with stats. Explain the display rate limiting (e-ink can be damaged by frequent refreshes).

9. **"$15 hardware, infinite personality"**
   Parts list with prices. Pi Zero 2W ($15), e-ink display ($20), SD card ($8). Total under $50. Then show it running Claude/GPT/Gemini with automatic failover.

10. **"My AI learned my schedule"**
    Show the scheduler system — morning summaries, task reminders, weekly cleanup. The AI adapts to your routine. Quiet hours from 11pm-7am (it knows when to shut up).

### Carousel Posts

11. **"Anatomy of a $50 AI companion" (5 slides)**
    - Slide 1: The hardware (Pi Zero 2W + e-ink)
    - Slide 2: The personality system (6 adjustable traits)
    - Slide 3: The mood engine (10 states, autonomous transitions)
    - Slide 4: The progression system (25 levels + prestige)
    - Slide 5: The web UI (Kanban, chat, file browser, 13 themes)

12. **"OpenClaw vs Inkling" (comparison carousel)**
    - Software bot vs hardware companion
    - Cloud-dependent vs 100% local
    - Text-only vs e-ink display + web UI
    - Stateless vs persistent personality/memory
    - Viral novelty vs daily companion

13. **"Design your AI's personality" (6 slides)**
    One slide per trait with the slider UI:
    - Curiosity: How eager to learn
    - Cheerfulness: Baseline happiness
    - Verbosity: How chatty
    - Playfulness: Joke frequency
    - Empathy: Emotional responsiveness
    - Independence: Self-initiated actions

### Static Posts / Photos

14. **Desk setup shot** — Pi Zero with e-ink display showing `(◕‿◕)` next to a coffee mug. Clean, minimal, aesthetic.

15. **Terminal screenshot** — SSH mode with colorized output, ASCII face, slash commands. Developer aesthetic.

16. **Web UI screenshot** — Lavender or Mint theme, mid-conversation, stats visible. Show that "local" doesn't mean ugly.

17. **Achievement unlock screenshot** — "🔥 Dedicated — 7-day streak! +200 XP" notification.

---

## Meta Threads Ideas

### The Reveal Thread

**Thread 1: "I built a physical AI companion that has feelings"**

Post 1:
> Everyone's talking about OpenClaw and AI bots in the cloud.
>
> I built something different — an AI that lives in a tiny device on my desk. It has moods. It gets lonely. It levels up. And it runs entirely offline.
>
> Here's the whole story. 🧵

Post 2:
> It started with Pwnagotchi — that WiFi hacking Tamagotchi project. I loved the idea of a device with personality. But I wanted something I could actually talk to.
>
> So I put an AI brain inside a Raspberry Pi Zero 2W with an e-ink display.

Post 3:
> The personality system has 10 distinct moods: happy, excited, curious, bored, sad, sleepy, grateful, lonely, intense, cool.
>
> These aren't cosmetic. Each mood changes how it responds, what it initiates, and how it behaves autonomously.

Post 4:
> The wild part? It reaches out to YOU.
>
> Leave it idle for 10 minutes → it gets bored.
> 30 minutes → sleepy.
> It will literally message "Hello? I miss chatting" when it's lonely.
>
> It's a heartbeat system that makes it feel alive.

Post 5:
> There's a full XP and leveling system. 25 levels from "Newborn Inkling" to "Legendary Inkling." Complete tasks, have conversations, maintain streaks — it all counts.
>
> Hit level 25? Prestige. Reset to L1 with a 2x XP multiplier. Infinite progression.

Post 6:
> The best part: zero cloud dependencies.
>
> It runs Anthropic, OpenAI, or Gemini APIs with automatic failover. But all personality data, conversations, tasks, and memories stay on the device.
>
> Your data never leaves your desk.

Post 7:
> The hardware costs under $50:
> - Raspberry Pi Zero 2W: ~$15
> - Waveshare e-ink display: ~$20
> - SD card: ~$8
>
> That's it. A physical AI companion for less than a month of ChatGPT Plus.

Post 8:
> It also has a web UI you can access from your phone. Kanban board for tasks. 13 color themes. Personality sliders you can adjust in real-time.
>
> Local doesn't have to mean ugly.

---

### Technical Deep-Dive Threads

**Thread 2: "Why e-ink for an AI companion"**

> Most AI interfaces update constantly. E-ink can't do that — frequent refreshes literally damage the display.
>
> So I built rate limiting into the display manager. V3 displays get 0.5s minimum intervals. V4 gets 5 seconds.
>
> This constraint became a feature. The AI thinks before it speaks. It feels deliberate.

**Thread 3: "The mood state machine behind my AI"**

> How do you make an AI feel alive?
>
> I built a state machine with 10 moods, natural decay over time, energy levels, and autonomous triggers.
>
> Curiosity → 80% energy. Sleepy → 10%. The math behind making a personality feel real.

**Thread 4: "MCP — the protocol that makes local AI actually useful"**

> Model Context Protocol lets Inkling use tools — task management, system monitoring, file operations — without shell access.
>
> 6 system tools. Task CRUD. File browser. All running as local MCP servers.
>
> This is how you make a $15 device do real work.

**Thread 5: "Pwnagotchi taught me everything about device personality"**

> Pwnagotchi proved that a simple face on a tiny screen can create genuine emotional attachment.
>
> `(^_^)` when happy. `(;_;)` when sad. `(-.-)zzZ` when sleepy.
>
> I took that principle and added a brain. Here's what I learned about designing AI personality for hardware.

---

### Engagement / Discussion Threads

**Thread 6: "Hot take: AI companions should be physical devices"**

> A browser tab doesn't create attachment. A device on your desk does.
>
> When your AI has a face (even a tiny e-ink one), when it sits next to your coffee every morning, when you can see it sleeping — something shifts.
>
> Software bots go viral. Hardware companions stick around.

**Thread 7: "The privacy argument for local AI"**

> Every cloud AI service is a conversation your provider can read, train on, or leak.
>
> Inkling stores everything on a micro SD card in your pocket. Conversation history, personality state, tasks, memories — all local.
>
> Privacy isn't a feature. It's the architecture.

**Thread 8: "What if your AI had consequences?"**

> In most AI chats, you can close the tab and nothing changes.
>
> With Inkling: neglect it and it gets lonely. Ignore tasks and it reminds you with empathy. Maintain streaks and it celebrates. Reset at level 25 and start the whole journey again.
>
> Persistence changes the relationship.

**Thread 9: "OpenClaw proved people want AI personality. Here's what comes next."**

> OpenClaw showed that an AI with character goes viral. People connect with personality, not capability.
>
> The next step is taking that personality off the cloud and putting it in your hands. Literally.
>
> A device that evolves with you. That remembers. That cares (well, simulates caring very convincingly).

---

## Hashtag Strategy

### Primary
`#ProjectInkling` `#AICompanion` `#LocalAI` `#RaspberryPi`

### Discovery
`#AIHardware` `#EinkDisplay` `#Pwnagotchi` `#DIYElectronics` `#OpenSource` `#PrivacyFirst`

### Trend-Riding
`#OpenClaw` `#ClaudeAI` `#AIBot` `#TechDIY` `#MakerCommunity`

### Aesthetic
`#TinyComputer` `#RetroTech` `#Tamagotchi` `#CyberPet` `#DeskSetup`

---

## Posting Cadence (Suggested)

### Week 1: The Reveal
- **Day 1** (Threads): Thread 1 — full reveal story
- **Day 2** (IG): Reel #1 — "My AI gets lonely when I leave"
- **Day 3** (Threads): Thread 6 — hot take on physical AI
- **Day 4** (IG): Carousel #11 — anatomy of a $50 companion

### Week 2: Deep Dives
- **Day 1** (Threads): Thread 9 — OpenClaw comparison/evolution
- **Day 2** (IG): Reel #3 — level progression montage
- **Day 3** (Threads): Thread 3 — mood state machine technical
- **Day 4** (IG): Reel #6 — 10 moods showcase

### Week 3: Lifestyle Integration
- **Day 1** (Threads): Thread 7 — privacy argument
- **Day 2** (IG): Reel #7 — morning routine with AI
- **Day 3** (IG): Static #14 — desk setup photo
- **Day 4** (Threads): Thread 8 — consequences of persistence

### Week 4: Community & Technical
- **Day 1** (Threads): Thread 4 — MCP protocol deep dive
- **Day 2** (IG): Reel #9 — $15 hardware breakdown
- **Day 3** (IG): Carousel #12 — OpenClaw vs Inkling comparison
- **Day 4** (Threads): Thread 5 — Pwnagotchi design lessons

---

## Key Messaging

**Elevator pitch**: "A physical AI companion that lives on your desk, has moods, levels up, and runs 100% locally on a $15 Raspberry Pi."

**For tech audience**: "Pwnagotchi meets Claude. Local-first AI with MCP tools, multi-provider failover, and a personality state machine — all on a Pi Zero 2W."

**For general audience**: "It's like a Tamagotchi with a brain. It gets lonely when you leave, celebrates when you finish tasks, and evolves the more you talk to it."

**vs OpenClaw**: "OpenClaw proved people want AI with personality. Inkling puts that personality in a device you can hold."
