export function reconstructTaggedModelResult(nodes) {
  if (nodes == null) {
    return []
  }

  let results = []

  for (let node of nodes) {
    if (node == null) {
      continue
    }

    // node is a cytoscape node
    // traverse tree in reverse until root is reached
    let n = node
    let text = []
    while (n != null) {
      if (!n.data("user_data.head.variable")) {
        return []
      }
      if (n.incomers().length > 0) {
        text.push({
          text: n.data("text"),
          variable: n.data("deterministic") ? "__prompt__" : n.data("user_data.head.variable"),
          pool: n.data("pool"),
        })
      }
      let next = n;
      next.incomers().forEach(p => {
        next = p
      })
      n = next;
      if (n.incomers().length == 0) {
        text.push({
          text: n.data("seqtext"),
          variable: "__prompt__",
          pool: "__prompt__"
        })
        break;
      }
    }
    // concat text in reverse
    let tokens = text.reverse()
    let current_variable = "__prompt__";
    let accumulated_text = ""
    let result = []

    tokens.forEach(t => {
      if (t.variable == null) {
        t.variable = current_variable
      }
      if (t.pool == null) {
        t.pool = ""
      }
      let v = t.variable
      if (v.includes(":before")) {
        v = "__prompt__"
      }

      if (v == "__done__" || t.text == "<|endoftext|>" || t.text == "</s>") {
        v = "<eos>"
        t.text = ""
      }

      if (v != current_variable) {
        result.push({ variable: current_variable, content: accumulated_text })
        accumulated_text = ""
      }
      current_variable = v
      accumulated_text += t.text
    })
    result.push({ variable: current_variable, content: accumulated_text })
    results.push({
      tokens: result,
      node: node
    })
  }
  return results;
}