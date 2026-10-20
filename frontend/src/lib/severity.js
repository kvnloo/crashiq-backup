// Severity colours: one K/A/B/C/O ramp for every view (#108). Mirrors backend/crashiq/severity.py and the --sev-*
// tokens in styles/app.css (a backend test keeps the three identical). Validated with the dataviz validator on the
// dark surface and on white: adjacent pairs pass for normal and colour-blind vision; U is a neutral "unknown".
export const SEVERITY = { K: '#d9003b', A: '#d37e01', B: '#666800', C: '#19a0b8', U: '#8e9aa6', O: '#6f57ab' }
export const SEVERITY_LABEL = { K: 'Fatal', A: 'Serious injury', B: 'Minor injury', C: 'Possible injury',
  U: 'Injury, level not stated', O: 'Property damage' }
