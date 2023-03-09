import React from "react";

export class SharedState {
    constructor(initial) {
        this.state = Object.assign({}, initial);
        this.listeners = [];
    }
    setState(updater) {
        this.state = updater(this.state);
    }
    onStateChange(callback) {
        this.listeners.push(callback);
    }
    removeStateChange(callback) {
        this.listeners = this.listeners.filter((cb) => cb !== callback);
    }
    notifyListeners() {
        this.listeners.forEach((cb) => cb(this.state));
    }
    connect(prop, setter) {
        let l = (state) => setter(state[prop]);
        this.onStateChange(l);
        return () => this.removeStateChange(l);
    }
}
