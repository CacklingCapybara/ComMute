# 📄 Product Requirements Document (PRD)

## 🛠 Product Name
**ComMute**

---

## 📌 Purpose

**ComMute** is a local application designed to detect commercials in a live TV feed and automatically mute the television during those commercials. It resumes audio playback when the live program returns. The app runs inside a Docker container, connects to a video capture device, analyzes incoming streams for commercial patterns, and controls audio via a USB infrared (IR) blaster.

---

## 🎯 Goals

### Short-Term
- Detect TV commercials in real-time using video and/or audio cues.
- Mute the TV using an IR blaster during commercial breaks.
- Unmute the TV once the live program resumes.

### Long-Term
- Maintain minimal false positives/negatives in ad detection.
- Improve commercial detection reliability through smarter heuristics or optional AI integration.
- Ensure seamless and silent operation as a background utility.

---

## 👥 Target Audience
- Primary: The developer/creator (yourself).
- Secondary (potentially): Other tech-savvy users interested in blocking or muting TV ads.

---

## 🧩 Features

### 1. **Input Handling**
- Interface with a video capture device (e.g., USB HDMI capture card).
- Decode and process live video/audio stream in real time.

### 2. **Commercial Detection Engine**
- Detect commercials using one or more of the following techniques:
  - **Audio Fingerprinting:** Compare audio snippets to known commercial fingerprints.
  - **Volume Pattern Detection:** Detect volume spikes or repetitive loud audio patterns common in ads.
  - **Visual Pattern Detection:** Detect scene changes, lower-third banners, or rapid edits typical of commercials.
  - **ML Model (Future):** Train a model to identify commercial segments.

### 3. **Mute/Unmute Control**
- Send mute/unmute commands via USB IR blaster to the TV.
- Ensure IR blaster is configured for the correct TV model or supports learning commands.

### 4. **Containerization**
- Runs entirely in a self-contained **Docker container**.
- Lightweight, minimal dependencies.
- Exposes a local web interface or CLI for logs/status (optional).

### 5. **Logging & Monitoring**
- Real-time logging of:
  - Detected commercial start/end times.
  - Mute/unmute commands sent.
  - Detection confidence (if applicable).
- Optional: Store logs for post-analysis/debugging.

---

## 🧪 Success Metrics
- >95% accuracy in muting during commercial breaks.
- <5% false positives (e.g., muting during regular program).
- Consistent uptime and performance over long viewing sessions.
- Responsive mute/unmute latency (under 1 second from detection to IR command).

---

## 🧱 Technical Stack

| Component                  | Tech / Notes                              |
|---------------------------|-------------------------------------------|
| Containerization          | Docker                                    |
| Video Input               | HDMI capture via ffmpeg / GStreamer       |
| Commercial Detection      | Python, OpenCV, pydub, or ML-based tools  |
| IR Control                | LIRC (Linux Infrared Remote Control), USB IR blaster |
| Optional Interface        | Local web app (Flask or Node.js) or CLI   |
| Logging                   | Local files, logrotate-compatible         |

---

## 👤 User Roles

- **Admin**: The only user role. Can:
  - Start/stop the container.
  - Configure video input and IR settings.
  - View logs.
  - Tweak detection parameters.

---

## ⚙️ Constraints

- The app will run locally on a system with:
  - USB video capture device.
  - USB IR blaster.
  - Docker installed.
- No need for external network access.
- Must be lightweight enough to run on a small Linux box or Raspberry Pi (optional goal).

---

## 🚧 Open Questions / To Be Defined

- Do you want to allow manual override (e.g., force mute/unmute)?
- Should there be an auto-update mechanism for commercial fingerprint database (if used)?
- Any plans to open-source it or keep it private?
- What level of configurability should be exposed to the user (e.g., mute duration buffer, detection sensitivity)?

---

## 📌 Version 1.0 Milestones

| Milestone                           | Status |
|------------------------------------|--------|
| Video capture integration          | ☐      |
| Basic mute/unmute via IR blaster   | ☐      |
| Naive commercial detection logic   | ☐      |
| Docker containerization            | ☐      |
| Logging and monitoring             | ☐      |
