// import { editor as MonacoEditor } from "monaco-editor";
// import tokenizer from "./lmql_js_tokenizer"
import {get_openai_secret} from "./openai_secret"
import * as lmql_openai_integration from "./lmql_openai_integration"
import * as lmql_http_integration from "./lmql_http_integration"

importScripts("https://cdn.jsdelivr.net/pyodide/v0.22.1/full/pyodide.js");

let pyodide = null;
let interrupt_buffer = null;
let editor = null;

let openai_credentials = {
    "secret": null,
    "organization": null
}

function addOutput(o) {
    // let output = document.getElementById("output");
    // console.log(o)
    postMessage({
        "type": "app-result",
        "data": o
    })
}

function postStatus(status, error) {
    postMessage({
        "type": "app-status",
        "data": {
            "status": status,
            "error": error
        }
    })
}

async function load_pyodide() {
    addOutput("Initializing LMQL browser environment...")
    postStatus("init", "python")
    pyodide = await loadPyodide({stdout: addOutput, stderr: addOutput});
    if (interrupt_buffer) {
        pyodide.setInterruptBuffer(interrupt_buffer)
    }
    await pyodide_main()
}
  
load_pyodide();

async function pyodide_main() {
    postStatus("init", "libraries")
    
    await pyodide.loadPackage("micropip");
    postStatus("init", "micropip")
    const micropip = pyodide.runPython("import micropip; micropip");
    await micropip.install(["requests", "pyyaml", "filelock", "regex", "importlib_metadata", "sacremoses", "typing_extensions", "ssl"])
    postStatus("init", "standard libraries")
    await pyodide.loadPackage(["wheels/astunparse-1.6.3-py2.py3-none-any.whl", "six", "packaging", "numpy", "tqdm", "termcolor", "wheels/pydot-1.4.2-py2.py3-none-any.whl", "wheels/gpt3_tokenizer-0.1.3-py2.py3-none-any.whl"])
    postStatus("init", "LMQL distribution")
    
    await pyodide.runPythonAsync(`
        from pyodide.http import pyfetch

        response = await pyfetch("wheels/openai-shim.tar.gz")
        await response.unpack_archive() # by default, unpacks to the current dir
        
        response = await pyfetch("wheels/lmql.tar.gz")
        await response.unpack_archive() # by default, unpacks to the current dir
        
        import sys
        import os
        sys.path.append(os.path.join(os.getcwd(), "lmql/ui/live"))

        try:
            # set USE_TORCH to true
            os.environ["USE_TORCH"] = "1"
            os.environ["LMQL_BROWSER"] = "1"
            import lmql
            print("LMQL", lmql.__version__, "on Pyodide Python", sys.version)
            # open and print lmql package folder BUILD
            with open(os.path.join(os.path.dirname(os.path.dirname(lmql.__file__)), "BUILD")) as f:
                print("BUILD_INFO", f.read())
        except Exception as e:
            print("Failed", e)
            # print stacktrace of 
            import traceback
            traceback.print_exc()
        os.chdir("lmql/ui/")
    `)

    postStatus("idle", null)

    // addOutput("Done loading python environment and LMQL\n")
    // addOutput("Running current editor contents")
    // run()
}

async function live(args) {
    const code = `
import lmql.ui.live.live as lmql_live
import json
import asyncio

async def cli(args):
    for i in range(1, len(args)):
        args[i] = json.dumps(args[i])
    args = ["web"] + args

    try:
        return await lmql_live.LiveApp.async_cli(args)
    except InterruptedError:
        print("APP EXIT App exited with status 1")
        return None
    except KeyboardInterrupt:
        print("APP EXIT App exited with status 1")
        return None
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("APP ERROR App exited with status 1")
        raise e
cli
`;  
    postStatus("running", null)
    const liveapp_cli = await pyodide.runPythonAsync(code);
    try {
        await liveapp_cli(pyodide.toPy(args))
    } finally {
        postStatus("idle", null)
    }
}
self["live"] = live;

async function send_input(s) {
    const code = `
import lmql.ui.live.live as lmql_live
async def send_input(s):
    try:
        r = await lmql_live.LiveApp.send_input(s)
        return r
    except Exception as e:
        print(e)
send_input
`;
    const send_input_fct = await pyodide.runPythonAsync(code);
    try {
        await send_input_fct(pyodide.toPy(s))
    } catch (e) {
        console.error("Error sending input", e)
    }
}
self["send_input"] = send_input;

async function set_interrupt_buffer(buffer) {
    if (pyodide) {
        pyodide.setInterruptBuffer(buffer);
        interrupt_buffer = buffer;
    } else {
        interrupt_buffer = buffer;
    }
}
self["set_interrupt_buffer"] = set_interrupt_buffer;

async function kill() {
    // postStatus("idle", null)
    console.log("Kill via LMQL interrupt")
    pyodide.runPython(`
from lmql.runtime.interrupt import interrupt
interrupt.set()
`);
}
self["kill"] = kill;

self.onmessage = async function(e) {
    let func = e.data.func;
    if (!self[func]) {
        console.error("Unknown worker function", func);
        return;
    }
    try {
        await self[func](e.data.args);
    } catch (e) {
        console.error("Error in worker function", func, e);
    }
}