import { BrowserRouter, Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import TopBar from './components/TopBar'
import Rail from './components/Rail'
import { STEPS } from './steps'
import { StudyProvider, useStudy } from './study'
import Placeholder from './screens/Placeholder'
import Setup from './screens/Setup'

const SCREENS = {
  setup: Setup,
  corridor: () => <Placeholder title="Corridor" />,
  profile: () => <Placeholder title="Crash profile" />,
  findings: () => <Placeholder title="Findings" />,
  export: () => <Placeholder title="Export" />,
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
        <Rail studyId={studyId} current={current} />
        <main className="stage">
          <Outlet />
        </main>
      </div>
    </>
  )
}

function Shell() {
  const { studyId } = useParams()
  return (
    <StudyProvider studyId={studyId}>
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
