import React from "react";
import { useNavigate } from "react-router-dom";

export interface JobResult {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
}

interface SearchResultProps {
  job: JobResult;
}


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
      </div>
      <div style={styles.companyCol}>
        <span style={styles.company}>{job.company}</span>
        <span style={styles.location}>{job.location}</span>
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
  },
  companyCol: {
    flex: "0 0 200px",
    display: "flex",
    flexDirection: "column",
    gap: 2,
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
  company: {
    fontWeight: 600,
    color: "white",
    fontSize: "0.9rem",
    fontFamily: "sans-serif",
  },
  location: {
    color: "#555",
    fontSize: "0.8rem",
    fontFamily: "sans-serif",
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
    transition: "background-color 0.15s",
  },
};

export default SearchResults;