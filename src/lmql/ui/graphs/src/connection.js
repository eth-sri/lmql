class GraphState {
    constructor(file) {
        this.ws = null;
        this.file = file;

        this.statusListeners = [];
        this.dataListeners = [];
    }

    addStatusListener(listener) {
        this.statusListeners.push(listener);
    }

    removeStatusListener(listener) {
        this.statusListeners = this.statusListeners.filter(l => l !== listener);
    }

    notifyStatusListeners(status) {
        this.statusListeners.forEach(l => l(status));
    }

    addDataListener(listener) {
        this.dataListeners.push(listener);
    }

    removeDataListener(listener) {
        this.dataListeners = this.dataListeners.filter(l => l !== listener);
    }

    notifyDataListeners(data) {
        this.dataListeners.forEach(l => l(data));
    }

    tryReconnect() {
        if (this.ws === null) {
            console.log("Trying to reconnect");
            this.connect();
            window.setTimeout(() => this.tryReconnect(), 1000);
        } 
    }

    connect() {
        this.ws = new WebSocket("ws://localhost:8000/watch/" + this.file);
        this.ws.onopen = () => {
            this.notifyStatusListeners("open");
        };
        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.notifyDataListeners(data);
            } catch (e) {
                console.error(e);
            }
        };
        this.ws.onclose = () => {
            this.notifyStatusListeners("closed");
            this.ws = null;
            this.tryReconnect();
        };
    }

    disconnect() {
        this.ws.close();
    }
}

let CONNECTIONS = {}

export function graph(file) {
    if (!CONNECTIONS[file]) {
        CONNECTIONS[file] = new GraphState(file);
        CONNECTIONS[file].connect();
    }
    return CONNECTIONS[file];
}