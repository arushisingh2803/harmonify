# Harmonify

Harmonify is a web application that provides Spotify users with personalized insights into their listening habits, connects them with like-minded music enthusiasts, and enables engaging concert-focused social interactions. It combines music analytics, user profiling, and social features to enhance the music discovery experience.
This is for my Final Year Project. This repository is used for version control and viewing overall progress goals. It is currently still work in progress and is being developed 

## Key Features
- **Music Persona**
  - Analyses Spotify listening history, top tracks and artists and generates a detailed music persona(classifies user) using Machine Learning(K-Means Clustering)
  - Visualises features such as energy and mood
- **Track and Artsts**
  - Displays the user's most listened tracks and artists
  - Allows insights over different time ranges( last 4 weeks, 6 months, all time)
- C**oncert Discovery**
  - Suggests upcoming concerts based on the user's top artsts
  - Chat rooms with other concertgoes can be joined to discuss shows, artsts and preferences
- **Similar Users Discovery**
   - Based on the user's persona - similar profiles are displayed and a match percentage is displayed
   - Can view profile and spotify profile through the application

## Technology Stack
- Frontend: React.js, TypeScript, Tailwind CSS, React Router
- Backend: Django, Django REST Framework, Django Channels
- API Dependencies - Spotify API, Ticketmaster API, iTunes API, Librosa Library
- Machine Learning: Python, scikit-learn (KMeans, StandardScaler), NumPy
- Database: Django ORM, MySQL
- Authentication: Spotify OAuth2
- Deployment: Daphne + ASGI for WebSocket support for local use + Further deployment pending

