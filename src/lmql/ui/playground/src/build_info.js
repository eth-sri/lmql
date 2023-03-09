class BuildInfoStore {
    constructor() {
        this.listeners = [];

        if (!window['BUILD_COMMIT']) {
            if (process.env.REACT_APP_BUILD_COMMIT) {
                window['BUILD_COMMIT'] = process.env.REACT_APP_BUILD_COMMIT;
            } else {
                window['BUILD_COMMIT'] = '';
            }
        }
        if (!window['BUILD_DATE']) {
            if (process.env.REACT_APP_BUILD_DATE) {
                window['BUILD_DATE'] = process.env.REACT_APP_BUILD_DATE;
            } else {
                window['BUILD_DATE'] = '';
            }
        }
    }

    info() {
        return {
            commit: window['BUILD_COMMIT'],
            date: window['BUILD_DATE'] || '-'
        }
    }

    addListener(listener) {
        this.listeners.push(listener);
    }

    removeListener(listener) {
        this.listeners = this.listeners.filter(l => l !== listener);
    }

    setInfo(info) {
        window['BUILD_COMMIT'] = info.commit;
        window['BUILD_DATE'] = info.date;
        this.listeners.forEach(listener => {
            listener(this.info());
        })
    }
}

export const BUILD_INFO = new BuildInfoStore();