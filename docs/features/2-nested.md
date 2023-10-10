---
title: Nested Queries bring Procedural Programming to Prompting
template: side-by-side
new: 0.7
---

LMQL now supports nested queries, enabling modularized local instructions and re-use of prompt components.

<br/>

<a class="btn" href="../guide/language/nestedqueries.html">
Learn more
</a>

%SPLIT%
```promptdown
# Execution Trace

![_|Q: When was Obama born?][@wait|200][@begin|incontext][dateformat|(respond in DD/MM/YYYY)][@end|incontext][@wait|200][ANSWER|04/08/1961][@wait|200][@fade|incontext][@wait|200][@hide|incontext][@wait|200]
![_|Q: When was Bruno Mars born?][@wait|200][@begin|incontext1][dateformat|(respond in DD/MM/YYYY)][@end|incontext1][@wait|200][ANSWER|08/10/1985][@wait|200][@fade|incontext1][@wait|200][@hide|incontext1][@wait|200]
![_|Q: When was Dua Lipa born?][@wait|200][@begin|incontext2][dateformat|(respond in DD/MM/YYYY)][@end|incontext2][@wait|200][ANSWER|22/08/1995][@wait|200][@fade|incontext2][@wait|200][@hide|incontext2][@wait|200]

[_|Out of these, who was born last?][LAST|Dua Lipa]
[:replay]
```