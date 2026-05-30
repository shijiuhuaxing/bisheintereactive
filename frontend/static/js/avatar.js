window.AvatarModule = (() => {
    const state = {
        ready: false,
        threeReady: false,
        loading3d: false,
        speaking: false,
        currentEmotion: '平静',
        frame: 0,
        startedAt: 0,
        display: null,
        stage: null,
        mouth: null,
        label: null,
        head: null,
        headLoadError: null,
    };

    const emotionClassMap = {
        '开心': 'happy',
        '难过': 'sad',
        '疲惫': 'tired',
        '感激': 'grateful',
        '平静': 'calm',
    };

    const moodMap = {
        '开心': 'happy',
        '难过': 'sad',
        '疲惫': 'sad',
        '感激': 'happy',
        '平静': 'neutral',
    };

    async function init() {
        state.stage = document.getElementById('talkingHeadStage');
        state.display = document.getElementById('avatarDisplay');
        state.mouth = state.display?.querySelector('.mouth') || null;
        state.label = state.display?.querySelector('.avatar-label') || null;
        state.ready = Boolean(state.display && state.mouth);

        if (state.ready) {
            state.display.classList.add('avatar-ready');
            setEmotion(state.currentEmotion);
        }

        if (state.stage && !state.loading3d && !state.threeReady) {
            state.stage.closest('.avatar-stage')?.classList.remove('avatar-load-failed');
            loadTalkingHead().catch((error) => {
                state.headLoadError = error;
                state.stage?.closest('.avatar-stage')?.classList.add('avatar-load-failed');
                console.warn('TalkingHead 3D avatar unavailable, using DOM fallback:', error);
            });
        }
        return state.ready;
    }

    async function loadTalkingHead() {
        state.loading3d = true;
        const { TalkingHead } = await import('../vendor/talkinghead/modules/talkinghead.mjs');
        state.head = new TalkingHead(state.stage, {
            cameraView: 'upper',
            cameraDistance: 0,
            cameraY: 0.1,
            cameraRotateEnable: false,
            modelPixelRatio: 1,
            lightAmbientIntensity: 2,
            lightDirectIntensity: 28,
            lipsyncLang: 'en',
            avatarMood: 'neutral',
        });

        const candidates = ['static/assets/avatars/brunette.glb'];

        let lastError = null;
        for (const url of candidates) {
            try {
                await state.head.showAvatar({
                    url,
                    body: 'F',
                    avatarMood: moodMap[state.currentEmotion] || 'neutral',
                    lipsyncLang: 'en',
                    avatarIdleEyeContact: 0.45,
                    avatarIdleHeadMove: 0.35,
                    avatarSpeakingEyeContact: 0.7,
                    avatarSpeakingHeadMove: 0.45,
                });
                state.threeReady = true;
                state.stage.classList.add('ready');
                state.stage.closest('.avatar-stage')?.classList.add('has-3d');
                state.stage.closest('.avatar-stage')?.classList.remove('avatar-load-failed');
                setEmotion(state.currentEmotion);
                return true;
            } catch (error) {
                lastError = error;
            }
        }
        throw lastError || new Error('No available avatar model');
    }

    function setEmotion(emotion = '平静') {
        if (!state.ready) {
            init();
        }
        state.currentEmotion = emotionClassMap[emotion] ? emotion : '平静';

        if (state.display) {
            state.display.classList.remove('happy', 'sad', 'tired', 'calm', 'grateful');
            state.display.classList.add(emotionClassMap[state.currentEmotion]);
            state.display.dataset.emotion = state.currentEmotion;
        }

        if (state.label) {
            state.label.textContent = `虚拟陪伴形象 · ${state.currentEmotion}`;
        }

        if (state.threeReady && state.head) {
            try {
                state.head.setMood(moodMap[state.currentEmotion] || 'neutral');
                state.head.lookAtCamera?.(500);
            } catch (error) {
                console.warn('TalkingHead mood update failed:', error);
            }
        }
    }

    function startSpeaking() {
        if (!state.ready) {
            init();
        }
        if (!state.ready || state.speaking) {
            return;
        }
        state.speaking = true;
        state.startedAt = performance.now();
        state.display?.classList.add('speaking');
        state.head?.makeEyeContact?.(900);
        tickMouth();
    }

    function stopSpeaking() {
        state.speaking = false;
        if (state.frame) {
            cancelAnimationFrame(state.frame);
            state.frame = 0;
        }
        state.display?.classList.remove('speaking');
        resetMouth();
        resetThreeMouth();
    }

    function tickMouth() {
        if (!state.speaking) {
            return;
        }

        const elapsed = performance.now() - state.startedAt;
        const period = 125 + 22 * Math.sin(elapsed / 620);
        const phase = (elapsed % period) / period;
        const pulse = Math.pow(Math.sin(Math.PI * phase), 1.22);
        const micro = 0.08 * Math.sin(elapsed / 190) + 0.04 * Math.sin(elapsed / 430);
        const open = Math.max(0.04, Math.min(1, 0.12 + pulse * 0.74 + micro));
        const syllable = Math.floor(elapsed / period) % 4;

        applyDomMouth(open, syllable);
        applyThreeMouth(open, syllable);
        state.frame = requestAnimationFrame(tickMouth);
    }

    function applyDomMouth(open, syllable) {
        if (!state.mouth) {
            return;
        }
        const width = [76, 58, 70, 64][syllable];
        const height = [24, 34, 18, 28][syllable] + open * 38;
        const radius = syllable === 1 ? '50% 50% 54% 54%' : '0 0 70px 70px';
        state.mouth.style.width = `${width}px`;
        state.mouth.style.height = `${height}px`;
        state.mouth.style.borderRadius = radius;
        state.mouth.style.transform = 'translateX(-50%) scaleY(1)';
    }

    function applyThreeMouth(open, syllable) {
        if (!state.threeReady || !state.head) {
            return;
        }
        const set = (name, value, ms = 35) => {
            try {
                state.head.setFixedValue?.(name, value, ms);
                state.head.setValue?.(name, value, ms);
            } catch (error) {
                void error;
            }
        };
        set('mouthOpen', Math.min(1, open * 0.82));
        set('jawOpen', Math.min(0.8, open * 0.58));
        set('viseme_aa', syllable === 0 ? open * 0.75 : 0);
        set('viseme_O', syllable === 1 ? open * 0.42 : 0);
        set('viseme_E', syllable === 2 ? open * 0.62 : 0);
        set('viseme_I', syllable === 3 ? open * 0.5 : 0);
    }

    function resetMouth() {
        if (!state.mouth) {
            return;
        }
        state.mouth.style.width = '';
        state.mouth.style.height = '';
        state.mouth.style.borderRadius = '';
        state.mouth.style.transform = '';
    }

    function resetThreeMouth() {
        if (!state.threeReady || !state.head) {
            return;
        }
        ['mouthOpen', 'jawOpen', 'viseme_aa', 'viseme_O', 'viseme_E', 'viseme_I'].forEach((name) => {
            try {
                state.head.setFixedValue?.(name, 0, 80);
                state.head.setValue?.(name, 0, 80);
            } catch (error) {
                void error;
            }
        });
    }

    function attachAudioElement(audio) {
        if (!audio) {
            return;
        }
        audio.addEventListener('playing', startSpeaking, { once: true });
        audio.addEventListener('ended', stopSpeaking, { once: true });
        audio.addEventListener('pause', stopSpeaking, { once: true });
        audio.addEventListener('error', stopSpeaking, { once: true });
    }

    return {
        init,
        setEmotion,
        startSpeaking,
        stopSpeaking,
        attachAudioElement,
    };
})();
