export const displayState = {
  mode: window.location.hash.startsWith("#embed") ? "embed" : "playground",
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
      let snippet = window.location.hash.substr(1)
      if (snippet) {
        let file = null;
        /* check for embed= or snippet= */
        if (snippet.startsWith("embed=")) {
          file = snippet.substr(6)
        } else if (snippet.startsWith("snippet=")) {
          file = snippet.substr(8)
        }
        // window.history.pushState('', document.title, window.location.pathname);
      
        /* load file as JSON */
        if (file) {
          console.log("loading snippet from", file)
          fetch(file).then(r => r.text()).then(data => {
            if (data) {
              displayState.embedFile = file
              this.load(data)
            }
          })
        }
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