import React, { useState } from "react";
import SearchResult from "./SearchResults";
import { JobResult } from "../types/job";
import "../assets/css/search.css";

const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Internship"];
const LOCATIONS = ["Remote", "On-site"];

function Search() {
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<JobResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.ceil(total / 10);

  const triggerSearch = async (q: string, types: string[], locations: string[], page = 1) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.append("title", q.trim());
      types.forEach((t) => params.append("type", t));
      locations.forEach((l) => params.append("setting", l));
      params.append("page", String(page));

      const res = await fetch(`/api/jobs/search/?${params}`);
      if (!res.ok) throw new Error("Failed to fetch jobs");
      const data = await res.json();

      const mapped: JobResult[] = data.results.map((job: any) => ({
        id: job.job_id,
        title: job.title,
        company: job.company,
        location: job.location,
        description: job.description,
        employmentType: job.employment_type,
        workSetting: job.work_setting,
      }));

      setResults(mapped);
      setTotal(data.total);
      setCurrentPage(page);
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
      setSearched(true);
    }
  };

  const handleSearch = (page = 1) => triggerSearch(query, selectedTypes, selectedLocations, page);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch(1);
  };

  const toggleType = (value: string) => {
    const updated = selectedTypes.includes(value)
      ? selectedTypes.filter((v) => v !== value)
      : [...selectedTypes, value];
    setSelectedTypes(updated);
    if (searched) triggerSearch(query, updated, selectedLocations);
  };

  const toggleLocation = (value: string) => {
    const updated = selectedLocations.includes(value)
      ? selectedLocations.filter((v) => v !== value)
      : [...selectedLocations, value];
    setSelectedLocations(updated);
    if (searched) triggerSearch(query, selectedTypes, updated);
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
        <button className="search-btn" onClick={() => handleSearch(1)} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
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
                <button
                  key={type}
                  className={`filter-chip${selectedTypes.includes(type) ? " active" : ""}`}
                  onClick={() => toggleType(type)}
                >{type}</button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <span className="filter-label">Work Setting</span>
            <div className="filter-options">
              {LOCATIONS.map((loc) => (
                <button
                  key={loc}
                  className={`filter-chip${selectedLocations.includes(loc) ? " active" : ""}`}
                  onClick={() => toggleLocation(loc)}
                >{loc}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {error && <p className="no-results">{error}</p>}

      {searched && !loading && !error && (
        <div className="results-section">
          <h2 className="results-heading">
            Search Results: <span className="results-count">{total} jobs found</span>
          </h2>
          {results.length === 0
            ? <p className="no-results">No jobs matched your search. Try a different title or fewer filters.</p>
            : results.map((job) => <SearchResult key={job.id} job={job} />)
          }

          {total > 10 && (
            <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center", justifyContent: "center" }}>
              {currentPage > 1 && (
                <button className="filter-chip" onClick={() => handleSearch(currentPage - 1)}>← Prev</button>
              )}
              <span style={{ fontSize: 14 }}>Page {currentPage} of {totalPages}</span>
              {currentPage < totalPages && (
                <button className="filter-chip" onClick={() => handleSearch(currentPage + 1)}>Next →</button>
              )}
            </div>
          )}
        </div>
      )}

      {!searched && !loading && (
        <p className="search-prompt">Enter a job title and click "Search" to find relevant job postings.</p>
      )}
    </div>
  );
}

export default Search;
