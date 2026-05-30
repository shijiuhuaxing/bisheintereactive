class RealtimeClient {
    constructor({ url, onEvent, onStatus } = {}) {
        this.url = url;
        this.onEvent = onEvent || (() => {});
        this.onStatus = onStatus || (() => {});
        this.socket = null;
        this.connected = false;
        this.sessionId = '';
    }

    async connect() {
        if (this.connected && this.socket?.readyState === WebSocket.OPEN) {
            return true;
        }

        return new Promise((resolve) => {
            try {
                this.socket = new WebSocket(this.url);
            } catch (error) {
                this.onStatus('error', error);
                resolve(false);
                return;
            }

            const timeout = setTimeout(() => {
                this.close();
                resolve(false);
            }, 3500);

            this.socket.onopen = () => {
                clearTimeout(timeout);
                this.connected = true;
                this.onStatus('open');
                resolve(true);
            };

            this.socket.onmessage = (message) => {
                try {
                    const event = JSON.parse(message.data);
                    if (event.type === 'session.ready') {
                        this.sessionId = event.session_id || '';
                    }
                    this.onEvent(event);
                } catch (error) {
                    this.onStatus('message-error', error);
                }
            };

            this.socket.onerror = (error) => {
                this.onStatus('error', error);
            };

            this.socket.onclose = () => {
                clearTimeout(timeout);
                this.connected = false;
                this.onStatus('close');
            };
        });
    }

    close() {
        if (this.socket) {
            try {
                this.socket.close();
            } catch (error) {
                void error;
            }
        }
        this.socket = null;
        this.connected = false;
    }

    async sendAudioTurn({ audioBlob, frameBlob = null, audioFormat = 'wav', turnId = '' } = {}) {
        const connected = await this.connect();
        if (!connected || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
            throw new Error('实时 WebSocket 未连接');
        }

        const payload = {
            type: 'audio.final',
            turn_id: turnId || RealtimeClient.createTurnId(),
            audio_format: audioFormat,
            audio_base64: await RealtimeClient.blobToBase64(audioBlob),
        };

        if (frameBlob) {
            payload.image_base64 = await RealtimeClient.blobToBase64(frameBlob);
        }

        this.socket.send(JSON.stringify(payload));
        return payload.turn_id;
    }

    async sendFaceSnapshot(frameBlob) {
        const connected = await this.connect();
        if (!connected || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return false;
        }
        this.socket.send(JSON.stringify({
            type: 'face.snapshot',
            turn_id: RealtimeClient.createTurnId(),
            image_base64: await RealtimeClient.blobToBase64(frameBlob),
        }));
        return true;
    }

    static createTurnId() {
        return `turn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    static blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const result = String(reader.result || '');
                resolve(result.includes(',') ? result.split(',', 2)[1] : result);
            };
            reader.onerror = () => reject(reader.error || new Error('Blob 转换失败'));
            reader.readAsDataURL(blob);
        });
    }
}

window.RealtimeClient = RealtimeClient;
