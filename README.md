RECALL AI 🎙️

Your Meetings. Your Lectures. Your Ideas. Never Miss a Detail.

RECALL AI is an AI-powered meeting and lecture copilot that transforms conversations and recordings into structured, searchable, and actionable knowledge.

Whether you're attending a university lecture, participating in a team meeting, conducting an interview, or recording a brainstorming session, RECALL AI helps you focus on the conversation instead of worrying about taking notes.

Record live conversations or upload existing audio recordings. RECALL AI transcribes speech, organizes important information, summarizes discussions, and extracts key decisions and action items — all through a single, intuitive workspace.

---

✨ Overview

Taking notes during a meeting or lecture often means choosing between actively listening and documenting everything being said.

RECALL AI aims to eliminate that trade-off.

It combines speech recognition and AI-powered information extraction to turn unstructured audio into useful, organized information.

The core idea is simple:

«Record once. Understand everything. Recall anything.»

🚀 Key Features

🎧 1. Live Recording & Transcription

- Record meetings and lectures directly through your browser.
- Capture microphone audio with start, pause, resume, and stop controls.
- View transcription progressively while the recording is in progress.
- Display timestamps alongside recognized speech.
- Support long-form recording sessions with session management.
- Retain the original recording for playback and download.
- Handle microphone permissions and recording errors gracefully.

📁 2. Audio File Upload

- Upload previously recorded meetings, lectures, interviews, and discussions.
- Support audio formats compatible with the transcription engine.
- Process recordings through an automated transcription pipeline.
- View the generated transcript in a dedicated workspace.
- Handle large recordings with appropriate upload limits and validation.

📝 3. Intelligent Transcription

- Convert speech into readable text using Whisper-based speech recognition.
- Automatically detect the spoken language where supported.
- Preserve timestamps for transcript segments.
- Process long recordings in manageable sections.
- Support transcription of conversations involving multiple people.
- Reconcile overlapping transcription windows to reduce duplicated text.

👥 4. Multi-Speaker Conversation Support

- Designed for meetings and conversations involving multiple participants.
- Support speaker identification and diarization as the capability is integrated.
- Organize conversation segments by speaker where identification is available.
- Make discussions easier to follow and review.

🧠 5. AI-Powered Smart Notes

Transform lengthy transcripts into structured notes.

RECALL AI is designed to generate:

- Executive Summary: A concise overview of the entire discussion.
- Key Points: Important information and concepts discussed.
- Action Items: Tasks, responsibilities, and follow-up activities.
- Decisions: Important conclusions and agreements.
- Topic-wise Sections: Organized content grouped by discussion topics.
- Revision Notes: Structured information useful for reviewing lectures and learning material.

📚 6. Dedicated Results Workspace

- View transcripts and generated notes together.
- Navigate timestamped transcript segments.
- Review summaries, decisions, and action items.
- Access information without repeatedly processing the original recording.
- Keep the experience organized and distraction-free.

🔊 7. Recording Playback

- Replay original audio recordings.
- Download recordings for offline access.
- Retain browser-local recordings independently of backend transcription.
- Use timestamps to navigate transcript content where supported.

📤 8. Export & Sharing

- Copy transcripts and generated notes.
- Download transcripts as ".txt" files.
- Export structured notes as ".md" files.
- Preserve transcript timestamps where available.
- Keep generated content accessible outside the application.

⚙️ 9. Reliable Processing

- Session-based processing for live recordings.
- Audio validation and upload-size limits.
- Controlled transcription concurrency.
- Temporary processing storage and cleanup.
- Error handling and retry support.
- Separation between audio capture, transcription, and notes generation.

---

🖥️ Product Workflow

RECALL AI follows a simple workflow:

1. Capture: Start a live recording or upload an existing audio file.
2. Transcribe: Convert speech into text using the speech recognition engine.
3. Organize: Process the transcript into structured information.
4. Understand: Generate summaries, key points, decisions, and action items.
5. Recall: Review, replay, copy, and export the information whenever needed.

---

🏗️ System Architecture

RECALL AI uses a modular frontend-backend architecture.

                  RECALL AI
                      |
          +-----------+-----------+
          |                       |
     LIVE RECORDING          FILE UPLOAD
          |                       |
     MediaRecorder             Audio File
          |                       |
          +-----------+-----------+
                      |
                FASTAPI BACKEND
                      |
             AUDIO PROCESSING
                      |
              FASTER-WHISPER
                      |
              TRANSCRIPTION
                      |
              FINAL TRANSCRIPT
                      |
             SMART NOTES ENGINE
                      |
       +--------------+--------------+
       |              |              |
    SUMMARY       KEY POINTS     ACTION ITEMS
       |              |              |
       +--------------+--------------+
                      |
               RESULTS WORKSPACE
                      |
           PLAYBACK / EXPORT / REVIEW

Technology Stack

Layer| Technology
Frontend Framework| Next.js
UI Library| React
Programming Language| TypeScript
Styling| Tailwind CSS
Backend Framework| FastAPI
Backend Language| Python
Speech Recognition| Faster-Whisper
Speech Recognition Model| Whisper
Audio Capture| Browser MediaRecorder API
API Communication| REST APIs
Data Validation| Pydantic
Transcription Processing| CPU-based inference with configurable model settings

The architecture is designed to support future improvements such as persistent session storage, speaker diarization, and more advanced language-model-powered note generation.

---

🧰 Project Structure

recall-ai/
│
├── frontend/
│   ├── public/
│   └── src/
│       └── app/
│           ├── page.tsx
│           ├── layout.tsx
│           ├── globals.css
│           ├── UploadWorkspace.tsx
│           ├── ResultsWorkspace.tsx
│           ├── ScrollVideo.tsx
│           └── scrollMapping.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── schemas/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── README.md
└── .gitignore

The structure above illustrates the intended organization; individual module names may evolve as development progresses.

---

⚡ Getting Started

Prerequisites

Make sure you have the following installed:

- Node.js (LTS recommended)
- npm
- Python 3.11+
- Git
- A working microphone for live recording

A compatible audio-processing environment is also required for Faster-Whisper.

1. Clone the Repository

git clone https://github.com/YOUR_USERNAME/recall-ai.git

cd recall-ai

2. Set Up the Backend

Navigate to the backend directory:

cd backend

Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Start the FastAPI server:

uvicorn app.main:app --reload --port 8001

The backend should be available at:

http://127.0.0.1:8001

API documentation:

http://127.0.0.1:8001/docs

3. Set Up the Frontend

Open another terminal:

cd frontend

Install dependencies:

npm install

Start the development server:

npm run dev -- --port 4552

Open RECALL AI:

http://localhost:4552

Note: The backend startup command assumes the application is exposed through "app.main:app". Adjust it if the repository uses a different entry point.

---

🔐 Privacy & Data Handling

RECALL AI is designed with user control and data minimization in mind.

- Microphone access is requested only when the user starts recording.
- Original live recordings can be retained locally in the browser.
- Audio is processed by the backend when transcription is requested.
- Temporary processing files should be removed after use or session expiry.
- Audio contents should not be unnecessarily written to application logs.
- Users should be informed about browser-local recording retention and the risk of losing unsaved recordings.
- Server-side audio retention and any future cloud storage must be explicitly documented.

Important: Browser-local recordings are not guaranteed to survive browser crashes, tab closure, or storage clearing unless durable persistence is implemented.

---

🛣️ Development Roadmap

RECALL AI is being developed incrementally, with reliability and usability prioritized over adding features prematurely.

Stage| Feature| Status
1| Project foundation and frontend/backend setup| Completed
2| Audio upload and transcription pipeline| Implemented
3| Smart notes generation| Implemented
4| Results workspace and transcript review| Implemented
5| Transcript and notes export| Implemented
6| UI/UX redesign and responsive workspace| Implemented
7| Browser-based live audio recording| In progress
8| Backend live-session management| Planned
9| Progressive live transcription| Planned
10| Final transcript reconciliation| Planned
11| Multi-speaker identification and diarization| Planned
12| Advanced AI-generated notes and insights| Planned
13| Production deployment and optimization| Planned

Status reflects the development roadmap and should be updated as each stage is tested and merged.

---

🔮 Future Possibilities

The long-term vision extends beyond basic transcription.

Potential future capabilities include:

- AI-powered conversational search across previous meetings.
- Ask questions about a meeting or lecture.
- Semantic search through transcripts and notes.
- Automatic lecture revision material.
- Flashcards and question generation.
- Meeting highlights and topic-based navigation.
- Speaker-wise conversation summaries.
- Multiple language support and translation.
- User accounts and synchronized recording libraries.
- Secure cloud-based storage and cross-device access.

These capabilities are part of the product vision, not promises of current availability.

---

🎯 Design Philosophy

RECALL AI is built around three principles:

1. Simplicity

Recording and reviewing information should not require a complicated workflow.

2. Clarity

Raw conversations should become structured, understandable information.

3. Control

Users should be able to access their recordings, transcripts, and notes without being locked into a complicated system.

The interface follows an editorial, minimal design direction with a focus on readability, thoughtful spacing, and a distraction-free workspace.

---

🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

If you want to contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test your implementation.
5. Submit a pull request with a clear description.

---

📄 License

A license has not yet been specified. Licensing terms will be added before public distribution.

---

👨‍💻 Author

Aarush Rastogi

B.Tech Computer Science Engineering | AI & ML

Interested in building practical AI applications that solve real-world problems.

---

<p align="center">RECALL AI

Listen less to the process. Remember more of the conversation.

</p>

