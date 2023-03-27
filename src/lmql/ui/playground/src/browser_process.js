import { BUILD_INFO } from "./build_info";

export class BrowserProcessConnection {
    constructor(worker) {
        this.worker = worker;
        this.processWorker = new Worker(worker);
        this.setup();

        this.hasSecret = false;
        this.secret = null;

        if (window.localStorage.getItem("openai-secret")) {
            this.hasSecret = this.secret != "";
            this.secret = window.localStorage.getItem("openai-secret");
        }
        
        if (typeof window.SharedArrayBuffer !== "undefined") {
            this.interruptBuffer = new Uint8Array(new window.SharedArrayBuffer(1));
            this.processWorker.postMessage({ func: "set_interrupt_buffer", args: this.interruptBuffer});
        } else {
            this.interruptBuffer = null;
        }

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
        this.killCounter = 0;
        this.hardKillTimer = null;

        this.ready = false;
        this.status = {
            connected: false,
            label: ""
        }

        this.addStatusListener((status) => {
            if (status.status == "idle") {
                this.killCounter = 0;
                this.status = Object.assign({}, status);

                if (!this.ready) {
                    this.ready = true;

                    this.connectionListeners.forEach(listener => {
                        listener(true)
                    })
                }
            }
        })
    }

    setup() {
        this.processWorker.onmessage = (event) => {
            if (event.data.type == "app-result") {
                this.onAppResult(event.data.data)
            } else if (event.data.type == "app-status") {
                this.statusListeners.forEach(listener => {
                    listener(event.data.data)
                })
            } else {
                console.log("Received unhandled message type from worker", event.data);
            }
        };
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

    listener_stats() {
        console.log("console listeners", this.consoleListeners.length)
        console.log("render listeners", this.renderers.length)
        console.log("status listeners", this.statusListeners.length)
        console.log("connection listeners", this.connectionListeners.length)
        console.log("renderers", this.renderers.length)
        console.log("run listeners", this.runListeners.length)
    }

    onAppResult(data) {
        if (data.startsWith("DEBUGGER OUTPUT")) {
            try {
                data = JSON.parse(data.substr("DEBUGGER OUTPUT".length))
                // console.log("got parsed data", data)
                this.renderers.forEach(renderer => {
                    renderer.add_result(data)
                })
            } catch {
                this.logToConsole("Failed to parse debugger output " + data.substr("DEBUGGER OUTPUT".length) + "\n")
            }
        } else if (data.startsWith("BUILD_INFO")) {
            let info = data.substr("BUILD_INFO ".length)
            let [commit, time] = info.split(", ")
            let commit_segments = commit.split(" ")
            let commit_str = commit_segments[1].substr(0, 7)
            if (commit_segments[commit_segments.length - 1] == "dirty") {
                commit_str += " (dirty)"
            }
            BUILD_INFO.setInfo({
                commit: commit_str,
                date: time
            })
        } else if (data.startsWith("APP EXIT")) {
            let exitMessage = data.substr("APP EXIT ".length)
            this.onAppExit(exitMessage)
        } else if (data.startsWith("APP ERROR")) {
            let errorMessage = data.substr("APP ERROR ".length)
            this.onAppError(errorMessage)
        } else {
            if (typeof data == "string") {
                this.logToConsole(data + "\n")
            } else {
                this.logToConsole(JSON.stringify(data) + "\n")
            }
        }
    }

    onAppError(error) {
        this.logToConsole(error)
        this.statusListeners.forEach(listener => {
            listener({
                status: "error",
                error: error
            })
        })
    }

    onAppExit(error) {
        this.logToConsole(error)
        this.statusListeners.forEach(listener => {
            listener({
                status: "exit",
                error: error
            })
        })
        this.remotePid = null;
    }

    run(parameters) {
        if (!this.hasSecret) {
            this.statusListeners.forEach(listener => {
                listener({
                    status: "secret-missing",
                    error: "No OpenAI secret set."
                })
            })
            return;
        } else {
            this.processWorker.postMessage({func: "set_openai_secret", args: this.secret});
        }

        this.renderers.forEach(renderer => {
            renderer.clear_results()
        })

        if (this.interruptBuffer) {
            this.interruptBuffer[0] = 0;
        }

        this.killCounter = 0;

        let browser_args = [parameters.name, parameters.app_input, parameters.app_arguments]
        this.processWorker.postMessage({func: "live", args: browser_args});
    }

    sendInput(data) {
        this.processWorker.postMessage({func: "send_input", args: data});
    }

    // on change in org persist contents
    setSecret(secret) {
        if (secret.startsWith("transient-")) {
            secret = secret.substring("transient-".length)
        } else {
            localStorage.setItem("openai-secret", secret);
        }
        this.secret = secret;
        this.hasSecret = this.secret != "";
        console.log("Setting OpenAI secret in browser process", secret, "secret")
        this.processWorker.postMessage({func: "set_openai_secret", args: this.secret});
    }

    kill() {
        if (this.killCounter != 0) {
            return;
        }

        this.statusListeners.forEach(listener => {
            listener({
                status: "stopping"
            })
        })

        this.processWorker.postMessage({func: "kill", args: []})

        let killId = 1 + parseInt(Math.random() * 1000000);
        this.killCounter = killId;
        
        console.log("Killing in-browser process")

        // clear hard kill timer
        if (this.hardKillTimer) {
            clearTimeout(this.hardKillTimer)
            this.hardKillTimer = null;
        }

        // if kill is not fast enough, trigger a hard kill (restart web worker)
        this.hardKillTimer = setTimeout(() => {
            if (this.killCounter != killId) {
                return;
            }
            this.hardKillTimer = null;
            this.processWorker.terminate()
            this.processWorker = new Worker(this.worker);
            this.setup()
        }, 2000)
    }
}

BrowserProcessConnection.registry = window.BrowserProcessConnectionRegistry = {};

BrowserProcessConnection.get = function(identifier) {
    if (!BrowserProcessConnection.registry[identifier]) {
        BrowserProcessConnection.registry[identifier] = new BrowserProcessConnection("lmql.web.min.js");
    }
    return BrowserProcessConnection.registry[identifier];
}