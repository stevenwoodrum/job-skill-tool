import {useEffect, useState} from "react";
import ResultBox from "../components/ResultBox"
import "../assets/css/SkillMatching.css"

type SkillResults = {
    jobOverview: string
    skillsAnalysis: string
    nextSteps: string
}

function SkillsOutput() {

    const [results, setResults] = useState<SkillResults>({
        jobOverview: "",
        skillsAnalysis: "",
        nextSteps: ""
    })

    const [loading, setLoading] = useState(false)

    // These will be implemented once the backend is set up, for now,
    // simulated useEffect will occur instead.
    async function fetchResults() {
        setLoading(true)

        const res = await fetch("/api/skill-match")
        const data = await res.json()

        setResults(data)
        setLoading(false)
    }

    /* useEffect(() => {
        fetchResults()
    }, [])
*/



    useEffect(() => {
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
    }, []);

    return (
        <div className="skills-output">
            <h1 className="title">Skill Matching</h1>

            {/*loading*/!results.jobOverview && <p>Analyzing resume...</p>}

            <ResultBox
                title="Job Overview:"
                content={results.jobOverview}
                variant="light"
            />

            <ResultBox
                title="Skills Analysis:"
                content={results.skillsAnalysis}
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