import styled from 'styled-components'

export const DataListView = styled.div`
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: auto;

  h3 {
    margin: 0;
    font-size: 10pt;
    text-transform: uppercase;
    color: #c0bfbf;
    padding: 0pt;
    margin-right: 5pt;
  }

  h4 {
    margin: 0;
    font-size: 8pt;
    text-transform: uppercase;
    color: #948e8e;
    padding: 2pt 0pt;
    /* inline */
    margin-right: 5pt;
    text-align: left;
  }

  /* vertical align of table cell top */
  table tr td:nth-child(2) {
    vertical-align: top;
    padding: 0;
    margin: 0;
  }

  table tr td.value {
    font-family: monospace;
    background-color: black;
    display: inline-block;
    border-radius: 2pt;
    padding: 2pt;
    /* break lines anywhere */
    word-break: break-all;
  }

  /* first column width */
  table tr td:first-child {
    width: 50pt;
  }

  table tr {
    font-size: 10pt;
  }

  table tr:nth-child(odd).header {
    background-color: transparent;
  }

  .textview {
    font-family: monospace;
    background-color: black;
    border-radius: 2pt;
    padding: 2pt;
    flex: 1;

    white-space: pre-wrap;
  }
`