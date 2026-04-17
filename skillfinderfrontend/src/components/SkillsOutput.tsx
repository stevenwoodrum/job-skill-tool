import {useEffect, useState} from "react";
import ResultBox from "../components/ResultBox"
import "../assets/css/SkillMatching.css"

type SkillResults = {
    jobOverview: string
    skillsAnalysis: string
    nextSteps: string;
    skills?: any[];
}

type ComparisonResults = {
    threshold?: number;
    matched: any[];
    unmatched_job_skills: string[];
    unused_resume_skills?: string[];
    coverage?: number;
    nextSteps?: string;
}

function SkillsOutput() {

    const [jobResults, setJobResults] = useState<SkillResults>({
        jobOverview: "",
        skillsAnalysis: "",
        nextSteps: "",
        skills: []
    })

    const [results, setResults] = useState<ComparisonResults>({
        matched: [],
        unmatched_job_skills: []
    })

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const [job, setJob] = useState<any>(null);
    const [resumeResults, setResumeResults] = useState<any>(null);

    useEffect(() => {
        const jobString = sessionStorage.getItem("selectedJob");
        if (!jobString) {
            setError("No job selected for skill analysis");
            return;
        }

        const analyzedResumeString = sessionStorage.getItem("analyzedResume");
        if (!analyzedResumeString) {
            //setError("No analyzed resume data available");
            return;
        }
        setResumeResults(JSON.parse(analyzedResumeString));
        const fullJob = JSON.parse(jobString)
        setJob(fullJob.description || fullJob.title || "")
    }, [])


    useEffect(() => {
        if (!job) return;

        const fetchSkills = async () => {
            const start = performance.now()
            setLoading(true)
            setError("");
            try {
                const res = await fetch("/skillapp/skill-match/", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({job_description: job}),
                });

                if (!res.ok) throw new Error("Skill extraction failed");
                const data = await res.json();
                const end = performance.now()
                console.log("Total request time: ", ((end - start) / 1000).toFixed(2), "seconds");
                if (data.error) {
                    setJobResults({jobOverview: "error", skillsAnalysis: data.error, nextSteps: "error"})
                } else {
                    setJobResults(data);
                }
            } catch (err) {
                setError("Failed to extract skills. Please try again");
            } finally {
                setLoading(false);
            }
        };
        fetchSkills();
    }, [job]);

    useEffect(() => {
        if (!jobResults.skills || jobResults.skills.length === 0 || !resumeResults) return;

        const fetchMatch = async () => {
            const start = performance.now()
            setLoading(true)
            setError("");
            try {
                const res = await fetch("/skillapp/match-resume-job/", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({resume: [
                            {skills: resumeResults?.skills?.map((s: any) =>
                                typeof s === "string" ? {skill: s} : s
                                )}], job: [{
                        skills: jobResults?.skills
                        }]
                    }),})

                if (!res.ok) throw new Error("Skill matching failed");
                const data = await res.json();
                const end = performance.now()
                console.log("Total matching request time: ", ((end - start) / 1000).toFixed(2), "seconds");
                if (data.error) {
                    setResults({matched: ["error"], unmatched_job_skills: ["error"]})
                } else {
                    setResults(data);
                }
            } catch (err) {
                setError("Failed to extract skills. Please try again");
            } finally {
                setLoading(false);
            }
        };
        fetchMatch();
    }, [jobResults]);



    if (error) {
        return <div className="skills-output"><p>{error}</p></div>
    }


    return (
        <div className="skills-output">
            <h1 className="title">Skill Matching</h1>

            {/*loading*/loading && <p>Analyzing resume...</p>}

            <ResultBox
                title="Job Overview:"
                content={job}
                variant="light"
            />

            <div className="skills-row">
                <ResultBox
                    title="Resume Skills:"
                    content={resumeResults?.skills?.map((s: any, i: number) => (
                        <li key={i}>{s.skill}</li>))}
                    variant="medium"
                />

                <ResultBox
                    title="Job Skills:"
                    content={!loading && jobResults?.skills ? (
                        <ul>
                            {jobResults?.skills?.map((s: any, i) => (
                        <li key={i}>{s.skill}</li>))}
                        </ul>
                        ) : null
                    }
                    variant="medium"
                />
            </div>

            <ResultBox
                title="Missing Skills:"
                content={
                !loading && results.unmatched_job_skills ? (
                    results.unmatched_job_skills?.length ? (
                        <ul>
                            {results.unmatched_job_skills.map((skill, i) => (
                                <li key={i}>{skill}</li>
                            ))}
                        </ul>
                    ) : (
                        "no missing skills"
                    )
                ) : null
                }
                variant="medium"
            />

            <ResultBox
                title="Recommended Next Steps:"
                content={results.nextSteps}
                variant="dark"
            />
        </div>
    )
}

export default SkillsOutput;



/*useEffect(() => {
    setTimeout(() => {
        setResults({
            jobOverview: `
The role you are targeting is typically a Frontend or Full Stack Software Engineer position focused on building interactive web applications.

These roles generally require strong proficiency in JavaScript, experience with modern frontend frameworks such as React, and familiarity with backend technologies. Engineers in this role collaborate with designers and backend developers to deliver responsive and scalable user interfaces.

Many positions also value experience with REST APIs, Git workflows, testing frameworks, and deployment tools. In competitive markets, employers may also look for experience with cloud infrastructure or DevOps tools.
`,

            skillsAnalysis: `
Your resume shows several strengths that align well with modern web development roles:

• Strong JavaScript and frontend development experience
• Familiarity with React and component-based architecture
• Experience building interactive web applications

However, there are a few areas where your profile could be strengthened:

• Limited evidence of backend API development
• Minimal cloud or deployment experience
• Testing frameworks (Jest, Cypress) are not clearly listed
• DevOps tools like Docker or CI/CD pipelines are not mentioned

Overall, your profile aligns well with frontend-focused roles but could benefit from broader full-stack experience.
`,

            nextSteps: `
To improve your competitiveness for modern software engineering roles, consider focusing on the following areas:

1. **Backend Development**
Learn Node.js or another backend framework and build a small API-driven project.

2. **Cloud Platforms**
Gain familiarity with AWS, Azure, or Google Cloud. Even basic deployment experience is valuable.

3. **Testing**
Add automated testing to your projects using tools like Jest or Cypress.

4. **Portfolio Projects**
Build and showcase one or two full-stack applications that demonstrate both frontend and backend capabilities.

5. **DevOps Basics**
Explore Docker and CI/CD workflows to understand how applications are deployed and maintained in production environments.
`
        });
    }, 1500);
}, []);*/
