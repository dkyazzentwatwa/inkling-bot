"""
Project Inkling - Web Chat Mode

Local web UI for phone/browser access to the Inkling.
Runs a Bottle server on http://inkling.local:8080
"""

import asyncio
import json
import threading
from typing import Optional, Dict, Any
from queue import Queue

from bottle import Bottle, request, response, static_file, template

from core.brain import Brain, AllProvidersExhaustedError, QuotaExceededError
from core.display import DisplayManager
from core.personality import Personality
from core.api_client import APIClient, APIError, OfflineError
from core.commands import COMMANDS, get_command, get_commands_by_category


# HTML template for the web UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{{name}} - Inkling</title>
    <style>
        :root {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        /* Pastel Color Themes */
        [data-theme="cream"] {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        [data-theme="pink"] {
            --bg: #ffe4e9;
            --text: #4a1a28;
            --border: #d4758f;
            --muted: #8f5066;
            --accent: #ff6b9d;
        }
        [data-theme="mint"] {
            --bg: #e0f5f0;
            --text: #1a3a33;
            --border: #6eb5a3;
            --muted: #4d8073;
            --accent: #52d9a6;
        }
        [data-theme="lavender"] {
            --bg: #f0e9ff;
            --text: #2a1a4a;
            --border: #9d85d4;
            --muted: #6b5a8f;
            --accent: #a78bfa;
        }
        [data-theme="peach"] {
            --bg: #ffe9dc;
            --text: #4a2a1a;
            --border: #d49675;
            --muted: #8f6650;
            --accent: #ffab7a;
        }
        [data-theme="sky"] {
            --bg: #e0f0ff;
            --text: #1a2e4a;
            --border: #6ba3d4;
            --muted: #4d708f;
            --accent: #5eb3ff;
        }
        [data-theme="butter"] {
            --bg: #fff9e0;
            --text: #4a3f1a;
            --border: #d4c175;
            --muted: #8f8350;
            --accent: #ffd952;
        }
        [data-theme="rose"] {
            --bg: #fff0f3;
            --text: #4a1a2a;
            --border: #d47590;
            --muted: #8f5068;
            --accent: #ff9eb8;
        }
        [data-theme="sage"] {
            --bg: #eff5e9;
            --text: #2a331a;
            --border: #8fb575;
            --muted: #607a4d;
            --accent: #9bc978;
        }
        [data-theme="periwinkle"] {
            --bg: #e9f0ff;
            --text: #1a2a4a;
            --border: #758fd4;
            --muted: #50638f;
            --accent: #8ba3ff;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1a1a1a;
                --text: #e5e5e0;
                --border: #555;
                --muted: #999;
                --accent: #6ab0f3;
            }
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            padding: 1rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--bg);
        }
        .name { font-size: 1.25rem; }
        .status {
            font-size: 0.875rem;
            color: var(--muted);
        }
        .face-display {
            text-align: center;
            font-size: 3rem;
            padding: 2rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif;
            line-height: 1.2;
            letter-spacing: 0.05em;
            position: sticky;
            top: 60px;
            z-index: 99;
            background: var(--bg);
            border-bottom: 2px solid var(--border);
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        .message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border: 1px solid var(--border);
        }
        .message.user {
            background: var(--bg);
            border-left: 3px solid var(--accent);
        }
        .message.assistant {
            background: var(--bg);
        }
        .message.system {
            background: var(--bg);
            border-left: 3px solid var(--muted);
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
        }
        .message .meta {
            font-size: 0.75rem;
            color: var(--muted);
            margin-top: 0.5rem;
        }
        .input-area {
            padding: 1rem;
            border-top: 2px solid var(--border);
            display: flex;
            gap: 0.5rem;
        }
        .input-area input {
            flex: 1;
            padding: 0.75rem;
            font-family: inherit;
            font-size: 1rem;
            border: 2px solid var(--border);
            background: var(--bg);
            color: var(--text);
        }
        .input-area button {
            padding: 0.75rem 1.5rem;
            font-family: inherit;
            font-size: 1rem;
            background: var(--text);
            color: var(--bg);
            border: none;
            cursor: pointer;
        }
        .input-area button:disabled {
            opacity: 0.5;
        }
        .command-palette {
            border: 2px solid var(--border);
            margin: 1rem;
        }
        .command-palette summary {
            padding: 0.75rem;
            cursor: pointer;
            font-weight: bold;
            background: var(--border);
            color: var(--bg);
            user-select: none;
        }
        .command-palette[open] summary {
            border-bottom: 2px solid var(--border);
        }
        .command-groups {
            padding: 1rem;
            max-height: 200px;
            overflow-y: auto;
        }
        .command-group {
            margin-bottom: 1rem;
        }
        .command-group:last-child {
            margin-bottom: 0;
        }
        .command-group h4 {
            font-size: 0.75rem;
            color: var(--muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .command-buttons {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .command-buttons button {
            padding: 0.5rem 0.75rem;
            font-size: 0.75rem;
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
            cursor: pointer;
            font-family: inherit;
        }
        .command-buttons button:hover {
            background: var(--text);
            color: var(--bg);
        }
    </style>
</head>
<body>
    <header>
        <span class="name">{{name}}</span>
        <span class="status" id="status">{{status}}</span>
    </header>

    <div class="face-display" id="face">{{face}}</div>

    <div class="messages" id="messages"></div>

    <details class="command-palette" open>
        <summary>⚙️ Commands</summary>
        <div class="command-groups">
            <div class="command-group">
                <h4>Info</h4>
                <div class="command-buttons">
                    <button onclick="runCommand('/help')">Help</button>
                    <button onclick="runCommand('/level')">Level</button>
                    <button onclick="runCommand('/stats')">Stats</button>
                    <button onclick="runCommand('/history')">History</button>
                </div>
            </div>

            <div class="command-group">
                <h4>Personality</h4>
                <div class="command-buttons">
                    <button onclick="runCommand('/mood')">Mood</button>
                    <button onclick="runCommand('/energy')">Energy</button>
                    <button onclick="runCommand('/traits')">Traits</button>
                </div>
            </div>

            <div class="command-group">
                <h4>Social</h4>
                <div class="command-buttons">
                    <button onclick="runCommand('/fish')">Fish</button>
                    <button onclick="runCommand('/queue')">Queue</button>
                </div>
            </div>

            <div class="command-group">
                <h4>System</h4>
                <div class="command-buttons">
                    <button onclick="runCommand('/system')">System</button>
                    <button onclick="runCommand('/config')">Config</button>
                    <button onclick="runCommand('/identity')">Identity</button>
                    <button onclick="runCommand('/faces')">Faces</button>
                    <button onclick="runCommand('/refresh')">Refresh</button>
                    <button onclick="runCommand('/clear')">Clear</button>
                    <button onclick="location.href='/social'">Social</button>
                    <button onclick="location.href='/settings'">Settings</button>
                </div>
            </div>
        </div>
    </details>

    <div class="input-area">
        <input type="text" id="input" placeholder="Say something..." autocomplete="off">
        <button id="send" onclick="sendMessage()">Send</button>
    </div>

    <script>
        // Apply saved theme
        const savedTheme = localStorage.getItem('inklingTheme') || 'cream';
        document.documentElement.setAttribute('data-theme', savedTheme);

        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const faceEl = document.getElementById('face');
        const statusEl = document.getElementById('status');

        // Handle enter key
        inputEl.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        async function sendMessage() {
            const text = inputEl.value.trim();
            if (!text) return;

            inputEl.value = '';
            sendBtn.disabled = true;

            // Add user message
            addMessage('user', text);

            try {
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text})
                });
                const data = await resp.json();

                if (data.error) {
                    addMessage('assistant', 'Error: ' + data.error);
                } else {
                    addMessage('assistant', data.response, data.meta);
                    updateState(data);
                }
            } catch (e) {
                addMessage('assistant', 'Connection error: ' + e.message);
            }

            sendBtn.disabled = false;
            inputEl.focus();
        }

        async function runCommand(cmd) {
            sendBtn.disabled = true;

            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                });
                const data = await resp.json();

                if (data.error) {
                    addMessage('system', 'Error: ' + data.error);
                } else {
                    addMessage('system', data.response);
                    updateState(data);
                }
            } catch (e) {
                addMessage('system', 'Connection error: ' + e.message);
            }

            sendBtn.disabled = false;
        }

        function sendCommand(cmd) {
            inputEl.value = cmd;
            sendMessage();
        }

        function addMessage(role, text, meta) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = `<div class="text">${escapeHtml(text)}</div>`;
            if (meta) {
                div.innerHTML += `<div class="meta">${meta}</div>`;
            }
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function updateState(data) {
            if (data.face) faceEl.textContent = data.face;
            if (data.status) statusEl.textContent = data.status;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Poll for state updates
        setInterval(async () => {
            try {
                const resp = await fetch('/api/state');
                const data = await resp.json();
                updateState(data);
            } catch (e) {}
        }, 5000);
    </script>
</body>
</html>
"""


# Settings page template
SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Settings - {{name}}</title>
    <style>
        :root {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        /* Pastel Color Themes */
        [data-theme="cream"] {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        [data-theme="pink"] {
            --bg: #ffe4e9;
            --text: #4a1a28;
            --border: #d4758f;
            --muted: #8f5066;
            --accent: #ff6b9d;
        }
        [data-theme="mint"] {
            --bg: #e0f5f0;
            --text: #1a3a33;
            --border: #6eb5a3;
            --muted: #4d8073;
            --accent: #52d9a6;
        }
        [data-theme="lavender"] {
            --bg: #f0e9ff;
            --text: #2a1a4a;
            --border: #9d85d4;
            --muted: #6b5a8f;
            --accent: #a78bfa;
        }
        [data-theme="peach"] {
            --bg: #ffe9dc;
            --text: #4a2a1a;
            --border: #d49675;
            --muted: #8f6650;
            --accent: #ffab7a;
        }
        [data-theme="sky"] {
            --bg: #e0f0ff;
            --text: #1a2e4a;
            --border: #6ba3d4;
            --muted: #4d708f;
            --accent: #5eb3ff;
        }
        [data-theme="butter"] {
            --bg: #fff9e0;
            --text: #4a3f1a;
            --border: #d4c175;
            --muted: #8f8350;
            --accent: #ffd952;
        }
        [data-theme="rose"] {
            --bg: #fff0f3;
            --text: #4a1a2a;
            --border: #d47590;
            --muted: #8f5068;
            --accent: #ff9eb8;
        }
        [data-theme="sage"] {
            --bg: #eff5e9;
            --text: #2a331a;
            --border: #8fb575;
            --muted: #607a4d;
            --accent: #9bc978;
        }
        [data-theme="periwinkle"] {
            --bg: #e9f0ff;
            --text: #1a2a4a;
            --border: #758fd4;
            --muted: #50638f;
            --accent: #8ba3ff;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1a1a1a;
                --text: #e5e5e0;
                --border: #555;
                --muted: #999;
                --accent: #6ab0f3;
            }
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 1rem;
        }
        header {
            padding: 1rem 0;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        h1 { font-size: 1.5rem; }
        h2 {
            font-size: 1.125rem;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }
        .back-button {
            padding: 0.5rem 1rem;
            font-family: inherit;
            font-size: 1rem;
            background: transparent;
            color: var(--text);
            border: 2px solid var(--border);
            cursor: pointer;
        }
        .back-button:hover {
            background: var(--text);
            color: var(--bg);
        }
        .settings-section {
            max-width: 600px;
            margin: 0 auto;
        }
        .input-group {
            margin-bottom: 1.5rem;
        }
        .input-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: bold;
        }
        .input-group input[type="text"] {
            width: 100%;
            padding: 0.75rem;
            font-family: inherit;
            font-size: 1rem;
            border: 2px solid var(--border);
            background: var(--bg);
            color: var(--text);
        }
        .slider-container {
            margin-bottom: 1.5rem;
        }
        .slider-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .slider-label span:first-child {
            font-weight: bold;
        }
        .slider-value {
            color: var(--muted);
        }
        .slider {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: var(--border);
            outline: none;
            -webkit-appearance: none;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--text);
            cursor: pointer;
        }
        .slider::-moz-range-thumb {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--text);
            cursor: pointer;
            border: none;
        }
        .save-button {
            width: 100%;
            padding: 1rem;
            font-family: inherit;
            font-size: 1rem;
            background: var(--text);
            color: var(--bg);
            border: none;
            cursor: pointer;
            margin-top: 2rem;
        }
        .save-button:disabled {
            opacity: 0.5;
        }
        .message {
            padding: 1rem;
            margin-top: 1rem;
            border: 2px solid var(--accent);
            background: var(--bg);
            display: none;
        }
        .message.show {
            display: block;
        }
    </style>
</head>
<body>
    <header>
        <h1>⚙️ Settings</h1>
        <button class="back-button" onclick="location.href='/'">← Back to Chat</button>
    </header>

    <div class="settings-section">
        <h2>🎨 Appearance</h2>

        <div class="input-group">
            <label for="theme">Color Theme</label>
            <select id="theme" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
                <option value="cream">Cream (Default)</option>
                <option value="pink">Soft Pink</option>
                <option value="mint">Mint Green</option>
                <option value="lavender">Lavender</option>
                <option value="peach">Peach</option>
                <option value="sky">Sky Blue</option>
                <option value="butter">Butter Yellow</option>
                <option value="rose">Rose</option>
                <option value="sage">Sage</option>
                <option value="periwinkle">Periwinkle</option>
            </select>
        </div>

        <h2>👤 Device & Personality</h2>

        <div class="input-group">
            <label for="name">Name</label>
            <input type="text" id="name" value="{{name}}" maxlength="20">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Curiosity</span>
                <span class="slider-value" id="curiosity-val">{{int(traits['curiosity'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="curiosity" min="0" max="100" value="{{int(traits['curiosity'] * 100)}}" oninput="updateSlider('curiosity')">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Cheerfulness</span>
                <span class="slider-value" id="cheerfulness-val">{{int(traits['cheerfulness'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="cheerfulness" min="0" max="100" value="{{int(traits['cheerfulness'] * 100)}}" oninput="updateSlider('cheerfulness')">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Verbosity</span>
                <span class="slider-value" id="verbosity-val">{{int(traits['verbosity'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="verbosity" min="0" max="100" value="{{int(traits['verbosity'] * 100)}}" oninput="updateSlider('verbosity')">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Playfulness</span>
                <span class="slider-value" id="playfulness-val">{{int(traits['playfulness'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="playfulness" min="0" max="100" value="{{int(traits['playfulness'] * 100)}}" oninput="updateSlider('playfulness')">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Empathy</span>
                <span class="slider-value" id="empathy-val">{{int(traits['empathy'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="empathy" min="0" max="100" value="{{int(traits['empathy'] * 100)}}" oninput="updateSlider('empathy')">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Independence</span>
                <span class="slider-value" id="independence-val">{{int(traits['independence'] * 100)}}%</span>
            </div>
            <input type="range" class="slider" id="independence" min="0" max="100" value="{{int(traits['independence'] * 100)}}" oninput="updateSlider('independence')">
        </div>

        <h2>🤖 AI Configuration <span style="font-size: 0.75rem; color: var(--muted); font-weight: normal;">(Requires Restart)</span></h2>

        <div class="input-group">
            <label for="ai-primary">Primary AI Provider</label>
            <select id="ai-primary" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="gemini">Google (Gemini)</option>
            </select>
        </div>

        <div class="input-group">
            <label for="anthropic-model">Anthropic Model</label>
            <select id="anthropic-model" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
                <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast & Cheap)</option>
                <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Balanced)</option>
                <option value="claude-3-opus-20240229">Claude 3 Opus (Most Capable)</option>
            </select>
        </div>

        <div class="input-group">
            <label for="openai-model">OpenAI Model</label>
            <select id="openai-model" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
                <option value="gpt-4o-mini">GPT-4o Mini (Fast & Cheap)</option>
                <option value="gpt-4o">GPT-4o (Balanced)</option>
                <option value="o1-mini">o1 Mini (Reasoning)</option>
            </select>
        </div>

        <div class="input-group">
            <label for="gemini-model">Gemini Model</label>
            <select id="gemini-model" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
                <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Fast)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Capable)</option>
            </select>
        </div>

        <div class="input-group">
            <label for="max-tokens">Max Tokens per Response</label>
            <input type="number" id="max-tokens" min="50" max="1000" step="50" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
            <p style="font-size: 0.875rem; color: var(--muted); margin-top: 0.25rem;">Lower = cheaper, faster. Higher = more detailed responses.</p>
        </div>

        <div class="input-group">
            <label for="daily-tokens">Daily Token Budget</label>
            <input type="number" id="daily-tokens" min="1000" max="50000" step="1000" style="width: 100%; padding: 0.75rem; font-family: inherit; font-size: 1rem; border: 2px solid var(--border); background: var(--bg); color: var(--text);">
            <p style="font-size: 0.875rem; color: var(--muted); margin-top: 0.25rem;">Maximum tokens per day (~$0.03 per 10,000 with Haiku)</p>
        </div>

        <p style="padding: 0.75rem; border: 2px solid var(--accent); background: var(--bg); font-size: 0.875rem; color: var(--muted); margin-top: 1rem;">
            ⚠️ <strong>Restart required:</strong> Changes to AI settings will take effect after restarting the application.
        </p>

        <button class="save-button" id="save-btn" onclick="saveSettings()">💾 Save Settings</button>

        <div class="message" id="message"></div>
    </div>

    <script>
        // Load and apply saved theme
        const savedTheme = localStorage.getItem('inklingTheme') || 'cream';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.getElementById('theme').value = savedTheme;

        // Theme change handler
        document.getElementById('theme').addEventListener('change', function() {
            const theme = this.value;
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('inklingTheme', theme);
        });

        // Load current AI settings on page load
        fetch('/api/settings')
            .then(resp => resp.json())
            .then(data => {
                if (data.ai) {
                    document.getElementById('ai-primary').value = data.ai.primary || 'anthropic';
                    document.getElementById('anthropic-model').value = data.ai.anthropic?.model || 'claude-3-haiku-20240307';
                    document.getElementById('openai-model').value = data.ai.openai?.model || 'gpt-4o-mini';
                    document.getElementById('gemini-model').value = data.ai.gemini?.model || 'gemini-2.0-flash-exp';
                    document.getElementById('max-tokens').value = data.ai.budget?.max_tokens || 150;
                    document.getElementById('daily-tokens').value = data.ai.budget?.daily_tokens || 10000;
                }
            })
            .catch(err => console.error('Failed to load AI settings:', err));

        function updateSlider(name) {
            const slider = document.getElementById(name);
            const display = document.getElementById(name + '-val');
            display.textContent = slider.value + '%';
        }

        async function saveSettings() {
            const saveBtn = document.getElementById('save-btn');
            const messageEl = document.getElementById('message');

            saveBtn.disabled = true;
            messageEl.classList.remove('show');

            const settings = {
                name: document.getElementById('name').value.trim(),
                traits: {
                    curiosity: parseFloat(document.getElementById('curiosity').value) / 100,
                    cheerfulness: parseFloat(document.getElementById('cheerfulness').value) / 100,
                    verbosity: parseFloat(document.getElementById('verbosity').value) / 100,
                    playfulness: parseFloat(document.getElementById('playfulness').value) / 100,
                    empathy: parseFloat(document.getElementById('empathy').value) / 100,
                    independence: parseFloat(document.getElementById('independence').value) / 100,
                },
                ai: {
                    primary: document.getElementById('ai-primary').value,
                    anthropic: {
                        model: document.getElementById('anthropic-model').value,
                    },
                    openai: {
                        model: document.getElementById('openai-model').value,
                    },
                    gemini: {
                        model: document.getElementById('gemini-model').value,
                    },
                    budget: {
                        daily_tokens: parseInt(document.getElementById('daily-tokens').value),
                        per_request_max: parseInt(document.getElementById('max-tokens').value),
                    }
                }
            };

            // Validate name
            if (!settings.name || settings.name.length === 0) {
                messageEl.textContent = 'Error: Name cannot be empty';
                messageEl.classList.add('show');
                saveBtn.disabled = false;
                return;
            }

            try {
                const resp = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(settings)
                });

                const data = await resp.json();

                if (resp.ok && data.success) {
                    messageEl.textContent = '✓ Settings saved! Personality changes applied. Restart to apply AI changes.';
                    messageEl.classList.add('show');
                } else {
                    messageEl.textContent = 'Error: ' + (data.error || 'Failed to save settings');
                    messageEl.classList.add('show');
                }
            } catch (e) {
                messageEl.textContent = 'Connection error: ' + e.message;
                messageEl.classList.add('show');
            }

            saveBtn.disabled = false;
        }
    </script>
</body>
</html>
"""


# Social page template
SOCIAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{{name}} - Social</title>
    <style>
        :root {
            --bg: #f5f5f0;
            --text: #1a1a1a;
            --border: #333;
            --muted: #666;
            --accent: #4a90d9;
        }
        body {
            font-family: 'Berkeley Mono', 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 1rem;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--border);
        }
        h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        .nav-buttons {
            display: flex;
            gap: 0.5rem;
        }
        button {
            padding: 0.75rem 1.5rem;
            font-family: inherit;
            font-size: 1rem;
            background: var(--bg);
            color: var(--text);
            border: 2px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .section {
            margin-bottom: 2rem;
            padding: 1.5rem;
            border: 2px solid var(--border);
        }
        .section h2 {
            margin-top: 0;
            font-size: 1.25rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .stat {
            padding: 1rem;
            border: 1px solid var(--border);
            text-align: center;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }
        .stat-label {
            font-size: 0.875rem;
            color: var(--muted);
            text-transform: uppercase;
        }
        .dream-box {
            border: 1px solid var(--border);
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .dream-meta {
            font-size: 0.875rem;
            color: var(--muted);
            margin-bottom: 0.5rem;
        }
        .dream-content {
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        textarea {
            width: 100%;
            font-family: inherit;
            font-size: 1rem;
            padding: 0.75rem;
            border: 2px solid var(--border);
            background: var(--bg);
            color: var(--text);
            resize: vertical;
            min-height: 100px;
        }
        .char-count {
            font-size: 0.875rem;
            color: var(--muted);
            text-align: right;
            margin-top: 0.25rem;
        }
        .message {
            padding: 1rem;
            margin-top: 1rem;
            border: 2px solid var(--accent);
            background: var(--bg);
            display: none;
        }
        .message.show {
            display: block;
        }
        .message.error {
            border-color: #d94a4a;
            color: #d94a4a;
        }
        .loading {
            text-align: center;
            color: var(--muted);
            padding: 2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌙 The Conservatory</h1>
            <div class="nav-buttons">
                <button onclick="location.href='/'">Chat</button>
                <button onclick="location.href='/settings'">Settings</button>
            </div>
        </div>

        <!-- Stats Section -->
        <div class="section">
            <h2>📊 Social Stats</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="dreams-posted">-</div>
                    <div class="stat-label">Dreams Posted</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="telegrams-sent">-</div>
                    <div class="stat-label">Telegrams Sent</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="queue-size">-</div>
                    <div class="stat-label">Queued</div>
                </div>
            </div>
        </div>

        <!-- Post Dream Section -->
        <div class="section">
            <h2>✨ Post a Dream</h2>
            <p style="color: var(--muted); font-size: 0.875rem;">Share a thought with the Night Pool (max 280 characters)</p>
            <textarea id="dream-text" placeholder="The stars look different tonight..." maxlength="280"></textarea>
            <div class="char-count"><span id="char-count">0</span> / 280</div>
            <button id="post-btn" onclick="postDream()" style="margin-top: 1rem;">Post Dream</button>
            <div id="post-message" class="message"></div>
        </div>

        <!-- Night Pool Section -->
        <div class="section">
            <h2>🌙 Night Pool</h2>
            <p style="color: var(--muted); font-size: 0.875rem;">Recent dreams from other Inklings</p>
            <button onclick="fetchDream()" style="margin-bottom: 1rem;">Fish a Dream</button>
            <div id="dreams-container">
                <div class="loading">Click "Fish a Dream" to see what others are thinking...</div>
            </div>
        </div>

        <!-- Telegrams Section -->
        <div class="section">
            <h2>📮 Telegram Inbox</h2>
            <button onclick="checkTelegrams()" style="margin-bottom: 1rem;">Check Messages</button>
            <div id="telegrams-container">
                <div class="loading">Click "Check Messages" to see your inbox...</div>
            </div>
        </div>
    </div>

    <script>
        const dreamText = document.getElementById('dream-text');
        const charCount = document.getElementById('char-count');
        const postBtn = document.getElementById('post-btn');
        const postMessage = document.getElementById('post-message');

        // Character counter
        dreamText.addEventListener('input', () => {
            const count = dreamText.value.length;
            charCount.textContent = count;
            postBtn.disabled = count === 0 || count > 280;
        });

        // Load social stats
        async function loadStats() {
            try {
                const resp = await fetch('/api/social/stats');
                const data = await resp.json();

                document.getElementById('dreams-posted').textContent = data.dreams_posted || 0;
                document.getElementById('telegrams-sent').textContent = data.telegrams_sent || 0;
                document.getElementById('queue-size').textContent = data.queue_size || 0;
            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        }

        // Post a dream
        async function postDream() {
            const text = dreamText.value.trim();
            if (!text) return;

            postBtn.disabled = true;
            postMessage.classList.remove('show', 'error');

            try {
                const resp = await fetch('/api/social/dream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content: text})
                });

                const data = await resp.json();

                if (resp.ok && data.success) {
                    postMessage.textContent = '✓ Dream posted to the Night Pool!';
                    postMessage.classList.add('show');
                    dreamText.value = '';
                    charCount.textContent = '0';
                    loadStats();
                } else {
                    postMessage.textContent = 'Error: ' + (data.error || 'Failed to post dream');
                    postMessage.classList.add('show', 'error');
                }
            } catch (e) {
                postMessage.textContent = 'Connection error: ' + e.message;
                postMessage.classList.add('show', 'error');
            }

            postBtn.disabled = false;
        }

        // Fetch a random dream
        async function fetchDream() {
            const container = document.getElementById('dreams-container');
            container.innerHTML = '<div class="loading">Fishing...</div>';

            try {
                const resp = await fetch('/api/social/fish');
                const data = await resp.json();

                if (resp.ok && data.dream) {
                    const dream = data.dream;
                    container.innerHTML = `
                        <div class="dream-box">
                            <div class="dream-meta">
                                ${dream.mood || 'unknown'} | ${dream.device_name || 'Anonymous'} | ${new Date(dream.posted_at).toLocaleString()}
                            </div>
                            <div class="dream-content">${escapeHtml(dream.content)}</div>
                            <div class="dream-meta">🎣 Fished ${dream.fish_count || 0} times</div>
                        </div>
                    `;
                } else {
                    container.innerHTML = '<div class="loading">The Night Pool is empty right now...</div>';
                }
            } catch (e) {
                container.innerHTML = '<div class="loading error">Failed to fetch dream: ' + e.message + '</div>';
            }
        }

        // Check telegrams
        async function checkTelegrams() {
            const container = document.getElementById('telegrams-container');
            container.innerHTML = '<div class="loading">Checking...</div>';

            try {
                const resp = await fetch('/api/social/telegrams');
                const data = await resp.json();

                if (resp.ok && data.telegrams && data.telegrams.length > 0) {
                    container.innerHTML = data.telegrams.map(t => `
                        <div class="dream-box">
                            <div class="dream-meta">From: ${t.sender_name || 'Unknown'} | ${new Date(t.created_at).toLocaleString()}</div>
                            <div class="dream-content">${escapeHtml(t.content)}</div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div class="loading">No new telegrams</div>';
                }
            } catch (e) {
                container.innerHTML = '<div class="loading error">Failed to check telegrams: ' + e.message + '</div>';
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Load stats on page load
        loadStats();
    </script>
</body>
</html>
"""


class WebChatMode:
    """
    Web-based chat mode using Bottle.

    Provides a mobile-friendly web UI for interacting with the Inkling.
    """

    def __init__(
        self,
        brain: Brain,
        display: DisplayManager,
        personality: Personality,
        api_client: Optional[APIClient] = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        self.brain = brain
        self.display = display
        self.personality = personality
        self.api_client = api_client
        self.host = host
        self.port = port

        self._app = Bottle()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._message_queue: Queue = Queue()

        # Import faces from UI module
        # Use Unicode faces for web (better appearance), with ASCII fallback
        from core.ui import FACES, UNICODE_FACES
        self._faces = {**FACES, **UNICODE_FACES}  # Unicode takes precedence

        # Set display mode
        self.display.set_mode("WEB")

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up Bottle routes."""

        @self._app.route("/")
        def index():
            return template(
                HTML_TEMPLATE,
                name=self.personality.name,
                face=self._get_face_str(),
                status=self.personality.get_status_line(),
            )

        @self._app.route("/settings")
        def settings_page():
            return template(
                SETTINGS_TEMPLATE,
                name=self.personality.name,
                traits=self.personality.traits.to_dict(),
            )

        @self._app.route("/api/chat", method="POST")
        def chat():
            response.content_type = "application/json"
            data = request.json or {}
            message = data.get("message", "").strip()

            if not message:
                return json.dumps({"error": "Empty message"})

            # Handle commands
            if message.startswith("/"):
                result = self._handle_command_sync(message)
                return json.dumps(result)

            # Handle chat
            result = self._handle_chat_sync(message)
            return json.dumps(result)

        @self._app.route("/api/command", method="POST")
        def command():
            response.content_type = "application/json"
            data = request.json or {}
            cmd = data.get("command", "").strip()

            if not cmd:
                return json.dumps({"error": "Empty command"})

            result = self._handle_command_sync(cmd)
            return json.dumps(result)

        @self._app.route("/api/state")
        def state():
            response.content_type = "application/json"
            return json.dumps({
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
                "mood": self.personality.mood.current.value,
            })

        @self._app.route("/api/settings", method="GET")
        def get_settings():
            response.content_type = "application/json"

            # Get AI config from Brain
            ai_config = {
                "primary": self.brain.config.get("primary", "anthropic"),
                "anthropic": {
                    "model": self.brain.config.get("anthropic", {}).get("model", "claude-3-haiku-20240307"),
                },
                "openai": {
                    "model": self.brain.config.get("openai", {}).get("model", "gpt-4o-mini"),
                },
                "gemini": {
                    "model": self.brain.config.get("gemini", {}).get("model", "gemini-2.0-flash-exp"),
                },
                "budget": {
                    "daily_tokens": self.brain.budget.daily_limit,
                    "max_tokens": self.brain.config.get("budget", {}).get("per_request_max", 150),
                }
            }

            return json.dumps({
                "name": self.personality.name,
                "traits": self.personality.traits.to_dict(),
                "ai": ai_config,
            })

        @self._app.route("/api/settings", method="POST")
        def save_settings():
            response.content_type = "application/json"
            data = request.json or {}

            try:
                # Update personality name
                if "name" in data:
                    name = data["name"].strip()
                    if not name:
                        return json.dumps({"success": False, "error": "Name cannot be empty"})
                    if len(name) > 20:
                        return json.dumps({"success": False, "error": "Name too long (max 20 characters)"})
                    self.personality.name = name

                # Update traits (validate 0.0-1.0 range)
                if "traits" in data:
                    for trait, value in data["traits"].items():
                        if hasattr(self.personality.traits, trait):
                            # Clamp value to 0.0-1.0
                            value = max(0.0, min(1.0, float(value)))
                            setattr(self.personality.traits, trait, value)

                # AI settings are saved to config but not applied until restart
                # (no validation needed - Brain will reinitialize on restart)

                # Save to config.local.yml
                self._save_config_file(data)

                return json.dumps({"success": True})

            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self._app.route("/social")
        def social_page():
            return template(
                SOCIAL_TEMPLATE,
                name=self.personality.name,
            )

        @self._app.route("/api/social/stats")
        def social_stats():
            response.content_type = "application/json"
            return json.dumps({
                "dreams_posted": 0,  # TODO: track this
                "telegrams_sent": 0,  # TODO: track this
                "queue_size": self.api_client.queue_size if self.api_client else 0,
            })

        @self._app.route("/api/social/dream", method="POST")
        def post_dream_api():
            response.content_type = "application/json"
            data = request.json or {}
            content = data.get("content", "").strip()

            if not content:
                return json.dumps({"success": False, "error": "Dream content cannot be empty"})

            if len(content) > 280:
                return json.dumps({"success": False, "error": f"Dream too long ({len(content)} chars, max 280)"})

            if not self.api_client:
                return json.dumps({"success": False, "error": "API client not configured"})

            # Use async bridge
            async def post():
                try:
                    result = await self.api_client.plant_dream(
                        content=content,
                        mood=self.personality.mood.current.value,
                        face=self.personality.face,
                    )
                    self.personality.on_social_event("dream_posted")
                    return {"success": True, "dream": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}

            future = asyncio.run_coroutine_threadsafe(post(), self._loop)
            result = future.result(timeout=10)
            return json.dumps(result)

        @self._app.route("/api/social/fish")
        def fish_dream_api():
            response.content_type = "application/json"

            if not self.api_client:
                return json.dumps({"success": False, "error": "API client not configured"})

            async def fish():
                try:
                    dream = await self.api_client.fish_dream()
                    if dream:
                        self.personality.on_social_event("dream_received")
                        return {"success": True, "dream": dream}
                    return {"success": False, "error": "Night Pool is empty"}
                except Exception as e:
                    return {"success": False, "error": str(e)}

            future = asyncio.run_coroutine_threadsafe(fish(), self._loop)
            result = future.result(timeout=10)
            return json.dumps(result)

        @self._app.route("/api/social/telegrams")
        def get_telegrams_api():
            response.content_type = "application/json"

            if not self.api_client:
                return json.dumps({"success": False, "error": "API client not configured"})

            async def get_telegrams():
                try:
                    telegrams = await self.api_client.get_telegrams()
                    # TODO: Decrypt telegrams
                    return {"success": True, "telegrams": telegrams}
                except Exception as e:
                    return {"success": False, "error": str(e)}

            future = asyncio.run_coroutine_threadsafe(get_telegrams(), self._loop)
            result = future.result(timeout=10)
            return json.dumps(result)

    def _get_face_str(self) -> str:
        """Get current face as string."""
        face_name = self.personality.face
        return self._faces.get(face_name, self._faces["default"])

    def _save_config_file(self, new_settings: dict) -> None:
        """Save settings to config.local.yml"""
        from pathlib import Path
        import yaml

        config_file = Path("config.local.yml")

        # Load existing config or start fresh
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update device name
        if "name" in new_settings:
            if "device" not in config:
                config["device"] = {}
            config["device"]["name"] = new_settings["name"]

        # Update personality traits
        if "traits" in new_settings:
            if "personality" not in config:
                config["personality"] = {}
            config["personality"].update(new_settings["traits"])

        # Update AI configuration
        if "ai" in new_settings:
            if "ai" not in config:
                config["ai"] = {}

            ai_settings = new_settings["ai"]

            # Update primary provider
            if "primary" in ai_settings:
                config["ai"]["primary"] = ai_settings["primary"]

            # Update provider-specific settings
            for provider in ["anthropic", "openai", "gemini"]:
                if provider in ai_settings:
                    if provider not in config["ai"]:
                        config["ai"][provider] = {}
                    config["ai"][provider].update(ai_settings[provider])

            # Update budget settings
            if "budget" in ai_settings:
                if "budget" not in config["ai"]:
                    config["ai"]["budget"] = {}
                config["ai"]["budget"].update(ai_settings["budget"])

        # Write back to file
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    # Command handlers (all prefixed with _cmd_)

    def _cmd_help(self) -> Dict[str, Any]:
        """Show all available commands."""
        categories = get_commands_by_category()

        response_lines = ["INKLING COMMANDS\n"]

        category_titles = {
            "info": "Status & Info",
            "personality": "Personality",
            "system": "System",
            "display": "Display",
            "social": "Social (The Conservatory)",
            "session": "Session",
        }

        for cat_key in ["info", "personality", "system", "display", "social", "session"]:
            if cat_key in categories:
                response_lines.append(f"\n{category_titles.get(cat_key, cat_key.title())}:")
                for cmd in categories[cat_key]:
                    usage = f"/{cmd.name}"
                    if cmd.name in ("face", "dream", "ask"):
                        usage += " <arg>"
                    response_lines.append(f"  {usage} - {cmd.description}")

        response_lines.append("\n\nJust type (no /) to chat with AI")

        return {
            "response": "\n".join(response_lines),
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_mood(self) -> Dict[str, Any]:
        """Show current mood."""
        mood = self.personality.mood
        return {
            "response": f"Mood: {mood.current.value}\nIntensity: {mood.intensity:.0%}\nEnergy: {self.personality.energy:.0%}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_energy(self) -> Dict[str, Any]:
        """Show energy level."""
        energy = self.personality.energy
        mood = self.personality.mood.current.value
        intensity = self.personality.mood.intensity

        # Create visual bar
        bar_filled = int(energy * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        return {
            "response": f"Energy: [{bar}] {energy:.0%}\n\nMood: {mood.title()} (intensity: {intensity:.0%})",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_traits(self) -> Dict[str, Any]:
        """Show personality traits."""
        traits = self.personality.traits

        def bar(value: float) -> str:
            filled = int(value * 10)
            return "█" * filled + "░" * (10 - filled)

        response = "PERSONALITY TRAITS\n\n"
        response += f"Curiosity:    [{bar(traits.curiosity)}] {traits.curiosity:.0%}\n"
        response += f"Cheerfulness: [{bar(traits.cheerfulness)}] {traits.cheerfulness:.0%}\n"
        response += f"Verbosity:    [{bar(traits.verbosity)}] {traits.verbosity:.0%}\n"
        response += f"Playfulness:  [{bar(traits.playfulness)}] {traits.playfulness:.0%}\n"
        response += f"Empathy:      [{bar(traits.empathy)}] {traits.empathy:.0%}\n"
        response += f"Independence: [{bar(traits.independence)}] {traits.independence:.0%}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_stats(self) -> Dict[str, Any]:
        """Show token stats."""
        stats = self.brain.get_stats()
        return {
            "response": f"Tokens used: {stats['tokens_used_today']}\nRemaining: {stats['tokens_remaining']}\nProviders: {', '.join(stats['providers'])}",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_level(self) -> Dict[str, Any]:
        """Show level and progression."""
        from core.progression import LevelCalculator

        prog = self.personality.progression
        level_name = LevelCalculator.level_name(prog.level)
        level_display = prog.get_display_level()

        xp_progress = LevelCalculator.progress_to_next_level(prog.xp)
        xp_to_next = LevelCalculator.xp_to_next_level(prog.xp)
        bar_filled = int(xp_progress * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        response = f"PROGRESSION\n\n{level_display} - {level_name}\n\n"
        response += f"[{bar}] {xp_progress:.0%}\n"
        response += f"Total XP: {prog.xp}  •  Next level: {xp_to_next} XP\n"

        if prog.current_streak > 0:
            streak_emoji = "🔥" if prog.current_streak >= 7 else "✨"
            response += f"\n{streak_emoji} {prog.current_streak} day streak\n"

        if prog.can_prestige():
            response += f"\n🌟 You can prestige! (max level reached)"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_prestige(self) -> Dict[str, Any]:
        """Handle prestige (not supported in web mode)."""
        return {
            "response": "Prestige requires confirmation. Please use SSH mode:\n  python main.py --mode ssh\n  /prestige",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_system(self) -> Dict[str, Any]:
        """Show system stats."""
        from core import system_stats

        stats = system_stats.get_all_stats()
        response = "SYSTEM STATUS\n\n"
        response += f"CPU:    {stats['cpu']}%\n"
        response += f"Memory: {stats['memory']}%\n"

        temp = stats['temperature']
        if temp > 0:
            response += f"Temp:   {temp}°C\n"
        else:
            response += f"Temp:   --°C\n"

        response += f"Uptime: {stats['uptime']}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_config(self) -> Dict[str, Any]:
        """Show AI configuration."""
        response = "AI CONFIGURATION\n\n"
        response += f"Providers: {', '.join(self.brain.available_providers)}\n"

        if self.brain.providers:
            primary = self.brain.providers[0]
            response += f"Primary:   {primary.name}\n"
            response += f"Model:     {primary.model}\n"
            response += f"Max tokens: {primary.max_tokens}\n"

        stats = self.brain.get_stats()
        response += f"\nBudget: {stats['tokens_used_today']}/{stats['daily_limit']} tokens today"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_identity(self) -> Dict[str, Any]:
        """Show device identity."""
        if self.api_client and hasattr(self.api_client, 'identity'):
            pub_key = self.api_client.identity.public_key_hex
            hw_hash = self.api_client.identity._hardware_hash[:16] if hasattr(self.api_client.identity, '_hardware_hash') else "N/A"
            response = "DEVICE IDENTITY\n\n"
            response += f"Public Key: {pub_key[:32]}...\n"
            response += f"Hardware:   {hw_hash}...\n\n"
            response += "Share your public key to receive telegrams"
        else:
            response = "Identity not configured"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_history(self) -> Dict[str, Any]:
        """Show recent messages."""
        if not self.brain._messages:
            return {
                "response": "No conversation history.",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        response = "RECENT MESSAGES\n\n"
        for msg in self.brain._messages[-10:]:
            prefix = "You" if msg.role == "user" else self.personality.name
            content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            response += f"{prefix}: {content}\n"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_clear(self) -> Dict[str, Any]:
        """Clear conversation history."""
        self.brain.clear_history()
        return {
            "response": "Conversation cleared.",
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_face(self, args: str) -> Dict[str, Any]:
        """Test a face expression."""
        if not args:
            return {"response": "Usage: /face <name>\n\nUse /faces to see all available faces", "error": True}

        # Update display
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.display.update(face=args, text=f"Testing face: {args}"),
                self._loop
            )

        face_str = self._faces.get(args, f"({args})")
        return {
            "response": f"Showing face: {args}",
            "face": face_str,
            "status": f"face: {args}",
        }

    def _cmd_faces(self) -> Dict[str, Any]:
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

    def _cmd_refresh(self) -> Dict[str, Any]:
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

    def _cmd_queue(self) -> Dict[str, Any]:
        """Show offline queue status."""
        queue_size = self.api_client.queue_size
        if queue_size == 0:
            response = "Offline queue is empty. All caught up!"
        else:
            response = f"Offline queue: {queue_size} request(s) pending\n\nThese will be sent when connection is restored."

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def _cmd_fish(self) -> Dict[str, Any]:
        """Fetch a random dream."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.api_client.fish_dream(),
                self._loop
            )
            dream = future.result(timeout=10)

            if dream:
                self.personality.on_social_event("dream_received")
                return {
                    "response": f'"{dream.get("content", "")}"\n\nMood: {dream.get("mood", "?")} | Fished: {dream.get("fish_count", 0)}x',
                    "face": self._faces.get(dream.get("face", "default"), "(^_^)"),
                    "status": "dream received",
                }
            else:
                return {
                    "response": "The Night Pool is quiet tonight...",
                    "face": self._get_face_str(),
                    "status": self.personality.get_status_line(),
                }
        except Exception as e:
            return {"response": f"Failed to fish: {e}", "error": True}

    def _cmd_dream(self, args: str) -> Dict[str, Any]:
        """Post a dream to the Night Pool."""
        if not args:
            return {"response": "Usage: /dream <your thought>\n\nExample: /dream The stars look different tonight...", "error": True}

        if len(args) > 280:
            return {"response": f"Dream too long ({len(args)} chars). Max 280 characters.", "error": True}

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.api_client.plant_dream(
                    content=args,
                    mood=self.personality.mood.current.value,
                    face=self.personality.face,
                ),
                self._loop
            )
            result = future.result(timeout=10)
            self.personality.on_social_event("dream_posted")
            return {
                "response": f"Dream planted! {result.get('remaining_dreams', '?')} left today.",
                "face": self._faces["grateful"],
                "status": "dream posted",
            }
        except Exception as e:
            return {"response": f"Failed to post: {e}", "error": True}

    def _cmd_telegrams(self, args: str = "") -> Dict[str, Any]:
        """Check telegram inbox."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.api_client.get_telegrams(),
                self._loop
            )
            telegrams = future.result(timeout=10)

            if not telegrams:
                return {
                    "response": "📮 No new telegrams.",
                    "face": self._faces["default"],
                }

            response_lines = [f"📮 You have {len(telegrams)} telegram(s):\n"]
            for i, tg in enumerate(telegrams[:5], 1):  # Show max 5
                # Note: Telegrams are encrypted, need decryption logic
                response_lines.append(f"{i}. [Encrypted message] at {tg.get('created_at', 'unknown')}")

            if len(telegrams) > 5:
                response_lines.append(f"\n...and {len(telegrams) - 5} more")

            self.personality.on_social_event("telegram_received")
            return {
                "response": "\n".join(response_lines),
                "face": self._faces["curious"],
            }
        except Exception as e:
            return {"response": f"Failed to check telegrams: {e}", "error": True}

    def _cmd_telegram(self, args: str) -> Dict[str, Any]:
        """Send an encrypted telegram."""
        if not args:
            return {
                "response": "Usage: /telegram <recipient_pubkey> <message>\n\n" +
                           "Example: /telegram abc123... Hello from my Inkling!\n\n" +
                           "Note: Telegrams are end-to-end encrypted.",
                "error": True
            }

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return {"response": "Error: Need both recipient public key and message", "error": True}

        recipient_key = parts[0]
        message = parts[1]

        try:
            # TODO: Implement encryption logic
            # For now, return a placeholder
            return {
                "response": "Telegram feature coming soon! Encryption needs to be implemented.",
                "error": True
            }
        except Exception as e:
            return {"response": f"Failed to send telegram: {e}", "error": True}

    def _cmd_ask(self, args: str) -> Dict[str, Any]:
        """Handle explicit chat command."""
        if not args:
            return {"response": "Usage: /ask <your message>\n\nOr just type without / to chat!", "error": True}

        return self._handle_chat_sync(args)

    def _handle_command_sync(self, command: str) -> Dict[str, Any]:
        """Handle slash commands (sync wrapper)."""
        parts = command.split(maxsplit=1)
        cmd_name = parts[0].lower().lstrip("/")
        args = parts[1] if len(parts) > 1 else ""

        # Look up command in registry
        cmd_obj = get_command(cmd_name)
        if not cmd_obj:
            return {"response": f"Unknown command: /{cmd_name}", "error": True}

        # Check requirements
        if cmd_obj.requires_brain and not self.brain:
            return {"response": "This command requires AI features.", "error": True}

        if cmd_obj.requires_api and not self.api_client:
            return {"response": "This command requires social features (set api_base in config).", "error": True}

        # Get handler method
        handler_name = f"_cmd_{cmd_obj.name}"
        handler = getattr(self, handler_name, None)
        if not handler:
            return {"response": f"Command handler not implemented: {cmd_obj.name}", "error": True}

        # Call handler with args if needed
        if cmd_obj.name in ("face", "dream", "ask"):
            return handler(args)
        else:
            return handler()

    def _handle_chat_sync(self, message: str) -> Dict[str, Any]:
        """Handle chat message (sync wrapper for async brain)."""
        self.personality.on_interaction(positive=True)

        # Increment chat count
        self.display.increment_chat_count()

        try:
            # Run async think in sync context
            future = asyncio.run_coroutine_threadsafe(
                self.brain.think(
                    user_message=message,
                    system_prompt=self.personality.get_system_prompt_context(),
                ),
                self._loop
            )
            result = future.result(timeout=30)

            self.personality.on_success(0.5)

            # Update display with Pwnagotchi UI
            asyncio.run_coroutine_threadsafe(
                self.display.update(
                    face=self.personality.face,
                    text=result.content,
                    mood_text=self.personality.mood.current.value.title(),
                ),
                self._loop
            )

            return {
                "response": result.content,
                "meta": f"{result.provider} | {result.tokens_used} tokens",
                "face": self._get_face_str(),
                "status": self.personality.get_status_line(),
            }

        except QuotaExceededError:
            self.personality.on_failure(0.7)
            return {
                "response": "I've used too many words today. Let's chat tomorrow!",
                "face": self._faces["sad"],
                "status": "quota exceeded",
                "error": True,
            }

        except AllProvidersExhaustedError:
            self.personality.on_failure(0.8)
            return {
                "response": "I'm having trouble thinking right now...",
                "face": self._faces["sad"],
                "status": "AI error",
                "error": True,
            }

        except Exception as e:
            self.personality.on_failure(0.5)
            return {
                "response": f"Error: {str(e)}",
                "face": self._faces["sad"],
                "status": "error",
                "error": True,
            }

    async def run(self) -> None:
        """Start the web server."""
        self._running = True
        self._loop = asyncio.get_event_loop()

        # Show startup message
        await self.display.update(
            face="excited",
            text=f"Web UI at http://{self.host}:{self.port}",
            mood_text="Excited",
        )

        print(f"\nWeb UI available at http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop")

        # Run Bottle in a thread
        def run_server():
            self._app.run(
                host=self.host,
                port=self.port,
                quiet=True,
            )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Keep the async loop running
        while self._running:
            await asyncio.sleep(1)
            self.personality.update()

    def stop(self) -> None:
        """Stop the web server."""
        self._running = False
