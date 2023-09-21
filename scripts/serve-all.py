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

summary += "Website on " + termcolor.colored("http://localhost:8080/\n\n", "green")
serve_web = subprocess.Popen(["python", "-m", "http.server", "8080"], cwd="web", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_web)

summary += "Browser Playground on " + termcolor.colored("http://localhost:8081/playground/\n\n", "green") 
serve_web_deploy = subprocess.Popen(["python", "-m", "http.server", "8081"], cwd="web-deploy", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_web_deploy)

# autobuild sphinx docs
# onchange "**/*.py" "**/*.md" "**/*.rst" "**/*.css" "**/*.js" "**/*.ipynb" -e "build" -- make html
autobuild_sphinx_p = subprocess.Popen(["onchange", "**/*.py", "**/*.md", "**/*.rst", "**/*.css", "**/*.js", "**/*.ipynb", "-e", "build", "--", "make", "html"], cwd="docs")
processes.append(autobuild_sphinx_p)
# serve docs/build/html on http://localhost:8081/
summary += "Docs on " + termcolor.colored("http://localhost:8082/\n\n", "green") 
# if docs are empty, build with make html
if not os.path.exists("docs/build/html/index.html"):
    subprocess.run(["make", "html"], cwd="docs")
serve_docs = subprocess.Popen(["python", "-m", "http.server", "8082"], cwd="docs/build/html", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_docs)

# autobuild blog
# onchange ../../docs/build/html/blog/*.html -- node generate.js
summary += "Blog on " + termcolor.colored("http://localhost:8080/blog\n\n", "green")
autobuild_blog_p = subprocess.Popen(["onchange", "../../docs/build/html/blog/*.html", "--", "node", "generate.js"], cwd="web/blog")
processes.append(autobuild_blog_p)

# autobuild web/
# onchange "index.template.html" "**/*.js" "**/*.css" "**/*.md" -e "./index.html" -- node generate.js
autobuild_web_p = subprocess.Popen(["onchange", "index.template.html", "**/*.js", "**/*.css", "**/*.md", "-e", "./index.html", "--", "node", "generate.js"], cwd="web")
processes.append(autobuild_web_p)

# autobuild web/actions
auto_build_actions_p = subprocess.Popen(["onchange", "**/*.js", "**/*.css", "**/*.md", "**/*.html", "**/*.pd", "**/*.json", "-e", "./index.html", "--", "node", "generate.js"], cwd="web/actions")
processes.append(auto_build_actions_p)

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
            subprocess.run(["bash", "deploy.sh"], cwd="web")
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