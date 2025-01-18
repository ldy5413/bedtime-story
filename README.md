# Story Generator with Text-to-Speech

A Flask web application that generates stories and provides text-to-speech functionality using multiple TTS services.

## Features

- Story generation with AI
- Multiple TTS services:
  - Google Text-to-Speech (gTTS)
  - F5 Text-to-Speech
- User authentication system
- Voice profile management
- Audio streaming
- Database integration for story storage

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/story-generator.git
cd story-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp config_template.py config.py
```
Edit config.py with your API keys and settings

4. Initialize the database:
```bash
python scripts/migrate_db.py
```

## Running the Application

Start the development server:
```bash
python run.py
```

The application will be available at http://localhost:5000

## Project Structure

```
story-generator/
├── app/                  # Main application package
│   ├── auth/             # Authentication module
│   ├── db/               # Database operations
│   ├── story/            # Story generation logic
│   ├── tts/              # Text-to-speech services
│   ├── utils/            # Utility functions
│   └── static/           # Static files (CSS, JS, images)
├── scripts/              # Database management scripts
├── voice_profiles/       # Voice profile assets
├── config_template.py    # Configuration template
├── requirements.txt      # Python dependencies
└── run.py                # Application entry point
```

## Configuration

Edit `config.py` to set up:

- Database path
- API keys
- TTS service preferences
- Application settings

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
