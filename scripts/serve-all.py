import subprocess
import os
import termcolor
import sys

"""
Serves all web-facing content:

- Serves web-deploy/ (website + blog + browser playground)
- Serves docs/build/html/ (docs)
- Auto-builds docs/ 
- Auto-builds web-deploy/blog/
- Auto-builds web-deploy/ (website + blog + browser playground)
"""

# chdir to project root 
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ensure web-deploy/ exists
os.makedirs("web-deploy", exist_ok=True)
os.makedirs("docs/build/html", exist_ok=True)

# make sure 'onchange' is installed
try:
    subprocess.run(["onchange", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except:
    print("Please install 'onchange' with 'npm install -g onchange'")
    sys.exit(1)

processes = []

summary = ""

summary += "Browser Playground on " + termcolor.colored("http://localhost:8081/playground/\n\n", "green") 
serve_web_deploy = subprocess.Popen(["python", "-m", "http.server", "8081"], cwd="web-deploy", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_web_deploy)

# autobuild web 
summary += "Web on " + termcolor.colored("http://localhost:5173/\n", "green")
auto_build_docs = subprocess.Popen(["yarn", "run", "docs:dev"], cwd="docs")
processes.append(auto_build_docs)

while True:
    try:
        print(summary)
        # listen for keyboard input
        command = input("Enter command (q to quit, bb to build browser playground, docs-clean to clean build docs, web-clean to clean build web-deploy): ")
        if command == "q":
            raise KeyboardInterrupt
        elif command == "bb": # browser build
            print(termcolor.colored("Building browser playground...", "yellow"))
            # run bash deploy.sh in web/
            subprocess.run(["bash", "deploy-web.sh"], cwd="scripts/")
            print(termcolor.colored("Done!", "green"))
        elif command == "docs-clean":
            # docs/ make clean
            subprocess.run(["make", "clean", "html"], cwd="docs")
        elif command == "web-clean":
            # rm -rf web-deploy/*
            subprocess.run(["rm", "-rf", "web-deploy/*"])
            # rm web/browser-build/temp
            subprocess.run(["rm", "-rf", "web/browser-build/temp"])
        else:
            print(termcolor.colored("Unknown command!", "red"))
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
        break