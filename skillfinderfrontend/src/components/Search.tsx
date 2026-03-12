import React, { useState } from "react";
import SearchResult, { JobResult } from "./SearchResults";
import "../assets/css/search.css";

const MOCK_JOBS: JobResult[] = [
  { id: "1", title: "Frontend Developer", company: "Amazon", location: "New York, NY (Remote)", description: "Build and maintain React-based web applications with a focus on performance and accessibility." },
  { id: "2", title: "Full Stack Engineer", company: "IBM", location: "Austin, TX (Hybrid)", description: "Work across the stack using Node.js and React. Collaborate with cross-functional teams to ship features." },
  { id: "3", title: "UI/UX Developer", company: "DesignHub", location: "Remote", description: "Create beautiful, responsive interfaces. Strong eye for design and proficiency in CSS and Figma required." },
  { id: "4", title: "Software Engineer", company: "CloudBase", location: "San Francisco, CA", description: "Join our platform team to build scalable microservices and improve developer tooling." },
  { id: "5", title: "React Developer", company: "StartupXYZ", location: "Chicago, IL (Remote)", description: "Own the frontend of our SaaS product. You'll work closely with design and backend teams." },
];

const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Internship"];
const LOCATIONS = ["Remote", "Hybrid", "On-site"];

function Search() {
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<JobResult[]>([]);

  const toggleFilter = (value: string, list: string[], setter: React.Dispatch<React.SetStateAction<string[]>>) => {
    setter(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  };

  const handleSearch = () => {
    const filtered = MOCK_JOBS.filter((job) =>
      query.trim() === "" || job.title.toLowerCase().includes(query.toLowerCase())
    );
    setResults(filtered);
    setSearched(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="search-page">
      <h1 className="search-heading">Job Search</h1>
      <p className="search-sublabel">Search by job title</p>

      <div className="search-bar-wrapper">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Software Engineer"
          className="search-input"
        />
        <button className="search-btn" onClick={handleSearch}>Search</button>
        <button className="filter-toggle" onClick={() => setShowFilters(!showFilters)}>
          Additional Filters {showFilters ? "▲" : "▼"}
        </button>
      </div>

      {showFilters && (
        <div className="filters-box">
          <div className="filter-group">
            <span className="filter-label">Employment Type</span>
            <div className="filter-options">
              {EMPLOYMENT_TYPES.map((type) => (
                <button key={type} className={`filter-chip${selectedTypes.includes(type) ? " active" : ""}`}
                  onClick={() => toggleFilter(type, selectedTypes, setSelectedTypes)}>{type}</button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <span className="filter-label">Work Setting</span>
            <div className="filter-options">
              {LOCATIONS.map((loc) => (
                <button key={loc} className={`filter-chip${selectedLocations.includes(loc) ? " active" : ""}`}
                  onClick={() => toggleFilter(loc, selectedLocations, setSelectedLocations)}>{loc}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {searched && (
        <div className="results-section">
          <h2 className="results-heading">
            Search Results: <span className="results-count">{results.length} job{results.length !== 1 ? "s" : ""} found</span>
          </h2>
          {results.length === 0
            ? <p className="no-results">No jobs matched your search. Try a different title.</p>
            : results.map((job) => <SearchResult key={job.id} job={job} />)
          }
        </div>
      )}

      {!searched && <p className="search-prompt">Enter a job title and click "Search" to find relevant job postings.</p>}
    </div>
  );
}

export default Search;