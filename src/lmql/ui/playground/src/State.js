import {queries} from "./queries";

function getSnippet(allow_snippet=true) {
  const url = window.location.href
  if (url.indexOf('?') === -1) {
    return null
  }
  const parameters = url.split('?')[1]
  if (parameters.startsWith('embed=')) {
    return parameters.substr(6)
  } else if (parameters.startsWith('snippet=') && allow_snippet) {
    return parameters.substr(8)
  } else {
    return null
  }
}

export const displayState = {
  // if ?embed, mode = embed, else playground
  mode: getSnippet(false) ? 'embed' : 'playground',
  preloaded: getSnippet(true) ? true : false,
  embedFile: null
}

class PersistedState {
    constructor() {
      this.items = {}
      this.listeners = {}
      this.restore()

      this.saveQueue = {}
    }
  
    persist(k) {
      Object.keys(this.items).forEach(key => {
        if (!key || key === k) {
          window.localStorage.setItem(key, this.items[key]);
        }
      })
    }
  
    restore() {
      Object.keys(this.items).forEach(key => {
        this.items[key] = window.localStorage.getItem(key);
      })

      // check for snippet or embed
      let snippetFile = getSnippet()
      if (snippetFile) {
        let load_as_json = true;

        console.log("loading snippet from", snippetFile)
        let matches = queries.filter(c => c.queries.find(q => q.state == "precomputed/" + snippetFile + ".json"))
        if (matches.length === 1) {
          let q = matches[0].queries.find(q => q.state == "precomputed/" + snippetFile + ".json")
          snippetFile = q.state
        }

        // check for github gist
        if (snippetFile.startsWith("gist:")) {
          // will be of this form gist:lbeurerkellner/9e203be6f9120dae2515c43517bc1aee/raw/test.lmql
          try {
            let parts = snippetFile.split(":")
            let user = parts[1].split("/")[0]
            let gist = parts[1].split("/")[1]
            let file = parts[1].split("/")[3]
            snippetFile = `https://gist.githubusercontent.com/${user}/${gist}/raw/${file}`

            load_as_json = file.endsWith(".json")
          } catch (e) {
            console.error("error parsing github gist URL", e)
            return;
          }
        }

        fetch(snippetFile).then(r => r.text()).then(data => {
          // remove ? from url
          if (!snippetFile.includes("gist.github")) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }
          // actually load data
          if (data) {
            if (!load_as_json) {
              data = JSON.stringify({ "lmql-editor-contents": data , "decoder-graph":"{\"nodes\":[],\"edges\":[]}"})
            }
            displayState.embedFile = snippetFile
            this.load(data)
          }
        })
      }
    }

    load(data) {
      data = JSON.parse(data);
      this.items = {};
      Object.keys(data).forEach(key => {
        this.items[key] = data[key];
        if (this.listeners[key]) {
          this.listeners[key].forEach(l => l(this.items[key]))
        }
      })
    }

    dump() {
      return JSON.stringify(this.items);
    }
  
    on(key, listener) {
      if (listener) {
        if (!this.listeners[key]) {
          this.listeners[key] = [];
        }
        this.listeners[key].push(listener);
      }
    }

    remove(key, listener) {
      if (this.listeners[key]) {
        this.listeners[key] = this.listeners[key].filter(l => l !== listener);
      }
    }

    getItem(key) {
      if (key in this.items) {
        return this.items[key];
      }
      let data = window.localStorage.getItem(key);
      if (data) {
        this.items[key] = data;
        return data;
      }

      return null;
    }
  
    setItem(key, value, exclude_listener=null) {
      this.items[key] = value;
      this.persist(key);
      
      if (this.listeners[key]) {
        this.listeners[key].forEach(listener => {
          if (listener !== exclude_listener) listener(value);
        })
      }
    }

    queueSetItem(key, value, exclude_listener=null) {
      if (this.saveQueue[key]) {
        clearTimeout(this.saveQueue[key]);
      }
      this.saveQueue[key] = setTimeout(() => {
        this.setItem(key, value, exclude_listener);
      })
    }
  }
  
export const persistedState = new PersistedState();

export const trackingState = {
  setTrackMostLikely: () => { },
  getTrackMostLikely: () => false,
  setSelectedNode: () => { },
}

export const errorState = {
  addListener: listener => {
    errorState.listeners.push(listener);
  },
  listeners: [],
  error: null,
  setError: (e) => { 
    errorState.error = e;
    errorState.listeners.forEach(l => l(e));
  },
  removeListener: (listener) => {
    errorState.listeners = errorState.listeners.filter(l => l !== listener);
  },
  showErrorOutput: () => { },
}