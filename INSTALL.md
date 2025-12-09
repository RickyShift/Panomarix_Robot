
# Fluid Asterix - Installation & Setup Guide

This guide details how to set up the Fluid Asterix environment on a new machine.

## Prerequisites

1.  **Hardware**
    - Windows PC (Host)
    - Elmo Robot V2 (Target)
    - WiFi Connection (for Robot) + USB Tethering (for Internet)

2.  **Software**
    - Python 3.10+
    - Git
    - VS Code (Recommended)
    - `ssh` client (usually built-in)

## 1. Network Configuration (CRITICAL)

The robot requires a specific network setup to allow simultaneous Internet access (for LLM/TTS) and Robot control.

1.  **Connect USB Tethering**: Connect your Phone via USB and enable "USB Tethering".
2.  **Connect Robot WiFi**: Connect your PC's WiFi to the Robot's Access Point.
3.  **Configure Metrics** (Force Internet via USB, Robot via WiFi):
    - **Step A**: Open "Network Connections" (Control Panel -> Network and Sharing Center -> Change adapter settings).
    - **Step B** (Internet Adapter - Ethernet X):
        - Right-click -> Properties -> IPv4 -> Advanced.
        - Uncheck "Automatic metric".
        - Set Interface Metric to **10** (High Priority).
    - **Step C** (Robot Adapter - WiFi):
        - Right-click -> Properties -> IPv4 -> Advanced.
        - Uncheck "Automatic metric".
        - Set Interface Metric to **500** (Low Priority).

## 2. Installation

1.  **Clone Repository**
    ```powershell
    git clone https://github.com/RickyShift/Panomarix_Robot.git
    cd Panomarix_Robot
    ```

2.  **Install Dependencies**
    ```powershell
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is missing, install manually: `netifaces requests paramiko pygame edge-tts speech_recognition python-dotenv`)*

3.  **Environment Variables**
    - Create a `.env` file in the root.
    - Add your Gemini API Key:
        ```
        GOOGLE_API_KEY=your_api_key_here
        ```

## 3. Running the Agent

1.  **Find the Robot**
    ```powershell
    python find_elmo_ip.py
    ```
    *Note the IP address found (e.g., 192.168.0.107).*

2.  **Launch Fluid Asterix**
    ```powershell
    python fluid_elmo.py <ROBOT_IP>
    ```
    *Example: `python fluid_elmo.py 192.168.0.107`*

3.  **Interact**
    - Press **ENTER** to Start Recording.
    - Speak.
    - Press **ENTER** to Stop.

## Troubleshooting

- **"No such file" error**: Ensure `audio_handler.py` points to `/home/idmind/elmo-v2/src/static/sounds/mic.wav`.
- **"No audio was received"**: Ensure script uses `play_sound` (not `play_audio`).
- **Ping fails**: Check WiFi connection and Metrics (Step 1).
