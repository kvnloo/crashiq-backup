// Severity colours: one K/A/B/C/O ramp for every view (#108). Mirrors backend/crashiq/severity.py and the --sev-*
// tokens in styles/app.css (a backend test keeps the three identical). Validated with the dataviz validator on the
// dark surface: all pairs pass for normal and colour-blind vision. Warm to cool, so the worst reads first; O is a
// quiet grey. U (level not stated) is drawn HOLLOW: an outline in its grey, never a fill (HOLLOW below).
export const SEVERITY = { K: '#e62b34', A: '#fd811b', B: '#f6c330', C: '#5dacba', U: '#8e9aa6', O: '#686c71' }
export const SEVERITY_LABEL = { K: 'Fatal', A: 'Serious injury', B: 'Minor injury', C: 'Possible injury',
  U: 'Injury, level not stated', O: 'Property damage' }
export const HOLLOW = new Set(['U'])
