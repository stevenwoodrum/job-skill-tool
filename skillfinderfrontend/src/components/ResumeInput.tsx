import '../assets/css/ResumeInput.css';
import '../assets/css/global.css';
import { useState } from "react";

export default function ResumeInput() {

    type FormData = {
        experience: string,
        education: string,
        skills: string
    }

    const [formData, setFormData] = useState<FormData>({
        experience: "",
        education: "",
        skills:""
    })

    const [resumeFile, setResumeFile] = useState<File | null>(null);

    function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
        const { name, value} = e.target;

        setFormData({
            ...formData,
            [name]: value
        });
    }

    function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0] ?? null;
        setResumeFile(file);
    }

    function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();

        console.log("Form Data:", formData);
        console.log("Uploaded File:", resumeFile);
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
                            accept=".pdf,.doc,.docx"
                            onChange={handleFileUpload}
                        />
                    </label>
                </div>
                <button className="submit-btn" type="submit">
                    Submit Resume
                </button>
            </form>
        </div>
    )
}
