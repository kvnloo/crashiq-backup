import { BrowserRouter, Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import TopBar from './components/TopBar'
import Rail from './components/Rail'
import { STEPS } from './steps'
import { StudyProvider, useStudy } from './study'
import Setup from './screens/Setup'
import Corridor from './screens/Corridor'
import Profile from './screens/Profile'
import Findings from './screens/Findings'
import Export from './screens/Export'

const SCREENS = {
  setup: Setup,
  corridor: Corridor,
  profile: Profile,
  findings: Findings,
  export: Export,
}

// Furthest step with data: corridor drawn → Corridor; crashes pulled → Profile (Findings is optional).
function reachedStep(study) {
  if (study?.progress?.crashes) return 3
  if (study?.progress?.corridor) return 1
  return 0
}

function Frame() {
  const { studyId, step = 'setup' } = useParams()
  const { study, error } = useStudy()
  const current = Math.max(0, STEPS.findIndex((s) => s.key === step))
  if (studyId && error?.status === 404) return <Navigate to="/" replace />
  return (
    <>
      <TopBar projectName={study?.name} />
      <div className="app">
        <Rail studyId={studyId} current={current} reached={reachedStep(study)} />
        <main className="stage">
          <Outlet />
        </main>
      </div>
    </>
  )
}

function Shell() {
  const { studyId, step } = useParams()
  return (
    <StudyProvider studyId={studyId} refreshKey={step}>
      <Frame />
    </StudyProvider>
  )
}

function StepScreen() {
  const { step } = useParams()
  const Screen = SCREENS[step]
  return Screen ? <Screen /> : <Navigate to="/" replace />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Setup />} />
        <Route path="s/:studyId/:step" element={<StepScreen />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
