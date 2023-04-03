const port = process.env.PORT || 3000;

var readline = require('readline');
const stream = require('stream')

const cors = require('cors')
const fs = require("fs")
const express = require("express")
const path = require('path');
const app = require('express')();
const http = require('http');
const server = http.createServer(app);
const io = require('socket.io')(server, {
  cors: {
    origin: '*',
  }
})
const exec = require('child_process').exec;
const spawn = require('child_process').spawn

let outputs = {};

// disable cors for app
app.use(cors({origin: '*'}));

io.on('connection', s => {
  s.on('app', request => {
    const app_name = request.name;
    const app_input = request.app_input;
    const app_arguments = request.app_arguments;
    
    // run "python live.py endpoints" and get output lines as array
    exec(`python live.py endpoints ${app_name}`, (err, stdout, stderr) => {
        if (err) {
            console.log(err);
            s.emit("app-error", stdout + stderr)
            return;
        }
        // get endpoints from output lines
        const endpoints = stdout.split('\n');
        // remove empty lines
        endpoints.splice(endpoints.length - 1, 1);
        // find endpoint name in endpoints
        const endpoint_name = endpoints.find(endpoint => endpoint == app_name);
        if (!endpoint_name) {
            s.emit('error', 'endpoint not found');
            return;
        } else {
            run_app(app_name, app_input, app_arguments, s);
        }
    });
  });
  
  s.on('app-kill', request => {
    let pid = request.pid
    let process = running_processes[pid]
    if (process) {
      console.log("app-kill: killing process with PID", pid)
      process.kill("SIGKILL")
      delete running_processes[pid];
    }
    if (pid == null) {
      console.log("app-kill: PID is null, killing all running processes")
      Object.keys(running_processes).forEach(pid => {
        running_processes[pid].kill("SIGKILL")
      })
    }
  })

  s.on('app-input', request => {
    let text = request.text
    let pid = request.pid
    let process = running_processes[pid]
    if (process) {
      console.log("app-input: sending text to process with PID", pid, text)
      process.stdin.write(text)
      process.stdin.write("\n")
    }
  })
});

app.get('/', (req, res) => {
  // disable all caching
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.sendFile(path.join(__dirname, 'base/index.html'));
});

// serve client.js
app.get('/client.js', (req, res) => {
  let client_script = fs.readFileSync(path.join(__dirname, 'base/client.js'), {encoding: 'utf8'})
  client_script = client_script.replace("<<<PORT>>>", port)
  res.send(client_script)
})

// serve base/base.css
app.get('/base.css', (req, res) => {
    res.sendFile(path.join(__dirname, 'base/base.css'));
});

// serve all files in node_modules/monaco-editor/min as /monaco
app.use('/vs', express.static(path.join(__dirname, 'node_modules/monaco-editor/min/vs')));
app.use('/js/vs', express.static(path.join(__dirname, 'node_modules/monaco-editor/min/vs')));
app.use('/app/vs', express.static(path.join(__dirname, 'node_modules/monaco-editor/min/vs')));

// Expose the node_modules folder as static resources (to access socket.io.js in the browser)
app.use('/static', express.static('node_modules'));

app.get('/socket.io.min.js', (req, res) => {
    // send client js for socket io
    res.sendFile(path.join(__dirname, 'node_modules/socket.io/client-dist/socket.io.min.js'));
});

app.get('/socket.io.min.js.map', (req, res) => {
    res.sendFile(path.join(__dirname, 'node_modules/socket.io/client-dist/socket.io.min.js.map'));
});

// serve /app/<app_name>
app.get('/app/:app_name', (req, res) => {
  const app_name = req.params.app_name;
  // disable all caching
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  let html = fs.readFileSync(path.join(__dirname, 'base/index.html'), {encoding: 'utf8'})
  
  exec(`python live.py client-html ${app_name}`, (err, stdout, stderr) => {
    if (err) {
        console.log(err);
        res.send(html.replace("<<<CLIENT_HTML>>>", "Failed to load app html for app."))
    } else {
      res.send(html.replace("<<<CLIENT_HTML>>>", stdout))
    }
  });
})

// serve /app/<app_name>
app.get('/app/:app_name/app-client.js', (req, res) => {
  const app_name = req.params.app_name;
  // run "python live.py endpoints" and get output lines as array
  exec(`python live.py client-script ${app_name}`, (err, stdout, stderr) => {
    if (err) {
        console.log(err);
        res.send("")
    } else {
      res.send(stdout)
    }
  });
})

let running_processes = {}

function run_app(app_name, app_input, app_arguments, socket) {
    const app_input_as_json = JSON.stringify(app_input);
    const app_arguments_as_json = JSON.stringify(app_arguments);
    // run "python live.py endpoints" and get output lines as array
    // console.log(" >", `python live.py ${app_name} ${app_input_as_json}`);
    
    if (!app_input) {
      socket.emit("app-exit", `Error: Cannot run app with empty input\n`)
      return;
    }

    const live_process = spawn('python', ['live.py', app_name, app_input_as_json, app_arguments_as_json]);
    // app input escape all double quotes as twice
    let input = app_input.replace(/"/g, '\\"');

    socket.emit("app-error", `App started running...\n`)
    console.log("App started running...")

    live_process.on("spawn", () => {
      running_processes[live_process.pid] = live_process;
      socket.emit("app-pid", {pid: live_process.pid})
      console.log("App pid:", live_process.pid)
    })

    var stdout_lines = readline.createInterface({
      input: live_process.stdout,
    });
    stdout_lines.on('line', (data) => {
      // console.log(data.toString())
      socket.emit("app-result", data.toString());
    });
    live_process.stderr.on('data', (data) => {
      socket.emit("app-error", data.toString())
    });
    live_process.on('exit', (code, error) => {
      delete running_processes[live_process.pid];
      if (code == 0) {
        socket.emit("app-exit", `App finished running with exit code ${code}\n`)
        console.log("App finished running with exit code", code)
      } else if (!code) {
        socket.emit("app-exit", `App exited with ${error}\n`)  
        console.log("App exited with", error)
      } else {
        socket.emit("app-exit", `App finished running with exit code ${code}\n`)
        console.log("App finished running with exit code", code)
      }
    });
}

server.listen(port, "0.0.0.0", () => console.error('livelib server listening on http://localhost:' + port))
// http.listen(port, () => console.error('listening on http://localhost:' + port));