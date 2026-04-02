import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import FeedbackFooter from './components/FeedbackFooter'
import HomePage from './pages/HomePage'
import GuidePage from './pages/GuidePage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/guide" element={<GuidePage />} />
      </Routes>
      <FeedbackFooter />
    </BrowserRouter>
  )
}

export default App
