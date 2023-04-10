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
        console.log("loading snippet from", snippetFile)
        let matches = queries.filter(c => c.queries.find(q => q.state == "precomputed/" + snippetFile + ".json"))
        if (matches.length === 1) {
          let q = matches[0].queries.find(q => q.state == "precomputed/" + snippetFile + ".json")
          snippetFile = q.state
        }

        fetch(snippetFile).then(r => r.text()).then(data => {
          // remove ? from url
          window.history.replaceState({}, document.title, window.location.pathname);
          if (data) {
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