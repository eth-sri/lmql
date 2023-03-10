import { BrowserProcessConnection } from './browser_process';
import { RemoteProcessConnection as RemoteRemoteProcessConnection} from './remote_process';

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