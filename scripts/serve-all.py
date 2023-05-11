import subprocess
import os
import termcolor

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

processes = []

summary = ""

summary += termcolor.colored("Website on http://localhost:8080/\n\n", "green")
serve_web = subprocess.Popen(["python", "-m", "http.server", "8080"], cwd="web", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_web)

summary += termcolor.colored("Browser Playground on http://localhost:8081/playground/\n\n", "green") 
serve_web_deploy = subprocess.Popen(["python", "-m", "http.server", "8081"], cwd="web-deploy", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_web_deploy)

# autobuild sphinx docs
# onchange "**/*.py" "**/*.md" "**/*.rst" "**/*.css" "**/*.js" "**/*.ipynb" -e "build" -- make html
autobuild_sphinx_p = subprocess.Popen(["onchange", "**/*.py", "**/*.md", "**/*.rst", "**/*.css", "**/*.js", "**/*.ipynb", "-e", "build", "--", "make", "html"], cwd="docs")
processes.append(autobuild_sphinx_p)
# serve docs/build/html on http://localhost:8081/
summary += termcolor.colored("Docs on http://localhost:8081/\n\n", "green") 
serve_docs = subprocess.Popen(["python", "-m", "http.server", "8081"], cwd="docs/build/html", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
processes.append(serve_docs)

# autobuild blog
# onchange ../../docs/build/html/blog/*.html -- node generate.js
summary += termcolor.colored("Blog on http://localhost:8080/blog\n\n", "green")
autobuild_blog_p = subprocess.Popen(["onchange", "../../docs/build/html/blog/*.html", "--", "node", "generate.js"], cwd="web-deploy/blog")
processes.append(autobuild_blog_p)

# autobuild web/
# onchange "index.template.html" "**/*.js" "**/*.css" "**/*.md" -e "./index.html" -- node generate.js
autobuild_web_p = subprocess.Popen(["onchange", "index.template.html", "**/*.js", "**/*.css", "**/*.md", "-e", "./index.html", "--", "node", "generate.js"], cwd="web")
processes.append(autobuild_web_p)

while True:
    try:
        print(summary)
        # listen for keyboard input
        command = input("Enter command (q to quit, bb to build browser playground): ")
        if command == "q":
            raise KeyboardInterrupt
        elif command == "bb": # browser build
            print(termcolor.colored("Building browser playground...", "yellow"))
            # run bash deploy.sh in web/
            subprocess.run(["bash", "deploy.sh"], cwd="web")
            print(termcolor.colored("Done!", "green"))
        else:
            print(termcolor.colored("Unknown command!", "red"))
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
        break