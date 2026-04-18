import '../assets/css/ResumeInput.css';
import '../assets/css/global.css';
import { useState } from "react";
import { useNavigate } from "react-router-dom";

type FormData = {
    experience: string;
    education: string;
    skills: string;
};

export default function ResumeInput() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState<FormData>({
        experience: "",
        education: "",
        skills: ""
    });

    const [resumeFile, setResumeFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    }

    function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0] ?? null;
        setResumeFile(file);
    }

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setError("");

        const resumeText = [
            formData.experience && `Work Experience:\n${formData.experience}`,
            formData.education  && `Education:\n${formData.education}`,
            formData.skills     && `Skills:\n${formData.skills}`,
        ].filter(Boolean).join("\n\n");

        if (!resumeText.trim() && !resumeFile) {
            setError("Please fill in at least one field or upload a file.");
            return;
        }

        setLoading(true);
        try {
            let res;

            if (resumeFile && !resumeText.trim()) {
                if (resumeFile.name.toLowerCase().endsWith(".txt")) {
                    // Read txt as plain text and send as JSON
                    const txtText = await new Promise<string>((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target?.result as string);
                        reader.onerror = () => reject();
                        reader.readAsText(resumeFile);
                    });
                    res = await fetch("/skillapp/skill-match/", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ job_description: txtText }),
                    });
                } else {
                    // pdf/docx — send as multipart
                    const form = new FormData();
                    form.append("file", resumeFile);
                    res = await fetch("/skillapp/skill-match/", {
                        method: "POST",
                        body: form,
                    });
                }
            } else {
                // Text fields filled (with or without a file) — just use the text
                res = await fetch("/skillapp/skill-match/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ job_description: resumeText }),
                });
            }

            if (!res.ok) throw new Error("Resume analysis failed");
            const data = await res.json();
            sessionStorage.setItem("analyzedResume", JSON.stringify(data));
            navigate("/search");
        } catch (err) {
            setError("Failed to analyze resume. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="resume-input">
            <h1 className="title">Resume Entry</h1>

            <form className="resume-form" onSubmit={handleSubmit}>
                <label> Work Experience </label>
                <textarea
                    name="experience"
                    value={formData.experience}
                    onChange={handleChange}
                />

                <label> Education </label>
                <textarea
                    name="education"
                    value={formData.education}
                    onChange={handleChange}
                />

                <label> Additional Skills </label>
                <textarea
                    name="skills"
                    value={formData.skills}
                    onChange={handleChange}
                />

                <div className="upload-section">
                    <label className="upload-button">
                        Or: Upload Resume
                        <input
                            type="file"
                            accept=".pdf,.docx,.txt"
                            onChange={handleFileUpload}
                        />
                    </label>
                    {resumeFile && <span className="file-name">📄 {resumeFile.name}</span>}
                </div>

                {error && <p className="error-message">{error}</p>}

                <button className="submit-btn" type="submit" disabled={loading}>
                    {loading ? "Analyzing..." : "Submit Resume"}
                </button>
            </form>
        </div>
    );
}