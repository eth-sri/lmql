import {get_openai_secret} from "./openai_secret"

async function openai_completion_create(payload, data_callback) {
    // turn payload Map into object
    let payload_object = {}
    payload.forEach((value, key) => {
        payload_object[key] = payload.get(key)
    })
    payload = payload_object;
    let logit_bias = payload["logit_bias"]

    // check if logit_bias is a Map
    if (logit_bias != null && logit_bias instanceof Map) {
        // convert to dict
        let logit_bias_object = {}
        logit_bias.forEach((value, key) => {
            logit_bias_object[key] = logit_bias.get(key)
        })
        logit_bias = logit_bias_object;
    }
    payload["logit_bias"] = logit_bias

    // EventStream-based fetch for curl above
    const eventSource = await fetch("https://api.openai.com/v1/completions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + get_openai_secret(),
        }, body: JSON.stringify(payload)
    })

    const reader = eventSource.body.getReader();
    const textDecoder = new TextDecoder("utf-8");
    let res = "<start>"

    while (res == "<start>" || !res.done) {
        res = await reader.read()
        let payload = textDecoder.decode(res.value);
        await data_callback(false, payload)
    }
    await data_callback(true, null)
}

self.openai_completion_create = openai_completion_create