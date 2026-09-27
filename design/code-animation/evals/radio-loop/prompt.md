---
max_turns: 150
timeout_seconds: 2700
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
tags: [music, loop]
expected_outcome: The pipeline analyses track.wav (100 BPM, 7.2 s), builds a seamless loop whose motion lands on the beat, checks the seam with qa --loop, and delivers a looping GIF plus an MP4 with the track muxed in.
---

Our late-night radio show is called Night Signal. Make a seamless looping GIF that pulses with track.wav, and an MP4 version with the sound.
