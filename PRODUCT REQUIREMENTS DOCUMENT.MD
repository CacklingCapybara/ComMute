

# **Product Requirements Document (PRD): ComMute**

## 1. Overview

**Product Name:** ComMute
**Owner:** [Your Name / Product Manager]
**Version:** 1.0
**Last Updated:** [Date]

### **Summary**

ComMute is an application that detects and automatically mutes TV commercials in real time. It does this by continuously monitoring live TV audio through a connected input device (e.g., line-in, HDMI audio, or microphone), processing it through a sound fingerprinting engine (powered by a `soundfingerprinting.emy` Docker container), and comparing it against a database of known commercial audio fingerprints. When a match is detected, ComMute mutes the audio output until the commercial ends, then unmutes when normal programming resumes.

---

## 2. Problem Statement

Viewers frequently experience repetitive, loud, or unwanted commercials when watching live TV or streaming through set-top boxes. Traditional DVRs or streaming platforms sometimes offer “ad-skip” features, but they are limited or unavailable in real-time broadcasts.

**ComMute** provides a universal solution by detecting commercials based solely on their audio signature — independent of broadcast source or platform.

---

## 3. Goals & Objectives

### **Primary Goals**

* Detect and mute commercials in real time with USB RF blaster with high accuracy using `soundfingerprinting.emy` docker container
* Use the JSON API included in `soundfingerprinting.emy` docker container for fast and easy interaction
* Automatically unmute when regular programming resumes.
* Allow the user to view mute history and performance statistics.

### **Secondary Goals**

* Enable continuous improvement by collecting anonymized fingerprint data (optional user consent).
* Provide easy integration with various input and output devices.
* Include an easy-to-use method that will record current audio and save to a file location so that it can be later fingerprinted

### **Non-Goals**

* ComMute does not skip or replace commercials (only mutes).
* ComMute does not perform any video analysis in its initial release.
Future revisions may expand detection capabilities to include video-based features such as:

Detection of channel logos, network watermarks, or advertiser logos in corners.

Analysis of scene cuts, rapid scene changes, or color histogram patterns typical of ad transitions.

Combining video and audio signatures for improved accuracy and faster detection.

---

## 4. Target Users

| User Type               | Description                                                        | Needs                                  |
| ----------------------- | ------------------------------------------------------------------ | -------------------------------------- |
| **Home viewers**        | Users watching cable or satellite TV through a smart device or PC. | Avoid loud or repetitive commercials.  |
| **Tech enthusiasts**    | Users who automate home entertainment setups.                      | Integrate ComMute into media centers.  |
| **Accessibility users** | Users sensitive to loud or flashing ads.                           | Reduce exposure and noise sensitivity. |

---

## 5. Key Features & Requirements

### **5.1 Functional Requirements**

| ID | Requirement                                                                            | Priority |
| -- | -------------------------------------------------------------------------------------- | -------- |
| F1 | Capture continuous audio input from a connected device (mic, HDMI, etc.)               | High     |
| F2 | Send live audio samples to the `soundfingerprinting.emy` Docker container for analysis | High     |
| F3 | Compare generated fingerprints against a database of known commercials                 | High     |
| F4 | Trigger mute/unmute commands when matches are found or end                             | High     |
| F5 | Maintain a rolling buffer for context (e.g., last 30 seconds of audio)                 | Medium   |
| F6 | Display mute events and stats (e.g., “Commercial muted for 1m 20s”)                    | Medium   |
| F7 | Support manual override (user can mute/unmute manually)                                | Low      |
| F8 | Provide configuration options (input device, threshold, database path, etc.)           | Medium   |

---

### **5.2 Technical Requirements**

| ID | Component                       | Requirement                                                                                               |
| -- | ------------------------------- | --------------------------------------------------------------------------------------------------------- |
| T1 | **Audio Input**                 | Must support PCM audio stream capture (44.1 kHz or 48 kHz).                                               |
| T2 | **Sound Fingerprinting Engine** | Use the open-source `soundfingerprinting` framework via Docker (`soundfingerprinting.emy` image).         |
| T3 | **Commercial Database**         | Maintain a local or remote store of commercial fingerprints (e.g., SQLite, PostgreSQL).                   |
| T4 | **Matching Logic**              | Identify commercial segments by comparing fingerprint similarity thresholds (configurable, default 0.85). |
| T5 | **Mute Control**                | Use OS-level or device-level mute API (e.g., ALSA, CoreAudio, WASAPI).                                    |
| T6 | **Latency Target**              | Detect and mute commercials within ≤3 seconds of start.                                                   |
| T7 | **System Compatibility**        | Initial target: Linux / Windows desktop. Future: Raspberry Pi, smart TV integration.                      |
| T8 | **Performance**                 | Should run continuously with <10% CPU on standard hardware.                                               |

---

## 6. User Experience (UX)

### **UI Wireframe Overview**

* **Dashboard**

  * Status indicator: Listening / Muted / Idle
  * Recent activity log: “Commercial detected on Channel X — Muted for 1:20”
  * Configuration panel (input device, sensitivity, DB path)
* **Settings**

  * Audio device selection
  * Matching threshold slider
  * Logging & debugging options
  * Privacy / telemetry toggle

### **Notifications**

* Small overlay (optional): “ComMute muted a commercial”
* Desktop/system tray icon to show status

---

## 7. Architecture Overview

**Data Flow:**

```
[Audio Input Device] 
   ↓
[Audio Capture Service]
   ↓
[Soundfingerprinting.emy Docker Container]
   ↓
[Fingerprint Match Engine]
   ↓
[Decision Logic → Mute/Unmute Controller]
   ↓
[System Audio API]
```

**Key Components:**

* `comute-core`: Audio capture, streaming, and control logic
* `comute-docker-client`: Interface for sending samples to the Docker container
* `comute-ui`: Frontend (Electron or web dashboard)

---

## 8. Metrics for Success

| Metric                            | Goal                                             |
| --------------------------------- | ------------------------------------------------ |
| **Commercial Detection Accuracy** | ≥ 90% true positives                             |
| **False Positive Rate**           | ≤ 5%                                             |
| **Detection Latency**             | ≤ 3 seconds                                      |


---

## 10. Future Enhancements

* Cloud-based fingerprint database updates
* Machine learning–based ad detection (in addition to fingerprints)


