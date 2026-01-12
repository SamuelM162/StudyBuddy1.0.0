# StudyBuddy – Flask + Firebase + Social App

Features:
- Firebase Auth (email/password)
- Student profiles (faculty, interests/subjects, tutor flag)
- Study matching (suggested connections by common subjects)
- Friend requests + friends list + messaging
- Tutoring offers + tutoring requests
- Ride sharing (create/join rides)
- Simple AI chatbot widget (placeholder logic)
- Dark/Light theme toggle (Bootstrap 5)
- Responsive layout usable on phone

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Edit `app/config.py` and put your real Firebase config (you already have it).  
Then:

```bash
python run.py
```

Open http://127.0.0.1:5000
