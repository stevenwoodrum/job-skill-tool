import React from 'react';
import './assets/css/app.css';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate,
} from "react-router-dom"
import AppHeader from './components/AppHeader';
import ResumeInput from "./components/ResumeInput";
import Search from "./components/Search";
import SearchResults from "./components/SearchResults";
import SkillsOutput from "./components/SkillsOutput";
import AppFooter from "./components/AppFooter";
import Home from "./components/Home";


function App() {
  return (
      <Router basename = {"SkillLens"}>
          <main>
              <AppHeader />
              <Routes>
                  <Route path="/" element={<Home/>} />
                  <Route path="/resume-input" element={<ResumeInput/>} />
                  <Route path="/search" element={<Search/>} />
                  <Route path="/skills-output" element={<SkillsOutput/>} />
              </Routes>
              <AppFooter/>
          </main>
      </Router>
  );
}

export default App;
