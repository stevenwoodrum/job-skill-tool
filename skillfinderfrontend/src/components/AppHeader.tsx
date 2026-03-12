import {Link} from 'react-router-dom';
import '../assets/css/AppHeader.css';
import '../assets/css/global.css';

function AppHeader() {



    return (

        <header className="container">
            <section className="title">
                <Link className="text-logo" to="/">SkillLens</Link>
            </section>
            <Link className="head-button" to="/resume-input">
                <h1>Resume Entry</h1>
            </Link>
            <Link className="head-button" to="/search">
                <h1>Job Search</h1>
            </Link>
        </header>
    )
}

export default AppHeader;