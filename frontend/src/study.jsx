import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './lib/api'

// The open study, shared by the header, rail and every step screen.
const StudyCtx = createContext({ study: null, setStudy: () => {}, reload: () => {}, error: null })

export function StudyProvider({ studyId, children }) {
  const [state, setState] = useState({ id: null, study: null, error: null })

  const load = useCallback(async (id, isAlive = () => true) => {
    try {
      const s = await api(`/studies/${id}`)
      if (isAlive()) setState({ id, study: s, error: null })
    } catch (e) {
      if (isAlive()) setState({ id, study: null, error: e })
    }
  }, [])

  useEffect(() => {
    if (!studyId) return undefined
    let alive = true
    api(`/studies/${studyId}`)
      .then((s) => { if (alive) setState({ id: studyId, study: s, error: null }) })
      .catch((e) => { if (alive) setState({ id: studyId, study: null, error: e }) })
    return () => { alive = false }
  }, [studyId])

  const current = state.id === studyId ? state : { study: null, error: null }
  const value = {
    study: studyId ? current.study : null,
    error: studyId ? current.error : null,
    setStudy: (s) => setState({ id: s?.id ?? null, study: s, error: null }),
    reload: () => (studyId ? load(studyId) : Promise.resolve()),
  }
  return <StudyCtx.Provider value={value}>{children}</StudyCtx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useStudy = () => useContext(StudyCtx)
