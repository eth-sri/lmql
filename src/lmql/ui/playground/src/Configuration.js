import { BrowserProcessConnection } from './browser_process';
import { RemoteProcessConnection as RemoteRemoteProcessConnection} from './remote_process';

const NEXT_MODE = window.location.host.includes("next") || window.location.hash.includes("is-next");

const BrowserProfile = {
    DEMO_MODE: true,
    BROWSER_MODE: true,
    DEV_MODE: true,
    NEXT_MODE: NEXT_MODE,
    ProcessConnection: BrowserProcessConnection
}

const RemoteProfile = {
    DEMO_MODE: true,
    BROWSER_MODE: false,
    DEV_MODE: true,
    NEXT_MODE: NEXT_MODE,
    ProcessConnection: RemoteRemoteProcessConnection
}

export let configuration = RemoteProfile;
let _is_local = true;
if (process.env.REACT_APP_WEB_BUILD) {
    configuration = BrowserProfile;
    _is_local = false;
}

export function isLocalMode() {
    return _is_local;
}

export const LMQLProcess = configuration.ProcessConnection.get("lmql");
export const RemoteProcessConnection = configuration.ProcessConnection;