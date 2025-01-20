let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Add event listener when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded'); // Debug log
    
    const inputMethodSelect = document.getElementById('input-method');
    if (inputMethodSelect) {
        console.log('Found input method select'); // Debug log
        
        // Set initial state
        handleInputMethodChange();
        
        // Add change event listener
        inputMethodSelect.addEventListener('change', handleInputMethodChange);
    }
});

function handleInputMethodChange() {
    const inputMethod = document.getElementById('input-method');
    const uploadSection = document.getElementById('upload-section');
    const recordSection = document.getElementById('record-section');
    
    if (!inputMethod || !uploadSection || !recordSection) {
        console.error('Required elements not found');
        return;
    }
    
    const selectedMethod = inputMethod.value;
    console.log('Selected method:', selectedMethod); // Debug log
    
    if (selectedMethod === 'upload') {
        uploadSection.style.display = 'block';
        recordSection.style.display = 'none';
    } else if (selectedMethod === 'record') {
        uploadSection.style.display = 'none';
        recordSection.style.display = 'block';
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const preview = document.getElementById('recordingPreview');
            preview.src = audioUrl;
            preview.style.display = 'block';
            
            // Convert blob to base64 for form submission
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
                const base64data = reader.result;
                // Ensure we're sending the complete base64 string including the data URI prefix
                document.getElementById('recorded-audio-data').value = base64data;
                console.log('Audio data prepared for submission'); // Debug log
            };
        };
        
        mediaRecorder.start();
        isRecording = true;
        updateRecordingUI();
        startRecordingTimer();
        
    } catch (err) {
        console.error('Error starting recording:', err);
        alert('Error starting recording. Please make sure you have granted microphone permissions.');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;
        updateRecordingUI();
        stopRecordingTimer();
    }
}

function updateRecordingUI() {
    const startBtn = document.getElementById('startRecordBtn');
    const stopBtn = document.getElementById('stopRecordBtn');
    const recordingStatus = document.getElementById('recordingStatus');
    
    if (startBtn && stopBtn && recordingStatus) {
        startBtn.disabled = isRecording;
        stopBtn.disabled = !isRecording;
        recordingStatus.textContent = isRecording ? 'Recording...' : 'Not recording';
        recordingStatus.className = isRecording ? 'recording' : '';
    }
}

let timerInterval;
let recordingSeconds = 0;

function startRecordingTimer() {
    recordingSeconds = 0;
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        recordingSeconds++;
        updateTimerDisplay();
    }, 1000);
}

function stopRecordingTimer() {
    clearInterval(timerInterval);
}

function updateTimerDisplay() {
    const timerDisplay = document.getElementById('recordingTimer');
    if (timerDisplay) {
        const minutes = Math.floor(recordingSeconds / 60);
        const seconds = recordingSeconds % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
} 