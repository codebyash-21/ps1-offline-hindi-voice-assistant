# System Architecture

The offline Hindi voice assistant follows a simple on-device pipeline:

Microphone Input
→ Offline Speech Recognition (Hindi ASR)
→ Intent Detection (rule-based)
→ Response Selection
→ Offline Text-to-Speech (Hindi TTS)
→ Speaker Output

All components run locally on the device without internet connectivity.
