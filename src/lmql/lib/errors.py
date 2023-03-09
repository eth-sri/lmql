import sys
import termcolor

def error_loc_visualisation(file, loc, msg, color):
    start, end = loc

    print("")
    with open(file, "r") as f:
        for i, l in enumerate(f):
            if start.line - 1 == i:
                if start.line != end.line: end.column = len(l)
                print(str(i+1) + ":", l.rstrip())
                print(" " * (start.column + 2) + termcolor.colored("-" * (end.column - start.column + 1), color))
                print(" " * (start.column + 2), termcolor.colored(msg, color))
                break
            # elif start.line - 2 < i and start.line + 2 > i:
                # print(i+1, l.rstrip())
    print("")

def error(msg, node):
    error_loc_visualisation(node.file, node.loc, "error: " + msg, "red")
    sys.exit(1)
