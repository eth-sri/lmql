import{_ as e,o as t,c as o,Q as n,k as s,a}from"./chunks/framework.4636910e.js";const k=JSON.parse('{"title":"Tool Augmentation","description":"","frontmatter":{},"headers":[],"relativePath":"docs/latest/language/tools.md","filePath":"docs/latest/language/tools.md"}'),l={name:"docs/latest/language/tools.md"},p=n("",4),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A simple math problem for addition (without solution, without words):
[MATH| 7 + 8 =] 15
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1516",text:"A","pd-insertion-point":"true"},[a(`A simple math problem for addition (without solution, without words):
`),s("span",{"pd-shadow-id":"1518","pd-instant":"false",text:"",class:"promptdown-var color-red"},[s("span",{"pd-shadow-id":"1519",text:"M",class:"promptdown-var-name"},"MATH"),a(" 7 + 8 =")]),a(` 15
`)])])],-1),i=n("",5),c=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?

Let's think step by step.
[REASON_OR_CALC|Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = <<] [EXPR|80,000 + (80,000*1.5) =] 200000.0>> 
[REASON_OR_CALC|The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = <<] [EXPR|200,000 - 80,000 - 50,000 =] 70000>> [REASON_OR_CALC| $70,000.
So the answer] is [RESULT|$70,000.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1525",text:"Q","pd-insertion-point":"true"},[a(`Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?

Let's think step by step.
`),s("span",{"pd-shadow-id":"1527","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1528",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a(`Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = <<`)]),a(),s("span",{"pd-shadow-id":"1533","pd-instant":"false",text:"",class:"promptdown-var color-yellow"},[s("span",{"pd-shadow-id":"1534",text:"E",class:"promptdown-var-name"},"EXPR"),a("80,000 + (80,000*1.5) =")]),a(` 200000.0>> 
`),s("span",{"pd-shadow-id":"1539","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1540",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a("The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = <<")]),a(),s("span",{"pd-shadow-id":"1545","pd-instant":"false",text:"",class:"promptdown-var color-yellow"},[s("span",{"pd-shadow-id":"1546",text:"E",class:"promptdown-var-name"},"EXPR"),a("200,000 - 80,000 - 50,000 =")]),a(" 70000>> "),s("span",{"pd-shadow-id":"1551","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1552",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a(` $70,000.
So the answer`)]),a(" is "),s("span",{"pd-shadow-id":"1557","pd-instant":"false",text:"",class:"promptdown-var color-orange"},[s("span",{"pd-shadow-id":"1558",text:"R",class:"promptdown-var-name"},"RESULT"),a("$70,000.")]),a(`
`)])])],-1),d=n("",5),h=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '[TERM| Norse]'.
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: [ANSWER|The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1564",text:"Q","pd-insertion-point":"true"},[a(`Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '`),s("span",{"pd-shadow-id":"1566","pd-instant":"false",text:"",class:"promptdown-var color-blue"},[s("span",{"pd-shadow-id":"1567",text:"T",class:"promptdown-var-name"},"TERM"),a(" Norse")]),a(`'.
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: `),s("span",{"pd-shadow-id":"1572","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1573",text:"A",class:"promptdown-var-name"},"ANSWER"),a("The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.")]),a(`
`)])])],-1),u=n("",2),m=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`# Model Output
(...)
A: Let's think step by step

[REASONING()| At the start of the game:
\`assign('Alice', 'black') # result] {Alice: 'black'}
[REASONING()| \`assign('Bob', 'brown') # result] {Bob: 'brown'}
[REASONING()| \`assign('Claire', 'blue') # result] {Claire: 'blue'}

[REASONING()| After Bob and Claire swap balls:
\`assign('Bob', 'blue') # result] {Bob: 'blue'}
[REASONING()| \`assign('Claire', 'brown') # result] {Claire: 'brown'}

[REASONING()| After Alice and Bob swap balls:
\`assign('Alice', 'blue') # result] {Alice: 'blue'}
[REASONING()| \`assign('Bob', 'black') # result] {Bob: 'black'}

[REASONING()| After Claire and Bob swap balls:
\`assign('Claire', 'black') # result] {Claire: 'black'}
[REASONING()| \`assign('Bob', 'brown') # result] {Bob: 'brown'}

[REASONING()| At the end of the game, Alice has a blue ball:
\`get('Alice') # result] blue\`
Therefore at the end of the game, Alice has the [OBJECT| blue ball.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("h1",{"pd-shadow-id":"1580",text:" "}," Model Output"),s("p",{"pd-shadow-id":"1582",text:"(","pd-insertion-point":"true"},[a(`(...)
A: Let's think step by step

`),s("span",{"pd-shadow-id":"1584","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1585",text:"R",class:"promptdown-var-name"},"REASONING"),a(" At the start of the game:\n`assign('Alice', 'black') # result")]),a(` {Alice: 'black'}
`),s("span",{"pd-shadow-id":"1590","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1591",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'brown') # result")]),a(` {Bob: 'brown'}
`),s("span",{"pd-shadow-id":"1596","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1597",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Claire', 'blue') # result")]),a(` {Claire: 'blue'}

`),s("span",{"pd-shadow-id":"1602","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1603",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Bob and Claire swap balls:\n`assign('Bob', 'blue') # result")]),a(` {Bob: 'blue'}
`),s("span",{"pd-shadow-id":"1608","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1609",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Claire', 'brown') # result")]),a(` {Claire: 'brown'}

`),s("span",{"pd-shadow-id":"1614","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1615",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Alice and Bob swap balls:\n`assign('Alice', 'blue') # result")]),a(` {Alice: 'blue'}
`),s("span",{"pd-shadow-id":"1620","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1621",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'black') # result")]),a(` {Bob: 'black'}

`),s("span",{"pd-shadow-id":"1626","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1627",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Claire and Bob swap balls:\n`assign('Claire', 'black') # result")]),a(` {Claire: 'black'}
`),s("span",{"pd-shadow-id":"1632","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1633",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'brown') # result")]),a(` {Bob: 'brown'}

`),s("span",{"pd-shadow-id":"1638","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1639",text:"R",class:"promptdown-var-name"},"REASONING"),a(" At the end of the game, Alice has a blue ball:\n`get('Alice') # result")]),a(" blue`\nTherefore at the end of the game, Alice has the "),s("span",{"pd-shadow-id":"1644","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1645",text:"O",class:"promptdown-var-name"},"OBJECT"),a(" blue ball.")]),a(`
`)])])],-1),w=s("p",null,[a("As shown in the example above, the "),s("code",null,"assign"),a(" and "),s("code",null,"get"),a(" functions can be used to store and retrieve values in a simple key-value store. The model is merely instructed to make use of these functions in its reasoning. The query then implements logic to intercept any function use and insert the result of the function call into the reasoning. This allows the model to incorporate the state of the key-value store into its reasoning.")],-1),g=[p,r,i,c,d,h,u,m,w];function b(f,j,y,_,A,q){return t(),o("div",null,g)}const N=e(l,[["render",b]]);export{k as __pageData,N as default};
