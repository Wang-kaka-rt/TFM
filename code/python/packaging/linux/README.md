# Strudel Voice for Linux

First run, in this directory:

```bash
chmod +x install.sh strudel-voice
./install.sh
```

Then start the application:

```bash
./strudel-voice
```

The browser opens at `http://127.0.0.1:8787/`. The release bundles the Strudel
interface, Python runtime, ASR dependencies, and (when built with
`--bundle-model base`) a local Whisper model cache. It still requires a Linux
desktop session with a visible PipeWire/PulseAudio microphone input.
