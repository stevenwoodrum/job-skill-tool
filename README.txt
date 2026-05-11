Do not run this Django project in a production environment. Development only.

SETUP:

Clone the repository on another computer, install Node.js, create a venv and then run
pip install -r 'requirements.txt'
and it will install all the dependencies for the cloned repository.

Also install:
- Python 3.x
- Node.js v25.7.0+
- npm v11.10.1+

Database setup:
1. Create a .env file in the project root with:
DB_PASSWORD=<ask team for password>

Database Access (Read-Only):
The database is hosted on Supabase with read-only access available.
Connection string:
postgresql://readonly:Team4pasVT@db.jkpuckqoppeukeebqnvq.supabase.co:5432/postgres

2. Run migrations:
python manage.py migrate

VT LLM setup:
1. Must be connected to the VT VPN (you can use Cisco AnyConnect)
2. Get your own API key from: https://docs.arc.vt.edu/ai/011_llm_api_arc_vt_edu.html
3. In skillapp/services/llm_skill.py, set:
   API_KEY = "your_key_here"

RUN APP:

python manage.py runserver
cd skillfinderfrontend
npm install (first time)
npm start
Web browser to http://localhost:3000/SkillLens

--------------
OTHER:

Django admin:
Web browser to http://127.0.0.1:8000/admin/ (admin page) or http://127.0.0.1:8000/skillapp/ (home page).

Data:
The job listings dataset (LinkedIn Job Postings 2023-2024, Kaggle) was 
preprocessed using scripts/preprocess.py and loaded into Supabase using
python manage.py load_jobs. 
CSVs are not included due to file size. 
Database is already hosted on Supabase, no reloading needed.

To train/evaluate model:
See README in 'analysis' folder.

