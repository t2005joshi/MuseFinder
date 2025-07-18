# MuseFinder

MuseFinder is a music search and analysis platform using AI for lyrics, vocal isolation, and more.

## Features

- Lyrics search and retrieval
- Vocal isolation
- Speech-to-text (multiple engines)
- Frontend for user interaction

## Setup

### Backend

1. Install Python dependencies:
   ```sh
   cd Backend
   pip install -r requirements.txt
   ```
2. Set up your `.env` file (see `Backend/.env.example`).

### Frontend

1. Install Node dependencies:
   ```sh
   cd frontend
   npm install
   ```
2. Set up your `.env` file (see `frontend/.env.example`).

## Running Locally

- Start backend:
  ```sh
  cd Backend
  python main.py
  ```
- Start frontend:
  ```sh
  cd frontend
  npm start
  ```

## Deployment

- Host frontend on Vercel/Netlify.
- Host backend on Render/Heroku.

## Environment Variables

- Copy `.env.example` to `.env` in both `Backend/` and `frontend/` and edit as needed.
- **Never commit `.env` files with secrets.**

## License

MIT

## Disclaimer

This project actively scrapes content from Google and Genius.com, which may violate their respective Terms of Service. This codebase was created strictly for educational and personal project purposes. The authors do not endorse or encourage misuse of this tool or violation of any platform's policies. Use at your own discretion and risk.
