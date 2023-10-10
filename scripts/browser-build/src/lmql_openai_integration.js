import {get_openai_secret} from "./openai_secret"

async function openai_completion_create(url, payload, data_callback) {
    // // turn payload Map into object
    // let payload_object = {}
    // payload.forEach((value, key) => {
    //     payload_object[key] = payload.get(key)
    // })
    // payload = payload_object;
    // let logit_bias = payload["logit_bias"]

    // // check if logit_bias is a Map
    // if (logit_bias != null && logit_bias instanceof Map) {
    //     // convert to dict
    //     let logit_bias_object = {}
    //     logit_bias.forEach((value, key) => {
    //         logit_bias_object[key] = logit_bias.get(key)
    //     })
    //     logit_bias = logit_bias_object;
    // }
    // payload["logit_bias"] = logit_bias

    // console.log(url, JSON.stringify(payload))

    // EventStream-based fetch for curl above
    const eventSource = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + get_openai_secret(),
        }, body: payload
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