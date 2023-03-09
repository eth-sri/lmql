import { BrowserProcessConnection } from './browser_process';
import { RemoteProcessConnection as RemoteRemoteProcessConnection} from './remote_process';
import { BUILD_INFO } from './build_info';

const default_is_browser = false;

const BrowserProfile = {
    DEMO_MODE: true,
    BROWSER_MODE: true,
    DEV_MODE: true,
    ProcessConnection: BrowserProcessConnection
}

const RemoteProfile = {
    DEMO_MODE: true,
    BROWSER_MODE: false,
    DEV_MODE: true,
    ProcessConnection: RemoteRemoteProcessConnection
}

export function isLocalModeCapable() {
    if (window.location.hostname !== "localhost") {
        return false;
    }
    return true
}

export function isLocalMode() {
    if (!isLocalModeCapable()) {
        return false;
    }
    if (window.localStorage.getItem("lmql-local-mode") === null) {
        window.localStorage.setItem("lmql-local-mode", "" + !default_is_browser);
    }

    if (window.localStorage.getItem("lmql-local-mode") !== "true") {
        return false;
    }

    return true;
}

export function setLMQLDistribution(d) {
    window.localStorage.setItem("lmql-local-mode", d == "browser");
    window.location.reload()
}

export const configuration = isLocalMode() ? RemoteProfile : BrowserProfile;
export const LMQLProcess = configuration.ProcessConnection.get("lmql");
export const RemoteProcessConnection = configuration.ProcessConnection;