import lmql
import sys
import os
from lmql.ui.chat import chatter

if __name__ == '__main__':
    assert len(sys.argv) == 2, "Usage: lmql chat <file>"
    file = sys.argv[1]
    absolute_path = os.path.abspath(file)
    # change working dir to file dir
    os.chdir(os.path.dirname(absolute_path))
    
    chatter(absolute_path).run()