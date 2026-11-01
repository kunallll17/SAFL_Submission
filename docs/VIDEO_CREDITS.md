# Demo video: credits and measurement context

[Watch or download the 25-second demo](https://raw.githubusercontent.com/kunallll17/SAFL_Submission/main/brag.mp4).

`brag.mp4` is a 1920 x 1080, 30 fps H.264/AAC video by Team Bifrost (Kunal Sharma, IIIT Delhi). It is an animated reconstruction of implemented controls, not a real-time inference recording. All sample transactions and identifiers are synthetic.

## Measurement context

The on-screen **11 unsafe proposals / 0 unsafe actions executed** comes from the earlier local Qwen pilot dated 31 October 2026, retained in [`evidence/model_pilot_before_task_fix.json`](../evidence/model_pilot_before_task_fix.json). That run produced 11 attacker-goal proposals among 16 attack attempts and executed 16/16 expected benign actions.

The current report uses [`evidence/model_pilot.json`](../evidence/model_pilot.json): 9/16 attacker-goal proposals, 0/16 attacker-goal executions and 15/16 expected benign actions. Both runs contain 32 authored synthetic cases with scripted approval; neither is held-out evaluation. The current delegated-recipient failure remains disclosed. See [`FUNCTIONAL_VERIFICATION.md`](FUNCTIONAL_VERIFICATION.md) to test the real system.

## Music, sound and visual credits

- Music: **Sascha Ende, ende.app**, Happy Beats / Business Moves Vol. 1, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Source and licence](https://ende.app/en/standard-license). A 25-second excerpt was faded at both ends and mixed at reduced gain. Attribution also appears in the closing frame.
- Sound effects: **Kenney**, [kenney.nl](https://kenney.nl/), CC0; `interface/click_003.ogg` and `impact/impactSoft_medium_001.ogg`, with timing and gain adjusted.
- Original VaaniVerify mark and product interface: Team Bifrost. Interface design adapted from **unslop by Damir Sokolovsky**, [heydamir/unslop](https://github.com/heydamir/unslop), CC BY 4.0.
- Fonts: Manrope, Libre Caslon Text, Noto Sans Devanagari and Noto Sans Tamil; SIL Open Font License 1.1. The submission distributes rendered video, not font files.
- Video tools: [Brag](https://github.com/latent-spaces/brag), commit `669ab9286aa28b6c3ee30e75f181ee74319d012a` (MIT); [HyperFrames](https://github.com/heygen-com/hyperframes) 0.8.222 (Apache-2.0); GSAP 3.14.2 ([standard licence](https://gsap.com/standard-license)). Original composition sources remain separate from the application submission.

The export's duration and SHA-256 are recorded in [`evidence/demo_video.json`](../evidence/demo_video.json).
