const util = require('util');
const exec = util.promisify(require('child_process').exec);

const path = require("path")
const WatchExternalFilesPlugin = require("webpack-watch-files-plugin").default

async function python_package(package_name, package_path, options, build_folder, compilation) {
    console.log(`[python-package] Compiling ${package_path}...`)
    // check that we did not run on this package_path for this compilation yet
    options = Object.assign({
        "exclude": []
    }, options)

    let excludeFlags = options.exclude.map(e => `--exclude="${e}"`).join(" ")

    if (!package_path.endsWith("/")) {
        package_path += "/"
    }

    // get git branch in package path
    let { stdout: git_branch } = await exec(`git rev-parse --abbrev-ref HEAD`, {
        cwd: package_path,
        stdio: "pipe"
    })
    git_branch = git_branch.trim()
    
    // get git commit in package path
    let { stdout: git_commit } = await exec(`git rev-parse HEAD`, {
        cwd: package_path,
        stdio: "pipe"
    })
    git_commit = git_commit.trim()
    
    // check if dirty
    let { stdout: git_status } = await exec(`git status --porcelain`, {
        cwd: package_path,
        stdio: "pipe"
    })
    let is_dirty = git_status.trim() !== ""
    
    // make sure temp/ exists
    await exec(`mkdir -p temp`, {
        stdio: "inherit"
    })

    await exec(`rsync -rd ${excludeFlags} ../${package_path} ${package_name}`, {
        cwd: "temp",
        stdio: "inherit"
    })
    // create file with build-time
    const build_string = `${git_branch} ${git_commit}${is_dirty ? " dirty" : ""}, ${new Date().toDateString()}`
    console.log(`[python-package] ${package_name}: ${build_string}`)
    await exec(`echo "${build_string}" > BUILD`, {
        stdio: "inherit",
        cwd: path.join("temp", package_name)
    })
    // await exec(`rm -rf ${package_name}.tar.gz`, {
    //     cwd: "temp"
    // })
    await exec(`tar -czf ../${package_name}.tar.gz *`, {
        cwd: path.join("temp", package_name),
        stdio: "inherit",
    })
    await exec(`cp ${package_name}.tar.gz ../${build_folder}`, {
        cwd: "temp/",
        stdio: "inherit",
    })
    await exec(`cp ${package_name}.tar.gz ../${build_folder}`, {
        cwd: "temp/",
        stdio: "inherit",
    })
    console.log(`[python-package] ${path.join(build_folder, package_name)}.tar.gz`)
}

class PythonPackagePlugin {
    constructor(packages, options) {
        this.packages = packages
        this.options = options

        this.watcher = new WatchExternalFilesPlugin({
            files: this.packages.map(p => `${p.path}/**/*.py`)
        })
    }

    apply(compiler) {
        const compilePackets = (compilation) => {
            return Promise.all(this.packages.map(p => python_package(p.name, p.path, p, this.options.build_folder, compilation)))
        }

        // compiler.hooks.beforeCompile.tapPromise("PythonPackagePlugin", )
        // run once per run
        // console.log(compiler.hooks)
        compiler.hooks.done.tapPromise("PythonPackagePlugin", compilePackets)
        this.watcher.apply(compiler)
    }
}

module.exports = {
    PythonPackagePlugin: PythonPackagePlugin
}