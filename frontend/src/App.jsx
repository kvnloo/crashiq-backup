import { BrowserRouter, Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import TopBar from './components/TopBar'
import Rail from './components/Rail'
import { STEPS } from './steps'
import Placeholder from './screens/Placeholder'

const SCREENS = {
  setup: () => <Placeholder title="Setup" />,
  corridor: () => <Placeholder title="Corridor" />,
  profile: () => <Placeholder title="Crash profile" />,
  findings: () => <Placeholder title="Findings" />,
  export: () => <Placeholder title="Export" />,
}

function Shell() {
  const { studyId, step = 'setup' } = useParams()
  const current = Math.max(0, STEPS.findIndex((s) => s.key === step))
  return (
    <>
      <TopBar projectName={null} />
      <div className="app">
        <Rail studyId={studyId} current={current} />
        <main className="stage">
          <Outlet />
        </main>
      </div>
    </>
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
        <Route index element={SCREENS.setup()} />
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
