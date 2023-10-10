function mapToObject(v) {
    if (!(v instanceof Map)) {
        return v;
    }
    // turn payload Map into object
    let o = {}
    payload.forEach((value, key) => {
        o[key] = mapToObject(value)
    })
    return o
}

async function fetch_bridge(url, payload, data_callback) {
    // convert Map to object
    payload = mapToObject(payload)

    // EventStream-based fetch for curl above
    try {
        const request = await fetch(url, payload)
        const text = await request.text()
        return [false, text]
    } catch (e) {
        return [true, e]
    }
}

self.fetch_bridge = fetch_bridge