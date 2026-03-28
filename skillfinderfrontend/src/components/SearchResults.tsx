import React from "react";
import { useNavigate } from "react-router-dom";
import { JobResult } from "../types/job";

interface SearchResultProps {
  job: JobResult;
}

const SETTING_COLORS: Record<string, string> = {
  Remote: "#1D9E75",
  Hybrid: "#185FA5",
  "On-site": "#888780",
};

const SearchResults: React.FC<SearchResultProps> = ({ job }) => {
  const navigate = useNavigate();

  const handleCheckSkills = () => {
    sessionStorage.setItem("selectedJob", JSON.stringify(job));
    navigate("/skills-output");
  };

  return (
    <div style={styles.row}>
      <div style={styles.titleCol}>
        <span style={styles.jobTitle}>{job.title}</span>
        <span style={styles.employmentType}>{job.employmentType}</span>
      </div>
      <div style={styles.companyCol}>
        <span style={styles.company}>{job.company}</span>
        <span style={styles.location}>{job.location}</span>
        <span style={{ ...styles.badge, backgroundColor: SETTING_COLORS[job.workSetting] ?? "#888" }}>
          {job.workSetting}
        </span>
      </div>
      <div style={styles.descCol}>
        <span style={styles.description}>{job.description}</span>
      </div>
      <div style={styles.btnCol}>
        <button style={styles.checkBtn} onClick={handleCheckSkills}>
          Check Skills
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  row: {
    display: "flex",
    alignItems: "center",
    backgroundColor: "#a8a8e8",
    borderRadius: 8,
    padding: "14px 16px",
    gap: 16,
    marginBottom: 10,
  },
  titleCol: {
    flex: "0 0 140px",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  companyCol: {
    flex: "0 0 200px",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  descCol: {
    flex: 1,
    overflow: "hidden",
  },
  btnCol: {
    flex: "0 0 auto",
  },
  jobTitle: {
    fontWeight: 700,
    color: "white",
    fontSize: "0.95rem",
    fontFamily: "sans-serif",
  },
  employmentType: {
    fontSize: "0.75rem",
    color: "white",
    fontFamily: "sans-serif",
    opacity: 0.85,
  },
  company: {
    fontWeight: 600,
    color: "white",
    fontSize: "0.9rem",
    fontFamily: "sans-serif",
  },
  location: {
    color: "#333",
    fontSize: "0.8rem",
    fontFamily: "sans-serif",
  },
  badge: {
    display: "inline-block",
    color: "white",
    fontSize: "0.7rem",
    fontFamily: "sans-serif",
    fontWeight: 600,
    padding: "2px 8px",
    borderRadius: 4,
    width: "fit-content",
  },
  description: {
    color: "white",
    fontSize: "0.85rem",
    fontFamily: "sans-serif",
    fontWeight: 600,
    display: "-webkit-box",
    WebkitLineClamp: 2,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  },
  checkBtn: {
    backgroundColor: "#fff",
    border: "2px solid #333",
    borderRadius: 6,
    padding: "8px 14px",
    fontWeight: 700,
    fontSize: "0.85rem",
    cursor: "pointer",
    color: "#111",
    fontFamily: "sans-serif",
    whiteSpace: "nowrap",
  },
};

export default SearchResults;