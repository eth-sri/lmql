import fs from 'fs'
import path from 'path'
import { terminalCodesToHtml } from 'terminal-codes-to-html'

const DEFAULT_CELL_ARGS = {
    // by default we show output
    show_stdout: true,
    // by default we do not show stderr
    show_stderr: false,
    // by default we do show the result
    show_result: true,
    // to hide an entire cell, set hidden to true
    hidden: false
}

// check for args
if (process.argv.length < 3) {
    console.log('Usage: node notebooks.js <directory>')
    process.exit(1)
}

const directory = process.argv[2]


function findAllNotebookFiles(directory) {
    // find all .ipynb files (also recursively)
    const files = []

    function findNotebooks(dir) {
        const items = fs.readdirSync(dir)
        const stat = fs.lstatSync(dir)
        if (stat.isSymbolicLink()) {
            return
        }

        for (const item of items) {
            const itemPath = path.join(dir, item)
            const stat = fs.statSync(itemPath)
            if (stat.isDirectory()) {
                findNotebooks(itemPath)
            } else if (item.endsWith('.ipynb')) {
                files.push(itemPath)
            }
        }
    }

    findNotebooks(directory)

    return files
}

function getArgs(lines) {
    let args = {}
    let control_lines = lines.filter(line => line.startsWith('#notebooks.js:'))
    let source_lines = lines.filter(line => !line.startsWith('#notebooks.js:'))

    for (let line of control_lines) {
        let entry = line.slice(14).trim()
        if (entry.includes('=')) {
            let [key, value] = entry.split('=')
            if (value == 'true') { 
                value = true
            } else if (value == 'false') {
                value = false
            } else {
                try {
                    let n = parseInt(value)
                    value = n
                } catch (e) {
                    // interpret as string
                }
            }
            args[key] = value
        } else {
            args[entry] = true
        }
    }
    
    args = {...DEFAULT_CELL_ARGS, ...args}

    return [args, source_lines]
}

function renderCell(cell) {
    if (cell.cell_type === 'markdown') {
        return cell.source.join('') + "\n\n"
    }

    if (cell.metadata && cell.metadata.nbsphinx == "hidden") {
        return ""
    }

    if (cell.cell_type === "code") {
        let [args, source] = getArgs(cell.source);

        if (source.length === 0) {
            return ""
        }

        if (args.hidden) {
            return "";
        }

        let rendered_source = "```lmql\n" + source.join('') + "\n```\n";
        let output = ""
        
        for (let output_part of cell.outputs) {
            if (output_part.output_type === "execute_result") {
                if (args.show_result) {
                    for (let output_type of Object.keys(output_part.data)) {
                        if (output_type === "text/plain") {
                            output += "```result\n" + output_part.data[output_type].join("") + "\n```\n"
                        } else {
                            output += "```result\n" + JSON.stringify(output_part.data[output_type], null, 2) + "\n```\n"
                        }
                    }
                }
            } else if (output_part.output_type === "stream") {
                let text = output_part.text.join("").trim()
                let text_before = text
                text = terminalCodesToHtml(text)

                if (output_part.name === "stdout" && args.show_stdout) {
                    output += "```output\n" + text + "\n```\n"
                } else if (output_part.name === "stderr" && args.show_stderr) {
                    output += "```output\n" + text + "\n```\n"
                }
            } else {
                output += "```output\n" + JSON.stringify(output_part, null, 2) + "\n```\n"
            }
        }

        return rendered_source + output
    }

    console.warn("Unknown cell type: " + cell.cell_type)

    return ""
}

findAllNotebookFiles(directory).forEach(file => {
    const contents = fs.readFileSync(file, 'utf-8')
    const json = JSON.parse(contents)

    let output = ""

    for (const cell of json.cells) {
        output += renderCell(cell)
    }

    let output_file = file.replace('.ipynb', '.md')
    console.log('[' + new Date().toISOString() + '] ' + file + ' -> ' + output_file)
    fs.writeFileSync(output_file, output)
})