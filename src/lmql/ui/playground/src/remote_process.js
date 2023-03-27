import io from "socket.io-client"

export class RemoteProcessConnection {
    constructor() {
        const PORT = process.env.REACT_APP_SOCKET_PORT || 3004

        this.socket = io.connect(':' + PORT);
        this.socket.on('connect', () => {
            this.socket.on('app-result', data => {
                this.onAppResult(data)
            })
            this.socket.on('app-pid', pid => {
                this.remotePid = pid.pid;
            })
            this.socket.on('app-error', (error) => {
                this.onAppError(error)
            })
            this.socket.on('app-exit', (error) => {
                this.onAppExit(error)
            })

            this.connectionListeners.forEach(listener => {
                listener(true)
            })
            this.statusListeners.forEach(listener => {
                listener({status: "idle"})
            })

            // disconnect
            this.socket.on('disconnect', () => {
                this.connectionListeners.forEach(listener => {
                    listener(false)
                })
            })
        });

        // console listener log(data)
        this.consoleListeners = [];
        // renderer {add_result(result), clear_results()}
        this.renderers = [];
        // status listener {onStatusChange(status)}
        this.statusListeners = [];
        // connection listener listener(connected)
        this.connectionListeners = [];
        // run listener listener()
        this.runListeners = [];

        this.remotePid = null;

        this.status = {
            connected: false,
            label: ""
        }

        this.addStatusListener((status) => {
            if (status.status === "idle") {
                this.killCounter = 0;
                this.status = Object.assign({}, status);
            }
        })
    }

    on(event, listener) {
        if (event === "console") {
            this.addConsoleListener(listener)
        } else if (event === "status") {
            this.addStatusListener(listener)
        } else if (event === "connection") {
            this.addConnectionListener(listener)
        } else if (event === "render") {
            this.addRenderer(listener)
        } else if (event === "run") {
            this.addRunListener(listener)
        } else {
            console.error("Unknown event", event)
        }
    }

    remove(event, listener) {
        if (event === "console") {
            this.consoleListeners = this.consoleListeners.filter(l => l !== listener)
        } else if (event === "status") {
            this.statusListeners = this.statusListeners.filter(l => l !== listener)
        } else if (event === "connection") {
            this.connectionListeners = this.connectionListeners.filter(l => l !== listener)
        } else if (event === "render") {
            this.renderers = this.renderers.filter(l => l !== listener)
        } else if (event === "run") {
            this.runListeners = this.runListeners.filter(l => l !== listener)
        } else {
            console.error("Unknown event", event)
        }
    }

    addRunListener(listener) {
        this.runListeners.push(listener);
    }

    addConnectionListener(listener) {
        this.connectionListeners.push(listener);
    }

    addStatusListener(listener) {
        this.statusListeners.push(listener);
    }

    addConsoleListener(listener) {
        this.consoleListeners.push(listener);
    }

    addRenderer(renderer) {
        this.renderers.push(renderer);
    }

    logToConsole(data) {
        this.consoleListeners.forEach(listener => {
            listener(data);
        })
    }

    onAppResult(data) {
        if (data.startsWith("DEBUGGER OUTPUT")) {
            try {
                data = JSON.parse(data.substr("DEBUGGER OUTPUT".length))
                this.renderers.forEach(renderer => {
                    renderer.add_result(data)
                })
            } catch {
                this.logToConsole("Failed to parse debugger output " + data.substr("DEBUGGER OUTPUT".length) + "\n")
            }
        } else {
            if (typeof data == "string") {
                this.logToConsole(data + "\n")
            } else {
                this.logToConsole(JSON.stringify(data) + "\n")
            }
        }
    }

    sendInput(data) {
        this.socket.emit('app-input', {
            pid: this.remotePid,
            text: data
        })
    }

    onAppError(error) {
        this.logToConsole(error)
        // this.statusListeners.forEach(listener => {
        //     listener({
        //         status: "idle",
        //         error: error
        //     })
        // })
    }

    onAppExit(error) {
        this.logToConsole(error)
        this.statusListeners.forEach(listener => {
            listener({
                status: "idle",
                error: error
            })
        })
        this.remotePid = null;
    }

    run(parameters) {
        if (this.remotePid) {
            console.error("Cannot run multiple processes at once")
            return;
        }
        this.runListeners.forEach(l => l())

        this.statusListeners.forEach(listener => {
            listener({
                status: "running",
                error: null
            })
        })

        console.log("Running with parameters", parameters)
        this.renderers.forEach(renderer => {
            renderer.clear_results()
        })
        this.socket.emit('app', parameters);
    }

    kill() {
        console.log("Killing remote process", this.remotePid)
        this.socket.emit("app-kill", {pid: this.remotePid})
    }
}

RemoteProcessConnection.registry = window.RemoteProcessConnectionRegistry = {};

RemoteProcessConnection.get = function(identifier) {
    if (!RemoteProcessConnection.registry[identifier]) {
        RemoteProcessConnection.registry[identifier] = new RemoteProcessConnection();
    }
    return RemoteProcessConnection.registry[identifier];
}