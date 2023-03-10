class WebWorkerProcessConnection {
    constructor(worker) {
        this.processWorker = new Worker(worker);

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

        // this.socket = io.connect(':' + PORT);
        // this.socket.on('connect', () => {
        //     this.socket.on('app-result', data => {
        //         this.onAppResult(data)
        //     })
        //     this.socket.on('app-pid', pid => {
        //         this.remotePid = pid.pid;
        //     })
        //     this.socket.on('app-error', (error) => {
        //         this.onAppError(error)
        //     })
        //     this.socket.on('app-exit', (error) => {
        //         this.onAppExit(error)
        //     })

        //     this.connectionListeners.forEach(listener => {
        //         listener(true)
        //     })

        //     // disconnect
        //     this.socket.on('disconnect', () => {
        //         this.connectionListeners.forEach(listener => {
        //             listener(false)
        //         })
        //     })
        // });

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

        this.ready = false;
        this.addStatusListener((status) => {
            if ((status.status == "ready" || status.status == "Ready") && !this.ready) {
                this.ready = true;
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
        console.log("Running with parameters", parameters)
        console.log(parameters)
        this.processWorker.postMessage({func: "live", args: parameters});
    }

    // on change in org persist contents
    saveSecret(secret) {
        localStorage.setItem("openai-secret", secret);
        this.processWorker.postMessage({func: "set_openai_secret", args: secret});
    }

    kill() {
        console.log("Killing in-browser process")
        this.processWorker.postMessage({func: "stop", args: null});
    }
}

WebWorkerProcessConnection.registry = window.WebWorkerProcessConnectionRegistry = {};

WebWorkerProcessConnection.get = function(identifier) {
    if (!WebWorkerProcessConnection.registry[identifier]) {
        WebWorkerProcessConnection.registry[identifier] = new WebWorkerProcessConnection("lmql.web.min.js");
    }
    return WebWorkerProcessConnection.registry[identifier];
}

const LMQLProcess = WebWorkerProcessConnection.get("lmql")

// LMQLProcess.addConsoleListener(d => {
//     console.log(d)
// })

// LMQLProcess.addStatusListener(s => {
//     console.log("Status", s)
// })

// function saveOnEdit() {
//     let code = document.getElementById("code").value;
//     window.localStorage.setItem("code", code);
// }

// function initEditor() {
//     let code = window.localStorage.getItem("code");

//     require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' }});
//     require(["vs/editor/editor.main"], () => {
//         window.editor = monaco.editor.create(document.getElementById('editor'), {
//             value: code || "",
//             language: 'python',
//             // font size
//             fontSize: 18,
//             // theme
//             theme: "vs-dark",
//         });
//         // on change persist contents
//         editor.onDidChangeModelContent(function(e) {
//             let code = editor.getValue();
//             window.localStorage.setItem("code", code);
//         });

//         document.getElementById("run").disabled = false;
//         document.getElementById("stop").disabled = false;
//     });
// }
// window.initEditor = initEditor

// // on window load, find openid-secret input and restore value from local storage
// window.addEventListener("load", function() {
//     // let secret = localStorage.getItem("openai-secret");
//     let secret = localStorage.getItem("openai-secret");
//     if (secret) {
//         document.getElementById("openai-secret").value = secret;
//     }
    
//     function saveSecret(e) {
//         LMQLProcess.saveSecret(document.getElementById("openai-secret").value);
//     }

//     document.getElementById("openai-secret").addEventListener("change", saveSecret);
//     document.getElementById("openai-secret").addEventListener("keyup", saveSecret);

//     saveSecret();
// })