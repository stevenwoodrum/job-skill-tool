

type ResultBoxProps = {
    title: string
    content: React.ReactNode;
    variant?: "light" | "medium" | "dark"
}

export default function ResultBox({ title, content, variant = "light"}: ResultBoxProps) {
    return (
        <div className="result-section">
            <h2>{title}</h2>
            <div className={`result-box ${variant}`}>
                {content || "Waiting for analysis..."}
            </div>
        </div>
    )
}