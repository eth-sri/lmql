export function reconstructTaggedModelResult(nodes) {
  if (nodes == null) {
    return []
  }

  function unescapeBytes(s) {
    if (s.length == 1) {
      // unpack array
      if (s[0].startsWith && s[0].startsWith("bytes:")) {
        return [s[0].substring(6)]
      } else {
        return [s]
      }
    }
    return s
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
          text: unescapeBytes(n.data("text")),
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
        result.push({ variable: current_variable, content: accumulated_text})
        accumulated_text = ""
      }
      current_variable = v
      accumulated_text += t.text
    })
    result.push({ variable: current_variable, content: accumulated_text })

    result = chunk_by_tags(result)

    results.push({
      tokens: result,
      node: node
    })
  }
  return results;
}

function chunk_by_tags(s) {
  let current_tag = undefined;
  
  if (!s.reduce((a, b) => a || b.content.includes("<lmql:"), true)) {
    return s
  }

  return s.flatMap(s => {
    let results = []
    let current_segment = ""
    let content = s.content
    let i = 0
    while (i < content.length) {
      if (content.substr(i).startsWith("<lmql:")) {
        if (current_segment.length > 0) {
          results.push({ variable: s.variable, content: current_segment, tag: current_tag })
        }
        current_segment = ""
        let start = i
        while (i < content.length && !content.substr(i).startsWith("/>")) {
          i++
        }
        i += 2
        let tag = content.substr(start, i - start)
        results.push({ variable: "__tag__", content: tag, tag: null })
        current_tag = tag.replace("<lmql:", "").replace("/>", "").trim()
        continue
      }
      current_segment += content[i]
      i++
    }
    results.push({ variable: s.variable, content: current_segment, tag: current_tag })
    return results
  })
}